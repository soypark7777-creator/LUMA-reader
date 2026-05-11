"""
LUMA — 감정·별자리·메모 서비스 (MySQL)
──────────────────────────────────────────────────────
"""
import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, date
from typing import Optional

from app.db import is_connected, execute_one, execute_all, execute_write

# ── Mock 데이터 ──────────────────────────────────────────
_emotions_mem: list[dict] = [
    {"emotion_id":"em_001","user_id":"user_demo","book_id":"book_001","emotion_type":"curious","intensity":4,"note":"허구를 믿는 능력이 인류를 협력하게 했다는 개념이 충격적","recorded_at":"2025-03-05"},
    {"emotion_id":"em_002","user_id":"user_demo","book_id":"book_001","emotion_type":"inspired","intensity":5,"note":"역사를 이렇게 큰 그림으로 볼 수 있다는 것이 감동","recorded_at":"2025-03-12"},
    {"emotion_id":"em_003","user_id":"user_demo","book_id":"book_002","emotion_type":"sad","intensity":5,"note":"가장 중요한 것은 눈에 보이지 않아 — 읽는 내내 눈물","recorded_at":"2025-03-21"},
    {"emotion_id":"em_004","user_id":"user_demo","book_id":"book_003","emotion_type":"peaceful","intensity":4,"note":"우주의 광대함 앞에서 일상의 고민이 작아지는 느낌","recorded_at":"2025-04-03"},
]
_connections_mem: list[dict] = [
    {"conn_id":"cn_001","user_id":"user_demo","book_id_a":"book_001","book_id_b":"book_002","theme":"허구와 상상력이 현실을 만든다","note":"사피엔스의 허구 믿기 ↔ 어린왕자의 마음으로 보기","strength":0.7},
    {"conn_id":"cn_002","user_id":"user_demo","book_id_a":"book_001","book_id_b":"book_003","theme":"인류가 우주에서 차지하는 위치","note":"역사적 관점 ↔ 우주적 관점","strength":0.6},
]
_memos_mem: list[dict] = []

EM_META = {
    "inspired":  {"label":"영감",   "emoji":"✨","color":"#F2C94C"},
    "curious":   {"label":"호기심","emoji":"🔍","color":"#56CCF2"},
    "sad":       {"label":"감동",   "emoji":"💙","color":"#2D9CDB"},
    "surprised": {"label":"놀람",   "emoji":"⚡","color":"#BB86FC"},
    "peaceful":  {"label":"평온",   "emoji":"🌿","color":"#6FCF97"},
    "excited":   {"label":"흥분",   "emoji":"🔥","color":"#EB5757"},
}


# ══════════════════════════════════════════════════════
#  감정 타임라인
# ══════════════════════════════════════════════════════

def add_emotion(user_id: str, data: dict) -> dict:
    book_id = data.get("book_id", "")
    em_type = data.get("emotion", data.get("emotion_type", "inspired"))
    intensity = int(data.get("intensity", 3))
    note      = data.get("note") or data.get("quote") or data.get("memo") or data.get("content") or ""
    rec_date  = data.get("date", date.today().isoformat())
    em_id     = f"em_{uuid.uuid4().hex[:8]}"

    if is_connected():
        try:
            execute_write(
                "INSERT INTO emotions(emotion_id,user_id,book_id,emotion_type,intensity,note,recorded_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (em_id, user_id, book_id, em_type, intensity, note, rec_date)
            )
            _auto_connect(book_id, user_id)
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        _emotions_mem.append({
            "emotion_id": em_id, "user_id": user_id, "book_id": book_id,
            "emotion_type": em_type, "intensity": intensity, "note": note, "recorded_at": rec_date,
        })
        _auto_connect(book_id, user_id)

    return {"ok": True, "emotion": {"emotion_id": em_id, "emotion_type": em_type,
                                     "intensity": intensity, "note": note}}


