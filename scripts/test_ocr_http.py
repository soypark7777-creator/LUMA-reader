"""Smoke test the running OCR HTTP endpoints."""
from __future__ import annotations

import argparse
import base64
from io import BytesIO

import requests


ONE_PIXEL_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/"
    "x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:5000")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    health = requests.get(f"{base_url}/ocr/health", timeout=10)
    print("health_status:", health.status_code)
    print("health_json:", health.json())

    image_bytes = base64.b64decode(ONE_PIXEL_PNG)
    files = {"file": ("one-pixel.png", BytesIO(image_bytes), "image/png")}
    response = requests.post(f"{base_url}/ocr", files=files, timeout=30)
    print("ocr_status:", response.status_code)
    print("ocr_json:", response.json())
    return 0 if response.ok and response.json().get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
