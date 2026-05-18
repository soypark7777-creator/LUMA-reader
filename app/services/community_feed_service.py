"""DB-backed community thought feed for /social.

The feed is intentionally built from the user's real reading artifacts:
users, books, shelf_books, memos, and emotions. Reactions/comments/saves live
in small community_* tables so the feed can remain a projection over memos.
"""
from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from app.db import execute_all, execute_one, execute_write, is_connected


_ENSURED = False
_memory_reactions: dict[str, set[str]] = defaultdict(set)
_memory_saves: dict[str, set[str]] = defaultdict(set)
_memory_comments: dict[str, list[dict]] = defaultdict(list)
_memory_questions: dict[str, str] = {}
_cover_cache: dict[str, str] = {}
_HAS_MEMO_IS_PUBLIC: bool | None = None


def ensure_community_tables() -> None:
    """Create the small social-state tables if MySQL is available."""
    global _ENSURED
    if _ENSURED or not is_connected():
        return
    statements = [
        """
        CREATE TABLE IF NOT EXISTS community_post_reactions (
            reaction_id VARCHAR(64) PRIMARY KEY,
            post_id VARCHAR(64) NOT NULL,
            user_id VARCHAR(64) NOT NULL,
            reaction_type VARCHAR(32) NOT NULL DEFAULT 'like',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_post_user_reaction (post_id, user_id, reaction_type),
            INDEX idx_post_reaction (post_id, reaction_type),
            INDEX idx_user_reaction (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS community_post_comments (
            comment_id VARCHAR(64) PRIMARY KEY,
            post_id VARCHAR(64) NOT NULL,
            user_id VARCHAR(64) NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_post_comment (post_id),
            INDEX idx_user_comment (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS community_post_saves (
            save_id VARCHAR(64) PRIMARY KEY,
            post_id VARCHAR(64) NOT NULL,
            user_id VARCHAR(64) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_post_user_save (post_id, user_id),
            INDEX idx_user_save (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS community_generated_questions (
            question_id VARCHAR(64) PRIMARY KEY,
            source_type VARCHAR(32) NOT NULL,
            source_id VARCHAR(64) NOT NULL,
            book_id VARCHAR(64),
            user_id VARCHAR(64),
            question TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_source_question (source_type, source_id),
            INDEX idx_book_question (book_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
    ]
    for sql in statements:
        execute_write(sql)
    _ensure_memo_public_column()
    _ENSURED = True



def _has_memo_is_public() -> bool:
    """Return whether memos.is_public exists, caching the check per process."""
    global _HAS_MEMO_IS_PUBLIC
    if _HAS_MEMO_IS_PUBLIC is not None:
        return _HAS_MEMO_IS_PUBLIC
    if not is_connected():
        _HAS_MEMO_IS_PUBLIC = False
        return False
    try:
        execute_one("SELECT is_public FROM memos LIMIT 1")
        _HAS_MEMO_IS_PUBLIC = True
    except Exception:
        _HAS_MEMO_IS_PUBLIC = False
    return _HAS_MEMO_IS_PUBLIC


def _ensure_memo_public_column() -> None:
    """Best-effort migration for public community feed visibility."""
    global _HAS_MEMO_IS_PUBLIC
    if not is_connected() or _has_memo_is_public():
        return
    try:
        execute_write("ALTER TABLE memos ADD COLUMN is_public TINYINT(1) NOT NULL DEFAULT 0 AFTER tags")
    except Exception:
        pass
    try:
        execute_write("CREATE INDEX idx_public_created ON memos (is_public, created_at)")
    except Exception:
        pass
    _HAS_MEMO_IS_PUBLIC = None
    _has_memo_is_public()


def _enrich_cover(book_title: str) -> str:
    """Fetch a missing book cover once and persist it for future feed requests."""
    title = str(book_title or "").strip()
    if not title:
        return ""
    if title in _cover_cache:
        return _cover_cache[title]
    try:
        from app.services.shelf_service import search_books_google, search_books_naver
        results = search_books_naver(title, 1) or search_books_google(title, 1)
        url = (results[0].get("cover_url") or results[0].get("thumbnail") or results[0].get("image") or "") if results else ""
    except Exception:
        url = ""
    _cover_cache[title] = url
    if url and is_connected():
        try:
            execute_write(
                "UPDATE books SET cover_url=%s WHERE title=%s AND (cover_url IS NULL OR cover_url='')",
                (url, title),
            )
        except Exception:
            pass
    return url

def get_feed(user_id: str = "user_demo", page: int = 1, limit: int = 12, tag: str = "", q: str = "", emotion: str = "") -> dict:
    page = max(1, int(page or 1))
    limit = max(1, min(int(limit or 12), 50))
    if is_connected():
        try:
            ensure_community_tables()
            rows, total = _db_feed_rows(user_id, page, limit, tag, q, emotion)
            posts = [_shape_post(row, user_id) for row in rows]
            return {"ok": True, "posts": posts, "cards": posts, "total": total, "page": page, "has_next": page * limit < total, "source": "db"}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "posts": [], "cards": [], "total": 0, "page": page, "has_next": False, "source": "db_error"}

    posts = _memory_posts(user_id, tag, q, emotion)
    total = len(posts)
    start = (page - 1) * limit
    sliced = posts[start:start + limit]
    return {"ok": True, "posts": sliced, "cards": sliced, "total": total, "page": page, "has_next": start + limit < total, "source": "memory"}


def get_trending_books(user_id: str = "user_demo", limit: int = 12) -> dict:
    limit = max(1, min(int(limit or 12), 30))
    if is_connected():
        try:
            ensure_community_tables()
            rows = execute_all(
                """
                SELECT b.book_id,b.title,b.author,b.cover_url,b.cover_emoji,b.genre,
                       COUNT(DISTINCT m.memo_id) AS thought_count,
                       COUNT(DISTINCT q.question_id) AS question_count,
                       COUNT(DISTINCT sb.user_id) AS reader_count
                FROM books b
                LEFT JOIN memos m ON m.book_id=b.book_id AND TRIM(m.content)<>''
                LEFT JOIN community_generated_questions q ON q.book_id=b.book_id
                LEFT JOIN shelf_books sb ON sb.book_id=b.book_id
                GROUP BY b.book_id,b.title,b.author,b.cover_url,b.cover_emoji,b.genre
                HAVING thought_count > 0 OR reader_count > 0
                ORDER BY thought_count DESC, reader_count DESC, b.created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return {"ok": True, "books": [_shape_trending_book(dict(r)) for r in rows], "source": "db"}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "books": [], "source": "db_error"}
    books = _memory_trending_books(limit)
    return {"ok": True, "books": books, "source": "memory"}