def update_emotion(user_id: str, emotion_id: str, data: dict) -> dict:
    em_type = data.get("emotion", data.get("emotion_type"))
    intensity = data.get("intensity")
    note = data.get("note", data.get("quote", data.get("memo")))
    book_id = data.get("book_id")
    rec_date = data.get("date", data.get("recorded_at"))

    if is_connected():
        try:
            exists = execute_one(
                "SELECT emotion_id FROM emotions WHERE emotion_id=%s AND user_id=%s",
                (emotion_id, user_id),
            )
            if not exists:
                return {"ok": False, "error": "감정 기록을 찾을 수 없습니다."}
            sets, vals = [], []
            if em_type: sets.append("emotion_type=%s"); vals.append(em_type)
            if intensity is not None: sets.append("intensity=%s"); vals.append(int(intensity))
            if note is not None: sets.append("note=%s"); vals.append(note)
            if book_id is not None: sets.append("book_id=%s"); vals.append(book_id)
            if rec_date: sets.append("recorded_at=%s"); vals.append(rec_date)
            if not sets:
                return {"ok": False, "error": "변경할 내용이 없습니다."}
            vals.extend([emotion_id, user_id])
            execute_write(
                "UPDATE emotions SET " + ",".join(sets) + " WHERE emotion_id=%s AND user_id=%s",
                vals,
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        emo = next((e for e in _emotions_mem if e.get("emotion_id") == emotion_id and e.get("user_id") == user_id), None)
        if not emo:
            return {"ok": False, "error": "감정 기록을 찾을 수 없습니다."}
        if em_type: emo["emotion_type"] = em_type
        if intensity is not None: emo["intensity"] = int(intensity)
        if note is not None: emo["note"] = note
        if book_id is not None: emo["book_id"] = book_id
        if rec_date: emo["recorded_at"] = rec_date
    return {"ok": True, "emotion": {"emotion_id": emotion_id}}


def delete_emotion(user_id: str, emotion_id: str) -> dict:
    if is_connected():
        try:
            exists = execute_one(
                "SELECT emotion_id FROM emotions WHERE emotion_id=%s AND user_id=%s",
                (emotion_id, user_id),
            )
            if not exists:
                return {"ok": False, "error": "감정 기록을 찾을 수 없습니다."}
            execute_write("DELETE FROM emotions WHERE emotion_id=%s AND user_id=%s", (emotion_id, user_id))
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        before = len(_emotions_mem)
        _emotions_mem[:] = [
            e for e in _emotions_mem
            if not (e.get("emotion_id") == emotion_id and e.get("user_id") == user_id)
        ]
        if len(_emotions_mem) == before:
            return {"ok": False, "error": "감정 기록을 찾을 수 없습니다."}
    return {"ok": True}


def get_emotion_timeline(user_id: str, book_id: str = None) -> dict:
    if is_connected():
        try:
            sql = """SELECT e.*, b.title AS book_title, b.cover_emoji AS book_emoji,
                            b.cover_url AS book_cover_url
                     FROM emotions e
                     LEFT JOIN books b ON e.book_id = b.book_id
                     WHERE e.user_id = %s"""
            params: list = [user_id]
            if book_id:
                sql += " AND e.book_id = %s"
                params.append(book_id)
            sql += " ORDER BY e.recorded_at DESC"
            rows = execute_all(sql, params)
            timeline = []
            for r in rows:
                r = dict(r)
                meta = EM_META.get(r.get("emotion_type",""), {})
                r.update({"emotion_label": meta.get("label",""), "emotion_emoji": meta.get("emoji",""),
                           "emotion_color": meta.get("color","#ccc"), "date": str(r.get("recorded_at","")),
                           "created_at": str(r.get("created_at") or r.get("recorded_at") or ""),
                           "emotion": r.get("emotion_type",""),
                           "quote": r.get("note", ""), "memo": r.get("note", "")})
                timeline.append(r)
        except Exception:
            timeline = []
    else:
        from app.services.shelf_service import _books_mem
        bmap = {b["book_id"]: b for b in _books_mem}
        items = [e for e in _emotions_mem if e["user_id"] == user_id]
        if book_id:
            items = [e for e in items if e["book_id"] == book_id]
        timeline = []
        for e in sorted(items, key=lambda x: x["recorded_at"], reverse=True):
            bk   = bmap.get(e["book_id"], {})
            meta = EM_META.get(e.get("emotion_type",""), {})
            timeline.append({**e, "emotion": e.get("emotion_type",""),
                              "book_title": bk.get("title",""), "book_emoji": bk.get("cover_emoji","📚"),
                              "book_cover_url": bk.get("cover_url",""),
                              "emotion_label": meta.get("label",""), "emotion_emoji": meta.get("emoji",""),
                              "emotion_color": meta.get("color","#ccc"), "date": e.get("recorded_at",""),
                              "created_at": e.get("created_at") or e.get("recorded_at",""),
                              "quote": e.get("note",""), "memo": e.get("note","")})

    # 통계
    counter: dict = defaultdict(int)
    for e in timeline:
        counter[e.get("emotion_type", e.get("emotion",""))] += 1
    by_em = [
        {**EM_META.get(k,{"label":k,"emoji":"","color":"#ccc"}), "type":k, "count":v}
        for k, v in sorted(counter.items(), key=lambda x:-x[1])
    ]
    return {
        "ok": True,
        "timeline": timeline,
        "stats": {
            "total":      len(timeline),
            "by_emotion": by_em,
            "dominant":   max(counter, key=counter.get) if counter else None,
        }
    }


# ══════════════════════════════════════════════════════
#  별자리 지식 그래프
# ══════════════════════════════════════════════════════

def get_constellation(user_id: str) -> dict:
    if is_connected():
        try:
            books_rows = execute_all(
                """SELECT sb.book_id, b.title AS label, b.author, b.cover_emoji AS emoji,
                          b.genre, b.cover_url, b.isbn, b.publisher, b.pub_year,
                          b.total_pages, b.description,
                          sb.status, sb.progress,
                          COALESCE(AVG(e.intensity),3) AS avg_intensity,
                          COUNT(DISTINCT m.memo_id) AS memo_count,
                          MAX(m.created_at) AS last_memo_at,
                          (SELECT emotion_type FROM emotions
                           WHERE user_id=%s AND book_id=sb.book_id
                           GROUP BY emotion_type ORDER BY COUNT(*) DESC LIMIT 1) AS dominant_em
                   FROM shelf_books sb
                   JOIN books b ON sb.book_id = b.book_id
                   LEFT JOIN emotions e ON e.book_id = sb.book_id AND e.user_id = sb.user_id
                   LEFT JOIN memos m ON m.book_id = sb.book_id AND m.user_id = sb.user_id
                   WHERE sb.user_id=%s
                   GROUP BY sb.book_id, b.title, b.author, b.cover_emoji, b.genre,
                            b.cover_url, b.isbn, b.publisher, b.pub_year, b.total_pages, b.description,
                            sb.status, sb.progress""",
                (user_id, user_id)
            )
            link_rows = execute_all(
                "SELECT * FROM book_connections WHERE user_id=%s", (user_id,)
            )
        except Exception:
            books_rows, link_rows = [], []
    else:
        from app.services.shelf_service import _books_mem, _shelf_mem
        shelf = [s for s in _shelf_mem if s["user_id"] == user_id]
        bmap  = {b["book_id"]: b for b in _books_mem}
        em_map: dict = defaultdict(list)
        for e in _emotions_mem:
            if e["user_id"] == user_id:
                em_map[e["book_id"]].append(e)
        books_rows = []
        for s in shelf:
            bk  = bmap.get(s["book_id"], {})
            ems = em_map.get(s["book_id"], [])
            memos = [m for m in _memos_mem if m["user_id"] == user_id and m.get("book_id") == s["book_id"]]
            avg = sum(e["intensity"] for e in ems) / len(ems) if ems else 3
            cnt: dict = defaultdict(int)
            for e in ems: cnt[e.get("emotion_type","inspired")] += 1
            dom = max(cnt, key=cnt.get) if cnt else "inspired"
            books_rows.append({"book_id": s["book_id"], "label": bk.get("title",""),
                                "author": bk.get("author",""), "emoji": bk.get("cover_emoji","📚"),
                                "genre": bk.get("genre",""), "cover_url": bk.get("cover_url", ""),
                                "isbn": bk.get("isbn", ""), "publisher": bk.get("publisher", ""),
                                "pub_year": bk.get("pub_year", ""),
                                "total_pages": bk.get("total_pages", 0), "description": bk.get("description", ""),
                                "status": s["status"], "progress": s.get("progress", 0),
                                "memo_count": len(memos), "avg_intensity": avg, "dominant_em": dom})
        link_rows = [c for c in _connections_mem if c["user_id"] == user_id]

    book_ids = {r["book_id"] for r in books_rows}
    nodes = []
    for r in books_rows:
        r = dict(r)
        meta = EM_META.get(r.get("dominant_em","inspired"), {"color":"#C17F3B"})
        memo_count = int(r.get("memo_count", 0) or 0)
        nodes.append({
            "id":      r["book_id"], "book_id": r["book_id"],
            "label": r.get("label",""), "title": r.get("label",""), "author": r.get("author",""),
            "emoji":   r.get("emoji","📚"), "genre": r.get("genre",""), "status": r.get("status",""),
            "progress": int(r.get("progress", 0) or 0),
            "cover_url": r.get("cover_url",""), "isbn": r.get("isbn",""),
            "publisher": r.get("publisher",""), "pub_year": r.get("pub_year", "") or "",
            "total_pages": r.get("total_pages", 0) or 0,
            "description": r.get("description",""), "memos": memo_count,
            "last_memo_at": str(r.get("last_memo_at") or ""),
            "is_current": r.get("status") == "reading",
            "size":    10 + float(r.get("avg_intensity",3)) * 3 + min(memo_count, 8),
            "color":   meta["color"], "emotion": r.get("dominant_em","inspired"),
        })

    links = []
    for r in link_rows:
        r = dict(r)
        a, b = r.get("book_id_a",""), r.get("book_id_b","")
        if a in book_ids and b in book_ids:
            links.append({"source": a, "target": b,
                          "theme": r.get("theme",""), "strength": float(r.get("strength",0.5))})

    stats = _get_constellation_stats(user_id)

    return {"ok": True, "nodes": nodes, "links": links,
            "total_books": len(nodes), "total_links": len(links), **stats}


def add_connection(user_id: str, data: dict) -> dict:
    from_id = data.get("from_book_id","")
    to_id   = data.get("to_book_id","")
    if not from_id or not to_id or from_id == to_id:
        return {"ok": False, "error": "서로 다른 두 책을 선택하세요."}

    conn_id = f"cn_{uuid.uuid4().hex[:8]}"
    a, b    = sorted([from_id, to_id])          # 정렬으로 중복 방지

    if is_connected():
        try:
            execute_write(
                "INSERT IGNORE INTO book_connections(conn_id,user_id,book_id_a,book_id_b,theme,note,strength) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (conn_id, user_id, a, b, data.get("theme",""), data.get("note",""),
                 float(data.get("strength",0.5)))
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        if not any(c["book_id_a"]==a and c["book_id_b"]==b and c["user_id"]==user_id
                   for c in _connections_mem):
            _connections_mem.append({"conn_id":conn_id,"user_id":user_id,
                                      "book_id_a":a,"book_id_b":b,
                                      "theme":data.get("theme",""),"note":data.get("note",""),
                                      "strength":float(data.get("strength",0.5))})
    return {"ok": True, "connection": {"conn_id": conn_id, "from": from_id, "to": to_id}}


def _auto_connect(book_id: str, user_id: str):
    """감정 기록 후 같은 서재의 책들과 약한 자동 연결을 만든다."""
    if not book_id:
        return

    if is_connected():
        try:
            rows = execute_all(
                "SELECT book_id FROM shelf_books WHERE user_id=%s AND book_id<>%s LIMIT 5",
                (user_id, book_id)
            )
            for row in rows:
                other = row.get("book_id")
                if not other:
                    continue
                a, b = sorted([book_id, other])
                theme = _generate_connection_theme(user_id, a, b)
                execute_write(
                    "INSERT IGNORE INTO book_connections"
                    "(conn_id,user_id,book_id_a,book_id_b,theme,note,strength,auto_created) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                    (f"cn_{uuid.uuid4().hex[:8]}", user_id, a, b,
                     theme, "", 0.2, 1)
                )
                execute_write(
                    "UPDATE book_connections SET theme=%s "
                    "WHERE user_id=%s AND book_id_a=%s AND book_id_b=%s AND auto_created=1",
                    (theme, user_id, a, b),
                )
        except Exception:
            return
        return

    from app.services.shelf_service import _shelf_mem
    others = [s["book_id"] for s in _shelf_mem
              if s["user_id"] == user_id and s["book_id"] != book_id]
    existing = {(c["book_id_a"], c["book_id_b"]) for c in _connections_mem}
    for other in others:
        a, b = sorted([book_id, other])
        theme = _generate_connection_theme(user_id, a, b)
        if (a, b) not in existing:
            _connections_mem.append({"conn_id": f"cn_{uuid.uuid4().hex[:6]}",
                                     "user_id": user_id, "book_id_a": a, "book_id_b": b,
                                     "theme": theme,
                                     "note": "", "strength": 0.2})
        else:
            for conn in _connections_mem:
                if conn["user_id"] == user_id and conn["book_id_a"] == a and conn["book_id_b"] == b:
                    conn["theme"] = theme
                    break


