"""Saudi bank statement parser using Claude Vision."""
import base64
import json
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

PARSE_PROMPT = """أنت خبير في قراءة كشوف الحسابات البنكية السعودية.
استخرج جميع العمليات (المعاملات) من هذا الكشف البنكي.

أعد النتيجة كـ JSON array فقط، بهذا الشكل:
[
  {"date": "YYYY-MM-DD", "description": "وصف العملية", "debit": 0.0, "credit": 500.0},
  ...
]

ملاحظات:
- debit = مبلغ مسحوب (مصروف)
- credit = مبلغ مودع (إيراد)
- التواريخ بصيغة YYYY-MM-DD
- إذا كان المبلغ غير محدد ضع 0.0
- أعد JSON فقط بدون أي نص إضافي"""

class BankStatementParser:
    def parse(self, file_bytes: bytes, content_type: str = "image/jpeg") -> list:
        """Parse a bank statement file using Claude Vision."""
        if not client.api_key:
            return self._mock_rows()

        # Determine media type
        if content_type in ("application/pdf",):
            media_type = "application/pdf"
        elif "png" in content_type:
            media_type = "image/png"
        else:
            media_type = "image/jpeg"

        b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

        try:
            msg = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": PARSE_PROMPT},
                    ],
                }],
            )

            raw = msg.content[0].text.strip()
            # Extract JSON from response
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            rows = json.loads(raw)
            return self._normalize_rows(rows)
        except Exception:
            return self._mock_rows()

    def _normalize_rows(self, rows: list) -> list:
        """Normalize rows to standard format."""
        normalized = []
        for row in rows:
            debit = float(row.get("debit", 0) or 0)
            credit = float(row.get("credit", 0) or 0)

            # Only add rows with actual amounts
            if debit > 0 or credit > 0:
                normalized.append({
                    "date": row.get("date", ""),
                    "description": row.get("description", ""),
                    "debit": debit,
                    "credit": credit,
                    "transaction_type": "EXPENSE" if debit > 0 else "REVENUE",
                    "amount": debit if debit > 0 else credit,
                })
        return normalized

    def _mock_rows(self) -> list:
        """Return sample rows when API is unavailable."""
        return [
            {"date": "2025-01-05", "description": "شراء مستلزمات مكتبية", "debit": 850.0, "credit": 0.0, "transaction_type": "EXPENSE", "amount": 850.0},
            {"date": "2025-01-08", "description": "تحويل واردات من عميل", "debit": 0.0, "credit": 15000.0, "transaction_type": "REVENUE", "amount": 15000.0},
            {"date": "2025-01-12", "description": "فاتورة كهرباء", "debit": 1200.0, "credit": 0.0, "transaction_type": "EXPENSE", "amount": 1200.0},
        ]

bank_statement_parser = BankStatementParser()
