"""OCR helpers used by the /api/ocr routes.

The service tries Google Vision first when credentials exist, then Gemini
Vision, and finally deterministic mock data so the frontend can keep working
without external API keys.
"""
from __future__ import annotations

import base64
import hashlib
import io
import os
import re
from typing import Optional


_gemini_ok = False
_vision_model = None
_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

try:
    import google.generativeai as genai

    _api_key = os.getenv("GEMINI_API_KEY", "")
    if _api_key and _api_key not in ("YOUR_GEMINI_API_KEY", "여기에_발급받은_API_KEY_입력", ""):
        genai.configure(api_key=_api_key)
        _vision_model = genai.GenerativeModel(_MODEL_NAME)
        _gemini_ok = True
        print(f"[OK] Gemini Vision OCR connected ({_MODEL_NAME})")
    else:
        print("[WARN] Gemini Vision not configured -> OCR mock mode")
except ImportError:
    print("[WARN] google-generativeai not installed -> OCR mock mode")
except Exception as exc:
    print(f"[WARN] Gemini Vision init failed: {exc} -> OCR mock mode")


_pillow_ok = False
try:
    from PIL import Image, ImageEnhance, ImageFilter

    _pillow_ok = True
except ImportError:
    pass


_MOCK_TEXTS = [
    "역사상 가장 중요한 사실은, 인류가 무언가를 집단적으로 상상하기 시작하면 그것은 점점 더 강력한 힘을 갖게 된다는 것이다.",
    "우리는 별의 재료로 만들어졌다. 이 우주적 관점은 일상의 사소한 갈등을 얼마나 작게 만드는가.",
    "가장 중요한 것은 눈에 보이지 않아. 마음으로만 볼 수 있어. 사람들은 이 진리를 잊어버렸어.",
    "새는 알을 깨고 나온다. 알은 세계다. 태어나려는 자는 하나의 세계를 파괴해야 한다.",
    "인간은 의미를 추구하는 존재다. 어떤 상황에서도 삶의 의미를 발견할 수 있다면, 그 사람은 살아남을 수 있다.",
    "행복은 완성된 상태가 아니라, 무언가를 향해 나아가는 과정에 있다.",
]

_MOCK_BOOKS = [
    {"title": "사피엔스", "author": "유발 하라리", "publisher": "김영사", "subtitle": "유인원에서 사이보그까지", "language": "ko"},
    {"title": "어린 왕자", "author": "생텍쥐페리", "publisher": "문학동네", "subtitle": None, "language": "ko"},
    {"title": "코스모스", "author": "칼 세이건", "publisher": "사이언스북스", "subtitle": "Carl Sagan's Cosmos", "language": "ko"},
]


def _bytes_to_image(image_bytes: bytes):
    """Convert bytes to a PIL Image when Pillow is installed."""
    if not _pillow_ok:
        return None
    try:
        return Image.open(io.BytesIO(image_bytes))
    except Exception:
        return None


def _preprocess_image(image_bytes: bytes) -> bytes:
    """Improve contrast and minimum width for OCR when Pillow is available."""
    if not _pillow_ok:
        return image_bytes
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("L")
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)
        w, h = img.size
        if w < 800:
            ratio = 800 / w
            img = img.resize((int(w * ratio), int(h * ratio)))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return image_bytes


def _image_payload_for_gemini(image_bytes: bytes) -> tuple[bytes, str]:
    """Return image bytes and a matching MIME type for Gemini Vision."""
    if not _pillow_ok:
        return image_bytes, "image/png"
    try:
        img = Image.open(io.BytesIO(image_bytes))
        fmt = (img.format or "PNG").upper()
        mime = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg",
            "WEBP": "image/webp",
            "GIF": "image/gif",
        }.get(fmt)
        if mime:
            return image_bytes, mime
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return buf.getvalue(), "image/png"
    except Exception:
        return image_bytes, "image/png"


def _gemini_ocr(image_bytes: bytes, prompt: str) -> Optional[str]:
    """Analyze an image with Gemini Vision."""
    if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("LUMA_DISABLE_EXTERNAL_AI"):
        return None
    if not _gemini_ok or not _vision_model:
        return None
    try:
        payload_bytes, mime_type = _image_payload_for_gemini(image_bytes)
        img_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(payload_bytes).decode(),
            }
        }
        response = _vision_model.generate_content([prompt, img_part], request_options={"timeout": 8})
        return response.text.strip()
    except Exception as exc:
        print(f"[Gemini Vision error] {exc}")
        return None


def _mock_extract(image_bytes: bytes, mode: str = "text") -> str:
    seed = int(hashlib.md5(image_bytes[:64]).hexdigest(), 16)
    return _MOCK_TEXTS[seed % len(_MOCK_TEXTS)]


def extract_text(image_bytes: bytes, language: str = "ko") -> dict:
    """Extract text from an image with Google Vision, Gemini, or mock fallback."""
    try:
        from app.services.google_vision_ocr import extract_text_google_vision, get_google_vision_status

        google_status = get_google_vision_status()
        if google_status.get("credentials_exists"):
            result = extract_text_google_vision(image_bytes)
            return {"ok": True, **result}
    except Exception as exc:
        print(f"[Google Vision OCR error] {exc} -> fallback mode")

    processed = _preprocess_image(image_bytes)
    prompt = f"""이 이미지에서 텍스트를 추출해주세요.
언어: {language}
규칙:
- 이미지에 있는 텍스트를 그대로 추출
- 줄바꿈은 실제 문단 구분에만 사용
- 인쇄 오류나 얼룩은 무시
- 설명 없이 텍스트만 출력"""
    raw = _gemini_ocr(processed, prompt)

    if raw:
        text = _clean_text(raw)
        source = "gemini"
        confidence = 0.92
    else:
        text = _mock_extract(image_bytes)
        source = "mock"
        confidence = 0.75

    return {
        "ok": True,
        "text": text,
        "confidence": confidence,
        "source": source,
        "engine": source,
        "language": _detect_language(text),
        "word_count": len(text.split()),
        "char_count": len(text),
    }


