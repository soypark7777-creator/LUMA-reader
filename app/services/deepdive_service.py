"""
Deep Dive curation service.

The service combines book lookup, YouTube Data API based video curation,
discussion questions, and lightweight saved items. YouTube API keys are read
only on the server side by youtube_service.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from app.db import execute_write, is_connected
from app.services.youtube_service import search_youtube_videos


_saved_deepdive_items: list[dict] = []


def search_deepdive(query: str, user_id: str = "user_demo", limit: int = 8) -> dict:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "q가 필요합니다."}
    books = _search_books(q, limit=5)
    video_result = search_youtube_videos(q, limit=limit)
    return {
        "ok": True,
        "data": {
            "query": q,
            "books": books,
            "videos": video_result.get("videos", []),
            "questions": _deepdive_questions(q),
            "source": {
                "books": "book-search",
                "videos": video_result.get("source", "mock"),
            },
        },
    }


def save_deepdive_item(user_id: str, data: dict) -> dict:
    target_type = (data.get("type") or data.get("target_type") or "").strip().lower()
    if target_type not in {"book", "video", "question"}:
        return {"ok": False, "error": "type은 book, video, question 중 하나여야 합니다."}

    item = data.get("item")
    if item is None:
        item = {k: v for k, v in data.items() if k not in {"type", "target_type", "user_id"}}
    if not item:
        return {"ok": False, "error": "저장할 item이 필요합니다."}

    saved = {
        "saved_id": f"dd_{uuid.uuid4().hex[:10]}",
        "user_id": user_id or "user_demo",
        "type": target_type,
        "item": item,
        "note": data.get("note", ""),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    _saved_deepdive_items.insert(0, saved)
    _try_persist_saved_item(saved)
    return {"ok": True, "saved": saved}


def list_saved_deepdive_items(user_id: str, limit: int = 50) -> dict:
    items = [x for x in _saved_deepdive_items if x.get("user_id") == user_id]
    return {"ok": True, "items": items[: max(1, min(limit, 100))]}


def _search_books(query: str, limit: int = 5) -> list[dict]:
    try:
        from app.services.shelf_service import search_books, search_books_naver, search_books_google

        books = []
        books.extend(search_books_naver(query, limit))
        books.extend(search_books_google(query, limit))
        books.extend(_enrich_local_books(search_books(query, limit)))
        books = _dedupe_books(books)
    except Exception:
        books = []
    if not books:
        books = _mock_books(query)
    return [_shape_book(book) for book in books[:limit]]


def _shape_book(book: dict) -> dict:
    try:
        from app.services.book_normalizer_service import normalize_book

        normalized = normalize_book(book, book.get("source") or "deepdive")
    except Exception:
        normalized = book
    cover_url = normalized.get("cover_url") or book.get("cover_url") or book.get("thumbnail") or ""
    return {
        "book_id": normalized.get("book_id") or normalized.get("isbn") or "",
        "title": normalized.get("title", ""),
        "author": normalized.get("author", ""),
        "publisher": normalized.get("publisher", ""),
        "published_date": normalized.get("published_date", ""),
        "cover_url": cover_url,
        "thumbnail": normalized.get("thumbnail") or cover_url,
        "thumbnail_url": normalized.get("thumbnail_url") or cover_url,
        "cover_url_candidates": normalized.get("cover_url_candidates") or ([cover_url] if cover_url else []),
        "fallback_cover": normalized.get("fallback_cover") or {},
        "initial": normalized.get("initial", ""),
        "theme": normalized.get("theme", "classic"),
        "isbn": normalized.get("isbn", ""),
        "description": normalized.get("description", ""),
        "source": normalized.get("source") or book.get("source", "local"),
    }


def _enrich_local_books(books: list[dict]) -> list[dict]:
    enriched = []
    for book in books or []:
        if book.get("cover_url"):
            enriched.append(book)
            continue
        query = " ".join(x for x in [book.get("title", ""), book.get("author", "")] if x).strip()
        if query:
            cover = _lookup_cover(query)
            if cover:
                book = {**book, "cover_url": cover, "thumbnail": cover, "thumbnail_url": cover}
        enriched.append(book)
    return enriched


def _lookup_cover(query: str) -> str:
    try:
        from app.services.shelf_service import search_books_google, search_books_naver

        for provider in (search_books_naver, search_books_google):
            for book in provider(query, 3):
                cover = book.get("cover_url") or book.get("thumbnail_url") or book.get("thumbnail") or ""
                if cover:
                    return cover
    except Exception:
        return ""
    return ""


def _dedupe_books(books: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for book in books or []:
        title = "".join(str(book.get("title") or "").lower().split())
        author = "".join(str(book.get("author") or book.get("authors") or "").lower().split())
        isbn = "".join(ch for ch in str(book.get("isbn") or book.get("book_id") or "") if ch.isalnum())
        key = isbn or f"{title}|{author}"
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(book)
    return result


def _mock_books(query: str) -> list[dict]:
    return [
        {
            "book_id": f"mock_{uuid.uuid5(uuid.NAMESPACE_URL, query).hex[:8]}",
            "title": query,
            "author": "저자 미상",
            "publisher": "LUMA mock",
            "published_date": "",
            "cover_url": "",
            "isbn": "",
            "description": f"{query}를 깊이 읽기 위한 임시 책 정보입니다.",
            "source": "mock",
        }
    ]


def _deepdive_questions(query: str) -> list[str]:
    return [
        "이 책은 인간을 어떻게 바라보게 하나요?",
        "이 주제는 내 삶과 어떻게 연결되나요?",
        "이 책을 읽기 전 알아야 할 배경은 무엇인가요?",
        f"{query}를 독서모임에서 다룬다면 가장 먼저 던질 질문은 무엇인가요?",
    ]


def _try_persist_saved_item(saved: dict) -> None:
    if not is_connected():
        return
    try:
        execute_write(
            """CREATE TABLE IF NOT EXISTS deepdive_saved_items (
                   saved_id VARCHAR(36) PRIMARY KEY,
                   user_id VARCHAR(64) NOT NULL,
                   item_type VARCHAR(20) NOT NULL,
                   item_json JSON NOT NULL,
                   note TEXT,
                   created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                   INDEX idx_deepdive_saved_user (user_id, created_at)
               ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            (),
        )
        import json

        execute_write(
            """INSERT INTO deepdive_saved_items(saved_id,user_id,item_type,item_json,note,created_at)
               VALUES(%s,%s,%s,%s,%s,%s)""",
            (
                saved["saved_id"],
                saved["user_id"],
                saved["type"],
                json.dumps(saved["item"], ensure_ascii=False),
                saved.get("note", ""),
                datetime.now(),
            ),
        )
    except Exception:
        return
