"""
OCR 서비스 — 이미지에서 텍스트 추출
────────────────────────────────────────
기능:
  1. extract_text()       이미지 → 텍스트 변환 (핵심)
  2. enhance_text()       추출 텍스트 정제/교정
  3. detect_book_info()   표지 이미지로 책 정보 감지
  4. analyze_page()       페이지 이미지 분석 (문단/인용구 구분)

Gemini Vision API 없으면 → Pillow 기반 Mock으로 자동 폴백
"""
import os
import io
import base64
import re
from typing import Optional

# ── Gemini Vision 초기화 ────────────────────────────────────
_gemini_ok = False
_vision_model = None
_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

try:
    import google.generativeai as genai
    _api_key = os.getenv("GEMINI_API_KEY", "")
    if _api_key and _api_key not in ("여기에_발급받은_키_입력", ""):
        genai.configure(api_key=_api_key)
        _vision_model = genai.GenerativeModel(_MODEL_NAME)
        _gemini_ok = True
        print(f"[OK] Gemini Vision OCR connected ({_MODEL_NAME})")
    else:
        print("[WARN] Gemini Vision not configured -> OCR mock mode")
except ImportError:
    print("[WARN] google-generativeai not installed -> OCR mock mode")
except Exception as e:
    print(f"[WARN] Gemini Vision init failed: {e} -> OCR mock mode")

# ── Pillow 초기화 ───────────────────────────────────────────
_pillow_ok = False
try:
    from PIL import Image, ImageFilter, ImageEnhance
    _pillow_ok = True
except ImportError:
    pass


# ══════════════════════════════════════════════════════════════
#  내부 헬퍼
# ══════════════════════════════════════════════════════════════

def _bytes_to_image(image_bytes: bytes):
    """bytes → PIL Image"""
    if not _pillow_ok:
        return None
    try:
        from PIL import Image
        return Image.open(io.BytesIO(image_bytes))
    except Exception:
        return None


def _preprocess_image(image_bytes: bytes) -> bytes:
    """OCR 정확도 향상을 위한 이미지 전처리"""
    if not _pillow_ok:
        return image_bytes
    try:
        from PIL import Image, ImageFilter, ImageEnhance
        img = Image.open(io.BytesIO(image_bytes))

        # 그레이스케일 변환
        img = img.convert("L")

        # 대비 강화
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)

        # 선명도 강화
        img = img.filter(ImageFilter.SHARPEN)

        # 최소 해상도 보장
        w, h = img.size
        if w < 800:
            ratio = 800 / w
            img = img.resize((int(w * ratio), int(h * ratio)))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return image_bytes


def _gemini_ocr(image_bytes: bytes, prompt: str) -> Optional[str]:
    """Gemini Vision으로 이미지 분석"""
    if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("LUMA_DISABLE_EXTERNAL_AI"):
        return None
    if not _gemini_ok or not _vision_model:
        return None
    try:
        import google.generativeai as genai

        # bytes → base64 → Part
        img_part = {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode(),
            }
        }
        resp = _vision_model.generate_content([prompt, img_part], request_options={"timeout": 8})
        return resp.text.strip()
    except Exception as e:
        print(f"[Gemini Vision 오류] {e}")
        return None


# ══════════════════════════════════════════════════════════════
#  Mock OCR 텍스트 샘플 (Gemini 없을 때)
# ══════════════════════════════════════════════════════════════
_MOCK_TEXTS = [
    "역사상 가장 중요한 사실은, 일단 인류가 무언가를 집단적으로 상상하기 시작하면, 그것은 점점 더 강력한 힘을 갖게 된다는 것이다.",
    "우리는 별의 재료로 만들어졌다. 이 우주적 관점이 일상의 사소한 갈등을 얼마나 작게 만드는가.",
    "가장 중요한 것은 눈에 보이지 않아. 마음으로만 볼 수 있어. 사람들이 이 진리를 잊어버렸어.",
    "새는 알을 깨고 나온다. 알은 세계다. 태어나려는 자는 하나의 세계를 파괴해야 한다.",
    "인간은 의미를 추구하는 존재다. 어떤 상황에서도 삶의 의미를 발견할 수 있다면, 그 사람은 살아남을 수 있다.",
    "우리가 두려워해야 할 유일한 것은 두려움 그 자체다.",
    "문명이란 폭력을 독점하고 그것을 정당화하는 집단의 이야기다.",
    "행복은 완성된 상태가 아니라, 무언가를 향해 나아가는 과정에 있다.",
]

