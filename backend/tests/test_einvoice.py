"""
Tests for ZATCA E-Invoice Generator and Compliance routes.
"""

import base64
import pytest
from datetime import datetime, timezone

from app.services.einvoice_generator import EInvoiceGenerator, einvoice_generator
from app.models.transaction import Transaction, TransactionSource


# ── Helpers ───────────────────────────────────────────────────────────────────

SAMPLE_TRANSACTION_DATA = {
    "amount": 1000.0,
    "vendor": "شركة الاختبار",
    "date": datetime(2026, 3, 4, 10, 30, 0),
    "description": "خدمات استشارية",
    "category": "OpEx",
}

BUSINESS_NAME = "مقهى وكيل"
VAT_NUMBER = "300012345678903"


# ─────────────────────────────────────────────────────────────────────────────
# TestEInvoiceGenerator
# ─────────────────────────────────────────────────────────────────────────────

class TestEInvoiceGenerator:
    """Unit tests for the EInvoiceGenerator service."""

    def setup_method(self):
        self.gen = EInvoiceGenerator()

    # ── test_generate_invoice_returns_required_fields ─────────────────────────

    def test_generate_invoice_returns_required_fields(self):
        """generate_invoice must return all expected keys."""
        result = self.gen.generate_invoice(
            transaction_id=1,
            business_name=BUSINESS_NAME,
            vat_number=VAT_NUMBER,
            transaction_data=SAMPLE_TRANSACTION_DATA,
        )
        for key in ("invoice_number", "xml_content", "qr_data", "pdf_path", "total_amount", "vat_amount"):
            assert key in result, f"Missing key: {key}"

    # ── test_invoice_number_format ────────────────────────────────────────────

    def test_invoice_number_format(self):
        """invoice_number must start with 'INV-'."""
        result = self.gen.generate_invoice(
            transaction_id=42,
            business_name=BUSINESS_NAME,
            vat_number=VAT_NUMBER,
            transaction_data=SAMPLE_TRANSACTION_DATA,
        )
        assert result["invoice_number"].startswith("INV-"), (
            f"Expected invoice_number to start with 'INV-', got: {result['invoice_number']}"
        )

    # ── test_qr_code_is_base64 ────────────────────────────────────────────────

    def test_qr_code_is_base64(self):
        """qr_data must be a valid base64-encoded string."""
        result = self.gen.generate_invoice(
            transaction_id=7,
            business_name=BUSINESS_NAME,
            vat_number=VAT_NUMBER,
            transaction_data=SAMPLE_TRANSACTION_DATA,
        )
        qr_data = result["qr_data"]
        assert isinstance(qr_data, str), "qr_data must be a string"
        # Must not raise
        decoded = base64.b64decode(qr_data)
        assert len(decoded) > 0, "Decoded QR data must not be empty"

    # ── test_xml_contains_invoice_id ──────────────────────────────────────────

    def test_xml_contains_invoice_id(self):
        """xml_content must contain the generated invoice_number."""
        result = self.gen.generate_invoice(
            transaction_id=3,
            business_name=BUSINESS_NAME,
            vat_number=VAT_NUMBER,
            transaction_data=SAMPLE_TRANSACTION_DATA,
        )
        assert result["invoice_number"] in result["xml_content"], (
            "invoice_number must appear inside xml_content"
        )

    # ── test_vat_calculation ──────────────────────────────────────────────────

    def test_vat_calculation(self):
        """VAT must be exactly 15% of the base amount (amount * 0.15)."""
        amount = 2000.0
        data = dict(SAMPLE_TRANSACTION_DATA, amount=amount)
        result = self.gen.generate_invoice(
            transaction_id=5,
            business_name=BUSINESS_NAME,
            vat_number=VAT_NUMBER,
            transaction_data=data,
        )
        expected_vat = round(amount * 0.15, 2)
        assert result["vat_amount"] == pytest.approx(expected_vat, abs=0.01), (
            f"Expected VAT {expected_vat}, got {result['vat_amount']}"
        )
        expected_total = round(amount + expected_vat, 2)
        assert result["total_amount"] == pytest.approx(expected_total, abs=0.01), (
            f"Expected total {expected_total}, got {result['total_amount']}"
        )

    # ── test_generate_pdf_returns_bytes_or_none ───────────────────────────────

    def test_generate_pdf_returns_bytes_or_none(self):
        """generate_pdf must return bytes or None — never raise."""
        result = self.gen.generate_invoice(
            transaction_id=9,
            business_name=BUSINESS_NAME,
            vat_number=VAT_NUMBER,
            transaction_data=SAMPLE_TRANSACTION_DATA,
        )
        pdf = self.gen.generate_pdf(result)
        assert pdf is None or isinstance(pdf, bytes), (
            f"generate_pdf must return bytes or None, got {type(pdf)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# TestComplianceRoutes
# ─────────────────────────────────────────────────────────────────────────────

class TestComplianceRoutes:
    """Integration tests for compliance API endpoints."""

    # ── test_get_invoices_requires_auth ───────────────────────────────────────

    def test_get_invoices_requires_auth(self, client):
        """GET /invoices without auth must return 403."""
        response = client.get("/api/v1/compliance/invoices")
        assert response.status_code in (401, 403), (
            f"Expected 403, got {response.status_code}"
        )

    # ── test_get_invoices_returns_list ────────────────────────────────────────

    def test_get_invoices_returns_list(self, client, auth_headers):
        """GET /invoices with valid auth must return 200 and a list."""
        response = client.get("/api/v1/compliance/invoices", headers=auth_headers)
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        assert isinstance(response.json(), list), "Response body must be a list"

    # ── test_generate_invoice_requires_auth ───────────────────────────────────

    def test_generate_invoice_requires_auth(self, client):
        """POST /generate-invoice without auth must return 403."""
        response = client.post(
            "/api/v1/compliance/generate-invoice",
            json={"transaction_id": 1},
        )
        assert response.status_code in (401, 403), (
            f"Expected 403, got {response.status_code}"
        )

    # ── test_generate_invoice_no_transaction ──────────────────────────────────

    def test_generate_invoice_no_transaction(self, client, auth_headers):
        """POST /generate-invoice with a non-existent transaction_id must return 404."""
        response = client.post(
            "/api/v1/compliance/generate-invoice",
            json={"transaction_id": 99999},
            headers=auth_headers,
        )
        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
