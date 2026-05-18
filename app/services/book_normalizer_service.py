"""Normalize external and local book data into the Lounge book contract."""
from __future__ import annotations

import re
from html import unescape


def clean_text(value: object, limit: int | None = None) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def first_author(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(clean_text(x) for x in value if clean_text(x))
    return clean_text(value)


def normalize_book(raw: dict, source: str = "") -> dict:
    raw = raw or {}
    ids = raw.get("industryIdentifiers") or raw.get("identifiers") or []
    isbn10 = clean_text(raw.get("isbn10", ""))
    isbn13 = clean_text(raw.get("isbn13", raw.get("isbn", "")))
    for item in ids if isinstance(ids, list) else []:
        if item.get("type") == "ISBN_10":
            isbn10 = clean_text(item.get("identifier", isbn10))
        if item.get("type") == "ISBN_13":
            isbn13 = clean_text(item.get("identifier", isbn13))

    title = clean_text(raw.get("title") or raw.get("name") or "제목 없음")
    author = first_author(raw.get("author") or raw.get("authors") or "저자 미상")
    description = clean_text(raw.get("description") or raw.get("summary") or "", 360)
    category = clean_text(raw.get("category") or raw.get("genre") or "")
    source_url = clean_text(raw.get("source_url") or raw.get("external_url") or raw.get("link") or "")
    cover_candidates = _cover_candidates(raw, isbn13 or isbn10)
    cover_url = cover_candidates[0] if cover_candidates else ""

    book_id = clean_text(raw.get("book_id") or raw.get("id") or isbn13 or isbn10 or f"{title}:{author}")
    rating = _float(raw.get("rating", raw.get("avg_rating", raw.get("averageRating", 0))))
    review_count = _int(raw.get("review_count", raw.get("ratings_count", raw.get("ratingsCount", 0))))
    published_date = clean_text(
        raw.get("published_date") or raw.get("publishedDate") or raw.get("pubdate") or raw.get("pub_year") or ""
    )

    book = {
        "book_id": book_id,
        "isbn10": isbn10,
        "isbn13": isbn13,
        "isbn": clean_text(isbn13 or isbn10),
        "title": title,
        "author": author,
        "publisher": clean_text(raw.get("publisher") or ""),
        "published_date": published_date,
        "cover_url": cover_url,
        "thumbnail": cover_url,
        "thumbnail_url": cover_url,
        "cover_url_candidates": cover_candidates,
        "description": description,
        "summary": description,
        "category": category,
        "genre": category,
        "sub_category": clean_text(raw.get("sub_category") or ""),
        "rating": rating,
        "review_count": review_count,
        "source": clean_text(source or raw.get("source") or "local"),
        "source_url": source_url,
        "external_url": source_url,
        "total_pages": _int(raw.get("total_pages", raw.get("page_count", raw.get("pageCount", 0)))),
    }
    book["fallback_cover"] = fallback_cover(book)
    book["initial"] = book["fallback_cover"]["initial"]
    book["theme"] = book["fallback_cover"]["theme"]
    return book


def fallback_cover(book: dict) -> dict:
    title = clean_text(book.get("title") or "책")
    category = clean_text(book.get("category") or book.get("genre") or "")
    text = f"{title} {category}".lower()
    theme = "classic"
    if any(word.lower() in text for word in ("과학", "기술", "sf", "우주", "cosmos")):
        theme = "science"
    elif any(word.lower() in text for word in ("심리", "자기", "성장", "마음", "healing")):
        theme = "growth"
    elif any(word.lower() in text for word in ("역사", "문명", "인류")):
        theme = "history"
    elif any(word.lower() in text for word in ("문학", "소설", "poetry", "에세이")):
        theme = "literature"
    palettes = {
        "classic": ("#173127", "#C17F3B"),
        "science": ("#102A3D", "#6EC6FF"),
        "growth": ("#183225", "#7DE8A8"),
        "history": ("#332818", "#E8A85A"),
        "literature": ("#2A2133", "#D7A7FF"),
    }
    background, accent = palettes.get(theme, palettes["classic"])
    return {
        "title": title,
        "initial": _initial(title),
        "theme": theme,
        "label": category[:12],
        "background": background,
        "accent": accent,
        "source_url": book.get("source_url", ""),
    }


def _cover_candidates(raw: dict, isbn: str) -> list[str]:
    image_links = raw.get("imageLinks") or {}
    volume_info = raw.get("volumeInfo") or {}
    if isinstance(volume_info, dict):
        image_links = {**(volume_info.get("imageLinks") or {}), **image_links}

    values = [
        raw.get("cover_url"),
        raw.get("thumbnail_url"),
        raw.get("thumbnail"),
        raw.get("cover_url_s"),
        raw.get("image"),
        raw.get("image_url"),
        raw.get("bookCover"),
        raw.get("cover"),
        raw.get("orbitImage"),
        image_links.get("extraLarge"),
        image_links.get("large"),
        image_links.get("medium"),
        image_links.get("thumbnail"),
        image_links.get("smallThumbnail"),
    ]

    candidates: list[str] = []
    seen: set[str] = set()
    for value in values:
        url = _clean_url(value)
        if url and url not in seen:
            seen.add(url)
            candidates.append(url)
    return candidates


def _clean_url(value: str) -> str:
    value = clean_text(value)
    if not value:
        return ""
    if value.startswith("//"):
        return "https:" + value
    if value.startswith("http://"):
        return "https://" + value[7:]
    if value.startswith(("https://", "/")):
        return value
    return ""


def _initial(title: str) -> str:
    for char in title.strip():
        if not char.isspace():
            return char.upper()
    return "책"


def _float(value: object) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _int(value: object) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0