def enhance_text(raw_text: str) -> dict:
    """Correct OCR text without changing the meaning."""
    from app.services.gemini_service import _call_gemini, _parse_json_safe

    prompt = f"""다음 OCR 추출 텍스트를 교정해주세요.

원문:
{raw_text}

규칙:
- 명백한 오탈자만 교정하고 의미는 바꾸지 않기
- 한국어 띄어쓰기와 문장 부호 정리
- JSON 형식으로만 응답

{{
  "corrected": "교정된 텍스트",
  "changes": ["변경사항 1", "변경사항 2"],
  "quality": "excellent|good|fair|poor"
}}"""
    raw = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None
    if parsed and "corrected" in parsed:
        return {
            "ok": True,
            "original": raw_text,
            "corrected": parsed["corrected"],
            "changes": parsed.get("changes", []),
            "quality": parsed.get("quality", "good"),
            "source": "gemini",
        }
    return {
        "ok": True,
        "original": raw_text,
        "corrected": raw_text,
        "changes": [],
        "quality": "good",
        "source": "mock",
    }


def detect_book_info(image_bytes: bytes) -> dict:
    """Detect book cover metadata from an image."""
    prompt = """이 이미지는 책 표지입니다. 다음 JSON 형식으로만 응답하세요.
{
  "title": "책 제목",
  "author": "저자명",
  "publisher": "출판사 또는 null",
  "subtitle": "부제 또는 null",
  "language": "ko|en|ja|zh|other"
}"""
    raw = _gemini_ocr(image_bytes, prompt)
    if raw:
        from app.services.gemini_service import _parse_json_safe

        parsed = _parse_json_safe(raw)
        if parsed and "title" in parsed:
            return {"ok": True, **parsed, "source": "gemini", "confidence": 0.88}

    seed = int(hashlib.md5(image_bytes[:32]).hexdigest(), 16) % len(_MOCK_BOOKS)
    return {"ok": True, **_MOCK_BOOKS[seed], "source": "mock", "confidence": 0.70}


def analyze_page(image_bytes: bytes) -> dict:
    """Analyze page layout and notable text."""
    prompt = """이 책 페이지를 분석해주세요. JSON 형식으로만 응답하세요.
{
  "full_text": "전체 텍스트",
  "paragraphs": ["문단1", "문단2"],
  "quotes": ["인용구"],
  "emphasized": ["강조 텍스트"],
  "page_number": null
}"""
    raw = _gemini_ocr(image_bytes, prompt)
    if raw:
        from app.services.gemini_service import _parse_json_safe

        parsed = _parse_json_safe(raw)
        if parsed and "full_text" in parsed:
            return {"ok": True, **parsed, "source": "gemini"}

    mock_text = _mock_extract(image_bytes)
    return {
        "ok": True,
        "full_text": mock_text,
        "paragraphs": [mock_text],
        "quotes": [],
        "emphasized": [],
        "page_number": None,
        "source": "mock",
    }


def generate_memo_from_text(extracted_text: str, book_title: str = "") -> dict:
    """Generate a reader memo draft from extracted text."""
    from app.services.gemini_service import _call_gemini, _parse_json_safe

    prompt = f"""다음 책 구절을 읽고 독자의 메모 초안을 생성해주세요.

책: {book_title or '제목 없음'}
구절: {extracted_text}

구절에서 독자가 붙잡을 수 있는 생각, 감상, 연결되는 아이디어를 1-2문장으로 작성해주세요.
JSON 형식으로만 응답하세요.

{{
  "memo_draft": "메모 초안",
  "tags": ["태그1", "태그2", "태그3"],
  "mood": "inspired|emotional|curious|neutral",
  "insight": "핵심 인사이트"
}}"""
    raw = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None
    if parsed and "memo_draft" in parsed:
        return {"ok": True, **parsed, "source": "gemini", "original_text": extracted_text}

    preview = extracted_text[:40].strip()
    return {
        "ok": True,
        "memo_draft": f"이 구절에서 깊은 인상을 받았다. '{preview}...'라는 문장이 오늘의 생각을 오래 붙잡게 한다.",
        "tags": ["독서", "인문", "생각"],
        "mood": "inspired",
        "insight": "이 문장은 평소 당연하게 여기던 관점을 다시 묻게 합니다.",
        "source": "mock",
        "original_text": extracted_text,
    }


def _clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _detect_language(text: str) -> str:
    korean = len(re.findall(r"[가-힣]", text))
    japanese = len(re.findall(r"[\u3040-\u30ff]", text))
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    english = len(re.findall(r"[a-zA-Z]", text))
    counts = {"ko": korean, "ja": japanese, "zh": chinese, "en": english}
    return max(counts, key=counts.get)


def get_ocr_status() -> dict:
    try:
        from app.services.google_vision_ocr import get_google_vision_status

        google_status = get_google_vision_status()
    except Exception:
        google_status = {
            "engine": "google_vision",
            "credentials_path": None,
            "credentials_exists": False,
            "source": "status_error",
        }

    mode = "google-vision" if google_status.get("credentials_exists") else ("gemini-vision" if _gemini_ok else "mock")
    return {
        "google_vision": google_status.get("credentials_exists", False),
        "google_vision_status": google_status,
        "gemini_vision": _gemini_ok,
        "pillow": _pillow_ok,
        "mode": mode,
        "engine": mode,
        "source": mode,
        "model": _MODEL_NAME if _gemini_ok else None,
        "fallback_available": True,
    }