def _generate_connection_theme(user_id: str, book_id_a: str, book_id_b: str) -> str:
    fallback = "연결 탐색 중"
    if os.getenv("LUMA_SYNC_GEMINI_THEME", "").lower() not in ("1", "true", "yes"):
        return fallback
    try:
        from app.services.gemini_service import _call_gemini

        if is_connected():
            rows = execute_all(
                """SELECT b.title, e.note
                   FROM emotions e
                   LEFT JOIN books b ON e.book_id=b.book_id
                   WHERE e.user_id=%s AND e.book_id IN (%s,%s)
                   ORDER BY e.recorded_at DESC LIMIT 6""",
                (user_id, book_id_a, book_id_b)
            )
            notes = [f"{r.get('title','책')}: {r.get('note','')}" for r in rows if r.get("note")]
        else:
            from app.services.shelf_service import _books_mem
            bmap = {b["book_id"]: b for b in _books_mem}
            notes = [
                f"{bmap.get(e['book_id'], {}).get('title','책')}: {e.get('note','')}"
                for e in _emotions_mem
                if e["user_id"] == user_id and e["book_id"] in (book_id_a, book_id_b) and e.get("note")
            ][:6]

        if not notes:
            return fallback
        prompt = "이 두 책의 감정 메모를 읽고 공통 주제를 한 줄로 표현해줘.\n" + "\n".join(notes)
        theme = (_call_gemini(prompt) or "").strip()
        return theme[:80] if theme else fallback
    except Exception:
        return fallback


