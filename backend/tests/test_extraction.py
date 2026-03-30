"""
Entity Extraction Service Tests.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.extraction import EntityExtractor, CATEGORY_MAP


class TestEntityExtractor:
    """Test entity extraction from Arabic financial text."""

    def test_mock_extract_returns_valid_structure(self):
        extractor = EntityExtractor()
        extractor._client = None  # Force mock mode
        extractor._openai_client = None
        result = extractor._mock_extract("حولت خمسة آلاف للمراعي")
        assert "amount" in result
        assert "vendor" in result
        assert "category" in result
        assert "description" in result
        assert "confidence" in result

    def test_mock_extract_amount_is_number(self):
        extractor = EntityExtractor()
        extractor._client = None
        extractor._openai_client = None
        result = extractor._mock_extract("test")
        assert isinstance(result["amount"], (int, float))
        assert result["amount"] > 0

    def test_mock_extract_confidence_in_range(self):
        extractor = EntityExtractor()
        extractor._client = None
        extractor._openai_client = None
        result = extractor._mock_extract("test")
        assert 0 <= result["confidence"] <= 1

    def test_mock_extract_category_is_arabic(self):
        extractor = EntityExtractor()
        extractor._client = None
        extractor._openai_client = None
        result = extractor._mock_extract("test")
        assert result["category"] in ("تشغيلية", "رأسمالية", "إيرادات")

    def test_category_map_has_all_values(self):
        assert "OpEx" in CATEGORY_MAP
        assert "CapEx" in CATEGORY_MAP
        assert "Revenue" in CATEGORY_MAP
        assert CATEGORY_MAP["OpEx"] == "تشغيلية"
        assert CATEGORY_MAP["CapEx"] == "رأسمالية"
        assert CATEGORY_MAP["Revenue"] == "إيرادات"

    @pytest.mark.asyncio
    async def test_extract_with_mock_client(self):
        """Test extraction with mocked Anthropic client."""
        extractor = EntityExtractor()

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='{"amount": 5000, "vendor": "المراعي", "category": "OpEx", "description": "توريد حليب", "confidence": 0.95}')
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        extractor._client = mock_client

        result = await extractor.extract_transaction("حولت خمسة آلاف للمراعي")
        assert result is not None
        assert result["amount"] == 5000
        assert result["vendor"] == "المراعي"
        # Category should be mapped to Arabic
        assert result["category"] == "تشغيلية"

    @pytest.mark.asyncio
    async def test_extract_handles_json_error(self):
        """Test extraction handles invalid JSON from Claude."""
        extractor = EntityExtractor()

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="not valid json")
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        extractor._client = mock_client

        result = await extractor.extract_transaction("test text")
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_handles_api_error(self):
        """Test extraction handles API errors gracefully."""
        extractor = EntityExtractor()

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        extractor._client = mock_client

        result = await extractor.extract_transaction("test text")
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_without_api_key_uses_mock(self):
        extractor = EntityExtractor()
        extractor._client = None
        extractor._openai_client = None
        result = await extractor.extract_transaction("حولت خمسة آلاف")
        assert result is not None
        assert result["amount"] == 5000.0
