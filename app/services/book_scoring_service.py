"""Scoring formula for Lounge book recommendations."""
from __future__ import annotations

from datetime import date, datetime

from app.services.book_tagger_service import normalize_field


def score_book(book: dict, filters: dict | None = None) -> dict:
    filters = filters or {}
    emotion = _emotion_score(book, filters.get("emotion", ""))
    field = _field_score(book, filters.get("field", ""))
    persona = _persona_score(book, filters.get("persona", ""))
    rating = _rating_score(book)
    discussion = _discussion_score(book)
    freshness, classic = _freshness_classic_scores(book, filters.get("mode", ""))
    fresh_or_classic = max(freshness, classic)

    final = (
        0.25 * emotion
        + 0.20 * field
        + 0.15 * persona
        + 0.15 * rating
        + 0.15 * discussion
        + 0.10 * fresh_or_classic
    )
    scores = {
        "final": round(final),
        "emotion": round(emotion),
        "field": round(field),
        "persona": round(persona),
        "rating": round(rating),
        "discussion": round(discussion),
        "freshness": round(freshness),
        "classic": round(classic),
    }
    book["scores"] = scores
    book["luma_score"] = round(scores["final"] / 20, 1)
    book["recommend_reason"] = recommend_reason(book, filters)
    return book


def recommend_reason(book: dict, filters: dict | None = None) -> str:
    filters = filters or {}
    title = book.get("title") or "이 책"
    field = normalize_field(filters.get("field", "")) or book.get("category") or "독서"
    if filters.get("emotion"):
        return f"지금의 감정과 {field} 관심사를 함께 붙잡고 이야기하기 좋은 책입니다."
    if filters.get("persona"):
        return f"{filters['persona']} 독자가 오래 생각해볼 만한 질문을 품은 책입니다."
    return f"{title}{_topic_particle(title)} 소개, 평점, 토론 가능성을 함께 보았을 때 오늘의 라운지에 잘 맞는 책입니다."


def _emotion_score(book: dict, emotion: str) -> float:
    if not emotion:
        return 72
    text = _text(book)
    mapping = {
        "calm": ("위로", "평온", "사색", "고요", "마음"),
        "growth": ("성장", "자기", "용기", "회복", "발견"),
        "lonely": ("고독", "외로움", "상실", "관계", "소외"),
        "curious": ("탐구", "질문", "과학", "역사", "분석"),
        "warm": ("따뜻", "감동", "가족", "우정", "관계"),
    }
    words = mapping.get(str(emotion).lower(), (str(emotion),))
    return 92 if any(word in text for word in words) else 68


def _field_score(book: dict, field: str) -> float:
    wanted = normalize_field(field)
    if not wanted:
        return 76
    actual = normalize_field(str(book.get("category") or book.get("genre") or ""))
    text = _text(book)
    if wanted and (wanted == actual or wanted in text):
        return 94
    return 62


def _persona_score(book: dict, persona: str) -> float:
    if not persona:
        return 74
    persona = persona.upper()
    text = _text(book)
    if persona.startswith("IN") and any(word in text for word in ("철학", "사유", "윤리", "고독")):
        return 92
    if persona.startswith("EN") and any(word in text for word in ("사회", "문명", "역사", "토론")):
        return 90
    if "F" in persona and any(word in text for word in ("관계", "감정", "회복", "가족")):
        return 88
    if "T" in persona and any(word in text for word in ("분석", "과학", "권력", "역사")):
        return 88
    return 72


def _rating_score(book: dict) -> float:
    rating = float(book.get("rating") or 0)
    reviews = int(book.get("review_count") or 0)
    base = rating * 18 if rating else 74
    review_bonus = min(10, reviews / 4000)
    return min(98, base + review_bonus)


def _discussion_score(book: dict) -> float:
    text = _text(book)
    score = 62
    for word in ("인간", "사회", "권력", "윤리", "역사", "철학", "고난", "정체성", "문명"):
        if word in text:
            score += 6
    return min(96, score)


def _freshness_classic_scores(book: dict, mode: str) -> tuple[float, float]:
    year = _year(book.get("published_date"))
    if not year:
        return 62, 72
    current = date.today().year
    age = max(0, current - year)
    freshness = max(45, 100 - age * 7)
    classic = min(96, 55 + age * 2.5)
    if mode == "new":
        freshness += 8
    if mode == "classic":
        classic += 8
    return min(100, freshness), min(100, classic)


def _year(value: object) -> int:
    raw = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y", "%Y%m%d"):
        try:
            return datetime.strptime(raw[: len(fmt)], fmt).year
        except ValueError:
            continue
    return 0


def _text(book: dict) -> str:
    return " ".join(str(book.get(key) or "") for key in ("title", "description", "category", "genre", "tags"))


def _topic_particle(text: str) -> str:
    if not text:
        return "은"
    last = text.strip()[-1]
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3:
        return "은" if (code - 0xAC00) % 28 else "는"
    return "은"
