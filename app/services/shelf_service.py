"""
LUMA — 서재 서비스 (MySQL)
──────────────────────────────────────────────────────
- 책 추가·수정·삭제·조회
- 서재 상태 관리 (want/reading/done)
- 진행률·별점 업데이트
- MySQL 없을 때 인메모리 Mock 자동 전환
"""
import json
import os
import re
import uuid
from datetime import datetime, date
from html import unescape
from typing import Optional

from app.db import is_connected, get_db, execute_one, execute_all, execute_write

# ── 인메모리 Mock ────────────────────────────────────────
_books_mem: list[dict] = [
    {"book_id":"book_001","title":"사피엔스","author":"유발 하라리","cover_emoji":"📕","genre":"역사/인류학","total_pages":636},
    {"book_id":"book_002","title":"어린왕자","author":"생텍쥐페리","cover_emoji":"📗","genre":"문학","total_pages":120},
    {"book_id":"book_003","title":"코스모스","author":"칼 세이건","cover_emoji":"📘","genre":"과학","total_pages":758},
]
_shelf_mem: list[dict] = [
    {"shelf_id":"sh_001","user_id":"user_demo","book_id":"book_001","status":"done","progress":100,"rating":5,"started_at":"2025-03-01","finished_at":"2025-03-20"},
    {"shelf_id":"sh_002","user_id":"user_demo","book_id":"book_002","status":"done","progress":100,"rating":5,"started_at":"2025-03-21","finished_at":"2025-03-22"},
    {"shelf_id":"sh_003","user_id":"user_demo","book_id":"book_003","status":"reading","progress":62,"rating":None,"started_at":"2025-04-01","finished_at":None},
]


def _book_full(book: dict, shelf: dict) -> dict:
    """책 + 서재 정보 합치기"""
    return {
        "book_id":     shelf.get("book_id") or book.get("book_id"),
        "id":          shelf.get("book_id") or book.get("book_id"),
        "shelf_id":    shelf.get("shelf_id"),
        "title":       book.get("title", ""),
        "author":      book.get("author", ""),
        "cover_emoji": book.get("cover_emoji", "📚"),
        "cover_url":   book.get("cover_url", ""),
        "isbn":        book.get("isbn", ""),
        "publisher":   book.get("publisher", ""),
        "description": book.get("description", ""),
        "genre":       book.get("genre", ""),
        "total_pages": book.get("total_pages", 0),
        "status":      shelf.get("status", "want"),
        "progress":    shelf.get("progress", 0),
        "rating":      shelf.get("rating"),
        "started_at":  str(shelf.get("started_at") or ""),
        "finished_at": str(shelf.get("finished_at") or ""),
        "user_id":     shelf.get("user_id"),
    }


def _normalize_shelf_row(row: dict) -> dict:
    """프론트가 안정적으로 쓰는 id/book_id/cover_url 필드를 보장한다."""
    row["id"] = row.get("book_id")
    row["cover_url"] = row.get("cover_url") or ""
    row["cover_emoji"] = row.get("cover_emoji") or "📚"
    row["progress"] = int(row.get("progress") or 0)
    return row


def _enrich_missing_covers(books: list[dict]) -> list[dict]:
    """서재 책 표지가 비어 있으면 네이버/구글 검색 결과로 보강하고 DB에도 저장한다."""
    if not books:
        return books
    for book in books:
        if book.get("cover_url") or not book.get("title"):
            continue
        query = " ".join(x for x in [book.get("title", ""), book.get("author", "")] if x).strip()
        found = []
        try:
            found = search_books_naver(query, 1) or search_books_google(query, 1)
        except Exception:
            found = []
        if not found:
            continue
        match = found[0]
        updates, vals = [], []
        for col, val in (
            ("cover_url", match.get("cover_url", "")),
            ("isbn", match.get("isbn", "")),
            ("publisher", match.get("publisher", "")),
            ("description", match.get("description", "")),
        ):
            if val and not book.get(col):
                book[col] = val
                updates.append(f"{col}=%s")
                vals.append(val)
        if updates and is_connected():
            try:
                vals.append(book["book_id"])
                execute_write("UPDATE books SET " + ",".join(updates) + " WHERE book_id=%s", vals)
            except Exception:
                pass
    return books


