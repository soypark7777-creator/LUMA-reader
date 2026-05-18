"""Smoke check for LUMA Google Vision OCR credentials."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def main() -> int:
    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./secrets/google-vision-key.json")
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = Path.cwd() / resolved

    print(f"GOOGLE_APPLICATION_CREDENTIALS={path}")
    print(f"resolved={resolved}")
    print(f"exists={resolved.exists()}")

    if not resolved.exists():
        return 1

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(resolved)

    try:
        print("importing google.cloud.vision...")
        from google.cloud import vision

        print("creating ImageAnnotatorClient...")
        vision.ImageAnnotatorClient()
        print("client=ok")
        return 0
    except Exception as exc:
        print(f"client=failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
