"""
ZATCA Compliance Validator.

Bachmann: "ZATCA Phase 2 is non-negotiable in Saudi. 
We validate: required fields, VAT format, QR code, VAT calculation.
Rule-based for now. API integration later."
"""

import re
from typing import List


class ZATCAValidator:
    """محقق الامتثال لهيئة الزكاة والضريبة والجمارك"""

    REQUIRED_FIELDS = [
        "seller_name",
        "seller_vat",
        "buyer_name",
        "date",
        "total",
        "vat_amount",
        "qr_code",
    ]

    VAT_RATE = 0.15  # 15% Saudi VAT

    def validate_invoice(self, invoice_data: dict) -> dict:
        """
        Validate an invoice against ZATCA Phase 2 requirements.

        Returns: {valid, errors, warnings, compliance_score}
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Check required fields
        for field in self.REQUIRED_FIELDS:
            value = invoice_data.get(field)
            if not value:
                errors.append(f"حقل مفقود: {self._field_arabic(field)}")

        # 2. Validate VAT number format (15 digits starting with 3)
        seller_vat = invoice_data.get("seller_vat", "")
        if seller_vat and not self._is_valid_vat(seller_vat):
            errors.append("رقم ضريبي غير صالح — يجب أن يكون 15 رقم ويبدأ بالرقم 3")

        # 3. Check QR code presence (Phase 2 requirement)
        if not invoice_data.get("qr_code"):
            errors.append("رمز QR مفقود — مطلوب في المرحلة الثانية من الفوترة الإلكترونية")

        # 4. VAT calculation check
        total = invoice_data.get("total")
        vat_amount = invoice_data.get("vat_amount")
        if total is not None and vat_amount is not None:
            try:
                total_f = float(total)
                vat_f = float(vat_amount)
                # VAT should be 15% of the pre-tax amount
                pre_tax = total_f / (1 + self.VAT_RATE)
                expected_vat = pre_tax * self.VAT_RATE

                if abs(expected_vat - vat_f) > 0.5:  # Allow small rounding
                    warnings.append(
                        f"تباين في حساب الضريبة: المتوقع {expected_vat:.2f} ر.س، الموجود {vat_f:.2f} ر.س"
                    )
            except (ValueError, TypeError):
                errors.append("قيمة المبلغ أو الضريبة غير صالحة")

        # 5. Date validation
        date_str = invoice_data.get("date")
        if date_str and not self._is_valid_date(date_str):
            warnings.append("تنسيق التاريخ غير معياري — يُفضل ISO 8601")

        score = self._calculate_score(errors, warnings)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "compliance_score": score,
        }

    def _is_valid_vat(self, vat_number: str) -> bool:
        """Saudi VAT number: 15 digits, starts with 3."""
        return bool(re.match(r"^3\d{14}$", str(vat_number)))

    def _is_valid_date(self, date_str: str) -> bool:
        """Basic date format check."""
        return bool(re.match(r"\d{4}-\d{2}-\d{2}", str(date_str)))

    def _calculate_score(self, errors: list, warnings: list) -> float:
        """Calculate compliance score 0–100."""
        if errors:
            # Each error deducts from 100, but never below 0
            deduction = len(errors) * 15
            base = max(0, 100 - deduction)
            return base - (len(warnings) * 5)
        return max(0.0, 100.0 - (len(warnings) * 10))

    def _field_arabic(self, field: str) -> str:
        """Map field names to Arabic labels."""
        mapping = {
            "seller_name": "اسم البائع",
            "seller_vat": "الرقم الضريبي للبائع",
            "buyer_name": "اسم المشتري",
            "date": "التاريخ",
            "total": "المبلغ الإجمالي",
            "vat_amount": "مبلغ الضريبة",
            "qr_code": "رمز QR",
        }
        return mapping.get(field, field)


zatca_validator = ZATCAValidator()
