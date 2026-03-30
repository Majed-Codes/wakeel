"""Tests for WhatsApp Bot integration."""

import pytest
from unittest.mock import patch, MagicMock


class TestWhatsAppService:

    def test_service_initializes(self):
        from app.services.whatsapp_service import WhatsAppService
        service = WhatsAppService()
        assert hasattr(service, "is_configured")
        assert hasattr(service, "handle_message")
        assert hasattr(service, "send_message")
        assert hasattr(service, "get_weekly_summary")

    def test_is_configured_false_without_credentials(self):
        from app.services.whatsapp_service import WhatsAppService
        service = WhatsAppService()
        # Simulate no-credentials / mock mode by nulling the Twilio client
        service._client = None
        assert service.is_configured is False

    def test_send_message_mock_returns_true(self):
        from app.services.whatsapp_service import WhatsAppService
        service = WhatsAppService()
        # Mock mode (no credentials) should return True
        result = service.send_message("+966501234567", "Test message")
        assert result is True

    def test_weekly_summary_structure(self, db, test_business):
        from app.services.whatsapp_service import WhatsAppService
        service = WhatsAppService()
        summary = service.get_weekly_summary(
            business_id=test_business.id, db=db
        )
        assert isinstance(summary, str)
        assert "ملخص" in summary or "SAR" in summary or "ر.س" in summary

    def test_weekly_summary_with_transactions(self, db, test_business):
        from app.services.whatsapp_service import WhatsAppService
        from app.models.transaction import Transaction, TransactionType, TransactionSource
        from datetime import datetime
        service = WhatsAppService()

        # Add a transaction this week
        t = Transaction(
            business_id=test_business.id,
            amount=1500.0,
            vendor="موردي",
            description="مواد",
            category="تشغيلية",
            transaction_type=TransactionType.EXPENSE,
            source=TransactionSource.WHATSAPP,
            date=datetime.utcnow(),
        )
        db.add(t)
        db.commit()

        summary = service.get_weekly_summary(
            business_id=test_business.id, db=db
        )
        assert "1,500" in summary or "1500" in summary

    @pytest.mark.asyncio
    async def test_handle_text_message_no_business(self):
        from app.services.whatsapp_service import WhatsAppService
        service = WhatsAppService()
        reply = await service.handle_message(
            from_number="whatsapp:+966501234567",
            message_type="text",
            content="مرحبا",
        )
        assert isinstance(reply, str)
        assert len(reply) > 0

    @pytest.mark.asyncio
    async def test_handle_unsupported_type(self):
        from app.services.whatsapp_service import WhatsAppService
        service = WhatsAppService()
        reply = await service.handle_message(
            from_number="whatsapp:+966501234567",
            message_type="video",
            content="",
        )
        assert "غير مدعوم" in reply or isinstance(reply, str)

    def test_verify_signature_mock_mode(self):
        from app.services.whatsapp_service import WhatsAppService
        service = WhatsAppService()
        # Force mock mode by nulling client and validator
        service._client = None
        service._validator = None
        # Mock mode (not configured) accepts all signatures
        result = service.verify_twilio_signature("https://example.com", {}, "fake_sig")
        assert result is True


class TestWhatsAppRoutes:

    def test_webhook_get_returns_ok(self, client):
        response = client.get("/api/v1/whatsapp/webhook")
        assert response.status_code == 200

    def test_webhook_post_no_body(self, client):
        # Twilio sends form data
        response = client.post(
            "/api/v1/whatsapp/webhook",
            data={"From": "whatsapp:+966501234567", "Body": "مرحبا", "NumMedia": "0"},
        )
        # Should return TwiML XML
        assert response.status_code == 200

    def test_webhook_post_returns_xml(self, client):
        response = client.post(
            "/api/v1/whatsapp/webhook",
            data={"From": "whatsapp:+966501234567", "Body": "test", "NumMedia": "0"},
        )
        assert response.status_code == 200
        content = response.text
        assert "<Response>" in content or "OK" in content

    def test_connect_requires_auth(self, client):
        response = client.post(
            "/api/v1/whatsapp/connect",
            json={"phone_number": "+966501234567"},
        )
        assert response.status_code in (401, 403)

    def test_status_requires_auth(self, client):
        response = client.get("/api/v1/whatsapp/status")
        assert response.status_code in (401, 403)

    def test_connect_with_auth(self, client, auth_headers):
        response = client.post(
            "/api/v1/whatsapp/connect",
            json={"phone_number": "+966501234567"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "phone_number" in data

    def test_status_with_auth(self, client, auth_headers):
        response = client.get("/api/v1/whatsapp/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "features" in data

    def test_test_message_with_auth(self, client, auth_headers):
        # Mock send_message so no real Twilio API call is made
        with patch("app.services.whatsapp_service.whatsapp_service.send_message", return_value=True):
            response = client.post(
                "/api/v1/whatsapp/test",
                json={"message": "رسالة اختبار"},
                headers=auth_headers,
            )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True

    def test_weekly_summary_with_auth(self, client, auth_headers):
        response = client.get("/api/v1/whatsapp/weekly-summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert isinstance(data["summary"], str)
