"""Profile reading-universe service layer.

Every public function returns an {ok: bool, ...} payload for /api/v2/profile.
The service is intentionally defensive: it uses existing shelf, memo, emotion,
Socrates, and live-room services when available, then falls back to stable empty
shapes so the profile page can render without special casing failures.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Any


def get_summary(user_id: str = "user_demo") -> dict:
    profile = _profile(user_id)
    shelf = _shelf(user_id)
    books = shelf.get("books") or []
    memos = _list_memos(user_id, 200)
    emotions = _emotion_items(user_id)
    persona = get_persona(user_id).get("persona", {})
    profile["persona"] = persona.get("persona") or profile.get("persona") or "사유형 독자"

    stats = shelf.get("stats") or {}
    done = sum(1 for book in books if book.get("status") == "done")
    reading = sum(1 for book in books if book.get("status") == "reading")
    want = sum(1 for book in books if book.get("status") == "want")
    total_pages = sum(_int(book.get("total_pages")) for book in books)
    connections = _connection_count(user_id)

    return {
        "ok": True,
        "profile": profile,
        "stats": {
            "total_books": stats.get("total", len(books)),
            "books_done": stats.get("done", done),
            "reading": stats.get("reading", reading),
            "want": stats.get("want", want),
            "memos": stats.get("memos", len(memos)),
            "sentences": len(memos),
            "emotions": len(emotions),
            "connections": stats.get("connections", connections),
            "reading_streak": stats.get("reading_streak", 0),
            "total_pages": stats.get("total_pages", total_pages),
            "this_month": stats.get("this_month", 0),
        },
        "persona": persona,
    }


def get_current_reading(user_id: str = "user_demo") -> dict:
    books = _shelf(user_id).get("books") or []
    reading = next((b for b in books if b.get("status") == "reading"), None)
    if not reading:
        reading = next((b for b in books if b.get("status") != "done"), None)
    if not reading:
        return {"ok": True, "current_reading": None, "book": None, "source": "empty"}

    book_id = reading.get("book_id") or ""
    memos = [m for m in _list_memos(user_id, 30) if not book_id or m.get("book_id") == book_id]
    emotion = _latest_emotion(user_id, book_id)
    book = {
        "book_id": book_id,
        "title": reading.get("title") or reading.get("label") or "읽는 중인 책",
        "author": reading.get("author", ""),
        "cover_url": reading.get("cover_url", ""),
        "cover_emoji": reading.get("cover_emoji") or reading.get("emoji") or "책",
        "progress": _int(reading.get("progress")),
        "recent_memo": (memos[0].get("content") if memos else "") or "아직 이 책에 남긴 문장이 없습니다.",
        "recent_emotion": emotion or reading.get("dominant_em") or "curious",
        "status": reading.get("status", "reading"),
        "started_at": str(reading.get("started_at") or ""),
        "finished_at": str(reading.get("finished_at") or ""),
    }
    return {"ok": True, "current_reading": book, "book": book, "source": "shelf"}


def get_constellation(user_id: str = "user_demo") -> dict:
    profile = _profile(user_id)
    nodes = [{"id": "user", "type": "user", "label": profile["display_name"], "meta": profile.get("persona", "")}]
    links: list[dict] = []

    try:
        from app.services.reading_service import get_constellation as reading_constellation

        raw = reading_constellation(user_id)
    except Exception:
        raw = {"nodes": [], "links": []}

    seen = {"user"}
    for node in (raw.get("nodes") or [])[:12]:
        node_id = node.get("id") or node.get("book_id") or node.get("title")
        if not node_id or node_id in seen:
            continue
        seen.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "type": "book",
                "label": node.get("title") or node.get("label") or "책",
                "meta": node.get("author") or "",
                "memos": _int(node.get("memos")),
            }
        )
        links.append({"source": "user", "target": node_id, "type": "read"})

    for link in raw.get("links") or []:
        source = link.get("source")
        target = link.get("target")
        if source and target:
            links.append({"source": source, "target": target, "type": link.get("type") or "connection", "insight": link.get("insight") or link.get("theme") or ""})

    for index, memo in enumerate(_list_memos(user_id, 10)[:5], start=1):
        sentence_id = f"sentence_{index}"
        label = _short(memo.get("content"), 42) or "저장한 문장"
        nodes.append({"id": sentence_id, "type": "sentence", "label": label, "meta": memo.get("book_title", "")})
        target = memo.get("book_id") if memo.get("book_id") in seen else "user"
        links.append({"source": target, "target": sentence_id, "type": "memo"})
        for tag in _safe_tags(memo.get("tags"))[:2]:
            tag_id = f"tag_{tag}"
            if tag_id not in seen:
                seen.add(tag_id)
                nodes.append({"id": tag_id, "type": "tag", "label": tag})
            links.append({"source": sentence_id, "target": tag_id, "type": "tag"})

    return {"ok": True, "constellation": {"nodes": nodes, "links": links}, "nodes": nodes, "links": links}


def get_sentences(user_id: str = "user_demo") -> dict:
    sentences = [
        {
            "memo_id": memo.get("memo_id") or memo.get("id"),
            "sentence": memo.get("content") or "",
            "content": memo.get("content") or "",
            "book_id": memo.get("book_id", ""),
            "book_title": memo.get("book_title") or memo.get("title") or "미분류",
            "saved_at": str(memo.get("created_at") or ""),
            "tags": _safe_tags(memo.get("tags")) or ["생각"],
        }
        for memo in _list_memos(user_id, 30)
        if memo.get("content")
    ]
    return {"ok": True, "sentences": sentences, "count": len(sentences)}


def get_timeline(user_id: str = "user_demo") -> dict:
    items: list[dict] = []
    for memo in _list_memos(user_id, 30):
        items.append(
            {
                "type": "sentence",
                "title": "문장 저장",
                "description": _short(memo.get("content"), 90),
                "book_id": memo.get("book_id", ""),
                "book_title": memo.get("book_title", ""),
                "date": str(memo.get("created_at") or ""),
            }
        )
    for book in (_shelf(user_id).get("books") or []):
        if book.get("started_at"):
            items.append(
                {
                    "type": "book_start",
                    "title": f"{book.get('title', '책')} 읽기 시작",
                    "description": book.get("author", ""),
                    "book_id": book.get("book_id", ""),
                    "book_title": book.get("title", ""),
                    "date": str(book.get("started_at")),
                }
            )
        if book.get("finished_at"):
            items.append(
                {
                    "type": "book_done",
                    "title": f"{book.get('title', '책')} 완독",
                    "description": "완독 기록",
                    "book_id": book.get("book_id", ""),
                    "book_title": book.get("title", ""),
                    "date": str(book.get("finished_at")),
                }
            )
    for session in _socrates_sessions(user_id, 10):
        items.append(
            {
                "type": "socrates",
                "title": "소크라테스 대화",
                "description": _short(session.get("passage") or session.get("question"), 90),
                "book_title": session.get("book_title", ""),
                "date": str(session.get("created_at") or ""),
            }
        )
    items.sort(key=lambda item: item.get("date") or "", reverse=True)
    return {"ok": True, "timeline": items[:40], "count": len(items[:40])}


def get_questions(user_id: str = "user_demo") -> dict:
    questions = []
    for session in _socrates_sessions(user_id, 30):
        question = _question_from_session(session)
        questions.append(
            {
                "question_id": session.get("session_id") or session.get("id"),
                "question": question or "이 문장은 나의 삶에 어떤 질문을 남기나요?",
                "book_title": session.get("book_title") or "미분류",
                "tags": ["사유", "대화"],
                "created_at": str(session.get("created_at") or ""),
            }
        )
    if not questions:
        for memo in _list_memos(user_id, 8):
            questions.append(
                {
                    "question_id": memo.get("memo_id"),
                    "question": _fallback_question(memo.get("book_title"), memo.get("content")),
                    "book_title": memo.get("book_title") or "미분류",
                    "tags": _safe_tags(memo.get("tags")) or ["생각"],
                    "created_at": str(memo.get("created_at") or ""),
                }
            )
    return {"ok": True, "questions": questions[:20], "count": len(questions[:20])}


def get_persona(user_id: str = "user_demo") -> dict:
    memos = _list_memos(user_id, 100)
    books = _shelf(user_id).get("books") or []
    emotions = _emotion_items(user_id)

    tag_counter = Counter()
    for memo in memos:
        tag_counter.update(_safe_tags(memo.get("tags")))
    genre_counter = Counter(
        str(book.get("genre") or book.get("category") or "").strip()
        for book in books
        if str(book.get("genre") or book.get("category") or "").strip()
    )
    emotion_counter = Counter(item.get("emotion_type") or item.get("emotion") or "curious" for item in emotions)

    top_subjects = [tag for tag, _ in tag_counter.most_common(5)]
    for genre, _ in genre_counter.most_common(5):
        if genre and genre not in top_subjects:
            top_subjects.append(genre)
        if len(top_subjects) >= 5:
            break
    top_emotions = [emotion for emotion, _ in emotion_counter.most_common(3)]

    primary_subject = top_subjects[0] if top_subjects else "사유"
    primary_emotion = top_emotions[0] if top_emotions else "curious"
    done_count = sum(1 for book in books if book.get("status") == "done")
    persona = {
        "persona": f"{primary_subject}형 독자",
        "summary": f"{primary_subject} 주제를 중심으로 문장과 질문을 오래 붙잡는 독서 성향입니다.",
        "traits": [
            f"저장한 문장 {len(memos)}개",
            f"완독 기록 {done_count}권",
            f"관심 감정 {primary_emotion}",
        ],
        "top_subjects": top_subjects,
        "top_emotions": top_emotions,
        "question_type": "문장 속 의미를 현재의 삶과 연결해 묻는 편입니다.",
        "recommendation": "짧은 문장 기록과 토론 질문을 함께 남기면 독서 우주가 더 촘촘해집니다.",
        "evidence": {"books": len(books), "memos": len(memos), "emotions": len(emotions)},
    }
    return {"ok": True, "persona": persona}


def get_lounges(user_id: str = "user_demo") -> dict:
    lounges = []
    try:
        from app.services.live_backend_service import list_rooms

        rooms = list_rooms("active")[:8]
    except Exception:
        rooms = []
    for room in rooms:
        lounges.append(
            {
                "room_id": room.get("room_id"),
                "id": room.get("room_id"),
                "name": room.get("title") or "독서모임",
                "book_title": room.get("book_title") or "함께 읽는 책",
                "member_count": _int(room.get("member_count")),
                "next_schedule": room.get("started_at") or "",
                "recent_question": room.get("discussion_topic") or "이 책이 지금 우리에게 던지는 질문은 무엇일까요?",
            }
        )
    return {"ok": True, "lounges": lounges, "count": len(lounges)}


def get_similar_readers(user_id: str = "user_demo") -> dict:
    profile = _profile(user_id)
    books = [b.get("title") for b in (_shelf(user_id).get("books") or []) if b.get("title")]
    try:
        from app.services.social_feed_service import find_reading_buddies

        matches = find_reading_buddies(user_id, profile.get("tags", []), books)
    except Exception:
        matches = []
    readers = [
        {
            "user_id": item.get("user_id"),
            "display_name": item.get("display_name") or "비슷한 독자",
            "emoji": item.get("emoji") or "책",
            "common_tags": item.get("shared_genres") or profile.get("tags", [])[:3],
            "common_books": item.get("shared_books") or books[:2],
            "question_style": "존재와 의미를 묻는 독자",
            "match_score": item.get("match_score", 72),
        }
        for item in matches
    ]
    return {"ok": True, "readers": readers}


def _profile(user_id: str) -> dict:
    try:
        from app.services.user_service import get_me

        user = get_me(user_id) or {}
    except Exception:
        user = {}
    tags = _safe_tags(user.get("genre_prefs") or user.get("tags"))
    return {
        "user_id": user.get("user_id") or user_id,
        "display_name": user.get("display_name") or "LUMA reader",
        "email": user.get("email") or "",
        "emoji": user.get("emoji") or "책",
        "bio": user.get("bio") or "독서와 질문으로 나만의 우주를 만드는 중입니다.",
        "tags": tags,
        "persona": "사유형 독자",
        "created_at": str(user.get("created_at") or "2026-01-05"),
    }


def _shelf(user_id: str) -> dict:
    try:
        from app.services.shelf_service import get_shelf

        result = get_shelf(user_id)
        result.setdefault("books", [])
        result.setdefault("stats", {})
        return result
    except Exception:
        return {"ok": True, "books": [], "stats": {}}


def _list_memos(user_id: str, limit: int = 20) -> list[dict]:
    try:
        from app.services.reading_service import list_memos

        return list_memos(user_id, limit=limit).get("memos", [])
    except Exception:
        return []


def _emotion_items(user_id: str) -> list[dict]:
    try:
        from app.services.reading_service import get_emotion_timeline

        result = get_emotion_timeline(user_id)
        return result.get("timeline") or result.get("emotions") or []
    except Exception:
        return []


def _latest_emotion(user_id: str, book_id: str = "") -> str:
    for item in _emotion_items(user_id):
        if not book_id or item.get("book_id") == book_id:
            return item.get("emotion_type") or item.get("emotion") or ""
    return ""


def _socrates_sessions(user_id: str, limit: int = 10) -> list[dict]:
    try:
        from app.services.live_socrates_service import list_sessions

        return list_sessions(user_id, limit).get("sessions", [])
    except Exception:
        return []


def _connection_count(user_id: str) -> int:
    try:
        from app.services.reading_service import get_constellation

        return len(get_constellation(user_id).get("links", []) or [])
    except Exception:
        return 0


def _question_from_session(session: dict) -> str:
    exchanges = session.get("exchanges")
    if isinstance(exchanges, str):
        try:
            exchanges = json.loads(exchanges)
        except Exception:
            exchanges = []
    if isinstance(exchanges, list) and exchanges:
        latest = exchanges[-1] or {}
        return latest.get("q") or latest.get("question") or latest.get("assistant") or ""
    return session.get("question") or ""


def _fallback_question(book_title: str = "", content: str = "") -> str:
    if "?" in str(content or ""):
        return str(content).split("?")[0][-80:] + "?"
    if book_title:
        return f"{book_title}은 지금 나에게 어떤 질문을 남기나요?"
    return "이 문장을 다시 읽는다면 무엇을 더 묻고 싶나요?"


def _safe_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = value
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
            raw = parsed if isinstance(parsed, list) else value.replace("#", "").split(",")
        except Exception:
            raw = value.replace("#", "").split(",")
    else:
        raw = []
    seen, tags = set(), []
    for item in raw:
        text = str(item or "").strip().strip("#")
        if text and text not in seen:
            seen.add(text)
            tags.append(text)
    return tags[:10]


def _short(value: object, limit: int = 80) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _int(value: object) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0