def _get_constellation_stats(user_id: str) -> dict:
    year_month = date.today().strftime("%Y-%m")
    if is_connected():
        try:
            reads = execute_one(
                "SELECT COUNT(*) AS cnt FROM shelf_books "
                "WHERE user_id=%s AND status='done' AND DATE_FORMAT(finished_at, '%%Y-%%m')=%s",
                (user_id, year_month)
            )
            emotions = execute_one("SELECT COUNT(*) AS cnt FROM emotions WHERE user_id=%s", (user_id,))
            genre = execute_one(
                """SELECT b.genre, COUNT(*) AS cnt
                   FROM shelf_books sb JOIN books b ON sb.book_id=b.book_id
                   WHERE sb.user_id=%s
                   GROUP BY b.genre ORDER BY cnt DESC LIMIT 1""",
                (user_id,)
            )
            return {
                "this_month_reads": int((reads or {}).get("cnt", 0) or 0),
                "total_emotions": int((emotions or {}).get("cnt", 0) or 0),
                "top_genre": (genre or {}).get("genre") or "",
            }
        except Exception:
            return {"this_month_reads": 0, "total_emotions": 0, "top_genre": ""}

    from app.services.shelf_service import _books_mem, _shelf_mem
    bmap = {b["book_id"]: b for b in _books_mem}
    shelf = [s for s in _shelf_mem if s["user_id"] == user_id]
    this_month_reads = sum(
        1 for s in shelf
        if s.get("status") == "done" and str(s.get("finished_at", ""))[:7] == year_month
    )
    genre_counts: dict = defaultdict(int)
    for s in shelf:
        genre_counts[bmap.get(s["book_id"], {}).get("genre", "")] += 1
    return {
        "this_month_reads": this_month_reads,
        "total_emotions": sum(1 for e in _emotions_mem if e["user_id"] == user_id),
        "top_genre": max(genre_counts, key=genre_counts.get) if genre_counts else "",
    }