def get_questions(user_id: str = "user_demo", limit: int = 12) -> dict:
    posts = get_feed(user_id, 1, limit, "", "", "")
    questions = [
        {
            "question_id": p["post_id"],
            "post_id": p["post_id"],
            "question": p["question"],
            "book": p["book"],
            "user": p["user"],
            "emotion_tags": p["emotion_tags"],
            "created_at": p["created_at"],
        }
        for p in posts.get("posts", [])
        if p.get("question")
    ]
    return {"ok": bool(posts.get("ok", True)), "questions": questions, "source": posts.get("source", "unknown")}


def get_quotes(user_id: str = "user_demo", limit: int = 12) -> dict:
    posts = get_feed(user_id, 1, limit, "", "", "")
    quotes = []
    for p in posts.get("posts", []):
        quote = p.get("quote") or _quote_from_text(p.get("thought", ""))
        if quote:
            quotes.append({**p, "quote": quote, "type": "quote"})
    return {"ok": bool(posts.get("ok", True)), "quotes": quotes[:limit], "source": posts.get("source", "unknown")}


def get_same_book_readers(book_id: str = "", title: str = "", limit: int = 12) -> dict:
    limit = max(1, min(int(limit or 12), 30))
    if is_connected():
        try:
            ensure_community_tables()
            params: list[Any] = []
            where = "sb.book_id=%s"
            params.append(book_id)
            if not book_id and title:
                where = "b.title=%s"
                params = [title]
            rows = execute_all(
                f"""
                SELECT sb.user_id,u.display_name,u.emoji,sb.status,sb.progress,
                       b.book_id,b.title,b.author,b.cover_url,b.cover_emoji,
                       COUNT(DISTINCT m.memo_id) AS memo_count,
                       COUNT(DISTINCT q.question_id) AS question_count
                FROM shelf_books sb
                JOIN books b ON b.book_id=sb.book_id
                LEFT JOIN users u ON u.user_id=sb.user_id
                LEFT JOIN memos m ON m.user_id=sb.user_id AND m.book_id=sb.book_id
                LEFT JOIN community_generated_questions q ON q.user_id=sb.user_id AND q.book_id=sb.book_id
                WHERE {where}
                GROUP BY sb.user_id,u.display_name,u.emoji,sb.status,sb.progress,
                         b.book_id,b.title,b.author,b.cover_url,b.cover_emoji
                ORDER BY FIELD(sb.status,'reading','done','want'), sb.progress DESC, memo_count DESC
                LIMIT %s
                """,
                tuple(params + [limit]),
            )
            return {"ok": True, "readers": [_shape_reader(dict(r)) for r in rows], "source": "db"}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "readers": [], "source": "db_error"}
    return {"ok": True, "readers": _memory_same_book_readers(book_id, title, limit), "source": "memory"}


