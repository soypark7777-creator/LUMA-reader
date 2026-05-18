"""Google Cloud Vision OCR helpers for the LUMA OCR MVP."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def credentials_path() -> str:
    return os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./secrets/google-vision-key.json")


def resolve_credentials_path() -> Path:
    path = Path(credentials_path())
    if not path.is_absolute():
        path = _project_root() / path
    return path


def get_google_vision_status() -> dict[str, Any]:
    path = credentials_path()
    resolved = resolve_credentials_path()
    return {
        "engine": "google_vision",
        "source": "google_vision_status",
        "credentials_path": path,
        "credentials_exists": resolved.exists(),
        "fallback_available": True,
    }


def extract_text_google_vision(image_bytes: bytes, filename: str = "") -> dict[str, Any]:
    """Extract OCR text with Google Cloud Vision document_text_detection."""
    if not image_bytes:
        raise ValueError("Empty image file.")

    resolved = resolve_credentials_path()
    if not resolved.exists():
        raise RuntimeError(
            f"Google Vision credentials not found: {credentials_path()}"
        )

    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(resolved))

    try:
        from google.cloud import vision
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-vision is not installed. Run: pip install google-cloud-vision"
        ) from exc

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(response.error.message)

    text = response.full_text_annotation.text if response.full_text_annotation else ""
    text = text.strip()
    return {
        "success": True,
        "engine": "google_vision",
        "filename": filename,
        "text": text,
        "text_length": len(text),
        "word_count": len(text.split()),
        "char_count": len(text),
        "source": "google_vision",
        "confidence": 0.95,
    }