# ──────────────────────────────────────────────────────────
#  서재 전체 조회
# ──────────────────────────────────────────────────────────
def get_shelf(user_id: str) -> dict:
    if is_connected():
        try:
            rows = execute_all(
                """SELECT sb.shelf_id, sb.user_id, sb.book_id, sb.status, sb.progress,
                          sb.rating, sb.started_at, sb.finished_at,
                          b.title, b.author, b.publisher, b.isbn, b.cover_emoji,
                          b.cover_url, b.genre, b.total_pages, b.description
                   FROM shelf_books sb
                   JOIN books b ON sb.book_id = b.book_id
                   WHERE sb.user_id = %s
                   ORDER BY sb.updated_at DESC""",
                (user_id,)
            )
            books = [_normalize_shelf_row(dict(r)) for r in rows]
            books = _enrich_missing_covers(books)
        except Exception:
            books = []
    else:
        book_map = {b["book_id"]: b for b in _books_mem}
        books = [
            _book_full(book_map.get(s["book_id"], {}), s)
            for s in _shelf_mem if s["user_id"] == user_id
        ]

    memo_total = 0
    connection_total = 0
    streak_info = {"reading_streak": 0, "last_activity_date": ""}
    if is_connected():
        try:
            memo_total = int((execute_one("SELECT COUNT(*) AS cnt FROM memos WHERE user_id=%s", (user_id,)) or {}).get("cnt", 0) or 0)
            connection_total = int((execute_one("SELECT COUNT(*) AS cnt FROM book_connections WHERE user_id=%s", (user_id,)) or {}).get("cnt", 0) or 0)
        except Exception:
            memo_total = 0
            connection_total = 0
    else:
        try:
            from app.services.reading_service import _memos_mem, _connections_mem
            memo_total = sum(1 for m in _memos_mem if m.get("user_id") == user_id)
            connection_total = sum(1 for c in _connections_mem if c.get("user_id") == user_id)
        except Exception:
            memo_total = 0
            connection_total = 0
    try:
        from app.services.reading_service import get_reading_streak
        streak_info = get_reading_streak(user_id)
    except Exception:
        streak_info = {"reading_streak": 0, "last_activity_date": ""}

    now_ym = date.today().strftime("%Y-%m")
    return {
        "ok": True,
        "books": books,
        "stats": {
            "total":      len(books),
            "done":       sum(1 for b in books if b.get("status") == "done"),
            "reading":    sum(1 for b in books if b.get("status") == "reading"),
            "want":       sum(1 for b in books if b.get("status") == "want"),
            "this_month": sum(1 for b in books
                              if b.get("status") == "done"
                              and str(b.get("finished_at", ""))[:7] == now_ym),
            "memos": memo_total,
            "connections": connection_total,
            "reading_streak": int(streak_info.get("reading_streak", 0) or 0),
            "last_activity_date": streak_info.get("last_activity_date", ""),
        },
    }


