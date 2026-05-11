"""Profile page service layer.

Builds the "reading universe" profile payloads from existing LUMA services.
Every public function returns an {ok: bool, ...} payload and falls back to
stable mock data when local data is empty.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime
from typing import Any


def _now_iso() -> str:
    return datetime.now().isoformat()


def _safe_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return _safe_tags(parsed)
        except Exception:
            pass
        return [v.strip().lstrip("#") for v in value.split(",") if v.strip()]
    return []


def _mock_profile(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "display_name": "박소연" if user_id == "user_demo" else "LUMA 독자",
        "email": "demo@luma.kr" if user_id == "user_demo" else "",
        "emoji": "✨",
        "bio": "사람의 마음과 우주, 고독에 대해 읽는 독자",
        "tags": ["철학", "우주", "고독", "성장"],
        "persona": "사유형 독자",
        "created_at": "2026-01-05",
    }


def _profile(user_id: str) -> dict:
    try:
        from app.services.user_service import get_me

        user = get_me(user_id) or {}
    except Exception:
        user = {}

    fallback = _mock_profile(user_id)
    tags = _safe_tags(user.get("genre_prefs") or user.get("tags"))
    return {
        "user_id": user.get("user_id") or fallback["user_id"],
        "display_name": user.get("display_name") or fallback["display_name"],
        "email": user.get("email") or fallback["email"],
        "emoji": user.get("emoji") or fallback["emoji"],
        "bio": user.get("bio") or fallback["bio"],
        "tags": tags or fallback["tags"],
        "persona": fallback["persona"],
        "created_at": str(user.get("created_at") or fallback["created_at"]),
    }


def _list_memos(user_id: str, limit: int = 20) -> list[dict]:
    try:
        from app.services.reading_service import list_memos

        return list_memos(user_id, limit=limit).get("memos", [])
    except Exception:
        return []


def _shelf(user_id: str) -> dict:
    try:
        from app.services.shelf_service import get_shelf

        return get_shelf(user_id)
    except Exception:
        return {"ok": True, "books": [], "stats": {}}


def _mock_current_reading() -> dict:
    return {
        "book_id": "book_cosmos",
        "title": "코스모스",
        "author": "칼 세이건",
        "cover_url": "",
        "cover_emoji": "🌌",
        "progress": 62,
        "recent_memo": "인간은 우주를 이해하려고 하는 존재다.",
        "recent_emotion": "curious",
        "status": "reading",
    }


def get_summary(user_id: str = "user_demo") -> dict:
    profile = _profile(user_id)
    try:
        from app.services.user_service import get_user_stats

        stats = get_user_stats(user_id)
    except Exception:
        stats = {}
    shelf = _shelf(user_id)
    profile["persona"] = get_persona(user_id).get("persona", {}).get("persona", profile["persona"])
    return {
        "ok": True,
        "profile": profile,
        "stats": {
            "books_done": stats.get("books_done", 0),
            "memos": stats.get("memos", shelf.get("stats", {}).get("memos", 0)),
            "emotions": stats.get("emotions", 0),
            "connections": stats.get("connections", 0),
            "reading": shelf.get("stats", {}).get("reading", 0),
            "total_books": shelf.get("stats", {}).get("total", stats.get("books_done", 0)),
            "reading_streak": shelf.get("stats", {}).get("reading_streak", 0),
        },
    }


def get_current_reading(user_id: str = "user_demo") -> dict:
    shelf = _shelf(user_id)
    books = shelf.get("books") or shelf.get("items") or []
    reading = next((b for b in books if b.get("status") == "reading"), None)
    if not reading:
        reading = next((b for b in books if b.get("status") != "done"), None)

    if not reading:
        book = _mock_current_reading()
        return {"ok": True, "current_reading": book, "book": book, "source": "fallback"}

    memos = [m for m in _list_memos(user_id, 20) if not reading.get("book_id") or m.get("book_id") == reading.get("book_id")]
    recent_memo = (memos[0].get("content") if memos else "") or "아직 이 책에 저장한 문장이 없습니다."
    book = {
        "book_id": reading.get("book_id", ""),
        "title": reading.get("title") or reading.get("label") or "읽는 중인 책",
        "author": reading.get("author", ""),
        "cover_url": reading.get("cover_url", ""),
        "cover_emoji": reading.get("cover_emoji") or reading.get("emoji") or "📘",
        "progress": int(reading.get("progress") or 0),
        "recent_memo": recent_memo,
        "recent_emotion": reading.get("dominant_em") or "curious",
        "status": reading.get("status", "reading"),
    }
    return {"ok": True, "current_reading": book, "book": book}


def get_constellation(user_id: str = "user_demo") -> dict:
    try:
        from app.services.reading_service import get_constellation as reading_constellation

        raw = reading_constellation(user_id)
    except Exception:
        raw = {"nodes": [], "links": []}

    profile = _profile(user_id)
    nodes = [{"id": "user", "type": "user", "label": profile["display_name"] or "나"}]
    links = []

    for node in (raw.get("nodes") or [])[:8]:
        node_id = node.get("id") or node.get("book_id")
        if not node_id:
            continue
        nodes.append({
            "id": node_id,
            "type": "book",
            "label": node.get("title") or node.get("label") or "책",
            "meta": node.get("author") or "",
        })
        links.append({"source": "user", "target": node_id})

    memos = _list_memos(user_id, 8)
    tag_seen = set()
    for i, memo in enumerate(memos[:4], start=1):
        qid = f"sentence_{i}"
        label = (memo.get("content") or "")[:34] or "저장한 문장"
        nodes.append({"id": qid, "type": "sentence", "label": label, "meta": memo.get("book_title", "")})
        target = memo.get("book_id") if any(n["id"] == memo.get("book_id") for n in nodes) else "user"
        links.append({"source": target, "target": qid})
        for tag in _safe_tags(memo.get("tags"))[:2]:
            if tag in tag_seen:
                continue
            tag_seen.add(tag)
            tid = f"tag_{tag}"
            nodes.append({"id": tid, "type": "tag", "label": tag})
            links.append({"source": qid, "target": tid})

    if len(nodes) == 1:
        nodes.extend([
            {"id": "book_cosmos", "type": "book", "label": "코스모스"},
            {"id": "q_1", "type": "question", "label": "인간은 왜 우주를 알고 싶어할까?"},
            {"id": "tag_space", "type": "tag", "label": "우주"},
        ])
        links.extend([
            {"source": "user", "target": "book_cosmos"},
            {"source": "book_cosmos", "target": "q_1"},
            {"source": "q_1", "target": "tag_space"},
        ])

    return {"ok": True, "constellation": {"nodes": nodes, "links": links}, "nodes": nodes, "links": links}


def get_sentences(user_id: str = "user_demo") -> dict:
    memos = _list_memos(user_id, 12)
    sentences = [
        {
            "memo_id": m.get("memo_id") or m.get("id"),
            "sentence": m.get("content") or "",
            "book_title": m.get("book_title") or "미분류",
            "saved_at": str(m.get("created_at") or ""),
            "tags": _safe_tags(m.get("tags")) or ["생각"],
        }
        for m in memos
        if m.get("content")
    ]
    if not sentences:
        sentences = [
            {
                "memo_id": "memo_sample_1",
                "sentence": "인간은 자유롭도록 선고받았다.",
                "book_title": "실존주의와 인간 감정",
                "saved_at": date.today().isoformat(),
                "tags": ["자유", "책임", "불안"],
            }
        ]
    return {"ok": True, "sentences": sentences}


def get_timeline(user_id: str = "user_demo") -> dict:
    items = []
    for memo in _list_memos(user_id, 10):
        items.append({
            "type": "sentence",
            "title": "문장 저장",
            "description": (memo.get("content") or "")[:80],
            "book_title": memo.get("book_title", ""),
            "date": str(memo.get("created_at") or ""),
        })
    for book in (_shelf(user_id).get("books") or [])[:8]:
        if book.get("started_at"):
            items.append({
                "type": "book_start",
                "title": f"{book.get('title', '책')} 읽기 시작",
                "description": book.get("author", ""),
                "book_title": book.get("title", ""),
                "date": str(book.get("started_at")),
            })
        if book.get("finished_at"):
            items.append({
                "type": "book_done",
                "title": f"{book.get('title', '책')} 완독",
                "description": "완독 기록",
                "book_title": book.get("title", ""),
                "date": str(book.get("finished_at")),
            })
    try:
        from app.services.live_socrates_service import list_sessions

        sessions = list_sessions(user_id, 8).get("sessions", [])
        for session in sessions:
            items.append({
                "type": "socrates",
                "title": "소크라테스 대화",
                "description": session.get("passage", "")[:80],
                "book_title": session.get("book_title", ""),
                "date": str(session.get("created_at") or ""),
            })
    except Exception:
        pass
    if not items:
        items = [
            {"type": "book_start", "title": "코스모스 읽기 시작", "description": "우주 관련 질문 3개 생성", "book_title": "코스모스", "date": "2026-05-01"},
            {"type": "socrates", "title": "소크라테스 대화 2회 완료", "description": "인간과 우주에 대한 대화", "book_title": "코스모스", "date": "2026-05-08"},
        ]
    items.sort(key=lambda item: item.get("date") or "", reverse=True)
    return {"ok": True, "timeline": items[:16]}


def get_questions(user_id: str = "user_demo") -> dict:
    questions = []
    try:
        from app.services.live_socrates_service import list_sessions

        for session in list_sessions(user_id, 20).get("sessions", []):
            question = ""
            exchanges = session.get("exchanges")
            if isinstance(exchanges, str):
                try:
                    exchanges = json.loads(exchanges)
                except Exception:
                    exchanges = []
            if isinstance(exchanges, list) and exchanges:
                question = exchanges[-1].get("q") or exchanges[-1].get("question") or ""
            questions.append({
                "question_id": session.get("session_id"),
                "question": question or "이 문장은 나의 삶에 어떤 질문을 남길까?",
                "book_title": session.get("book_title") or "미분류",
                "tags": ["사유", "대화"],
                "created_at": str(session.get("created_at") or ""),
            })
    except Exception:
        pass
    if not questions:
        questions = [
            {
                "question_id": "q_sample_1",
                "question": "인간은 왜 자신의 위치를 알고 싶어할까?",
                "book_title": "코스모스",
                "tags": ["우주", "인간", "존재"],
                "created_at": date.today().isoformat(),
            }
        ]
    return {"ok": True, "questions": questions[:12]}


def get_persona(user_id: str = "user_demo") -> dict:
    memos = _list_memos(user_id, 50)
    tag_counter = Counter()
    for memo in memos:
        tag_counter.update(_safe_tags(memo.get("tags")))
    top_subjects = [tag for tag, _count in tag_counter.most_common(5)] or ["철학", "우주", "고독"]
    emotion_counter = Counter()
    try:
        from app.services.reading_service import get_emotion_timeline

        for item in get_emotion_timeline(user_id).get("timeline", []):
            emotion_counter[item.get("emotion_type") or item.get("emotion") or "curious"] += 1
    except Exception:
        pass
    persona = {
        "persona": "사유형 독자",
        "summary": "질문을 남기며 읽고, 감정보다 의미를 오래 붙잡는 독자입니다.",
        "traits": [
            "질문을 남기며 읽습니다.",
            "철학과 인간 존재에 관심이 많습니다.",
            "감정보다 의미를 오래 붙잡습니다.",
        ],
        "top_subjects": top_subjects,
        "top_emotions": [k for k, _ in emotion_counter.most_common(3)] or ["curious", "inspired"],
        "question_type": "존재와 의미를 묻는 질문",
        "recommendation": "다음에는 철학 Lounge에 참여해보세요.",
    }
    return {"ok": True, "persona": persona}


def get_lounges(user_id: str = "user_demo") -> dict:
    try:
        from app.services.live_backend_service import list_rooms

        rooms = list_rooms("active")[:6]
    except Exception:
        rooms = []
    lounges = [
        {
            "room_id": r.get("room_id"),
            "name": r.get("title") or "독서모임",
            "book_title": r.get("book_title") or "함께 읽는 책",
            "member_count": r.get("member_count", 0),
            "next_schedule": r.get("started_at") or "금요일 오후 9시",
            "recent_question": r.get("discussion_topic") or "과학책은 인간을 더 겸손하게 만들까?",
        }
        for r in rooms
    ]
    if not lounges:
        lounges = [
            {
                "room_id": "room_cosmos",
                "name": "코스모스 읽기 모임",
                "book_title": "코스모스",
                "member_count": 12,
                "next_schedule": "금요일 오후 9시",
                "recent_question": "과학책은 인간을 더 겸손하게 만들까?",
            }
        ]
    return {"ok": True, "lounges": lounges}


def get_similar_readers(user_id: str = "user_demo") -> dict:
    profile = _profile(user_id)
    shelf_books = [b.get("title") for b in (_shelf(user_id).get("books") or []) if b.get("title")]
    try:
        from app.services.social_feed_service import find_reading_buddies

        matches = find_reading_buddies(user_id, profile.get("tags", []), shelf_books)
    except Exception:
        matches = []
    readers = [
        {
            "user_id": m.get("user_id"),
            "display_name": m.get("display_name") or "비슷한 독자",
            "emoji": m.get("emoji") or "✨",
            "common_tags": m.get("shared_genres") or profile.get("tags", [])[:3],
            "common_books": m.get("shared_books") or shelf_books[:2],
            "question_style": "존재와 의미를 묻는 독자",
            "match_score": m.get("match_score", 72),
        }
        for m in matches
    ]
    if not readers:
        readers = [
            {
                "user_id": "reader_cosmos",
                "display_name": "김하늘",
                "emoji": "🌙",
                "common_tags": ["철학", "우주", "고독"],
                "common_books": ["코스모스", "어린왕자"],
                "question_style": "존재와 의미를 묻는 독자",
                "match_score": 84,
            }
        ]
    return {"ok": True, "readers": readers}
