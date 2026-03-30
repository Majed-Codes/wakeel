"""Tests for receipt OCR feature — Claude Vision extraction."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


# Minimal valid PNG bytes (1×1 white pixel)
FAKE_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
    b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
    b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
)


class TestReceiptOCRService:

    def test_mock_extract_returns_valid_structure(self):
        from app.services.receipt_ocr import ReceiptOCRService
        service = ReceiptOCRService()
        result = service._mock_extract()
        assert "amount" in result
        assert "vendor" in result
        assert "category" in result
        assert "confidence" in result

    def test_mock_extract_amount_positive(self):
        from app.services.receipt_ocr import ReceiptOCRService
        service = ReceiptOCRService()
        result = service._mock_extract()
        assert result["amount"] > 0

    def test_mock_extract_category_arabic(self):
        from app.services.receipt_ocr import ReceiptOCRService
        service = ReceiptOCRService()
        result = service._mock_extract()
        assert result["category"] in ("تشغيلية", "رأسمالية", "إيرادات")

    def test_mock_extract_confidence_in_range(self):
        from app.services.receipt_ocr import ReceiptOCRService
        service = ReceiptOCRService()
        result = service._mock_extract()
        assert 0.0 <= result["confidence"] <= 1.0

    def test_extract_without_api_key_uses_mock(self):
        """Without Anthropic key, returns mock data."""
        from app.services.receipt_ocr import ReceiptOCRService
        service = ReceiptOCRService()
        service._client = None  # Force mock mode

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            service.extract_from_image(FAKE_PNG, "receipt.png")
        )
        assert result is not None
        assert result["amount"] > 0

    def test_extract_with_mock_anthropic_client(self):
        """Mock Anthropic client returns correctly parsed result."""
        from app.services.receipt_ocr import ReceiptOCRService
        import json, asyncio

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "amount": 1250.0,
            "vendor": "محل البقالة",
            "date": "2024-06-15",
            "description": "مشتريات متنوعة",
            "category": "تشغيلية",
            "vat_amount": 187.5,
            "items": [],
            "confidence": 0.92,
        }))]

        service = ReceiptOCRService()
        service._client = MagicMock()
        service._client.messages.create.return_value = mock_response

        result = asyncio.get_event_loop().run_until_complete(
            service.extract_from_image(FAKE_PNG, "receipt.jpg")
        )
        assert result["amount"] == 1250.0
        assert result["vendor"] == "محل البقالة"
        assert result["confidence"] == 0.92

    def test_extract_handles_json_error(self):
        """Invalid JSON response returns None."""
        from app.services.receipt_ocr import ReceiptOCRService
        import asyncio

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="هذا ليس JSON صالح")]

        service = ReceiptOCRService()
        service._client = MagicMock()
        service._client.messages.create.return_value = mock_response

        result = asyncio.get_event_loop().run_until_complete(
            service.extract_from_image(FAKE_PNG, "receipt.jpg")
        )
        assert result is None


class TestReceiptRoutes:

    def test_receipt_upload_invalid_extension(self, client, auth_headers):
        files = {"file": ("receipt.txt", b"data", "text/plain")}
        response = client.post("/api/v1/transactions/receipt", files=files, headers=auth_headers)
        assert response.status_code == 400

    def test_receipt_upload_requires_auth(self, client):
        files = {"file": ("receipt.jpg", FAKE_PNG, "image/jpeg")}
        response = client.post("/api/v1/transactions/receipt", files=files)
        assert response.status_code in (401, 403)

    def test_receipt_upload_success_with_mock(self, client, auth_headers, db):
        """With mocked OCR service, receipt upload creates transaction."""
        mock_result = {
            "amount": 500.0,
            "vendor": "مطعم البيك",
            "date": "2024-06-15",
            "description": "وجبات",
            "category": "تشغيلية",
            "vat_amount": 75.0,
            "confidence": 0.90,
        }
        with patch("app.routes.transactions.receipt_ocr_service") as mock_service:
            mock_service.extract_from_image = AsyncMock(return_value=mock_result)
            files = {"file": ("receipt.jpg", FAKE_PNG, "image/jpeg")}
            response = client.post(
                "/api/v1/transactions/receipt", files=files, headers=auth_headers
            )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] in ("success", "needs_confirmation")
        assert data["transaction"] is not None
        assert data["transaction"]["amount"] == 500.0

    def test_receipt_upload_ocr_failure(self, client, auth_headers):
        """If OCR returns None, returns error status."""
        with patch("app.routes.transactions.receipt_ocr_service") as mock_service:
            mock_service.extract_from_image = AsyncMock(return_value=None)
            files = {"file": ("receipt.jpg", FAKE_PNG, "image/jpeg")}
            response = client.post(
                "/api/v1/transactions/receipt", files=files, headers=auth_headers
            )
        assert response.status_code == 201
        assert response.json()["status"] == "error"

    def test_receipt_png_extension_allowed(self, client, auth_headers):
        """PNG extension is valid."""
        with patch("app.routes.transactions.receipt_ocr_service") as mock_service:
            mock_service.extract_from_image = AsyncMock(return_value=None)
            files = {"file": ("receipt.png", FAKE_PNG, "image/png")}
            response = client.post(
                "/api/v1/transactions/receipt", files=files, headers=auth_headers
            )
        # Should not be 400 (bad extension) — should be 201 with error status from OCR
        assert response.status_code == 201