def get_lounge_recruit(user_id: str = "user_demo", limit: int = 8) -> dict:
    try:
        from app.services.club_service import get_all_clubs
        clubs = get_all_clubs(user_id)[:limit]
    except Exception:
        clubs = []
    recruits = [
        {
            "club_id": c.get("club_id") or c.get("id"),
            "name": c.get("name", "독서모임"),
            "description": c.get("description", ""),
            "book": {
                "title": c.get("current_book") or c.get("current_book_title") or "",
                "author": c.get("current_book_author", ""),
            },
            "member_count": c.get("member_count", len(c.get("member_ids", []) or [])),
            "card_count": c.get("card_count", 0),
            "tags": c.get("tags", []) or [],
            "emoji": c.get("emoji", "📚"),
            "created_at": str(c.get("created_at") or ""),
        }
        for c in clubs
    ]
    for recruit in recruits:
        if not recruit.get("cover_url"):
            book_title = (recruit.get("book") or {}).get("title") or recruit.get("book_title") or ""
            recruit["cover_url"] = _enrich_cover(book_title)
            if recruit.get("book") is not None:
                recruit["book"]["cover_url"] = recruit["cover_url"]
    return {"ok": True, "recruits": recruits, "clubs": recruits, "source": "club_service"}


def create_post(user_id: str, data: dict) -> dict:
    thought_text = str(data.get("thought") or data.get("content") or data.get("text") or "").strip()
    passage_text = str(data.get("passage") or "").strip()
    if passage_text and thought_text and passage_text not in thought_text:
        content = f"\uacf5\uc720\ud55c \uad6c\uc808:\n{passage_text}\n\n\ub0b4 \uc0dd\uac01:\n{thought_text}"
    else:
        content = thought_text or passage_text
    if not content:
        return {"ok": False, "error": "thought/content is required"}
    memo_id = data.get("memo_id") or f"memo_{uuid.uuid4().hex[:8]}"
    book_id = data.get("book_id") or ""
    book_title = data.get("book_title") or data.get("title") or ""
    tags = _normalize_tags(data.get("tags") or data.get("emotion_tags") or [])
    if is_connected():
        try:
            ensure_community_tables()
            if not book_id and book_title:
                row = execute_one("SELECT book_id FROM books WHERE title=%s ORDER BY created_at DESC LIMIT 1", (book_title,))
                book_id = (row or {}).get("book_id", "")
            execute_write(
                "INSERT INTO memos(memo_id,user_id,book_id,content,tags,source,page_num,is_public,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (memo_id, user_id, book_id, content, json.dumps(tags, ensure_ascii=False), "manual", data.get("page_num") or data.get("page_number"), 1, datetime.now()),
            )
            question = (data.get("question") or "").strip()
            if question:
                _upsert_question(memo_id, user_id, book_id, question)
            post = _db_post_by_id(memo_id, user_id)
            return {"ok": True, "post": post, "card": post, "source": "db"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    from app.services.reading_service import _memos_mem
    memo = {
        "memo_id": memo_id,
        "user_id": user_id,
        "book_id": book_id,
        "book_title": book_title,
        "content": content,
        "tags": tags,
        "page_num": data.get("page_num") or data.get("page_number"),
        "created_at": datetime.now().isoformat(),
    }
    _memos_mem.insert(0, memo)
    if data.get("question"):
        _memory_questions[memo_id] = str(data["question"]).strip()
    post = _shape_memory_post(memo, user_id)
    return {"ok": True, "post": post, "card": post, "source": "memory"}


def toggle_like(post_id: str, user_id: str = "user_demo") -> dict:
    if is_connected():
        try:
            ensure_community_tables()
            existing = execute_one(
                "SELECT reaction_id FROM community_post_reactions WHERE post_id=%s AND user_id=%s AND reaction_type='like'",
                (post_id, user_id),
            )
            if existing:
                execute_write("DELETE FROM community_post_reactions WHERE reaction_id=%s", (existing["reaction_id"],))
                liked = False
            else:
                execute_write(
                    "INSERT INTO community_post_reactions(reaction_id,post_id,user_id,reaction_type) VALUES(%s,%s,%s,'like')",
                    (f"rx_{uuid.uuid4().hex[:10]}", post_id, user_id),
                )
                liked = True
            count = execute_one(
                "SELECT COUNT(*) AS cnt FROM community_post_reactions WHERE post_id=%s AND reaction_type='like'",
                (post_id,),
            )
            return {"ok": True, "liked": liked, "likes": int((count or {}).get("cnt", 0) or 0), "like_count": int((count or {}).get("cnt", 0) or 0)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    bucket = _memory_reactions[post_id]
    if user_id in bucket:
        bucket.remove(user_id)
        liked = False
    else:
        bucket.add(user_id)
        liked = True
    return {"ok": True, "liked": liked, "likes": len(bucket), "like_count": len(bucket)}


def get_comments(post_id: str, limit: int = 50) -> list[dict]:
    limit = max(1, min(int(limit or 50), 100))
    if is_connected():
        try:
            ensure_community_tables()
            rows = execute_all(
                """
                SELECT c.comment_id,c.post_id,c.user_id,c.content,c.created_at,u.display_name,u.emoji
                FROM community_post_comments c
                LEFT JOIN users u ON u.user_id=c.user_id
                WHERE c.post_id=%s
                ORDER BY c.created_at ASC
                LIMIT %s
                """,
                (post_id, limit),
            )
            return [_shape_comment(dict(r)) for r in rows]
        except Exception:
            return []
    return [_shape_comment(c) for c in _memory_comments.get(post_id, [])[:limit]]


def add_comment(post_id: str, data: dict, user_id: str = "user_demo") -> dict:
    content = (data.get("content") or data.get("text") or "").strip()
    if not content:
        return {"ok": False, "error": "comment content is required"}
    if is_connected():
        try:
            ensure_community_tables()
            comment_id = f"cmt_{uuid.uuid4().hex[:10]}"
            execute_write(
                "INSERT INTO community_post_comments(comment_id,post_id,user_id,content) VALUES(%s,%s,%s,%s)",
                (comment_id, post_id, user_id, content),
            )
            comment = execute_one(
                """
                SELECT c.comment_id,c.post_id,c.user_id,c.content,c.created_at,u.display_name,u.emoji
                FROM community_post_comments c LEFT JOIN users u ON u.user_id=c.user_id
                WHERE c.comment_id=%s
                """,
                (comment_id,),
            )
            count = execute_one("SELECT COUNT(*) AS cnt FROM community_post_comments WHERE post_id=%s", (post_id,))
            return {"ok": True, "comment": _shape_comment(dict(comment or {})), "total_comments": int((count or {}).get("cnt", 0) or 0), "comment_count": int((count or {}).get("cnt", 0) or 0)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    comment = {
        "comment_id": f"cmt_{uuid.uuid4().hex[:8]}",
        "post_id": post_id,
        "user_id": user_id,
        "display_name": data.get("display_name") or data.get("author_name") or "나",
        "emoji": data.get("emoji") or data.get("author_emoji") or "✨",
        "content": content,
        "created_at": datetime.now().isoformat(),
    }
    _memory_comments[post_id].append(comment)
    return {"ok": True, "comment": _shape_comment(comment), "total_comments": len(_memory_comments[post_id]), "comment_count": len(_memory_comments[post_id])}


def toggle_save(post_id: str, user_id: str = "user_demo") -> dict:
    if is_connected():
        try:
            ensure_community_tables()
            existing = execute_one("SELECT save_id FROM community_post_saves WHERE post_id=%s AND user_id=%s", (post_id, user_id))
            if existing:
                execute_write("DELETE FROM community_post_saves WHERE save_id=%s", (existing["save_id"],))
                saved = False
            else:
                execute_write(
                    "INSERT INTO community_post_saves(save_id,post_id,user_id) VALUES(%s,%s,%s)",
                    (f"save_{uuid.uuid4().hex[:10]}", post_id, user_id),
                )
                saved = True
            count = execute_one("SELECT COUNT(*) AS cnt FROM community_post_saves WHERE post_id=%s", (post_id,))
            return {"ok": True, "saved": saved, "saves": int((count or {}).get("cnt", 0) or 0)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    bucket = _memory_saves[post_id]
    if user_id in bucket:
        bucket.remove(user_id)
        saved = False
    else:
        bucket.add(user_id)
        saved = True
    return {"ok": True, "saved": saved, "saves": len(bucket)}


def check_and_create_bookclub(book_title: str) -> None:
    # Compatibility hook for reading_service/social_feed_service.
    return None


def _db_feed_rows(user_id: str, page: int, limit: int, tag: str, q: str, emotion: str) -> tuple[list[dict], int]:
    where = ["TRIM(m.content) <> ''"]
    if _has_memo_is_public():
        where.append("m.is_public = 1")
    params: list[Any] = []
    if tag:
        where.append("(m.tags LIKE %s OR b.genre LIKE %s)")
        params.extend([f"%{tag}%", f"%{tag}%"])
    if q:
        where.append("(m.content LIKE %s OR b.title LIKE %s OR b.author LIKE %s)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if emotion:
        where.append("(m.tags LIKE %s OR e.emotion_type=%s)")
        params.extend([f"%{emotion}%", emotion])
    where_sql = " AND ".join(where)
    total_row = execute_one(f"SELECT COUNT(DISTINCT m.memo_id) AS cnt FROM memos m LEFT JOIN books b ON b.book_id=m.book_id LEFT JOIN emotions e ON e.user_id=m.user_id AND e.book_id=m.book_id WHERE {where_sql}", tuple(params))
    rows = execute_all(
        f"""
        SELECT m.memo_id AS post_id,m.memo_id,m.user_id,m.book_id,m.content,m.tags,m.page_num,m.created_at,
               u.display_name,u.emoji,u.genre_prefs,
               b.title AS book_title,b.author AS book_author,b.cover_url,b.cover_emoji,b.genre,
               q.question,
               (SELECT e2.emotion_type FROM emotions e2 WHERE e2.user_id=m.user_id AND e2.book_id=m.book_id ORDER BY e2.recorded_at DESC,e2.created_at DESC LIMIT 1) AS emotion_type,
               (SELECT COUNT(*) FROM community_post_reactions r WHERE r.post_id=m.memo_id AND r.reaction_type='like') AS like_count,
               (SELECT COUNT(*) FROM community_post_comments c WHERE c.post_id=m.memo_id) AS comment_count,
               EXISTS(SELECT 1 FROM community_post_reactions r2 WHERE r2.post_id=m.memo_id AND r2.user_id=%s AND r2.reaction_type='like') AS liked,
               EXISTS(SELECT 1 FROM community_post_saves s WHERE s.post_id=m.memo_id AND s.user_id=%s) AS saved
        FROM memos m
        LEFT JOIN users u ON u.user_id=m.user_id
        LEFT JOIN books b ON b.book_id=m.book_id
        LEFT JOIN community_generated_questions q ON q.source_type='memo' AND q.source_id=m.memo_id
        LEFT JOIN emotions e ON e.user_id=m.user_id AND e.book_id=m.book_id
        WHERE {where_sql}
        GROUP BY m.memo_id,m.user_id,m.book_id,m.content,m.tags,m.page_num,m.created_at,
                 u.display_name,u.emoji,u.genre_prefs,b.title,b.author,b.cover_url,b.cover_emoji,b.genre,q.question
        ORDER BY m.created_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple([user_id, user_id] + params + [limit, (page - 1) * limit]),
    )
    return [dict(r) for r in rows], int((total_row or {}).get("cnt", 0) or 0)


def _db_post_by_id(post_id: str, user_id: str) -> dict:
    rows, _ = _db_feed_rows(user_id, 1, 1, "", post_id, "")
    for row in rows:
        if row.get("post_id") == post_id:
            return _shape_post(row, user_id)
    row = execute_one(
        """
        SELECT m.memo_id AS post_id,m.*,u.display_name,u.emoji,u.genre_prefs,
               b.title AS book_title,b.author AS book_author,b.cover_url,b.cover_emoji,b.genre,
               q.question,0 AS like_count,0 AS comment_count,0 AS liked,0 AS saved
        FROM memos m
        LEFT JOIN users u ON u.user_id=m.user_id
        LEFT JOIN books b ON b.book_id=m.book_id
        LEFT JOIN community_generated_questions q ON q.source_type='memo' AND q.source_id=m.memo_id
        WHERE m.memo_id=%s
        """,
        (post_id,),
    )
    return _shape_post(dict(row or {}), user_id)


def _upsert_question(memo_id: str, user_id: str, book_id: str, question: str) -> None:
    existing = execute_one("SELECT question_id FROM community_generated_questions WHERE source_type='memo' AND source_id=%s", (memo_id,))
    if existing:
        execute_write("UPDATE community_generated_questions SET question=%s WHERE question_id=%s", (question, existing["question_id"]))
    else:
        execute_write(
            "INSERT INTO community_generated_questions(question_id,source_type,source_id,book_id,user_id,question) VALUES(%s,'memo',%s,%s,%s,%s)",
            (f"q_{uuid.uuid4().hex[:10]}", memo_id, book_id, user_id, question),
        )


def _shape_post(row: dict, viewer_id: str) -> dict:
    post_id = row.get("post_id") or row.get("memo_id") or ""
    thought = str(row.get("content") or row.get("thought") or "").strip()
    tags = _merged_tags(row.get("tags"), row.get("emotion_type"), row.get("genre"))
    question = (row.get("question") or "").strip() or _fallback_question(row.get("book_title"), thought, tags)
    quote = _quote_from_text(thought)
    post_type = "question" if thought.endswith("?") or "?" in question else ("quote" if quote else "thought")
    return {
        "post_id": post_id,
        "id": post_id,
        "card_id": post_id,
        "type": post_type,
        "user": {
            "user_id": row.get("user_id") or "",
            "display_name": row.get("display_name") or "독자",
            "emoji": row.get("emoji") or "📚",
            "tags": _normalize_tags(row.get("genre_prefs")),
        },
        "book": {
            "book_id": row.get("book_id") or "",
            "title": row.get("book_title") or "미분류",
            "author": row.get("book_author") or "",
            "cover_url": row.get("cover_url") or _enrich_cover(row.get("book_title") or row.get("title") or ""),
            "cover_emoji": row.get("cover_emoji") or "📚",
        },
        "thought": thought,
        "content": thought,
        "question": question,
        "quote": quote,
        "emotion_tags": tags,
        "tags": tags,
        "likes": int(row.get("like_count") or row.get("likes") or 0),
        "like_count": int(row.get("like_count") or row.get("likes") or 0),
        "comments": int(row.get("comment_count") or row.get("comments") or 0),
        "comment_count": int(row.get("comment_count") or row.get("comments") or 0),
        "saved": bool(row.get("saved")),
        "liked": bool(row.get("liked")),
        "is_liked": bool(row.get("liked")),
        "created_at": str(row.get("created_at") or ""),
    }


def _shape_trending_book(row: dict) -> dict:
    return {
        "book_id": row.get("book_id") or "",
        "title": row.get("title") or "",
        "author": row.get("author") or "",
        "cover_url": row.get("cover_url") or _enrich_cover(row.get("book_title") or row.get("title") or ""),
        "cover_emoji": row.get("cover_emoji") or "📚",
        "genre": row.get("genre") or "",
        "thought_count": int(row.get("thought_count") or 0),
        "question_count": int(row.get("question_count") or 0),
        "reader_count": int(row.get("reader_count") or 0),
    }


def _shape_reader(row: dict) -> dict:
    return {
        "user_id": row.get("user_id") or "",
        "display_name": row.get("display_name") or "독자",
        "emoji": row.get("emoji") or "📚",
        "status": row.get("status") or "",
        "progress": int(row.get("progress") or 0),
        "memo_count": int(row.get("memo_count") or 0),
        "question_count": int(row.get("question_count") or 0),
        "book": {
            "book_id": row.get("book_id") or "",
            "title": row.get("title") or "",
            "author": row.get("author") or "",
            "cover_url": row.get("cover_url") or _enrich_cover(row.get("book_title") or row.get("title") or ""),
            "cover_emoji": row.get("cover_emoji") or "📚",
        },
    }


def _shape_comment(row: dict) -> dict:
    comment_id = row.get("comment_id") or row.get("id") or ""
    return {
        "comment_id": comment_id,
        "id": comment_id,
        "post_id": row.get("post_id") or "",
        "user_id": row.get("user_id") or "",
        "content": row.get("content") or row.get("text") or "",
        "author_name": row.get("display_name") or row.get("author_name") or "독자",
        "author_emoji": row.get("emoji") or row.get("author_emoji") or "📚",
        "created_at": str(row.get("created_at") or ""),
    }


def _memory_posts(user_id: str, tag: str, q: str, emotion: str) -> list[dict]:
    try:
        from app.services.reading_service import _memos_mem, _emotions_mem
    except Exception:
        _memos_mem, _emotions_mem = [], []
    posts = [_shape_memory_post(m, user_id, _emotions_mem) for m in sorted(_memos_mem, key=lambda x: str(x.get("created_at") or ""), reverse=True) if str(m.get("content") or "").strip()]
    if tag:
        posts = [p for p in posts if tag in p.get("emotion_tags", []) or tag in p.get("book", {}).get("title", "")]
    if q:
        ql = q.lower()
        posts = [p for p in posts if ql in p.get("thought", "").lower() or ql in p.get("book", {}).get("title", "").lower()]
    if emotion:
        posts = [p for p in posts if emotion in p.get("emotion_tags", [])]
    return posts


def _shape_memory_post(memo: dict, viewer_id: str, emotions: list[dict] | None = None) -> dict:
    try:
        from app.services.shelf_service import _books_mem
        bmap = {b.get("book_id"): b for b in _books_mem}
    except Exception:
        bmap = {}
    book = bmap.get(memo.get("book_id"), {})
    emotion_type = ""
    for e in emotions or []:
        if e.get("user_id") == memo.get("user_id") and e.get("book_id") == memo.get("book_id"):
            emotion_type = e.get("emotion_type", "")
            break
    row = {
        "post_id": memo.get("memo_id"),
        "memo_id": memo.get("memo_id"),
        "user_id": memo.get("user_id"),
        "content": memo.get("content"),
        "tags": memo.get("tags", []),
        "created_at": memo.get("created_at"),
        "book_id": memo.get("book_id"),
        "book_title": memo.get("book_title") or book.get("title"),
        "book_author": book.get("author"),
        "cover_url": book.get("cover_url", ""),
        "cover_emoji": book.get("cover_emoji", "📚"),
        "genre": book.get("genre", ""),
        "display_name": "나" if memo.get("user_id") == viewer_id else "독자",
        "emoji": "✨",
        "emotion_type": emotion_type,
        "question": _memory_questions.get(memo.get("memo_id", "")),
        "like_count": len(_memory_reactions.get(memo.get("memo_id"), set())),
        "comment_count": len(_memory_comments.get(memo.get("memo_id"), [])),
        "liked": viewer_id in _memory_reactions.get(memo.get("memo_id"), set()),
        "saved": viewer_id in _memory_saves.get(memo.get("memo_id"), set()),
    }
    return _shape_post(row, viewer_id)


def _memory_trending_books(limit: int) -> list[dict]:
    try:
        from app.services.reading_service import _memos_mem
        from app.services.shelf_service import _books_mem, _shelf_mem
    except Exception:
        return []
    memo_counts = Counter(m.get("book_id") for m in _memos_mem if m.get("book_id"))
    reader_counts = Counter(s.get("book_id") for s in _shelf_mem if s.get("book_id"))
    books = []
    for book in _books_mem:
        bid = book.get("book_id")
        if not bid:
            continue
        books.append(_shape_trending_book({
            **book,
            "thought_count": memo_counts.get(bid, 0),
            "question_count": sum(1 for k in _memory_questions if k),
            "reader_count": reader_counts.get(bid, 0),
        }))
    books.sort(key=lambda b: (b["thought_count"], b["reader_count"]), reverse=True)
    return books[:limit]


def _memory_same_book_readers(book_id: str, title: str, limit: int) -> list[dict]:
    try:
        from app.services.shelf_service import _books_mem, _shelf_mem
    except Exception:
        return []
    bmap = {b.get("book_id"): b for b in _books_mem}
    rows = []
    for shelf in _shelf_mem:
        book = bmap.get(shelf.get("book_id"), {})
        if (book_id and shelf.get("book_id") != book_id) or (title and book.get("title") != title):
            continue
        rows.append(_shape_reader({**shelf, **book, "memo_count": 0, "question_count": 0}))
    return rows[:limit]


def _normalize_tags(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        raw = value
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
            raw = parsed if isinstance(parsed, list) else [value]
        except Exception:
            raw = [x.strip() for x in value.replace("#", "").split(",")]
    else:
        raw = [str(value)]
    seen, tags = set(), []
    for item in raw:
        text = str(item or "").strip().strip("#")
        if text and text not in seen:
            seen.add(text)
            tags.append(text)
    return tags[:8]


def _merged_tags(tags: Any, emotion: str = "", genre: str = "") -> list[str]:
    merged = _normalize_tags(tags)
    for item in [emotion, genre]:
        item = str(item or "").strip()
        if item and item not in merged:
            merged.append(item)
    return merged[:8]


def _fallback_question(book_title: str, thought: str, tags: list[str]) -> str:
    if "?" in thought:
        parts = [p.strip() for p in thought.replace("？", "?").split("?") if p.strip()]
        if parts:
            return parts[-1][-80:] + "?"
    if book_title:
        return f"{book_title}은 우리에게 어떤 질문을 남길까?"
    if tags:
        return f"{tags[0]}이라는 감정은 어디에서 시작됐을까?"
    return "이 생각에 동의한다면, 그 이유는 무엇일까?"


def _quote_from_text(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        return ""
    for left, right in [("\"", "\""), ("“", "”"), ("'", "'"), ("‘", "’")]:
        if left in text and right in text:
            start = text.find(left)
            end = text.find(right, start + 1)
            if end > start:
                quote = text[start + 1:end].strip()
                if 4 <= len(quote) <= 180:
                    return quote
    if len(text) <= 120 and any(mark in text for mark in [".", "다", "요", "까"]):
        return text
    return ""
