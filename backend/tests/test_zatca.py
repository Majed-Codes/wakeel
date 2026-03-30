"""
ZATCA Compliance Validator Tests.
"""

from app.services.zatca import zatca_validator


class TestZATCAValidator:
    """Test ZATCA invoice validation."""

    def _valid_invoice(self) -> dict:
        """Return a fully compliant invoice."""
        return {
            "seller_name": "المراعي للتجارة",
            "seller_vat": "300000000000003",
            "buyer_name": "مقهى الوكيل",
            "date": "2026-01-15",
            "total": 1150.0,
            "vat_amount": 150.0,
            "qr_code": "TVRJR05FUkFJLi4u",
        }

    def test_valid_invoice_scores_100(self):
        result = zatca_validator.validate_invoice(self._valid_invoice())
        assert result["valid"] is True
        assert result["compliance_score"] == 100.0
        assert result["errors"] == []

    def test_missing_seller_name(self):
        data = self._valid_invoice()
        data["seller_name"] = ""
        result = zatca_validator.validate_invoice(data)
        assert result["valid"] is False
        assert any("اسم البائع" in e for e in result["errors"])

    def test_missing_qr_code(self):
        data = self._valid_invoice()
        data["qr_code"] = ""
        result = zatca_validator.validate_invoice(data)
        assert result["valid"] is False
        assert any("QR" in e for e in result["errors"])

    def test_invalid_vat_number_too_short(self):
        data = self._valid_invoice()
        data["seller_vat"] = "12345"
        result = zatca_validator.validate_invoice(data)
        assert result["valid"] is False
        assert any("ضريبي" in e for e in result["errors"])

    def test_invalid_vat_number_wrong_start(self):
        data = self._valid_invoice()
        data["seller_vat"] = "100000000000003"
        result = zatca_validator.validate_invoice(data)
        assert result["valid"] is False

    def test_vat_calculation_mismatch(self):
        data = self._valid_invoice()
        data["total"] = 1150.0
        data["vat_amount"] = 200.0  # Wrong — should be ~150
        result = zatca_validator.validate_invoice(data)
        assert len(result["warnings"]) > 0
        assert any("تباين" in w for w in result["warnings"])

    def test_invalid_date_format(self):
        data = self._valid_invoice()
        data["date"] = "15/01/2026"
        result = zatca_validator.validate_invoice(data)
        assert any("تاريخ" in w for w in result["warnings"])

    def test_valid_date_format(self):
        data = self._valid_invoice()
        data["date"] = "2026-01-15"
        result = zatca_validator.validate_invoice(data)
        assert not any("تاريخ" in w for w in result["warnings"])

    def test_multiple_missing_fields(self):
        data = {
            "seller_name": "",
            "seller_vat": "",
            "buyer_name": "",
            "date": "",
            "total": None,
            "vat_amount": None,
            "qr_code": "",
        }
        result = zatca_validator.validate_invoice(data)
        assert result["valid"] is False
        assert len(result["errors"]) >= 5
        assert result["compliance_score"] < 30

    def test_score_decreases_with_errors(self):
        # 1 error
        data1 = self._valid_invoice()
        data1["qr_code"] = ""
        score1 = zatca_validator.validate_invoice(data1)["compliance_score"]

        # 2 errors
        data2 = self._valid_invoice()
        data2["qr_code"] = ""
        data2["seller_name"] = ""
        score2 = zatca_validator.validate_invoice(data2)["compliance_score"]

        assert score2 < score1