def auto_suggest_books(user_id: str) -> dict:
    fallback = [
        {"title": "물고기는 존재하지 않는다", "author": "룰루 밀러", "reason": "지식과 믿음이 흔들리는 경험을 이어가기 좋습니다.", "genre": "에세이"},
        {"title": "랩 걸", "author": "호프 자런", "reason": "과학적 호기심과 삶의 감정을 함께 확장합니다.", "genre": "과학"},
        {"title": "데미안", "author": "헤르만 헤세", "reason": "자기 탐색과 성장의 질문을 더 깊게 이어줍니다.", "genre": "문학"},
    ]
    try:
        if is_connected():
            genres = execute_all(
                """SELECT b.genre, COUNT(*) AS cnt
                   FROM shelf_books sb JOIN books b ON sb.book_id=b.book_id
                   WHERE sb.user_id=%s GROUP BY b.genre ORDER BY cnt DESC LIMIT 5""",
                (user_id,)
            )
            emotions = execute_all(
                "SELECT emotion_type, COUNT(*) AS cnt FROM emotions "
                "WHERE user_id=%s GROUP BY emotion_type ORDER BY cnt DESC LIMIT 5",
                (user_id,)
            )
        else:
            from app.services.shelf_service import _books_mem, _shelf_mem
            bmap = {b["book_id"]: b for b in _books_mem}
            genre_counts: dict = defaultdict(int)
            for s in _shelf_mem:
                if s["user_id"] == user_id:
                    genre_counts[bmap.get(s["book_id"], {}).get("genre", "")] += 1
            emotion_counts: dict = defaultdict(int)
            for e in _emotions_mem:
                if e["user_id"] == user_id:
                    emotion_counts[e.get("emotion_type", "inspired")] += 1
            genres = [{"genre": k, "cnt": v} for k, v in genre_counts.items()]
            emotions = [{"emotion_type": k, "cnt": v} for k, v in emotion_counts.items()]

        persona_books = _search_persona_books(genres, emotions)
        if persona_books:
            return {"ok": True, "books": persona_books[:12], "source": "persona_search"}

        if os.getenv("LUMA_SYNC_GEMINI_THEME", "").lower() not in ("1", "true", "yes"):
            return {"ok": True, "books": fallback, "source": "mock"}

        from app.services.gemini_service import _call_gemini, _parse_json_safe

        prompt = (
            "사용자의 장르 분포와 감정 패턴을 보고 다음 읽을 책 3권을 추천해줘. "
            "JSON 배열로만 답하고 각 항목은 title, author, reason, genre를 포함해줘.\n"
            f"장르: {json.dumps(genres, ensure_ascii=False, default=str)}\n"
            f"감정: {json.dumps(emotions, ensure_ascii=False, default=str)}"
        )
        raw = _call_gemini(prompt, expect_json=True)
        parsed = _parse_json_safe(raw) if raw else None
        if isinstance(parsed, list) and parsed:
            return {"ok": True, "books": parsed[:3], "source": "gemini"}
    except Exception:
        pass
    return {"ok": True, "books": fallback, "source": "mock"}


