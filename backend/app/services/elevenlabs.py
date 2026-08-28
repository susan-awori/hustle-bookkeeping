from __future__ import annotations

import httpx

from app.config import get_settings

STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
TTS_URL_TEMPLATE = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/webm;codecs=opus",
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/ogg",
    "audio/x-wav",
}


class ElevenLabsError(RuntimeError):
    pass


def transcribe_audio(audio_bytes: bytes, content_type: str, filename: str = "take.webm") -> str:
    settings = get_settings()
    if not settings.elevenlabs_api_key.strip():
        raise ElevenLabsError("ElevenLabs API key is not configured")
    headers = {"xi-api-key": settings.elevenlabs_api_key}
    data = {"model_id": "scribe_v1", "language_code": "sw"}
    files = {"file": (filename, audio_bytes, content_type.split(";")[0])}
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(STT_URL, headers=headers, data=data, files=files)
    except httpx.HTTPError as exc:
        raise ElevenLabsError("Speech-to-text request failed") from exc
    if response.status_code >= 400:
        raise ElevenLabsError("Speech-to-text rejected the audio")
    payload = response.json()
    text = (payload.get("text") or "").strip()
    if not text:
        raise ElevenLabsError("Empty transcript")
    return text


def synthesize_speech(text: str) -> bytes:
    settings = get_settings()
    if not settings.elevenlabs_api_key.strip():
        raise ElevenLabsError("ElevenLabs API key is not configured")
    url = TTS_URL_TEMPLATE.format(voice_id=settings.elevenlabs_voice_id)
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.7},
    }
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise ElevenLabsError("Text-to-speech request failed") from exc
    if response.status_code >= 400:
        raise ElevenLabsError("Text-to-speech rejected the request")
    return response.content