import hashlib
import random


def _mock_extract(image_bytes: bytes, mode: str = "text") -> str:
    """이미지 해시 기반 일관된 Mock 텍스트 반환"""
    seed = int(hashlib.md5(image_bytes[:64]).hexdigest(), 16)
    idx  = seed % len(_MOCK_TEXTS)
    return _MOCK_TEXTS[idx]


# ══════════════════════════════════════════════════════════════
#  1. 핵심: 이미지 → 텍스트 추출
# ══════════════════════════════════════════════════════════════

def extract_text(image_bytes: bytes, language: str = "ko") -> dict:
    """
    이미지에서 텍스트를 추출한다.

    반환:
        {
          "text":       추출된 텍스트,
          "confidence": 신뢰도 (0~1),
          "source":     "gemini" | "mock",
          "language":   감지 언어,
          "word_count": 단어 수,
        }
    """
    # 이미지 전처리
    processed = _preprocess_image(image_bytes)

    # Gemini Vision 시도
    prompt = f"""이 이미지에서 텍스트를 추출해주세요.
언어: {language}
규칙:
- 이미지에 있는 텍스트를 그대로 추출
- 줄바꿈은 실제 문단 구분에만 사용
- 인쇄 오류나 얼룩은 무시
- 텍스트만 출력 (설명 없이)"""

    raw = _gemini_ocr(processed, prompt)

    if raw:
        text   = _clean_text(raw)
        source = "gemini"
        conf   = 0.92
    else:
        text   = _mock_extract(image_bytes)
        source = "mock"
        conf   = 0.75

    return {
        "text":       text,
        "confidence": conf,
        "source":     source,
        "language":   _detect_language(text),
        "word_count": len(text.split()),
        "char_count": len(text),
    }


# ══════════════════════════════════════════════════════════════
#  2. 텍스트 정제 / 교정
# ══════════════════════════════════════════════════════════════

def enhance_text(raw_text: str) -> dict:
    """
    OCR로 추출된 텍스트를 AI로 정제한다.
    띄어쓰기 교정, 오탈자 수정, 문단 구조화
    """
    from app.services.gemini_service import _call_gemini, _parse_json_safe

    prompt = f"""다음 OCR 추출 텍스트를 교정해주세요.

원문:
{raw_text}

규칙:
- 명백한 오탈자만 교정 (의미 변경 금지)
- 한국어 띄어쓰기 교정
- 문장 부호 정규화

JSON 형식으로만 응답:
{{
  "corrected": "교정된 텍스트",
  "changes":   ["변경사항 1", "변경사항 2"],
  "quality":   "excellent|good|fair|poor"
}}"""

    raw = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and "corrected" in parsed:
        return {
            "original":  raw_text,
            "corrected": parsed["corrected"],
            "changes":   parsed.get("changes", []),
            "quality":   parsed.get("quality", "good"),
            "source":    "gemini",
        }

    return {
        "original":  raw_text,
        "corrected": raw_text,
        "changes":   [],
        "quality":   "good",
        "source":    "mock",
    }


# ══════════════════════════════════════════════════════════════
#  3. 책 표지 정보 감지
# ══════════════════════════════════════════════════════════════

def detect_book_info(image_bytes: bytes) -> dict:
    """
    책 표지 이미지에서 제목, 저자, 출판사를 추출한다.
    """
    prompt = """이 이미지는 책 표지입니다.
다음 JSON 형식으로만 응답하세요:
{
  "title":     "책 제목",
  "author":    "저자명",
  "publisher": "출판사 (없으면 null)",
  "subtitle":  "부제목 (없으면 null)",
  "language":  "ko|en|ja|zh|other"
}"""

    raw = _gemini_ocr(image_bytes, prompt)

    if raw:
        from app.services.gemini_service import _parse_json_safe
        parsed = _parse_json_safe(raw)
        if parsed and "title" in parsed:
            return {**parsed, "source": "gemini", "confidence": 0.88}

    # Mock
    mock_books = [
        {"title": "사피엔스",  "author": "유발 하라리", "publisher": "김영사",    "subtitle": "유인원에서 사이보그까지", "language": "ko"},
        {"title": "어린왕자",  "author": "생텍쥐페리",  "publisher": "문학동네",   "subtitle": None, "language": "ko"},
        {"title": "코스모스",  "author": "칼 세이건",   "publisher": "사이언스북스","subtitle": "Carl Sagan's Cosmos", "language": "ko"},
    ]
    seed = int(hashlib.md5(image_bytes[:32]).hexdigest(), 16) % len(mock_books)
    return {**mock_books[seed], "source": "mock", "confidence": 0.70}


