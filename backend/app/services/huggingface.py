import httpx
from app.config import get_settings
from app.logging_policy import get_logger

logger = get_logger()


class HuggingFaceError(Exception):
    """Raised when Hugging Face API call fails."""


def transcribe_audio_huggingface(audio_bytes: bytes, content_type: str = "audio/webm") -> str:
    """Transcribes audio using Hugging Face Inference API (openai/whisper-large-v3-turbo)."""
    settings = get_settings()
    model = settings.huggingface_model
    url = f"https://api-inference.huggingface.co/models/{model}"

    headers = {"Content-Type": content_type}
    if settings.huggingface_api_key:
        headers["Authorization"] = f"Bearer {settings.huggingface_api_key}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, content=audio_bytes)
            if response.status_code != 200:
                logger.error("huggingface_stt_error", status_code=response.status_code, body=response.text[:200])
                raise HuggingFaceError(f"Hugging Face STT returned status {response.status_code}")

            data = response.json()
            if isinstance(data, dict) and "text" in data:
                return data["text"].strip()
            elif isinstance(data, list) and len(data) > 0 and "text" in data[0]:
                return data[0]["text"].strip()
            else:
                return str(data).strip()
    except Exception as e:
        logger.error("huggingface_stt_exception", error=str(e))
        raise HuggingFaceError(f"Hugging Face STT request failed: {e}") from e
