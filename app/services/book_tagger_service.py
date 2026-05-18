"""Rule-based tags and filter normalization for Lounge recommendations."""
from __future__ import annotations


FIELD_ALIASES = {
    "literature": "문학",
    "fiction": "문학",
    "novel": "문학",
    "essay": "에세이",
    "poetry": "에세이",
    "philosophy": "철학",
    "science": "과학",
    "history": "역사",
    "humanities": "인문",
    "psychology": "심리",
    "art": "예술",
    "business": "경제경영",
    "economy": "경제경영",
    "self": "자기계발",
    "selfhelp": "자기계발",
    "sf": "SF",
    "mystery": "미스터리",
}


def normalize_field(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    compact = raw.lower().replace("-", "").replace("_", "").replace(" ", "")
    return FIELD_ALIASES.get(compact, raw)


def tag_book(book: dict, filters: dict | None = None) -> dict:
    filters = filters or {}
    text = _text(book)
    category = normalize_field(book.get("category") or book.get("genre") or "") or infer_field(text)
    tags: list[str] = []
    if category:
        tags.append(category)
    tags.extend(infer_emotion_tags(text))
    tags.extend(infer_tone_tags(text))
    if discussion_score_hint(book) >= 80:
        tags.append("토론거리 많음")
    if filters.get("persona"):
        tags.append(f"{filters['persona']} 추천")

    seen = set()
    book["tags"] = [tag for tag in tags if tag and not (tag in seen or seen.add(tag))][:8]
    book["category"] = category
    book["genre"] = category
    return book


def infer_field(text: str) -> str:
    if any(word in text for word in ("과학", "우주", "기술", "생명", "물리", "SF")):
        return "과학"
    if any(word in text for word in ("철학", "사유", "실존", "윤리", "자유")):
        return "철학"
    if any(word in text for word in ("역사", "문명", "인류", "전쟁", "시대")):
        return "역사"
    if any(word in text for word in ("심리", "마음", "감정", "치유")):
        return "심리"
    if any(word in text for word in ("경제", "경영", "비즈니스", "투자")):
        return "경제경영"
    if any(word in text for word in ("자기", "성장", "습관", "목표")):
        return "자기계발"
    if any(word in text for word in ("예술", "미술", "음악", "디자인")):
        return "예술"
    return "문학"


def infer_emotion_tags(text: str) -> list[str]:
    tags = []
    if any(word in text for word in ("위로", "평온", "사색", "고요")):
        tags.append("차분함")
    if any(word in text for word in ("성장", "자기", "용기", "회복")):
        tags.append("성장")
    if any(word in text for word in ("고독", "외로움", "상실", "관계")):
        tags.append("외로움")
    if any(word in text for word in ("질문", "탐구", "과학", "역사", "분석")):
        tags.append("호기심")
    if any(word in text for word in ("따뜻", "감동", "가족", "우정")):
        tags.append("따뜻함")
    return tags or ["사색"]


def infer_tone_tags(text: str) -> list[str]:
    tags = []
    if any(word in text for word in ("토론", "질문", "권력", "문명", "인간", "사회")):
        tags.append("토론추천")
    if any(word in text for word in ("고전", "오래", "불멸", "명작")):
        tags.append("고전")
    if any(word in text for word in ("지식", "통찰", "문제", "세계")):
        tags.append("인문감각")
    return tags


def discussion_score_hint(book: dict) -> int:
    text = _text(book)
    score = 62
    for word in ("인간", "사회", "권력", "윤리", "역사", "철학", "고난", "정체성", "문명"):
        if word in text:
            score += 6
    return min(score, 96)


def _text(book: dict) -> str:
    return " ".join(
        str(book.get(key) or "")
        for key in ("title", "author", "description", "summary", "category", "genre", "sub_category")
    )