# ──────────────────────────────────────────────────────────
#  책 추가 (서재에 등록)
# ──────────────────────────────────────────────────────────
def add_book(user_id: str, data: dict) -> dict:
    title  = (data.get("title") or "").strip()
    if not title:
        return {"ok": False, "error": "책 제목을 입력하세요."}

    book_id  = f"book_{uuid.uuid4().hex[:8]}"
    shelf_id = f"sh_{uuid.uuid4().hex[:8]}"
    now      = datetime.now()
    status   = data.get("status", "want")
    progress = int(data.get("progress", 100 if status == "done" else 0) or 0)
    if status == "done":
        progress = 100
    progress = max(0, min(progress, 100))
    incoming_cover = (data.get("cover_url") or data.get("thumbnail") or "").strip()
    incoming_isbn = (data.get("isbn") or "").strip()
    published_year = str(data.get("published_date") or data.get("publishedDate") or data.get("pub_year") or "")[:4]
    published_year = int(published_year) if published_year.isdigit() else None

    started_at  = now.date() if status == "reading" else None
    finished_at = now.date() if status == "done"    else None

    if is_connected():
        try:
            # books 테이블에 없으면 INSERT
            existing = None
            if incoming_isbn:
                existing = execute_one("SELECT book_id FROM books WHERE isbn=%s", (incoming_isbn,))
            if not existing:
                existing = execute_one("SELECT book_id FROM books WHERE title=%s AND author=%s",
                                       (title, data.get("author", "")))
            if existing:
                book_id = existing["book_id"]
                updates, vals = [], []
                for col, val in (
                    ("cover_url", incoming_cover),
                    ("isbn", incoming_isbn),
                    ("publisher", data.get("publisher", "")),
                    ("pub_year", published_year),
                    ("description", data.get("description", "")),
                ):
                    if val:
                        updates.append(f"{col}=%s")
                        vals.append(val)
                if updates:
                    vals.append(book_id)
                    execute_write("UPDATE books SET " + ",".join(updates) + " WHERE book_id=%s", vals)
            else:
                execute_write(
                    """INSERT INTO books(book_id,title,author,publisher,isbn,cover_emoji,
                              cover_url,genre,total_pages,pub_year,description,created_at)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (book_id, title, data.get("author",""), data.get("publisher",""),
                     incoming_isbn, data.get("cover_emoji","📚"), incoming_cover,
                     data.get("genre",""), int(data.get("total_pages",0) or 0),
                     published_year, data.get("description",""), now)
                )
            # shelf_books — 중복 방지 (IGNORE)
            execute_write(
                "INSERT IGNORE INTO shelf_books(shelf_id,user_id,book_id,status,progress,started_at,finished_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (shelf_id, user_id, book_id, status, progress, started_at, finished_at)
            )
            execute_write(
                "UPDATE shelf_books SET status=%s, progress=%s WHERE user_id=%s AND book_id=%s",
                (status, progress, user_id, book_id)
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        _books_mem.append({
            "book_id": book_id, "title": title,
            "author": data.get("author",""), "cover_emoji": data.get("cover_emoji","📚"),
            "cover_url": incoming_cover, "isbn": incoming_isbn,
            "genre": data.get("genre",""), "total_pages": int(data.get("total_pages",0) or 0),
            "pub_year": published_year,
        })
        _shelf_mem.append({
            "shelf_id": shelf_id, "user_id": user_id, "book_id": book_id,
            "status": status, "progress": progress, "rating": None,
            "started_at": str(started_at or ""), "finished_at": str(finished_at or ""),
        })

    book = {"book_id": book_id, "shelf_id": shelf_id, "title": title,
            "author": data.get("author",""), "cover_emoji": data.get("cover_emoji","📚"),
            "cover_url": incoming_cover, "isbn": incoming_isbn,
            "publisher": data.get("publisher",""), "description": data.get("description",""),
            "genre": data.get("genre",""), "total_pages": int(data.get("total_pages",0) or 0),
            "pub_year": published_year,
            "status": status, "progress": progress, "rating": None, "user_id": user_id}
    return {"ok": True, "book": book}


# ──────────────────────────────────────────────────────────
#  서재 업데이트
# ──────────────────────────────────────────────────────────
def update_shelf_book(book_id: str, user_id: str, data: dict) -> dict:
    status   = data.get("status")
    progress = data.get("progress")
    rating   = data.get("rating")
    now      = datetime.now()

    finished_at = now.date() if status == "done" else None

    if is_connected():
        try:
            sets, vals = [], []
            if status   is not None: sets.append("status=%s");      vals.append(status)
            if progress is not None: sets.append("progress=%s");    vals.append(int(progress))
            if rating   is not None: sets.append("rating=%s");      vals.append(int(rating))
            if finished_at:          sets.append("finished_at=%s"); vals.append(finished_at)
            if status in ("reading", "want"):
                sets.append("finished_at=%s"); vals.append(None)
            if status == "reading":
                sets.append("started_at=COALESCE(started_at,%s)"); vals.append(now.date())
            if not sets:
                return {"ok": False, "error": "변경할 내용이 없습니다."}
            vals += [book_id, user_id]
            execute_write(
                "UPDATE shelf_books SET " + ",".join(sets) + " WHERE book_id=%s AND user_id=%s",
                vals
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        s = next((x for x in _shelf_mem if x["book_id"] == book_id and x["user_id"] == user_id), None)
        if not s:
            return {"ok": False, "error": "서재에 없는 책입니다."}
        if status:   s["status"]   = status
        if progress is not None: s["progress"] = int(progress)
        if rating:   s["rating"]   = int(rating)
        if finished_at: s["finished_at"] = str(finished_at)

    return {"ok": True}


# ──────────────────────────────────────────────────────────
#  서재에서 삭제
# ──────────────────────────────────────────────────────────
def delete_shelf_book(book_id: str, user_id: str) -> dict:
    if is_connected():
        try:
            execute_write(
                "DELETE FROM shelf_books WHERE book_id=%s AND user_id=%s", (book_id, user_id))
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        global _shelf_mem
        _shelf_mem = [s for s in _shelf_mem
                      if not (s["book_id"] == book_id and s["user_id"] == user_id)]
    return {"ok": True}


# ──────────────────────────────────────────────────────────
#  책 검색
# ──────────────────────────────────────────────────────────
def search_books(query: str, limit: int = 10) -> list:
    if not query:
        return []
    if is_connected():
        try:
            rows = execute_all(
                "SELECT book_id,title,author,cover_emoji,genre,total_pages "
                "FROM books WHERE title LIKE %s OR author LIKE %s LIMIT %s",
                (f"%{query}%", f"%{query}%", limit)
            )
            return [dict(r) for r in rows]
        except Exception:
            return []
    q = query.lower()
    return [b for b in _books_mem
            if q in b.get("title","").lower() or q in b.get("author","").lower()][:limit]


def _usable_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        return ""
    placeholders = ("발급받은_", "여기에_", "your_", "YOUR_")
    if value.startswith(placeholders):
        return ""
    return value


def _clean_api_text(value: str) -> str:
    """외부 도서 API가 섞어 보내는 HTML 태그/엔티티를 제거한다."""
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _pick_isbn(isbn_raw: str) -> str:
    """네이버 isbn 문자열에서 대표 ISBN을 고른다. 가능하면 13자리 우선."""
    tokens = re.findall(r"[\dXx]{10,13}", str(isbn_raw or ""))
    if not tokens:
        return ""
    return next((t for t in tokens if len(t) == 13), tokens[-1])


def _external_get(url: str, *, params: dict, headers: dict | None = None, timeout: int = 5):
    """
    외부 도서 API GET helper.

    일부 실행 환경은 HTTP(S)_PROXY가 127.0.0.1:9 같은 차단 프록시로
    잡혀 있어 requests가 실제 API까지 도달하지 못한다. 먼저 기본 환경으로
    호출하고, 프록시 연결 오류일 때만 환경 프록시를 무시해 재시도한다.
    """
    import requests

    try:
        return requests.get(url, params=params, headers=headers or {}, timeout=timeout)
    except requests.exceptions.ProxyError:
        session = requests.Session()
        session.trust_env = False
        return session.get(url, params=params, headers=headers or {}, timeout=timeout)


def search_books_naver(query: str, limit: int = 10) -> list:
    """네이버 책 검색. 키/네트워크 실패 시 빈 배열을 반환해 route가 fallback하게 한다."""
    if not query:
        return []

    client_id = _usable_env("NAVER_CLIENT_ID")
    client_secret = _usable_env("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        return []

    try:
        import requests

        display = max(1, min(int(limit or 10), 100))
        response = _external_get(
            "https://openapi.naver.com/v1/search/book.json",
            params={"query": query, "display": display, "start": 1, "sort": "sim"},
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
            },
            timeout=5,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except Exception:
        return []

    books = []
    for item in items[:limit]:
        isbn_raw = item.get("isbn", "")
        books.append({
            "book_id": _pick_isbn(isbn_raw) or item.get("link", ""),
            "title": _clean_api_text(item.get("title", "")),
            "author": _clean_api_text(item.get("author", "")),
            "cover_url": item.get("image", ""),
            "cover_emoji": "🌱",
            "genre": "",
            "category": "",
            "rating": 4.5,
            "review_count": 0,
            "source": "naver",
            "reason": "국내 도서 검색에서 발견한 생각의 씨앗입니다.",
            "saved": False,
            "reading_status": "want",
            "total_pages": 0,
            "description": _clean_api_text(item.get("description", "")),
            "isbn": _pick_isbn(isbn_raw),
            "isbn_raw": isbn_raw,
            "publisher": _clean_api_text(item.get("publisher", "")),
            "published_date": _clean_api_text(item.get("pubdate", "")),
            "external_url": item.get("link", ""),
        })
    return [b for b in books if b.get("title")]


def search_books_google(query: str, limit: int = 5) -> list:
    """Google Books 검색. 키/네트워크 실패 시 로컬 Mock 검색으로 폴백."""
    if not query:
        return []
    api_key = _usable_env("GOOGLE_BOOKS_API_KEY")
    if api_key:
        try:
            import requests
            r = _external_get(
                "https://www.googleapis.com/books/v1/volumes",
                params={"q": query, "maxResults": limit, "key": api_key},
                timeout=5,
            )
            r.raise_for_status()
            items = r.json().get("items", [])
            books = []
            for item in items[:limit]:
                info = item.get("volumeInfo", {})
                identifiers = info.get("industryIdentifiers") or []
                isbn = next((x.get("identifier") for x in identifiers if x.get("identifier")), "")
                books.append({
                    "book_id": isbn or item.get("id", ""),
                    "title": info.get("title", ""),
                    "author": ", ".join(info.get("authors", [])),
                    "cover_url": (info.get("imageLinks") or {}).get("thumbnail", ""),
                    "isbn": isbn,
                    "total_pages": info.get("pageCount", 0),
                    "description": info.get("description", ""),
                    "publisher": info.get("publisher", ""),
                    "published_date": info.get("publishedDate", ""),
                    "external_url": (info.get("infoLink") or ""),
                    "rating": info.get("averageRating", 0) or 0,
                    "review_count": info.get("ratingsCount", 0) or 0,
                    "source": "google",
                    "reason": "넓은 도서 데이터에서 발견한 생각의 씨앗입니다.",
                })
            if books:
                return books
        except Exception:
            pass

    return [
        {
            "title": b.get("title", ""),
            "author": b.get("author", ""),
            "cover_url": "",
            "isbn": "",
            "total_pages": b.get("total_pages", 0),
            "description": b.get("description", ""),
            "publisher": b.get("publisher", ""),
            "published_date": b.get("published_date", ""),
            "rating": b.get("rating", 4.3),
            "review_count": b.get("review_count", 0),
            "source": "local",
        }
        for b in search_books(query, limit)
    ]


def update_reading_progress(book_id: str, user_id: str, pages_read: int) -> dict:
    """읽은 페이지 수를 기준으로 서재 진행률을 갱신한다."""
    pages_read = max(0, int(pages_read or 0))

    if is_connected():
        try:
            row = execute_one(
                """SELECT sb.status, sb.progress, b.total_pages
                   FROM shelf_books sb
                   JOIN books b ON sb.book_id=b.book_id
                   WHERE sb.book_id=%s AND sb.user_id=%s""",
                (book_id, user_id),
            )
            if not row:
                return {"ok": False, "error": "서재에 없는 책입니다."}
            total_pages = int(row.get("total_pages") or 0)
            progress = int(row.get("progress") or 0)
            if total_pages > 0:
                progress = min(100, round((pages_read / total_pages) * 100))
            status = "reading" if row.get("status") == "want" and pages_read > 0 else row.get("status")
            execute_write(
                "UPDATE shelf_books SET progress=%s, status=%s WHERE book_id=%s AND user_id=%s",
                (progress, status, book_id, user_id),
            )
            return {"ok": True, "progress": progress, "status": status}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    shelf = next((s for s in _shelf_mem if s["book_id"] == book_id and s["user_id"] == user_id), None)
    book = next((b for b in _books_mem if b["book_id"] == book_id), None)
    if not shelf or not book:
        return {"ok": False, "error": "서재에 없는 책입니다."}
    total_pages = int(book.get("total_pages") or 0)
    if total_pages > 0:
        shelf["progress"] = min(100, round((pages_read / total_pages) * 100))
    if shelf.get("status") == "want" and pages_read > 0:
        shelf["status"] = "reading"
    return {"ok": True, "progress": shelf.get("progress", 0), "status": shelf.get("status")}