# ══════════════════════════════════════════════════════════════
#  4. 페이지 분석 (문단 구조 파악)
# ══════════════════════════════════════════════════════════════

def analyze_page(image_bytes: bytes) -> dict:
    """
    책 페이지 이미지를 분석하여 문단, 인용구, 강조 텍스트를 구분한다.
    """
    prompt = """이 책 페이지를 분석해주세요.

JSON 형식으로만 응답:
{
  "full_text":   "전체 텍스트",
  "paragraphs":  ["문단1", "문단2"],
  "quotes":      ["인용구1"],
  "emphasized":  ["강조 텍스트"],
  "page_number": null
}"""

    raw = _gemini_ocr(image_bytes, prompt)

    if raw:
        from app.services.gemini_service import _parse_json_safe
        parsed = _parse_json_safe(raw)
        if parsed and "full_text" in parsed:
            return {**parsed, "source": "gemini"}

    # Mock
    mock_text = _mock_extract(image_bytes)
    return {
        "full_text":   mock_text,
        "paragraphs":  [mock_text],
        "quotes":      [],
        "emphasized":  [],
        "page_number": None,
        "source":      "mock",
    }


# ══════════════════════════════════════════════════════════════
#  5. 텍스트 → 독서 메모 자동 생성
# ══════════════════════════════════════════════════════════════

def generate_memo_from_text(extracted_text: str, book_title: str = "") -> dict:
    """
    OCR로 추출한 텍스트를 바탕으로 독서 메모 초안을 생성한다.
    """
    from app.services.gemini_service import _call_gemini, _parse_json_safe

    prompt = f"""다음 책 구절을 읽고 독자의 메모 초안을 생성해주세요.

책: {book_title or '알 수 없음'}
구절: {extracted_text}

이 구절에서 독자가 느낄 수 있는 생각, 감상, 연결되는 아이디어를
1-2문장으로 메모 형태로 작성해주세요.

JSON 형식으로만 응답:
{{
  "memo_draft":  "메모 초안 (1-2문장)",
  "tags":        ["태그1", "태그2", "태그3"],
  "mood":        "inspired|emotional|curious|neutral",
  "insight":     "이 구절의 핵심 인사이트 한 줄"
}}"""

    raw = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and "memo_draft" in parsed:
        return {**parsed, "source": "gemini", "original_text": extracted_text}

    return {
        "memo_draft":    f"이 구절에서 깊은 인상을 받았다. '{extracted_text[:40]}...'",
        "tags":          ["독서", "인문학", "생각"],
        "mood":          "inspired",
        "insight":       "이 문장은 우리가 당연하게 여기는 것에 의문을 던진다.",
        "source":        "mock",
        "original_text": extracted_text,
    }


# ══════════════════════════════════════════════════════════════
#  유틸리티
# ══════════════════════════════════════════════════════════════

def _clean_text(text: str) -> str:
    """추출 텍스트 기본 정제"""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def _detect_language(text: str) -> str:
    """간단한 언어 감지"""
    korean  = len(re.findall(r'[가-힣]', text))
    japanese= len(re.findall(r'[ぁ-ん]|[ァ-ン]', text))
    chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
    english = len(re.findall(r'[a-zA-Z]', text))

    counts = {"ko": korean, "ja": japanese, "zh": chinese, "en": english}
    return max(counts, key=counts.get)


def get_ocr_status() -> dict:
    return {
        "gemini_vision": _gemini_ok,
        "pillow":        _pillow_ok,
        "mode":          "gemini-vision" if _gemini_ok else "mock",
        "model":         _MODEL_NAME if _gemini_ok else None,
    }
