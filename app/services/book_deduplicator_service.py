"""Book deduplication helpers for Lounge recommendations."""
from __future__ import annotations

import re


def dedupe_books(books: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for book in books:
        key = dedupe_key(book)
        if key in seen:
            continue
        seen.add(key)
        result.append(book)
    return result


def dedupe_key(book: dict) -> str:
    isbn13 = _isbn(book.get("isbn13") or book.get("isbn"))
    if len(isbn13) == 13:
        return f"isbn13:{isbn13}"
    isbn10 = _isbn(book.get("isbn10") or book.get("isbn"))
    if len(isbn10) == 10:
        return f"isbn10:{isbn10}"
    title = _plain(book.get("title"))
    author = _plain(book.get("author"))
    return f"text:{title}|{author}"


def _isbn(value: object) -> str:
    return re.sub(r"[^0-9Xx]", "", str(value or "")).lower()


def _plain(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())