def _search_persona_books(genres: list[dict], emotions: list[dict]) -> list[dict]:
    top_genre = next((g.get("genre") for g in genres if g.get("genre")), "")
    top_emotion = next((e.get("emotion_type") for e in emotions if e.get("emotion_type")), "")
    emotion_keywords = {
        "inspired": "영감 에세이",
        "curious": "호기심 과학 인문",
        "sad": "위로 문학",
        "surprised": "반전 지식 교양",
        "peaceful": "평온한 에세이",
        "excited": "몰입 소설",
    }
    queries = []
    if top_genre and top_emotion:
        queries.append(f"{top_genre} {emotion_keywords.get(top_emotion, '')}".strip())
    if top_genre:
        queries.append(f"{top_genre} 추천")
    if top_emotion:
        queries.append(emotion_keywords.get(top_emotion, top_emotion))
    queries.extend(["독서가 추천 도서", "인생 책"])

    books, seen = [], set()
    try:
        from app.services.shelf_service import search_books_naver, search_books_google, search_books
        for query in queries:
            found = search_books_naver(query, 6) or search_books_google(query, 6) or search_books(query, 6)
            for book in found:
                key = (book.get("isbn") or f"{book.get('title','')}|{book.get('author','')}").lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                book["reason"] = _persona_reason(top_genre, top_emotion)
                books.append(book)
            if len(books) >= 12:
                break
    except Exception:
        return []
    return books


def _persona_reason(genre: str, emotion: str) -> str:
    labels = {
        "inspired": "영감을 자주 남기는 독서 패턴",
        "curious": "호기심이 강한 독서 패턴",
        "sad": "감정과 여운을 깊게 붙잡는 독서 패턴",
        "surprised": "새로운 관점에 반응하는 독서 패턴",
        "peaceful": "차분한 사유를 좋아하는 독서 패턴",
        "excited": "몰입감 있는 책에 끌리는 독서 패턴",
    }
    if genre and emotion:
        return f"{genre}을 자주 읽고, {labels.get(emotion, '현재 감정 패턴')}과 잘 맞는 책입니다."
    if genre:
        return f"당신의 서재에서 자주 보이는 {genre} 취향과 이어지는 책입니다."
    if emotion:
        return f"{labels.get(emotion, '당신의 감정 기록')}과 연결해 읽기 좋은 책입니다."
    return "당신의 독서 페르소나를 넓혀줄 추천입니다."


# ══════════════════════════════════════════════════════
#  메모
# ══════════════════════════════════════════════════════

