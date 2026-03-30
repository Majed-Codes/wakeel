"""
Transcription Service — Google Cloud Speech-to-Text for Arabic voice.

Uses Google Cloud STT v2 with Saudi Arabic model as primary.
Falls back to OpenAI Whisper if Google Cloud is not configured.
"""

import logging
import uuid
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)


class TranscriptionService:
    """خدمة تحويل الصوت إلى نص"""

    # Saudi financial terms — used as Whisper prompt (fallback) and for reference
    WHISPER_PROMPT = (
        "تحويل، ريال، مصاريف، تشغيلية، رأسمالية، إيرادات، زكاة، ضريبة، فاتورة، "
        "مورد، عميل، راتب، إيجار، كهرباء، ماء، صيانة، توريد، مبيعات، أرباح، "
        "حولت، دفعت، استلمت، صرفت، اشتريت، بعت، "
        "المراعي، نادك، أرامكو، الاتصالات، موبايلي، زين، "
        "ألف، ألفين، ثلاثة آلاف، خمسة آلاف، عشرة آلاف، عشرين ألف، مية ألف"
    )

    # Saudi financial phrases for Google Cloud Speech Adaptation
    FINANCIAL_PHRASES = [
        "تحويل", "ريال", "مصاريف", "تشغيلية", "رأسمالية", "إيرادات",
        "زكاة", "ضريبة", "فاتورة", "مورد", "عميل", "راتب", "إيجار",
        "كهرباء", "ماء", "صيانة", "توريد", "مبيعات", "أرباح",
        "حولت", "دفعت", "استلمت", "صرفت", "اشتريت", "بعت",
        "المراعي", "نادك", "أرامكو", "الاتصالات", "موبايلي", "زين",
        "ألف", "ألفين", "ثلاثة آلاف", "خمسة آلاف", "عشرة آلاف", "عشرين ألف",
    ]

    def __init__(self):
        self._client = None        # Google Cloud STT
        self._groq_client = None   # Groq Whisper (free, fast)
        self._openai_client = None # OpenAI Whisper (paid fallback)

        if settings.has_google_cloud:
            try:
                from google.cloud.speech_v2 import SpeechClient
                self._client = SpeechClient()
                logger.info("Transcription: using Google Cloud Speech-to-Text")
            except Exception as e:
                logger.warning(f"Google Cloud Speech init failed: {e}")

        if not self._client and settings.has_groq_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info("Transcription: using Groq Whisper large-v3 (free)")
            except Exception as e:
                logger.warning(f"Groq init failed: {e}")

        if not self._client and not self._groq_client and settings.has_openai_key:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("Transcription: using OpenAI Whisper (fallback)")

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.ogg") -> str:
        """
        Transcribe audio bytes to Arabic text.

        Priority: Google Cloud STT → Groq Whisper (free) → OpenAI Whisper → Mock
        """
        if not self._client and not self._groq_client and not self._openai_client:
            logger.warning("No transcription service configured — using mock")
            return self._mock_transcribe()

        if not audio_bytes or len(audio_bytes) < 100:
            raise ValueError("Audio file is empty or too small")

        # Groq Whisper (free, fast — preferred when no Google Cloud)
        if not self._client and self._groq_client:
            return await self._transcribe_groq(audio_bytes, filename)

        # OpenAI Whisper fallback
        if not self._client and self._openai_client:
            return await self._transcribe_openai(audio_bytes, filename)

        # Primary: Google Cloud Speech-to-Text v2
        try:
            from google.cloud.speech_v2 import types

            config = types.RecognitionConfig(
                auto_decoding_config=types.AutoDetectDecodingConfig(),
                language_codes=["ar-SA"],
                model="long",
                features=types.RecognitionFeatures(
                    enable_automatic_punctuation=True,
                ),
                adaptation=types.SpeechAdaptation(
                    phrase_sets=[
                        types.SpeechAdaptation.AdaptationPhraseSet(
                            inline_phrase_set=types.PhraseSet(
                                phrases=[
                                    types.PhraseSet.Phrase(value=phrase, boost=10.0)
                                    for phrase in self.FINANCIAL_PHRASES
                                ]
                            )
                        )
                    ]
                ),
            )

            request = types.RecognizeRequest(
                recognizer=f"projects/{settings.GOOGLE_CLOUD_PROJECT_ID}/locations/{settings.GOOGLE_CLOUD_LOCATION}/recognizers/_",
                config=config,
                content=audio_bytes,
            )

            response = self._client.recognize(request=request)

            transcript_parts = []
            for result in response.results:
                if result.alternatives:
                    transcript_parts.append(result.alternatives[0].transcript)

            text = " ".join(transcript_parts).strip()

            if not text:
                raise ValueError("Speech-to-Text returned empty transcription")

            logger.info(f"Transcribed audio ({len(audio_bytes)} bytes): {text[:80]}...")
            return text

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Google Cloud transcription failed: {e}")
            # Try OpenAI Whisper as fallback
            if self._openai_client:
                logger.info("Falling back to OpenAI Whisper...")
                return await self._transcribe_openai(audio_bytes, filename)
            raise

    async def _transcribe_groq(self, audio_bytes: bytes, filename: str) -> str:
        """Transcribe using Groq Whisper large-v3 — free tier, fast Arabic support."""
        try:
            temp_path = Path(f"/tmp/wakeel_{uuid.uuid4().hex}_{filename}")
            temp_path.write_bytes(audio_bytes)

            with open(temp_path, "rb") as audio_file:
                response = self._groq_client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=audio_file,
                    language="ar",
                    prompt=self.WHISPER_PROMPT,
                    response_format="text",
                )

            temp_path.unlink(missing_ok=True)

            text = response.strip() if isinstance(response, str) else response.text.strip()
            if not text:
                raise ValueError("Groq Whisper returned empty transcription")

            logger.info(f"Groq Whisper transcribed ({len(audio_bytes)} bytes): {text[:80]}...")
            return text

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Groq transcription failed: {e}")
            # Try OpenAI as last resort
            if self._openai_client:
                logger.info("Falling back to OpenAI Whisper...")
                return await self._transcribe_openai(audio_bytes, filename)
            raise

    async def _transcribe_openai(self, audio_bytes: bytes, filename: str) -> str:
        """Fallback: transcribe using OpenAI Whisper."""
        try:
            temp_path = Path(f"/tmp/wakeel_{uuid.uuid4().hex}_{filename}")
            temp_path.write_bytes(audio_bytes)

            with open(temp_path, "rb") as audio_file:
                response = self._openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ar",
                    prompt=self.WHISPER_PROMPT,
                )

            temp_path.unlink(missing_ok=True)

            text = response.text.strip()
            if not text:
                raise ValueError("Whisper returned empty transcription")

            logger.info(f"Transcribed audio via Whisper ({len(audio_bytes)} bytes): {text[:80]}...")
            return text

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise

    def _mock_transcribe(self) -> str:
        """Mock transcription for development without API key."""
        return "حولت خمسة آلاف ريال للمراعي مقابل توريد حليب"


transcription_service = TranscriptionService()
