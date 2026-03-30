"""
Transcription Service Tests.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.transcription import TranscriptionService


class TestTranscriptionService:
    """Test transcription service (Google Cloud STT primary, Whisper fallback)."""

    def test_mock_transcribe_returns_arabic(self):
        service = TranscriptionService()
        service._client = None
        service._openai_client = None
        result = service._mock_transcribe()
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain Arabic text
        assert any("\u0600" <= c <= "\u06FF" for c in result)

    @pytest.mark.asyncio
    async def test_transcribe_without_api_key_uses_mock(self):
        service = TranscriptionService()
        # Null out ALL clients so mock path is taken (Groq, Google, OpenAI)
        service._client = None
        service._groq_client = None
        service._openai_client = None
        result = await service.transcribe_audio(b"fake audio bytes" * 100)
        assert "حولت" in result or "ريال" in result

    @pytest.mark.asyncio
    async def test_transcribe_empty_audio_raises(self):
        service = TranscriptionService()
        service._client = MagicMock()  # Real client mode
        with pytest.raises(ValueError, match="empty or too small"):
            await service.transcribe_audio(b"")

    @pytest.mark.asyncio
    async def test_transcribe_tiny_audio_raises(self):
        service = TranscriptionService()
        service._client = MagicMock()  # Real client mode
        with pytest.raises(ValueError, match="empty or too small"):
            await service.transcribe_audio(b"tiny")

    def test_whisper_prompt_contains_financial_terms(self):
        assert "ريال" in TranscriptionService.WHISPER_PROMPT
        assert "فاتورة" in TranscriptionService.WHISPER_PROMPT
        assert "حولت" in TranscriptionService.WHISPER_PROMPT
        assert "دفعت" in TranscriptionService.WHISPER_PROMPT

    @pytest.mark.asyncio
    async def test_transcribe_with_mock_client(self):
        """Test transcription with mocked Google Cloud STT client."""
        service = TranscriptionService()

        # Mock Google Cloud STT response structure
        mock_alternative = MagicMock()
        mock_alternative.transcript = "حولت ثلاثة آلاف للمراعي"

        mock_result = MagicMock()
        mock_result.alternatives = [mock_alternative]

        mock_response = MagicMock()
        mock_response.results = [mock_result]

        mock_client = MagicMock()
        mock_client.recognize.return_value = mock_response

        # Patch google.cloud.speech_v2 so the import inside transcribe_audio works
        mock_types = MagicMock()
        mock_types.RecognitionConfig.return_value = MagicMock()
        mock_types.RecognizeRequest.return_value = MagicMock()
        mock_types.AutoDetectDecodingConfig.return_value = MagicMock()
        mock_types.RecognitionFeatures.return_value = MagicMock()
        mock_types.SpeechAdaptation.return_value = MagicMock()
        mock_types.SpeechAdaptation.AdaptationPhraseSet.return_value = MagicMock()
        mock_types.PhraseSet.return_value = MagicMock()
        mock_types.PhraseSet.Phrase.return_value = MagicMock()

        with patch.dict("sys.modules", {
            "google": MagicMock(),
            "google.cloud": MagicMock(),
            "google.cloud.speech_v2": MagicMock(types=mock_types),
            "google.cloud.speech_v2.types": mock_types,
        }):
            service._client = mock_client
            service._groq_client = None
            service._openai_client = None
            result = await service.transcribe_audio(b"x" * 1000, filename="test.ogg")

        assert result == "حولت ثلاثة آلاف للمراعي"

    @pytest.mark.asyncio
    async def test_transcribe_empty_response_raises(self):
        """Test that empty transcription result raises ValueError."""
        service = TranscriptionService()

        # Mock empty response (no results)
        mock_response = MagicMock()
        mock_response.results = []

        mock_client = MagicMock()
        mock_client.recognize.return_value = mock_response

        mock_types = MagicMock()
        mock_types.RecognitionConfig.return_value = MagicMock()
        mock_types.RecognizeRequest.return_value = MagicMock()
        mock_types.AutoDetectDecodingConfig.return_value = MagicMock()
        mock_types.RecognitionFeatures.return_value = MagicMock()
        mock_types.SpeechAdaptation.return_value = MagicMock()
        mock_types.PhraseSet.return_value = MagicMock()

        with patch.dict("sys.modules", {
            "google": MagicMock(),
            "google.cloud": MagicMock(),
            "google.cloud.speech_v2": MagicMock(types=mock_types),
            "google.cloud.speech_v2.types": mock_types,
        }):
            service._client = mock_client
            service._groq_client = None
            service._openai_client = None
            with pytest.raises(ValueError, match="empty transcription"):
                await service.transcribe_audio(b"x" * 1000)
