"""
Entity Extraction Service — Claude for structured transaction data.

Uses Anthropic Claude as primary LLM, with OpenAI GPT-4o as fallback.
Temperature 0.1 for determinism.
"""

import json
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Category mapping: internal → Arabic display labels
CATEGORY_MAP = {
    "OpEx": "تشغيلية",
    "CapEx": "رأسمالية",
    "Revenue": "إيرادات",
}

CATEGORY_MAP_REVERSE = {v: k for k, v in CATEGORY_MAP.items()}

EXTRACTION_SYSTEM_PROMPT = (
    "أنت خبير مالي سعودي متخصص في استخراج البيانات المالية من النصوص العربية "
    "واللهجة السعودية. تفهم المصطلحات المحلية مثل 'حولت'، 'دفعت'، 'حق'، 'صرفت'. "
    "أرجع JSON فقط بدون أي نص إضافي."
)

EXTRACTION_PROMPT_TEMPLATE = """استخرج معلومات المعاملة المالية من النص التالي:
"{text}"

أرجع JSON فقط بهذا التنسيق:
{{
    "amount": <رقم بالريال — حوّل الكلمات العربية إلى أرقام>,
    "vendor": "<اسم المورد أو الجهة أو null إذا غير محدد>",
    "category": "<تشغيلية|رأسمالية|إيرادات>",
    "description": "<وصف مختصر للمعاملة بالعربي>",
    "confidence": <0.0 إلى 1.0>
}}

قواعد التصنيف:
- "تشغيلية" (OpEx): رواتب، إيجار، كهرباء، ماء، مواد خام، صيانة، توريدات يومية، اشتراكات
- "رأسمالية" (CapEx): شراء معدات، أجهزة، سيارات، تجهيزات، أثاث، استثمار في أصول
- "إيرادات" (Revenue): مبيعات، تحصيل، استلام مبلغ من عميل، دخل، أرباح

تحويل الأرقام العربية:
- "خمسة آلاف" أو "٥٠٠٠" = 5000
- "عشرين ألف" = 20000
- "ثلاثمية" أو "ثلاث مئة" = 300
- "مليون" = 1000000
- "ألف وخمسمية" = 1500

أمثلة:
- "حولت خمسة آلاف للمراعي مقابل توريد حليب" → amount: 5000, vendor: "المراعي", category: "تشغيلية", confidence: 0.95
- "دفعت ٣٠٠٠ حق الكهرباء" → amount: 3000, vendor: "شركة الكهرباء", category: "تشغيلية", confidence: 0.90
- "استلمت عشرين ألف من عميل أبو محمد" → amount: 20000, vendor: "أبو محمد", category: "إيرادات", confidence: 0.92
- "اشتريت جهاز كمبيوتر بـ ٤٥٠٠" → amount: 4500, category: "رأسمالية", confidence: 0.88
- "الراتب الشهري ٨٠٠٠ ريال" → amount: 8000, category: "تشغيلية", description: "راتب شهري", confidence: 0.85

قواعد الثقة (confidence):
- 0.9-1.0: المبلغ والمورد والتصنيف واضحة تماماً
- 0.7-0.9: المبلغ واضح لكن بعض التفاصيل غير مؤكدة
- 0.5-0.7: المبلغ تقريبي أو التصنيف غير واضح
- أقل من 0.5: النص غامض أو لا يحتوي معاملة مالية واضحة"""


class EntityExtractor:
    """خدمة استخراج البيانات المالية من النص العربي"""

    def __init__(self):
        self._client = None
        self._openai_client = None

        if settings.has_anthropic_key:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info("Entity extraction: using Anthropic Claude")
        elif settings.has_openai_key:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("Entity extraction: using OpenAI GPT-4o (fallback)")

    async def extract_transaction(self, text: str) -> Optional[dict]:
        """
        Extract transaction info from Arabic text.

        Returns dict with: amount, vendor, category, description, confidence
        Falls back to mock when no API key is configured.
        """
        if not self._client and not self._openai_client:
            logger.warning("No LLM API key configured — using mock extraction")
            return self._mock_extract(text)

        # Fallback to OpenAI if Anthropic not available
        if not self._client and self._openai_client:
            return await self._extract_openai(text)

        try:
            prompt = EXTRACTION_PROMPT_TEMPLATE.format(text=text)

            response = self._client.messages.create(
                model="claude-sonnet-4-20250514",
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=300,
            )

            data = json.loads(response.content[0].text)

            # Normalize: ensure category is in Arabic
            cat = data.get("category", "")
            if cat in CATEGORY_MAP:
                data["category"] = CATEGORY_MAP[cat]

            # Ensure amount is a number
            if isinstance(data.get("amount"), str):
                data["amount"] = float(data["amount"].replace(",", ""))

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return None
        except Exception as e:
            error_str = str(e)
            logger.error(f"Entity extraction failed: {error_str}")
            if "overloaded" in error_str.lower() or "rate_limit" in error_str.lower():
                logger.warning("Anthropic rate limited — falling back to mock extraction")
                return self._mock_extract(text)
            return None

    async def _extract_openai(self, text: str) -> Optional[dict]:
        """Fallback: extract using OpenAI GPT-4o if Anthropic is unavailable."""
        try:
            prompt = EXTRACTION_PROMPT_TEMPLATE.format(text=text)

            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"},
            )

            data = json.loads(response.choices[0].message.content)

            cat = data.get("category", "")
            if cat in CATEGORY_MAP:
                data["category"] = CATEGORY_MAP[cat]

            if isinstance(data.get("amount"), str):
                data["amount"] = float(data["amount"].replace(",", ""))

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            return None
        except Exception as e:
            error_str = str(e)
            logger.error(f"OpenAI extraction failed: {error_str}")
            if "insufficient_quota" in error_str or "quota" in error_str:
                logger.warning("OpenAI quota exceeded — falling back to mock extraction")
                return self._mock_extract(text)
            return None

    def _mock_extract(self, text: str) -> dict:
        """Mock extraction for development without API key."""
        return {
            "amount": 5000.0,
            "vendor": "المراعي",
            "category": "تشغيلية",
            "description": "توريد حليب ومنتجات ألبان",
            "confidence": 0.92,
        }


entity_extractor = EntityExtractor()
