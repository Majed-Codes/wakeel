"""
Chat API Tests.
"""

import pytest
from unittest.mock import patch, AsyncMock


class TestChatEndpoints:
    """Test chat API endpoints."""

    @patch("app.routes.chat.financial_rag")
    def test_send_message(self, mock_rag, client, auth_headers):
        mock_rag.answer_query = AsyncMock(return_value="مرحباً! أنا وكيل، مساعدك المالي.")
        mock_rag.index_transactions.return_value = None

        response = client.post(
            "/api/v1/chat/",
            json={"message": "مرحبا"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"
        assert "وكيل" in data["content"]
        assert "created_at" in data

    @patch("app.routes.chat.financial_rag")
    def test_send_message_saves_history(self, mock_rag, client, auth_headers):
        mock_rag.answer_query = AsyncMock(return_value="إجابة تجريبية")
        mock_rag.index_transactions.return_value = None

        # Send a message
        client.post(
            "/api/v1/chat/",
            json={"message": "كم المصاريف؟"},
            headers=auth_headers,
        )

        # Check history
        response = client.get("/api/v1/chat/history", headers=auth_headers)
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) == 2  # user + assistant
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_send_message_requires_auth(self, client):
        response = client.post("/api/v1/chat/", json={"message": "hello"})
        assert response.status_code in (401, 403)

    def test_get_history_empty(self, client, auth_headers):
        response = client.get("/api/v1/chat/history", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @patch("app.routes.chat.financial_rag")
    def test_chat_passes_history_to_rag(self, mock_rag, client, auth_headers):
        mock_rag.answer_query = AsyncMock(return_value="response")
        mock_rag.index_transactions.return_value = None

        # Send first message
        client.post(
            "/api/v1/chat/",
            json={"message": "مرحبا"},
            headers=auth_headers,
        )

        # Send second message — should include history
        client.post(
            "/api/v1/chat/",
            json={"message": "كم المصاريف؟"},
            headers=auth_headers,
        )

        # The second call should have chat_history
        second_call = mock_rag.answer_query.call_args_list[1]
        assert second_call.kwargs.get("chat_history") is not None or len(second_call.args) > 2

    def test_send_empty_message_rejected(self, client, auth_headers):
        response = client.post(
            "/api/v1/chat/",
            json={"message": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @patch("app.routes.chat.financial_rag")
    def test_multiple_messages_in_history(self, mock_rag, client, auth_headers):
        mock_rag.answer_query = AsyncMock(return_value="إجابة")
        mock_rag.index_transactions.return_value = None

        for i in range(5):
            client.post(
                "/api/v1/chat/",
                json={"message": f"سؤال رقم {i+1}"},
                headers=auth_headers,
            )

        response = client.get("/api/v1/chat/history?limit=50", headers=auth_headers)
        messages = response.json()
        assert len(messages) == 10  # 5 user + 5 assistant
