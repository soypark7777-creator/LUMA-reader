"""Smoke test Google Vision OCR configuration without printing key contents."""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


ONE_PIXEL_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/"
    "x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="Optional image path to OCR.")
    args = parser.parse_args()

    load_dotenv(override=True)

    from app.services.google_vision_ocr import (
        extract_text_google_vision,
        get_google_vision_status,
        resolve_credentials_path,
    )

    status = get_google_vision_status()
    resolved = resolve_credentials_path()
    print("engine:", status.get("engine"))
    print("credentials_path:", status.get("credentials_path"))
    print("resolved_exists:", resolved.exists())

    try:
        from google.cloud import vision

        vision.ImageAnnotatorClient()
        print("client:", "ok")
    except Exception as exc:
        print("client:", "error")
        print("error:", exc)
        return 1

    if args.image:
        image_bytes = Path(args.image).read_bytes()
    else:
        image_bytes = base64.b64decode(ONE_PIXEL_PNG)

    try:
        result = extract_text_google_vision(image_bytes, args.image or "one-pixel.png")
        print("ocr:", "ok")
        print("text_length:", result.get("text_length", 0))
        print("source:", result.get("source"))
        return 0
    except Exception as exc:
        print("ocr:", "error")
        print("error:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
