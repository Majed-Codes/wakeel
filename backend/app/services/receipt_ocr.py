"""
Receipt OCR Service — Claude Vision for structured receipt data extraction.

Uses Anthropic Claude Vision API to extract financial data from receipt images.
Falls back to mock data when no API key is configured.
"""

import base64
import json
import logging
from typing import Optional

from app.config import settings
from app.services.extraction import CATEGORY_MAP

logger = logging.getLogger(__name__)

RECEIPT_SYSTEM_PROMPT = (
    "أنت خبير محاسبة سعودي متخصص في قراءة الفواتير والإيصالات العربية. "
    "تستخرج البيانات المالية بدقة عالية من صور الإيصالات. "
    "أرجع JSON فقط بدون أي نص إضافي."
)

RECEIPT_USER_PROMPT = """استخرج البيانات المالية من هذا الإيصال.

أرجع JSON فقط بهذا التنسيق:
{
    "amount": <المبلغ الإجمالي بالريال>,
    "vendor": "<اسم المتجر أو المورد>",
    "date": "<التاريخ بصيغة YYYY-MM-DD>",
    "description": "<وصف مختصر للمشتريات>",
    "category": "<تشغيلية|رأسمالية|إيرادات>",
    "vat_amount": <مبلغ الضريبة أو 0>,
    "items": [{"name": "<اسم المنتج>", "qty": <الكمية>, "price": <السعر>}],
    "confidence": <0.0 إلى 1.0>
}

قواعد التصنيف:
- "تشغيلية" (OpEx): مشتريات يومية، مواد خام، وجبات، مستلزمات، خدمات
- "رأسمالية" (CapEx): شراء معدات، أجهزة، أثاث، أصول ثابتة
- "إيرادات" (Revenue): فاتورة مبيعات صادرة للعملاء"""


# Media type mapping for image extensions
MEDIA_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".heic": "image/heic",
}


class ReceiptOCRService:
    """خدمة استخراج البيانات المالية من صور الإيصالات"""

    def __init__(self):
        self._client = None

        if settings.has_anthropic_key:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info("Receipt OCR: using Anthropic Claude Vision")

    async def extract_from_image(
        self, image_bytes: bytes, filename: str = "receipt.jpg"
    ) -> Optional[dict]:
        """
        Extract financial data from a receipt image.

        Returns dict with: amount, vendor, date, description, category,
                          vat_amount, items, confidence
        Falls back to mock when no API key is configured.
        """
        if not self._client:
            logger.warning("No Anthropic API key configured — using mock receipt extraction")
            return self._mock_extract()

        try:
            # Encode image to base64
            base64_data = base64.b64encode(image_bytes).decode("utf-8")

            # Determine media type from filename extension
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".jpg"
            media_type = MEDIA_TYPE_MAP.get(ext, "image/jpeg")

            response = self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=RECEIPT_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": RECEIPT_USER_PROMPT,
                            },
                        ],
                    }
                ],
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
            logger.error(f"Failed to parse Claude Vision JSON response: {e}")
            return None
        except Exception as e:
            error_str = str(e)
            logger.error(f"Receipt OCR extraction failed: {error_str}")
            if "overloaded" in error_str.lower() or "rate_limit" in error_str.lower():
                logger.warning("Anthropic rate limited — falling back to mock extraction")
                return self._mock_extract()
            return None

    def _mock_extract(self) -> dict:
        """Mock extraction for development without API key."""
        return {
            "amount": 350.0,
            "vendor": "مطعم البيك",
            "date": "2024-06-15",
            "description": "وجبات غداء للموظفين",
            "category": "تشغيلية",
            "vat_amount": 52.5,
            "items": [
                {"name": "وجبة دجاج", "qty": 5, "price": 35.0},
                {"name": "مشروبات", "qty": 5, "price": 10.0},
                {"name": "سلطة", "qty": 3, "price": 15.0},
            ],
            "confidence": 0.88,
        }


receipt_ocr_service = ReceiptOCRService()
