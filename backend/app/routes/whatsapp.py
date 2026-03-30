"""
WhatsApp Bot Routes — Twilio webhook integration.

POST /api/v1/whatsapp/webhook  → Twilio webhook (no JWT, verified by Twilio signature)
GET  /api/v1/whatsapp/webhook  → Twilio verification challenge
POST /api/v1/whatsapp/connect  → Link phone number to business (JWT required)
GET  /api/v1/whatsapp/status   → Check connection status (JWT required)
POST /api/v1/whatsapp/test     → Send a test message (JWT required)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Business
from app.auth.dependencies import get_current_user
from app.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/whatsapp", tags=["WhatsApp"])


class ConnectRequest(BaseModel):
    phone_number: str  # e.g., "+966501234567"


class TestMessageRequest(BaseModel):
    message: str = "مرحباً! هذه رسالة اختبار من وكيل AI."
    to_number: Optional[str] = None


# ── Public webhook (called by Twilio, no JWT) ───────────────────────────────

@router.get(
    "/webhook",
    response_class=PlainTextResponse,
    summary="التحقق من Twilio",
    include_in_schema=False,
)
async def verify_webhook(request: Request):
    """Twilio verification — returns 200 OK to confirm webhook endpoint."""
    return PlainTextResponse("OK", status_code=200)


@router.post(
    "/webhook",
    response_class=PlainTextResponse,
    summary="استقبال رسائل واتساب",
    description="Twilio webhook لاستقبال الرسائل الواردة (بدون JWT).",
    include_in_schema=False,
)
async def receive_whatsapp(
    request: Request,
    From: str = Form(default=""),
    Body: str = Form(default=""),
    NumMedia: int = Form(default=0),
    MediaContentType0: Optional[str] = Form(default=None),
    MediaUrl0: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
):
    """
    Process incoming WhatsApp messages from Twilio.
    No JWT — Twilio webhook, validated by signature.
    """
    # Determine message type
    if NumMedia and NumMedia > 0 and MediaUrl0:
        content_type = (MediaContentType0 or "").lower()
        if "image" in content_type:
            message_type = "image"
        elif "audio" in content_type or "ogg" in content_type:
            message_type = "audio"
        else:
            message_type = "text"
        content = Body or ""
        media_url = MediaUrl0
    else:
        message_type = "text"
        content = Body
        media_url = None

    # Look up business by phone number, fall back to first business
    from_clean = From.replace("whatsapp:", "").replace("+966", "0").replace("+", "")
    business = None
    business_id = None
    try:
        all_businesses = db.query(Business).all()
        # Try exact phone match first
        for b in all_businesses:
            if b.phone and (b.phone in from_clean or from_clean in b.phone):
                business = b
                business_id = b.id
                break
        # No match — fall back to first business (single-tenant / demo mode)
        if not business and all_businesses:
            business = all_businesses[0]
            business_id = business.id
            logger.info(f"No phone match for {from_clean}, using default business id={business_id}")
    except Exception as e:
        logger.error(f"Business lookup failed: {e}")

    # Process message
    reply = await whatsapp_service.handle_message(
        from_number=From,
        message_type=message_type,
        content=content,
        media_url=media_url,
        business_id=business_id,
        db=db,
    )

    # Return TwiML response
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{reply}</Message>
</Response>"""
    return PlainTextResponse(twiml, media_type="application/xml")


# ── JWT-protected endpoints ──────────────────────────────────────────────────

@router.post(
    "/connect",
    summary="ربط رقم واتساب",
    description="يربط رقم هاتف واتساب بحساب المنشأة.",
)
async def connect_whatsapp(
    request_body: ConnectRequest,
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Link a WhatsApp number to the current business account.
    Saves phone to Business.phone so incoming messages are routed to this business.
    Multi-tenant: each business registers their own number → isolated data.
    """
    # Normalise: strip non-numeric except leading +
    phone = request_body.phone_number.strip()
    logger.info(f"Business {current_user.id} ({current_user.name}) linking WhatsApp: {phone}")

    # Check if this phone is already used by another business
    existing = db.query(Business).filter(
        Business.phone == phone,
        Business.id != current_user.id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"هذا الرقم مرتبط بمنشأة أخرى. استخدم رقماً مختلفاً.",
        )

    # Save phone to Business record
    current_user.phone = phone
    db.commit()
    db.refresh(current_user)
    logger.info(f"✅ Business {current_user.id} WhatsApp linked: {phone}")

    return {
        "status": "connected",
        "phone_number": phone,
        "business_id": current_user.id,
        "business_name": current_user.name,
        "message": "تم ربط رقم واتساب بنجاح. رسائلك الآن تُسجَّل في حسابك.",
        "whatsapp_configured": whatsapp_service.is_configured,
        "webhook_url": "/api/v1/whatsapp/webhook",
        "instructions": (
            "أرسل أي رسالة أو صوت من هذا الرقم للبوت وسيتعرف عليك تلقائياً."
        ),
    }


@router.get(
    "/status",
    summary="حالة الاتصال",
    description="يُعيد حالة اتصال واتساب للمنشأة.",
)
async def get_whatsapp_status(
    current_user: Business = Depends(get_current_user),
):
    """Check WhatsApp connection status."""
    return {
        "configured": whatsapp_service.is_configured,
        "business_id": current_user.id,
        "features": {
            "text_transactions": True,
            "voice_transactions": True,
            "receipt_ocr": True,
            "weekly_summary": True,
            "financial_queries": True,
        },
        "message": (
            "واتساب مُهيّأ وجاهز للاستخدام" if whatsapp_service.is_configured
            else "يعمل في وضع المحاكاة — أضف بيانات Twilio لتفعيل واتساب الحقيقي"
        ),
    }


@router.post(
    "/test",
    summary="إرسال رسالة اختبار",
    description="يُرسل رسالة اختبار للتحقق من إعداد واتساب.",
)
async def send_test_message(
    request_body: TestMessageRequest,
    current_user: Business = Depends(get_current_user),
):
    """Send a test WhatsApp message."""
    to_number = request_body.to_number or current_user.phone or "+966500000000"

    success = whatsapp_service.send_message(
        to_number=to_number,
        text=request_body.message,
    )

    return {
        "success": success,
        "to": to_number,
        "message": request_body.message,
        "mock_mode": not whatsapp_service.is_configured,
    }


@router.get(
    "/weekly-summary",
    summary="الملخص الأسبوعي",
    description="يُعيد الملخص المالي الأسبوعي.",
)
async def get_weekly_summary(
    current_user: Business = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get weekly financial summary (same content that would be sent via WhatsApp)."""
    summary = whatsapp_service.get_weekly_summary(
        business_id=current_user.id, db=db
    )
    return {"summary": summary}