def save_memo(user_id: str, data: dict) -> dict:
    content = (data.get("content") or "").strip()
    if not content:
        return {"ok": False, "error": "메모 내용이 없습니다."}

    memo_id = f"memo_{uuid.uuid4().hex[:8]}"
    tags    = json.dumps(data.get("tags", []), ensure_ascii=False)
    now     = datetime.now()
    source  = data.get("source", "manual")
    book_id = data.get("book_id", "") or _resolve_book_id(user_id, data.get("book_title", ""))
    page_num = data.get("page_num", data.get("page_number"))
    if source not in ("manual", "ocr", "voice", "ai"):
        source = "manual"

    book_title = data.get("book_title", "")
    if is_connected():
        try:
            execute_write(
                "INSERT INTO memos(memo_id,user_id,book_id,content,tags,source,page_num,created_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (memo_id, user_id, book_id, content, tags, source, page_num, now)
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        _memos_mem.append({
            "memo_id": memo_id, "user_id": user_id, "book_id": book_id,
            "book_title": data.get("book_title", ""),
            "content": content, "tags": data.get("tags",[]), "source": source,
            "page_num": page_num, "page_number": page_num, "created_at": now.isoformat(),
        })

    public_card = None
    if data.get("is_public"):
        public_card = _publish_memo_to_feed(user_id, {
            **data,
            "book_id": book_id,
            "book_title": book_title,
            "content": content,
            "memo_id": memo_id,
        })

    if book_id:
        _auto_connect(book_id, user_id)

    return {
        "ok": True,
        "memo": {"memo_id": memo_id, "book_id": book_id, "content": content},
        "public_card": public_card,
    }


def _publish_memo_to_feed(user_id: str, memo: dict) -> dict | None:
    try:
        from app.services.social_feed_service import create_card, check_and_create_bookclub
        card = create_card(user_id, {
            "book_title": memo.get("book_title", ""),
            "passage": memo.get("content", ""),
            "thought": memo.get("content", ""),
            "emotion": memo.get("mood") if memo.get("mood") in EM_META else "inspired",
            "tags": memo.get("tags", []),
            "card_style": "cosmic",
        })
        check_and_create_bookclub(memo.get("book_title", ""))
        return card
    except Exception:
        return None


def list_memos(user_id: str, book_id: str = None, limit: int = 20) -> dict:
    if is_connected():
        try:
            sql    = """SELECT m.*, b.title AS book_title, b.author AS book_author,
                               b.cover_url AS book_cover_url, b.cover_emoji AS book_emoji
                        FROM memos m
                        LEFT JOIN books b ON m.book_id=b.book_id
                        WHERE m.user_id=%s"""
            params: list = [user_id]
            if book_id:
                sql += " AND book_id=%s"; params.append(book_id)
            sql += " ORDER BY created_at DESC LIMIT %s"; params.append(limit)
            rows = execute_all(sql, params)
            memos = [_normalize_memo(dict(r)) for r in rows]
        except Exception:
            memos = []
    else:
        memos = [m for m in _memos_mem if m["user_id"] == user_id]
        if book_id:
            memos = [m for m in memos if m["book_id"] == book_id]
        memos = [_normalize_memo(m) for m in memos[:limit]]

    return {"ok": True, "memos": memos, "total": len(memos)}


def update_memo(user_id: str, memo_id: str, data: dict) -> dict:
    content = (data.get("content") or "").strip()
    if not content:
        return {"ok": False, "error": "메모 내용이 없습니다."}

    tags = json.dumps(data.get("tags", []), ensure_ascii=False)
    page_num = data.get("page_num", data.get("page_number"))
    book_id = data.get("book_id")
    if not book_id and data.get("book_title"):
        book_id = _resolve_book_id(user_id, data.get("book_title", ""))

    if is_connected():
        try:
            exists = execute_one("SELECT memo_id FROM memos WHERE memo_id=%s AND user_id=%s", (memo_id, user_id))
            if not exists:
                return {"ok": False, "error": "메모를 찾을 수 없습니다."}
            sets = ["content=%s", "tags=%s", "page_num=%s"]
            vals = [content, tags, page_num]
            if book_id is not None:
                sets.append("book_id=%s")
                vals.append(book_id)
            vals.extend([memo_id, user_id])
            execute_write(
                "UPDATE memos SET " + ",".join(sets) + " WHERE memo_id=%s AND user_id=%s",
                vals,
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        memo = next((m for m in _memos_mem if m.get("memo_id") == memo_id and m.get("user_id") == user_id), None)
        if not memo:
            return {"ok": False, "error": "메모를 찾을 수 없습니다."}
        memo.update({"content": content, "tags": data.get("tags", []), "page_num": page_num, "page_number": page_num})
        if book_id is not None:
            memo["book_id"] = book_id
        if data.get("book_title"):
            memo["book_title"] = data.get("book_title", "")
    return {"ok": True, "memo": {"memo_id": memo_id, "content": content}}


def delete_memo(user_id: str, memo_id: str) -> dict:
    if is_connected():
        try:
            exists = execute_one("SELECT memo_id FROM memos WHERE memo_id=%s AND user_id=%s", (memo_id, user_id))
            if not exists:
                return {"ok": False, "error": "메모를 찾을 수 없습니다."}
            execute_write("DELETE FROM memos WHERE memo_id=%s AND user_id=%s", (memo_id, user_id))
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        before = len(_memos_mem)
        _memos_mem[:] = [m for m in _memos_mem if not (m.get("memo_id") == memo_id and m.get("user_id") == user_id)]
        if len(_memos_mem) == before:
            return {"ok": False, "error": "메모를 찾을 수 없습니다."}
    return {"ok": True}


def _resolve_book_id(user_id: str, book_title: str) -> str:
    title = (book_title or "").strip()
    if not title:
        return ""
    if is_connected():
        try:
            row = execute_one(
                """SELECT sb.book_id
                   FROM shelf_books sb
                   JOIN books b ON sb.book_id=b.book_id
                   WHERE sb.user_id=%s AND b.title=%s
                   ORDER BY sb.updated_at DESC LIMIT 1""",
                (user_id, title),
            )
            return (row or {}).get("book_id", "")
        except Exception:
            return ""
    try:
        from app.services.shelf_service import _books_mem, _shelf_mem
        bmap = {b.get("book_id"): b for b in _books_mem}
        for shelf in _shelf_mem:
            book = bmap.get(shelf.get("book_id"), {})
            if shelf.get("user_id") == user_id and book.get("title") == title:
                return shelf.get("book_id", "")
    except Exception:
        pass
    return ""


def _normalize_memo(memo: dict) -> dict:
    tags = memo.get("tags", [])
    if isinstance(tags, str):
        try:
            tags = json.loads(tags) if tags else []
        except Exception:
            tags = [t.strip() for t in tags.split(",") if t.strip()]
    memo["tags"] = tags if isinstance(tags, list) else []
    memo["page_number"] = memo.get("page_number", memo.get("page_num"))
    memo["page_num"] = memo.get("page_num", memo.get("page_number"))
    memo["book_title"] = memo.get("book_title") or "미분류"
    if memo.get("created_at") is not None:
        memo["created_at"] = str(memo.get("created_at"))
    if memo.get("updated_at") is not None:
        memo["updated_at"] = str(memo.get("updated_at"))
    return memo


def get_memo_stats(user_id: str) -> dict:
    if is_connected():
        try:
            r = execute_one("SELECT COUNT(*) AS cnt FROM memos WHERE user_id=%s", (user_id,))
            total = (r or {}).get("cnt", 0)
        except Exception:
            total = 0
    else:
        total = sum(1 for m in _memos_mem if m["user_id"] == user_id)
    return {"ok": True, "total": total}


def get_reading_streak(user_id: str) -> dict:
    """Return consecutive reading activity days from memos, emotions, and shelf dates."""
    activity_dates: set[date] = set()
    if is_connected():
        try:
            rows = execute_all(
                """SELECT DATE(created_at) AS day FROM memos WHERE user_id=%s
                   UNION
                   SELECT DATE(recorded_at) AS day FROM emotions WHERE user_id=%s
                   UNION
                   SELECT DATE(started_at) AS day FROM shelf_books WHERE user_id=%s AND started_at IS NOT NULL
                   UNION
                   SELECT DATE(finished_at) AS day FROM shelf_books WHERE user_id=%s AND finished_at IS NOT NULL""",
                (user_id, user_id, user_id, user_id),
            )
            for row in rows:
                day = row.get("day")
                if isinstance(day, date):
                    activity_dates.add(day)
                elif day:
                    activity_dates.add(datetime.fromisoformat(str(day)).date())
        except Exception:
            activity_dates = set()
    else:
        for memo in _memos_mem:
            if memo.get("user_id") == user_id and memo.get("created_at"):
                activity_dates.add(datetime.fromisoformat(str(memo["created_at"])[:10]).date())
        for emotion in _emotions_mem:
            if emotion.get("user_id") == user_id and emotion.get("recorded_at"):
                activity_dates.add(datetime.fromisoformat(str(emotion["recorded_at"])[:10]).date())

    if not activity_dates:
        return {"ok": True, "reading_streak": 0, "last_activity_date": ""}

    last_day = max(activity_dates)
    cursor = last_day
    streak = 0
    while cursor in activity_dates:
        streak += 1
        cursor = date.fromordinal(cursor.toordinal() - 1)
    return {"ok": True, "reading_streak": streak, "last_activity_date": last_day.isoformat()}


# ══════════════════════════════════════════════════════
#  월간 리포트
# ══════════════════════════════════════════════════════

def get_monthly_report(user_id: str, year_month: str = None) -> dict:
    if not year_month:
        year_month = date.today().strftime("%Y-%m")

    if is_connected():
        try:
            ym_start = f"{year_month}-01"
            ym_end   = f"{year_month}-31"
            books = execute_all(
                """SELECT sb.*, b.title, b.cover_emoji, b.total_pages
                   FROM shelf_books sb JOIN books b ON sb.book_id=b.book_id
                   WHERE sb.user_id=%s AND sb.status='done'
                   AND sb.finished_at BETWEEN %s AND %s""",
                (user_id, ym_start, ym_end)
            )
            ems = execute_all(
                "SELECT * FROM emotions WHERE user_id=%s AND recorded_at BETWEEN %s AND %s",
                (user_id, ym_start, ym_end)
            )
            books = [dict(r) for r in books]
            ems   = [dict(r) for r in ems]
        except Exception:
            books, ems = [], []
    else:
        from app.services.shelf_service import _books_mem, _shelf_mem
        bmap  = {b["book_id"]: b for b in _books_mem}
        books_raw = [s for s in _shelf_mem
                     if s["user_id"]==user_id and s["status"]=="done"
                     and str(s.get("finished_at",""))[:7]==year_month]
        books = [{**s, **bmap.get(s["book_id"],{})} for s in books_raw]
        ems   = [e for e in _emotions_mem
                 if e["user_id"]==user_id and str(e.get("recorded_at",""))[:7]==year_month]

    em_counter: dict = defaultdict(int)
    for e in ems:
        em_counter[e.get("emotion_type", e.get("emotion",""))] += 1
    top_type  = max(em_counter, key=em_counter.get) if em_counter else "inspired"
    top_meta  = EM_META.get(top_type, {"label":"영감","emoji":"✨","color":"#F2C94C"})

    words: list = []
    for e in ems:
        words.extend([w for w in (e.get("note","") or "").split() if len(w)>=2])
    from collections import Counter
    top_kw = [w for w,_ in Counter(words).most_common(5)]

    return {"ok": True, "report": {
        "year_month":   year_month,
        "books_read":   len(books),
        "books":        books,
        "emotions":     ems,
        "top_emotion":  {**top_meta, "type": top_type, "count": em_counter.get(top_type,0)},
        "top_keywords": top_kw,
        "total_pages":  sum(int(b.get("total_pages",0) or 0) for b in books),
        "memo_count":   len(ems),
    }}
