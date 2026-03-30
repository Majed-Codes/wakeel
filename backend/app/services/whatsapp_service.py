"""
WhatsApp Business Service — Twilio integration for Wakeel AI.

Handles:
- Incoming messages (text, audio, image) via Twilio webhook
- Text → Financial RAG query or transaction creation
- Audio → Transcription → Entity extraction → Transaction
- Image → Receipt OCR → Transaction
- Weekly summary delivery

Setup:
- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER in .env
- Twilio webhook URL: POST /api/v1/whatsapp/webhook
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.transaction import Transaction, TransactionType, TransactionSource

logger = logging.getLogger(__name__)

# Try Twilio import
try:
    from twilio.rest import Client as TwilioClient
    from twilio.request_validator import RequestValidator
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio not installed — WhatsApp service in mock mode")


class WhatsAppService:
    """Manages WhatsApp Business messaging via Twilio."""

    # Conversation memory settings
    _CONVERSATION_TTL: int = 7200       # 2 hours of inactivity → session cleared
    _MAX_HISTORY_PAIRS: int = 10        # Keep last 10 user/assistant pairs (20 turns)

    def __init__(self):
        self._client: Optional[object] = None
        self._validator: Optional[object] = None

        # In-memory conversation store: {phone: {"messages": [...], "last_active": ts}}
        # Each message: {"role": "user"|"assistant", "content": str}
        self._conversations: Dict[str, Dict[str, Any]] = {}

        if TWILIO_AVAILABLE and settings.has_twilio:
            self._client = TwilioClient(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN,
            )
            self._validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
            logger.info("WhatsApp service: using Twilio")
        else:
            logger.info("WhatsApp service: mock mode (no Twilio credentials)")

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    # ── Conversation memory helpers ──────────────────────────────────────────

    def _get_history(self, phone: str) -> List[Dict[str, str]]:
        """
        Return conversation history for this phone number.
        Returns [] if no session or session expired (TTL exceeded).
        """
        session = self._conversations.get(phone)
        if not session:
            return []
        if time.time() - session["last_active"] > self._CONVERSATION_TTL:
            del self._conversations[phone]
            logger.info(f"Conversation session expired for {phone}")
            return []
        return list(session["messages"])

    def _save_turns(self, phone: str, user_msg: str, assistant_msg: str) -> None:
        """
        Append a user+assistant turn to conversation history.
        Trims to _MAX_HISTORY_PAIRS (oldest turns dropped first).
        """
        if phone not in self._conversations:
            self._conversations[phone] = {"messages": [], "last_active": time.time()}

        session = self._conversations[phone]
        session["messages"].append({"role": "user", "content": user_msg})
        session["messages"].append({"role": "assistant", "content": assistant_msg})
        session["last_active"] = time.time()

        # Keep only the most recent N pairs
        max_msgs = self._MAX_HISTORY_PAIRS * 2
        if len(session["messages"]) > max_msgs:
            session["messages"] = session["messages"][-max_msgs:]
            logger.debug(f"Trimmed conversation history for {phone} to {max_msgs} messages")

    def _clear_history(self, phone: str) -> None:
        """Explicitly clear a phone's conversation history (e.g. user says 'ابدأ من جديد')."""
        self._conversations.pop(phone, None)

    async def handle_message(
        self,
        from_number: str,
        message_type: str,
        content: str,
        media_url: Optional[str] = None,
        business_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> str:
        """
        Process an incoming WhatsApp message.

        Args:
            from_number: Sender's phone number (e.g., whatsapp:+966501234567)
            message_type: "text" | "audio" | "image"
            content: Message body (for text) or transcription (for audio)
            media_url: URL to media file (for audio/image)
            business_id: Associated business (looked up from phone number)
            db: Database session

        Returns:
            str: Reply message in Arabic
        """
        # Normalise phone to a clean key for conversation memory
        phone_key = from_number.replace("whatsapp:", "").strip()
        logger.info(f"WhatsApp message from {phone_key}: type={message_type}")

        # User can reset session with keywords
        if message_type == "text" and content.strip() in ("ابدأ من جديد", "reset", "مسح", "clear"):
            self._clear_history(phone_key)
            return "تمام! بدأنا من جديد. كيف أقدر أساعدك؟ 🔄"

        if message_type == "text":
            return await self._handle_text(content, business_id, db, phone_key)
        elif message_type == "audio":
            return await self._handle_audio(media_url, business_id, db, phone_key)
        elif message_type == "image":
            return await self._handle_image(media_url, business_id, db)
        else:
            return "نوع الرسالة غير مدعوم. أرسل نصاً أو صوتاً أو صورة إيصال."

    async def _handle_text(
        self,
        text: str,
        business_id: Optional[int],
        db: Optional[Session],
        phone_key: str = "",
    ) -> str:
        """Handle text messages — pass everything through Claude AI for intelligent response."""
        if not text:
            return "الرسالة فارغة. كيف يمكنني مساعدتك؟"
        return await self._ai_respond(text, business_id, db, phone_key)

    # Financial keywords that signal a transaction (used for fallback detection)
    _FINANCIAL_KEYWORDS = (
        "دفعت", "حولت", "صرفت", "اشتريت", "بعت", "استلمت", "دفع", "تحويل",
        "فاتورة", "راتب", "إيجار", "كهرباء", "ماء", "صيانة", "مبيعات",
        "ريال", "ر.س", "ألف", "مئة", "مليون", "شريت", "بعث", "أرسلت",
    )

    async def _ai_respond(
        self,
        text: str,
        business_id: Optional[int],
        db: Optional[Session],
        phone_key: str = "",
    ) -> str:
        """
        Use Claude to understand the message (with conversation memory),
        optionally save a transaction, and reply in Saudi Arabic.

        Protocol:
        - Transactions → Claude returns TRANSACTION:{json} then MESSAGE: reply
        - Queries/chat  → Claude returns plain Arabic text (no TRANSACTION:)
        - Memory        → last _MAX_HISTORY_PAIRS exchanges passed as multi-turn
        - Fallback      → entity_extractor if financial keywords detected but
                          Claude returned plain text
        """
        import json as _json

        try:
            if not settings.has_anthropic_key:
                return await self._fallback_respond(text, business_id, db)

            from anthropic import Anthropic
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            # Build recent-transactions context (last 5) — goes in system prompt
            business_context = ""
            if business_id and db:
                try:
                    recent = (
                        db.query(Transaction)
                        .filter(Transaction.business_id == business_id)
                        .order_by(Transaction.date.desc())
                        .limit(5)
                        .all()
                    )
                    if recent:
                        lines = [
                            f"- {t.vendor}: {float(t.amount):,.0f} ر.س ({t.category})"
                            for t in recent
                        ]
                        business_context = "\n\n[آخر معاملاتك]\n" + "\n".join(lines)
                except Exception:
                    pass

            system_prompt = (
                "أنت وكيل، مساعد مالي ذكي للمنشآت السعودية الصغيرة والمتوسطة.\n"
                "تتحدث باللهجة السعودية العامية وتفهمها جيداً.\n"
                "لديك ذاكرة للمحادثة — تذكّر ما قيل قبلاً في نفس الجلسة.\n"
                "ردودك قصيرة ومباشرة. لا تستخدم markdown أو جداول أو نجوم أو تنسيق خاص.\n\n"
                "===== قاعدة مهمة جداً =====\n"
                "إذا كانت الرسالة تذكر أي معاملة مالية (دفع، شراء، صرف، استلام، تحويل،\n"
                "حولت، دفعت، اشتريت، صرفت، بعت، استلمت، راتب، فاتورة، إيجار...):\n"
                "يجب أن يبدأ ردك بـ TRANSACTION: متبوعاً مباشرةً بـ JSON بدون مسافة،\n"
                "ثم في السطر التالي MESSAGE: ثم ردك.\n\n"
                "مثال 1 — مصروف:\n"
                'TRANSACTION:{"amount":500,"vendor":"المراعي","category":"تشغيلية","description":"حليب","type":"expense"}\n'
                "MESSAGE: تم! سجلت 500 ريال للمراعي 👍\n\n"
                "مثال 2 — إيراد:\n"
                'TRANSACTION:{"amount":3000,"vendor":"أبو محمد","category":"إيرادات","description":"دفعة من عميل","type":"revenue"}\n'
                "MESSAGE: ممتاز! استلمت 3000 ريال من أبو محمد 💰\n\n"
                "مثال 3 — سؤال (لا معاملة):\n"
                "إيراداتك هذا الأسبوع 67,000 ريال. المصاريف 12,000 ريال.\n\n"
                "التصنيف: تشغيلية=رواتب/إيجار/كهرباء/مشتريات يومية، رأسمالية=معدات/أجهزة، إيرادات=مبيعات/تحصيل\n"
                "النوع في JSON: expense للمصروفات والتكاليف، revenue للإيرادات والمبيعات."
                + business_context
            )

            # ── Build messages with conversation history ──────────────────────
            history = self._get_history(phone_key)
            messages_for_claude = history + [{"role": "user", "content": text}]

            if len(history) > 0:
                logger.info(
                    f"Conversation memory: {len(history)} prior turns for {phone_key}"
                )

            response = client.messages.create(
                model="claude-opus-4-5",
                system=system_prompt,
                messages=messages_for_claude,
                max_tokens=400,
                temperature=0.1,  # Low temp = consistent structured output
            )

            reply_text = response.content[0].text.strip()
            logger.info(f"Claude WhatsApp reply: {reply_text[:200]}")

            # ── Parse TRANSACTION block ──────────────────────────────────────
            if "TRANSACTION:" in reply_text:
                # Find the TRANSACTION: line (it might not be the very first char)
                lines = reply_text.split("\n")
                txn_line = ""
                msg_lines = []
                found_txn = False

                for line in lines:
                    stripped = line.strip()
                    if not found_txn and "TRANSACTION:" in stripped:
                        txn_line = stripped
                        found_txn = True
                    elif found_txn:
                        if stripped.startswith("MESSAGE:"):
                            msg_lines.append(stripped.replace("MESSAGE:", "").strip())
                        elif stripped:
                            msg_lines.append(stripped)

                json_str = txn_line.split("TRANSACTION:", 1)[1].strip()
                message = " ".join(msg_lines).strip()

                try:
                    data = _json.loads(json_str)
                    amount = data.get("amount")

                    if business_id and db and amount:
                        txn = Transaction(
                            business_id=business_id,
                            amount=float(amount),
                            vendor=data.get("vendor", "غير محدد"),
                            description=data.get("description", text[:100]),
                            category=data.get("category", "تشغيلية"),
                            transaction_type=(
                                TransactionType.REVENUE
                                if data.get("type") == "revenue"
                                else TransactionType.EXPENSE
                            ),
                            source=TransactionSource.WHATSAPP,
                            date=datetime.utcnow(),
                        )
                        db.add(txn)
                        db.commit()
                        db.refresh(txn)
                        logger.info(
                            f"✅ WhatsApp transaction saved: id={txn.id} "
                            f"vendor={data.get('vendor')} amount={amount}"
                        )

                    if not message:
                        vendor = data.get("vendor", "")
                        emoji = "💰" if data.get("type") == "revenue" else "💸"
                        message = (
                            f"{emoji} تم تسجيل المعاملة\n"
                            f"الجهة: {vendor}\n"
                            f"المبلغ: {float(amount):,.0f} ر.س"
                        )
                    # ── Save this turn to conversation memory ─────────────
                    if phone_key:
                        self._save_turns(phone_key, text, message)
                    return message

                except (_json.JSONDecodeError, Exception) as e:
                    logger.error(f"Failed to parse/save WhatsApp transaction JSON: {e} | json_str={json_str!r}")
                    final = message or reply_text
                    if phone_key:
                        self._save_turns(phone_key, text, final)
                    return final

            # ── No TRANSACTION: in Claude reply ─────────────────────────────
            # Safety-net: if the original text looks financial, try entity_extractor
            clean_text = text.replace("[رسالة صوتية]: ", "").strip()
            if any(kw in clean_text for kw in self._FINANCIAL_KEYWORDS):
                logger.info("Claude skipped TRANSACTION: — running entity_extractor safety-net")
                try:
                    from app.services.extraction import entity_extractor
                    extracted = await entity_extractor.extract_transaction(clean_text)
                    if extracted and extracted.get("confidence", 0) >= 0.65 and extracted.get("amount"):
                        if business_id and db:
                            txn = Transaction(
                                business_id=business_id,
                                amount=float(extracted["amount"]),
                                vendor=extracted.get("vendor", "غير محدد"),
                                description=extracted.get("description", clean_text[:100]),
                                category=extracted.get("category", "تشغيلية"),
                                transaction_type=(
                                    TransactionType.REVENUE
                                    if extracted.get("category") == "إيرادات"
                                    else TransactionType.EXPENSE
                                ),
                                source=TransactionSource.WHATSAPP,
                                date=datetime.utcnow(),
                            )
                            db.add(txn)
                            db.commit()
                            db.refresh(txn)
                            logger.info(
                                f"✅ WhatsApp transaction saved via extractor fallback: "
                                f"id={txn.id} vendor={extracted.get('vendor')} amount={extracted.get('amount')}"
                            )
                        vendor = extracted.get("vendor", "")
                        amt = float(extracted.get("amount", 0))
                        confirmation = f"✅ تم تسجيل: {vendor} - {amt:,.0f} ر.س\n\n"
                        final = confirmation + reply_text
                        if phone_key:
                            self._save_turns(phone_key, text, final)
                        return final
                except Exception as e:
                    logger.warning(f"Entity extractor safety-net failed: {e}")

            # Pure conversational reply — save to memory and return
            if phone_key:
                self._save_turns(phone_key, text, reply_text)
            return reply_text

        except Exception as e:
            logger.error(f"Claude WhatsApp AI failed: {e}")
            return await self._fallback_respond(text, business_id, db)

    async def _fallback_respond(
        self, text: str, business_id: Optional[int], db: Optional[Session]
    ) -> str:
        """Rule-based fallback when Claude is unavailable."""
        return await self._create_transaction_from_text(text, business_id, db)

    async def _handle_audio(
        self,
        media_url: Optional[str],
        business_id: Optional[int],
        db: Optional[Session],
        phone_key: str = "",
    ) -> str:
        """Download WhatsApp voice note, transcribe, then pass through Claude AI."""
        if not media_url:
            return "لم أتمكن من استقبال الملف الصوتي. حاول مجدداً."

        # Step 1 — Download audio from Twilio (requires Basic auth)
        try:
            import httpx
            async with httpx.AsyncClient(follow_redirects=True) as http_client:
                audio_response = await http_client.get(
                    media_url,
                    auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    if settings.has_twilio else None,
                    timeout=30,
                )
            content_type = audio_response.headers.get("content-type", "unknown")
            audio_bytes = audio_response.content
            logger.info(
                f"Downloaded WhatsApp audio: {len(audio_bytes)} bytes, "
                f"status={audio_response.status_code}, content-type={content_type}"
            )
            if audio_response.status_code != 200 or len(audio_bytes) < 100:
                logger.error(f"Bad audio download: status={audio_response.status_code}, body={audio_bytes[:200]}")
                return "فشل تحميل الملف الصوتي. حاول مجدداً."
        except Exception as e:
            logger.error(f"Failed to download WhatsApp audio: {e}")
            return "فشل تحميل الملف الصوتي. تأكد من اتصالك بالإنترنت."

        # Step 2 — Convert OGG/Opus → MP3 if ffmpeg available (Groq prefers MP3)
        filename = "whatsapp_voice.ogg"
        try:
            import subprocess, uuid as _uuid, os
            tmp_ogg = f"/tmp/wa_{_uuid.uuid4().hex}.ogg"
            tmp_mp3 = tmp_ogg.replace(".ogg", ".mp3")
            with open(tmp_ogg, "wb") as f:
                f.write(audio_bytes)
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_ogg, "-ar", "16000", "-ac", "1", "-q:a", "4", tmp_mp3],
                capture_output=True, timeout=30
            )
            if result.returncode == 0 and os.path.exists(tmp_mp3):
                with open(tmp_mp3, "rb") as f:
                    audio_bytes = f.read()
                filename = "whatsapp_voice.mp3"
                logger.info(f"Converted OGG→MP3: {len(audio_bytes)} bytes")
            os.unlink(tmp_ogg) if os.path.exists(tmp_ogg) else None
            os.unlink(tmp_mp3) if os.path.exists(tmp_mp3) else None
        except FileNotFoundError:
            logger.info("ffmpeg not available — sending OGG directly to Groq")
        except Exception as e:
            logger.warning(f"Audio conversion failed (using original): {e}")

        # Step 3 — Transcribe
        try:
            from app.services.transcription import transcription_service
            transcription = await transcription_service.transcribe_audio(
                audio_bytes, filename=filename
            )
            if not transcription:
                return "لم أتمكن من فهم الصوت. حاول مجدداً بصوت أوضح."
            logger.info(f"WhatsApp voice transcription: {transcription}")
        except Exception as e:
            logger.error(f"WhatsApp audio transcription failed: {e}")
            return "حدث خطأ في تحويل الصوت إلى نص. حاول مجدداً."

        # Step 4 — Pass transcription through Claude AI (with memory)
        return await self._ai_respond(
            f"[رسالة صوتية]: {transcription}", business_id, db, phone_key
        )

    async def _handle_image(
        self, media_url: Optional[str], business_id: Optional[int], db: Optional[Session]
    ) -> str:
        """Download image, run OCR, create transaction."""
        if not media_url:
            return "لم أتمكن من استقبال الصورة. حاول مجدداً."

        try:
            import httpx
            async with httpx.AsyncClient() as http_client:
                img_response = await http_client.get(
                    media_url,
                    auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    if settings.has_twilio else None,
                    timeout=30,
                )
            image_bytes = img_response.content
        except Exception as e:
            logger.error(f"Failed to download WhatsApp image: {e}")
            return "فشل تحميل الصورة. تأكد من اتصالك بالإنترنت."

        try:
            from app.services.receipt_ocr import receipt_ocr_service
            extracted = await receipt_ocr_service.extract_from_image(image_bytes)

            if not extracted or not extracted.get("amount"):
                return "لم أتمكن من قراءة بيانات الإيصال. تأكد من وضوح الصورة."

            if business_id and db:
                transaction = Transaction(
                    business_id=business_id,
                    amount=extracted["amount"],
                    vendor=extracted.get("vendor", "غير محدد"),
                    description=extracted.get("description", "إيصال واتساب"),
                    category=extracted.get("category", "تشغيلية"),
                    transaction_type=TransactionType.EXPENSE,
                    source=TransactionSource.WHATSAPP,
                    date=datetime.utcnow(),
                )
                db.add(transaction)
                db.commit()

            return (
                f"✅ تم تسجيل الإيصال:\n"
                f"• الجهة: {extracted.get('vendor', 'غير محدد')}\n"
                f"• المبلغ: {extracted.get('amount', 0):,.0f} ر.س\n"
                f"• الفئة: {extracted.get('category', 'تشغيلية')}\n"
                f"• الثقة: {extracted.get('confidence', 0) * 100:.0f}%"
            )
        except Exception as e:
            logger.error(f"WhatsApp image OCR failed: {e}")
            return "حدث خطأ أثناء معالجة صورة الإيصال."

    async def _create_transaction_from_text(
        self, text: str, business_id: Optional[int], db: Optional[Session]
    ) -> str:
        """Extract financial entity from text and create transaction."""
        try:
            from app.services.extraction import entity_extractor
            extracted = await entity_extractor.extract_transaction(text)

            if not extracted or extracted.get("confidence", 0) < 0.5:
                return (
                    f"استلمت رسالتك: \"{text}\"\n"
                    "لم أتمكن من استخراج تفاصيل المعاملة. "
                    "حاول مثلاً: \"دفعت 500 ريال للمراعي مقابل حليب\""
                )

            if business_id and db:
                transaction = Transaction(
                    business_id=business_id,
                    amount=extracted["amount"],
                    vendor=extracted.get("vendor", "غير محدد"),
                    description=extracted.get("description", text[:100]),
                    category=extracted.get("category", "تشغيلية"),
                    transaction_type=(
                        TransactionType.REVENUE
                        if extracted.get("transaction_type") == "إيرادات"
                        else TransactionType.EXPENSE
                    ),
                    source=TransactionSource.WHATSAPP,
                    date=datetime.utcnow(),
                )
                db.add(transaction)
                db.commit()

            emoji = "💰" if extracted.get("transaction_type") == "إيرادات" else "💸"
            return (
                f"{emoji} تم تسجيل المعاملة:\n"
                f"• الجهة: {extracted.get('vendor', 'غير محدد')}\n"
                f"• المبلغ: {extracted.get('amount', 0):,.0f} ر.س\n"
                f"• الفئة: {extracted.get('category', 'تشغيلية')}"
            )
        except Exception as e:
            logger.error(f"Transaction extraction from WhatsApp text failed: {e}")
            return "حدث خطأ أثناء معالجة رسالتك. حاول مجدداً."

    def send_message(self, to_number: str, text: str) -> bool:
        """Send a WhatsApp message via Twilio."""
        if not self._client:
            logger.info(f"[Mock] Sending WhatsApp to {to_number}: {text[:50]}...")
            return True

        try:
            self._client.messages.create(
                from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
                to=f"whatsapp:{to_number}",
                body=text,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False

    def get_weekly_summary(self, business_id: int, db: Session) -> str:
        """Generate and return a weekly financial summary message."""
        try:
            week_ago = datetime.utcnow() - timedelta(days=7)
            transactions = (
                db.query(Transaction)
                .filter(
                    Transaction.business_id == business_id,
                    Transaction.date >= week_ago,
                )
                .all()
            )

            revenue = sum(
                float(t.amount) for t in transactions
                if t.transaction_type == TransactionType.REVENUE
            )
            expenses = sum(
                float(t.amount) for t in transactions
                if t.transaction_type == TransactionType.EXPENSE
            )
            net = revenue - expenses

            trend_emoji = "📈" if net > 0 else "📉"

            return (
                f"📊 *ملخصك المالي الأسبوعي*\n\n"
                f"💰 الإيرادات: {revenue:,.0f} ر.س\n"
                f"💸 المصاريف: {expenses:,.0f} ر.س\n"
                f"{trend_emoji} الصافي: {net:,.0f} ر.س\n"
                f"📝 عدد المعاملات: {len(transactions)}\n\n"
                f"للتفاصيل الكاملة، افتح تطبيق وكيل."
            )
        except Exception as e:
            logger.error(f"Failed to generate weekly summary: {e}")
            return "حدث خطأ في إنشاء الملخص الأسبوعي."

    def verify_twilio_signature(self, url: str, params: dict, signature: str) -> bool:
        """Verify that the request came from Twilio."""
        if not self._validator:
            return True  # In mock mode, accept all
        try:
            return self._validator.validate(url, params, signature)
        except Exception:
            return False


whatsapp_service = WhatsAppService()
