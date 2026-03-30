"""
Transaction API Tests.
"""

import pytest
from unittest.mock import patch, AsyncMock


class TestTransactionEndpoints:
    """Test transaction CRUD and voice pipeline endpoints."""

    def test_list_transactions_empty(self, client, auth_headers):
        response = client.get("/api/v1/transactions/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_transactions_with_data(self, client, auth_headers, sample_transactions):
        response = client.get("/api/v1/transactions/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_list_transactions_pagination(self, client, auth_headers, sample_transactions):
        response = client.get("/api/v1/transactions/?skip=0&limit=2", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_create_transaction(self, client, auth_headers):
        payload = {
            "amount": 3500,
            "category": "تشغيلية",
            "description": "توريد بن",
            "vendor": "المراعي",
        }
        response = client.post("/api/v1/transactions/", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 3500
        assert data["category"] == "تشغيلية"
        assert data["vendor"] == "المراعي"
        assert data["source"] == "manual"

    def test_create_transaction_requires_auth(self, client):
        payload = {"amount": 1000}
        response = client.post("/api/v1/transactions/", json=payload)
        assert response.status_code in (401, 403)

    def test_get_transaction_by_id(self, client, auth_headers, sample_transactions):
        txn_id = sample_transactions[0].id
        response = client.get(f"/api/v1/transactions/{txn_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == txn_id

    def test_get_transaction_not_found(self, client, auth_headers):
        response = client.get("/api/v1/transactions/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_transaction(self, client, auth_headers, sample_transactions):
        txn_id = sample_transactions[0].id
        response = client.delete(f"/api/v1/transactions/{txn_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/v1/transactions/{txn_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_transaction_not_found(self, client, auth_headers):
        response = client.delete("/api/v1/transactions/99999", headers=auth_headers)
        assert response.status_code == 404

    @patch("app.routes.transactions.transcription_service")
    @patch("app.routes.transactions.entity_extractor")
    def test_voice_transaction_success(self, mock_extractor, mock_transcription, client, auth_headers):
        mock_transcription.transcribe_audio = AsyncMock(return_value="حولت خمسة آلاف للمراعي")
        mock_extractor.extract_transaction = AsyncMock(return_value={
            "amount": 5000,
            "vendor": "المراعي",
            "category": "تشغيلية",
            "description": "توريد حليب",
            "confidence": 0.95,
        })

        # Create a fake audio file
        audio_content = b"fake audio content" * 100
        response = client.post(
            "/api/v1/transactions/voice",
            headers=auth_headers,
            files={"audio": ("test.ogg", audio_content, "audio/ogg")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["transaction"]["amount"] == 5000

    @patch("app.routes.transactions.transcription_service")
    @patch("app.routes.transactions.entity_extractor")
    def test_voice_transaction_low_confidence(self, mock_extractor, mock_transcription, client, auth_headers):
        mock_transcription.transcribe_audio = AsyncMock(return_value="حولت مبلغ للمورد")
        mock_extractor.extract_transaction = AsyncMock(return_value={
            "amount": 3000,
            "vendor": "غير محدد",
            "category": "تشغيلية",
            "description": "تحويل",
            "confidence": 0.6,
        })

        audio_content = b"fake audio content" * 100
        response = client.post(
            "/api/v1/transactions/voice",
            headers=auth_headers,
            files={"audio": ("test.ogg", audio_content, "audio/ogg")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "needs_confirmation"
        assert data["extracted_data"] is not None

    @patch("app.routes.transactions.transcription_service")
    @patch("app.routes.transactions.entity_extractor")
    def test_voice_transaction_extraction_failure(self, mock_extractor, mock_transcription, client, auth_headers):
        mock_transcription.transcribe_audio = AsyncMock(return_value="نص غامض")
        mock_extractor.extract_transaction = AsyncMock(return_value=None)

        audio_content = b"fake audio content" * 100
        response = client.post(
            "/api/v1/transactions/voice",
            headers=auth_headers,
            files={"audio": ("test.ogg", audio_content, "audio/ogg")},
        )
        # Returns 201 with error status (not HTTP error)
        data = response.json()
        assert data["status"] == "error"
