"""
LUMA — 라이브 독서방 + 소크라테스 서비스 (MySQL)
──────────────────────────────────────────────────────
"""
import json
import uuid
from datetime import datetime
from typing import Optional

from app.db import is_connected, execute_one, execute_all, execute_write

# ── Mock ────────────────────────────────────────────────
_rooms_mem: dict = {}
_socrates_mem: dict = {}
_dict_mem: list = []
_plans_mem: list = []

SOCRATES_STAGES = [
    "이 문장이 처음 눈에 들어온 순간 어떤 감정이 느껴졌나요?",
    "이 생각과 연결되는 당신의 경험이 있다면 무엇인가요?",
    "만약 이 생각이 틀렸다면, 어떤 반론이 가능할까요?",
    "이 통찰을 오늘 당장 삶에 적용한다면 어떻게 하겠나요?",
    "이 문장을 한 줄로 '나만의 언어'로 다시 써보면 어떻게 될까요?",
]

KEYWORDS_POOL = ["인생","죽음","행복","자유","사랑","진리","역사","과학","철학",
                 "인류","우주","시간","의미","성장","허구","기억","감정","언어"]


# ══════════════════════════════════════════════════════
#  라이브 독서방
# ══════════════════════════════════════════════════════

def create_room(data: dict) -> dict:
    room_id = f"room_{uuid.uuid4().hex[:8]}"
    now     = datetime.now()
    title   = data.get("title","독서 모임")
    book    = data.get("book_title","")
    author  = data.get("book_author","")
    host_id = data.get("host_id","user_demo")

    if is_connected():
        try:
            execute_write(
                "INSERT INTO live_rooms(room_id,title,book_title,book_author,host_id,status,created_at) "
                "VALUES(%s,%s,%s,%s,%s,'waiting',%s)",
                (room_id, title, book, author, host_id, now)
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        _rooms_mem[room_id] = {
            "room_id": room_id, "title": title, "book_title": book, "book_author": author,
            "host_id": host_id, "status": "waiting",
            "members": {}, "messages": [], "keywords": [],
            "created_at": now.isoformat(), "started_at": None, "ended_at": None, "ai_report": None,
        }

    room = {"room_id": room_id, "title": title, "book_title": book,
            "book_author": author, "host_id": host_id, "status": "waiting",
            "member_count": 0, "keywords": []}
    return {"ok": True, "room": room}


def join_room(room_id: str, data: dict) -> dict:
    peer_id      = f"peer_{uuid.uuid4().hex[:6]}"
    user_id      = data.get("user_id","user_demo")
    display_name = data.get("display_name","독서인")
    emojis       = ["⭐","🦋","🌊","🔥","🌸","💫","🦉","🌿"]
    emoji        = emojis[len(_rooms_mem.get(room_id,{}).get("members",{})) % len(emojis)]
    now          = datetime.now()

    if is_connected():
        try:
            room = execute_one("SELECT * FROM live_rooms WHERE room_id=%s", (room_id,))
            if not room:
                return {"ok": False, "error": "방을 찾을 수 없습니다."}
            execute_write(
                "INSERT INTO live_members(room_id,user_id,peer_id,display_name,emoji,joined_at) "
                "VALUES(%s,%s,%s,%s,%s,%s)",
                (room_id, user_id, peer_id, display_name, emoji, now)
            )
            cnt = execute_one(
                "SELECT COUNT(*) AS cnt FROM live_members WHERE room_id=%s AND left_at IS NULL",
                (room_id,)
            )
            member_count = (cnt or {}).get("cnt",1)
            if member_count >= 2 and dict(room).get("status") == "waiting":
                execute_write(
                    "UPDATE live_rooms SET status='live', started_at=%s WHERE room_id=%s",
                    (now, room_id)
                )
            room_data = {
                "room_id": room_id, "title": dict(room).get("title",""),
                "book_title": dict(room).get("book_title",""),
                "status": "live" if member_count >= 2 else "waiting",
                "member_count": member_count, "keywords": [],
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        if room_id not in _rooms_mem:
            return {"ok": False, "error": "방을 찾을 수 없습니다."}
        room = _rooms_mem[room_id]
        room["members"][peer_id] = {
            "peer_id": peer_id, "user_id": user_id,
            "display_name": display_name, "emoji": emoji, "joined_at": now.isoformat(),
        }
        if len(room["members"]) >= 2 and room["status"] == "waiting":
            room["status"]     = "live"
            room["started_at"] = now.isoformat()
        member_count = len(room["members"])
        room_data = {"room_id": room_id, "title": room["title"],
                     "book_title": room.get("book_title",""),
                     "status": room["status"], "member_count": member_count,
                     "keywords": room["keywords"]}

    member = {"peer_id": peer_id, "display_name": display_name, "emoji": emoji}
    return {"ok": True, "room": room_data, "member": member, "peer_id": peer_id}


def send_message(room_id: str, data: dict) -> dict:
    msg_id  = f"msg_{uuid.uuid4().hex[:8]}"
    text    = data.get("text","")
    now     = datetime.now()
    kws     = [kw for kw in KEYWORDS_POOL if kw in text]

    if is_connected():
        try:
            execute_write(
                "INSERT INTO live_messages(msg_id,room_id,peer_id,display_name,emoji,content,msg_type,created_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,'chat',%s)",
                (msg_id, room_id, data.get("peer_id",""), data.get("display_name","독서인"),
                 data.get("emoji","⭐"), text, now)
            )
            if kws:
                existing_kws_row = execute_one("SELECT keywords FROM live_rooms WHERE room_id=%s", (room_id,))
                existing_kws     = json.loads((existing_kws_row or {}).get("keywords") or "[]")
                merged = list(set(existing_kws + kws))[:20]
                execute_write("UPDATE live_rooms SET keywords=%s WHERE room_id=%s",
                              (json.dumps(merged, ensure_ascii=False), room_id))
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        if room_id in _rooms_mem:
            room = _rooms_mem[room_id]
            room["messages"].append({
                "msg_id": msg_id, "text": text,
                "peer_id": data.get("peer_id",""),
                "display_name": data.get("display_name","독서인"),
                "emoji": data.get("emoji","⭐"),
                "ts": now.isoformat(),
            })
            for kw in kws:
                if kw not in room["keywords"]:
                    room["keywords"].append(kw)

    msg = {"msg_id": msg_id, "text": text, "peer_id": data.get("peer_id",""),
           "name": data.get("display_name","독서인"), "emoji": data.get("emoji","⭐"),
           "ts": now.isoformat()}
    return {"ok": True, "message": msg, "new_keywords": kws}


def get_room_updates(room_id: str, since_msg_id=0) -> dict:
    """폴링용 새 메시지/키워드/멤버 수 조회."""
    if is_connected():
        try:
            since_id = 0
            if str(since_msg_id).isdigit():
                since_id = int(since_msg_id)
            elif since_msg_id:
                row = execute_one(
                    "SELECT id FROM live_messages WHERE room_id=%s AND msg_id=%s",
                    (room_id, str(since_msg_id)),
                )
                since_id = int((row or {}).get("id") or 0)

            rows = execute_all(
                """SELECT id, msg_id, peer_id, display_name, emoji, content, msg_type, created_at
                   FROM live_messages
                   WHERE room_id=%s AND id>%s
                   ORDER BY id ASC
                   LIMIT 50""",
                (room_id, since_id),
            )
            room = execute_one("SELECT keywords FROM live_rooms WHERE room_id=%s", (room_id,))
            cnt = execute_one(
                "SELECT COUNT(*) AS cnt FROM live_members WHERE room_id=%s AND left_at IS NULL",
                (room_id,),
            )
            messages = [
                {
                    "id": r.get("id"),
                    "msg_id": r.get("msg_id"),
                    "peer_id": r.get("peer_id", ""),
                    "display_name": r.get("display_name", ""),
                    "name": r.get("display_name", ""),
                    "emoji": r.get("emoji", "⭐"),
                    "text": r.get("content", ""),
                    "content": r.get("content", ""),
                    "msg_type": r.get("msg_type", "chat"),
                    "ts": str(r.get("created_at") or ""),
                }
                for r in rows
            ]
            return {
                "ok": True,
                "messages": messages,
                "keywords": json.loads((room or {}).get("keywords") or "[]"),
                "member_count": (cnt or {}).get("cnt", 0),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    room = _rooms_mem.get(room_id)
    if not room:
        return {"ok": False, "error": "방을 찾을 수 없습니다."}
    messages = room.get("messages", [])
    if str(since_msg_id).isdigit():
        new_messages = messages[int(since_msg_id):]
    elif since_msg_id:
        idx = next((i for i, m in enumerate(messages) if m.get("msg_id") == since_msg_id), -1)
        new_messages = messages[idx + 1:] if idx >= 0 else messages
    else:
        new_messages = messages
    return {
        "ok": True,
        "messages": [
            {"id": i + 1, "name": m.get("display_name", ""), "content": m.get("text", ""), **m}
            for i, m in enumerate(new_messages[:50])
        ],
        "keywords": room.get("keywords", []),
        "member_count": len(room.get("members", {})),
    }


def get_room(room_id: str) -> Optional[dict]:
    if is_connected():
        try:
            row = execute_one("SELECT * FROM live_rooms WHERE room_id=%s", (room_id,))
            if not row:
                return None
            row  = dict(row)
            cnt  = execute_one(
                "SELECT COUNT(*) AS cnt FROM live_members WHERE room_id=%s AND left_at IS NULL",
                (room_id,)
            )
            kws  = json.loads(row.get("keywords") or "[]")
            return {"room_id": room_id, "title": row.get("title",""),
                    "book_title": row.get("book_title",""), "status": row.get("status","waiting"),
                    "member_count": (cnt or {}).get("cnt",0), "keywords": kws}
        except Exception:
            return None
    room = _rooms_mem.get(room_id)
    if not room:
        return None
    return {"room_id": room_id, "title": room["title"], "book_title": room.get("book_title",""),
            "status": room["status"], "member_count": len(room["members"]),
            "keywords": room["keywords"]}


def list_rooms(status: str = "live") -> list:
    if is_connected():
        try:
            rows = execute_all(
                """SELECT r.*, COUNT(m.id) AS member_count
                   FROM live_rooms r
                   LEFT JOIN live_members m ON r.room_id=m.room_id AND m.left_at IS NULL
                   WHERE r.status=%s GROUP BY r.room_id ORDER BY r.created_at DESC""",
                (status,)
            )
            result = []
            for row in rows:
                row = dict(row)
                kws = json.loads(row.get("keywords") or "[]")
                result.append({
                    "room_id": row["room_id"], "title": row.get("title",""),
                    "book_title": row.get("book_title",""), "status": row.get("status",""),
                    "member_count": row.get("member_count",0), "keywords": kws,
                })
            return result
        except Exception:
            return []
    return [
        {"room_id": rid, "title": r["title"], "book_title": r.get("book_title",""),
         "status": r["status"], "member_count": len(r["members"]), "keywords": r["keywords"]}
        for rid, r in _rooms_mem.items() if r["status"] == status
    ]


def end_room(room_id: str) -> dict:
    now = datetime.now()
    keywords, messages, book_title = [], [], ""

    if is_connected():
        try:
            row = execute_one("SELECT * FROM live_rooms WHERE room_id=%s", (room_id,))
            if row:
                row       = dict(row)
                keywords  = json.loads(row.get("keywords") or "[]")
                book_title = row.get("book_title","")
            msgs_rows  = execute_all(
                "SELECT content FROM live_messages WHERE room_id=%s ORDER BY created_at", (room_id,))
            messages   = [dict(r).get("content","") for r in msgs_rows]
            execute_write(
                "UPDATE live_rooms SET status='ended', ended_at=%s WHERE room_id=%s",
                (now, room_id)
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        room = _rooms_mem.get(room_id, {})
        keywords   = room.get("keywords",[])
        messages   = [m.get("text","") for m in room.get("messages",[])]
        book_title = room.get("book_title","")
        if room:
            room["status"]   = "ended"
            room["ended_at"] = now.isoformat()

    report = _gen_report(book_title, keywords, messages)
    if is_connected():
        try:
            execute_write("UPDATE live_rooms SET ai_report=%s WHERE room_id=%s",
                          (json.dumps(report, ensure_ascii=False), room_id))
        except Exception:
            pass

    return {"ok": True, "report": report}


def leave_room(room_id: str, peer_id: str) -> dict:
    """방 나가기. 남은 멤버가 없으면 방을 종료한다."""
    now = datetime.now()
    if is_connected():
        try:
            execute_write(
                "UPDATE live_members SET left_at=%s WHERE room_id=%s AND peer_id=%s",
                (now, room_id, peer_id),
            )
            cnt = execute_one(
                "SELECT COUNT(*) AS cnt FROM live_members WHERE room_id=%s AND left_at IS NULL",
                (room_id,),
            )
            member_count = (cnt or {}).get("cnt", 0)
            if member_count == 0:
                execute_write(
                    "UPDATE live_rooms SET status='ended', ended_at=%s WHERE room_id=%s",
                    (now, room_id),
                )
            return {"ok": True, "member_count": member_count}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    room = _rooms_mem.get(room_id)
    if not room:
        return {"ok": False, "error": "방을 찾을 수 없습니다."}
    room.get("members", {}).pop(peer_id, None)
    member_count = len(room.get("members", {}))
    if member_count == 0:
        room["status"] = "ended"
        room["ended_at"] = now.isoformat()
    return {"ok": True, "member_count": member_count}


def _gen_report(book_title, keywords, messages):
    from app.services.gemini_service import _call_gemini, _parse_json_safe
    prompt = f"""독서 모임 대화를 분석해서 1장 요약 보고서를 만들어주세요.
책: {book_title}
키워드: {keywords}
대화: {' | '.join(messages[:15])}
JSON 형식으로만:
{{"title":"모임 제목","one_line":"한 줄 요약","mood":"분위기","mood_emoji":"이모지",
  "key_insights":["인사이트1","인사이트2"],"highlight_quotes":["발언1"],
  "main_keywords":["키워드1","키워드2","키워드3"],
  "next_questions":["질문1","질문2"],"summary":"전체 요약"}}"""
    raw    = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None
    if parsed and "summary" in parsed:
        return {**parsed, "book_title": book_title, "created_at": datetime.now().isoformat()}
    return {
        "title": f"《{book_title}》 독서 모임", "one_line": "책을 통해 서로의 생각을 나눈 소중한 시간",
        "mood": "사색적", "mood_emoji": "🌿",
        "key_insights": ["책에서 새로운 관점을 공유했습니다.", "서로 다른 해석이 깊은 이해로 이어졌습니다."],
        "highlight_quotes": ["가장 인상 깊은 구절을 함께 읽었습니다."],
        "main_keywords": keywords[:5] or ["독서","공유","성장"],
        "next_questions": ["다음 장에서 작가는 무엇을 말하고 싶었을까요?","이 책이 삶을 어떻게 바꿀 수 있을까요?"],
        "summary": f"《{book_title}》에 대한 깊은 토론이 이루어졌습니다.",
        "book_title": book_title, "created_at": datetime.now().isoformat(), "source": "mock",
    }


# ══════════════════════════════════════════════════════
#  소크라테스 대화
# ══════════════════════════════════════════════════════

def start_session(data: dict) -> dict:
    from app.services.socrates_discussion_service import normalize_discussion_mode

    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    user_id    = data.get("user_id","user_demo")
    passage    = data.get("passage","")
    book_title = data.get("book_title","")
    discussion_mode = normalize_discussion_mode(data.get("discussion_mode"))
    now        = datetime.now()

    first_q = _gen_question(passage, book_title, 0, [], discussion_mode)
    exchanges = [{"q": first_q, "a": None, "stage": 0, "discussion_mode": discussion_mode}]

    if is_connected():
        try:
            execute_write(
                "INSERT INTO socrates_sessions(session_id,user_id,book_title,passage,stage,total_stages,exchanges,created_at) "
                "VALUES(%s,%s,%s,%s,0,5,%s,%s)",
                (session_id, user_id, book_title, passage,
                 json.dumps(exchanges, ensure_ascii=False), now)
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        _socrates_mem[session_id] = {
            "session_id": session_id, "user_id": user_id,
            "book_title": book_title, "passage": passage,
            "stage": 0, "total_stages": 5,
            "discussion_mode": discussion_mode,
            "exchanges": exchanges, "completed": False, "final_insight": None,
        }

    return {"ok": True, "session_id": session_id, "question": first_q,
            "stage": 0, "total_stages": 5, "discussion_mode": discussion_mode}


def answer_session(session_id: str, answer: str) -> dict:
    if is_connected():
        try:
            row = execute_one("SELECT * FROM socrates_sessions WHERE session_id=%s", (session_id,))
            if not row:
                return {"ok": False, "error": "세션 없음"}
            row       = dict(row)
            exchanges = json.loads(row.get("exchanges") or "[]")
            stage     = int(row.get("stage",0))
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        sess = _socrates_mem.get(session_id)
        if not sess:
            return {"ok": False, "error": "세션 없음"}
        exchanges = sess["exchanges"]
        stage     = sess["stage"]
        row       = sess

    if exchanges and exchanges[-1].get("a") is None:
        exchanges[-1]["a"] = answer

    discussion_mode = (
        row.get("discussion_mode")
        or (exchanges[0].get("discussion_mode") if exchanges else None)
        or "appreciation"
    )
    next_stage = stage + 1
    if next_stage >= 5:
        insight = _gen_insight(row.get("passage",""), row.get("book_title",""), exchanges)
        if is_connected():
            try:
                execute_write(
                    "UPDATE socrates_sessions SET stage=5, completed=1, exchanges=%s, final_insight=%s WHERE session_id=%s",
                    (json.dumps(exchanges, ensure_ascii=False), json.dumps(insight, ensure_ascii=False), session_id)
                )
            except Exception:
                pass
        else:
            sess = _socrates_mem.get(session_id, {})
            sess.update({"stage": 5, "completed": True, "final_insight": insight, "exchanges": exchanges})
        return {"ok": True, "completed": True, "insight": insight}

    next_q = _gen_question(row.get("passage",""), row.get("book_title",""), next_stage, exchanges, discussion_mode)
    exchanges.append({"q": next_q, "a": None, "stage": next_stage, "discussion_mode": discussion_mode})

    if is_connected():
        try:
            execute_write(
                "UPDATE socrates_sessions SET stage=%s, exchanges=%s WHERE session_id=%s",
                (next_stage, json.dumps(exchanges, ensure_ascii=False), session_id)
            )
        except Exception:
            pass
    else:
        if session_id in _socrates_mem:
            _socrates_mem[session_id].update({"stage": next_stage, "exchanges": exchanges})

    return {"ok": True, "completed": False, "question": next_q,
            "stage": next_stage, "total_stages": 5, "progress": f"{next_stage}/5"}


def list_sessions(user_id: str, limit: int = 10) -> dict:
    """사용자의 소크라테스 세션 목록."""
    limit = max(1, min(int(limit or 10), 50))
    if is_connected():
        try:
            rows = execute_all(
                """SELECT session_id, book_title, passage, stage, total_stages,
                          completed, final_insight, created_at
                   FROM socrates_sessions
                   WHERE user_id=%s
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (user_id, limit),
            )
            return {"ok": True, "sessions": [_session_summary(dict(r)) for r in rows]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    sessions = [
        _session_summary(s)
        for s in _socrates_mem.values()
        if s.get("user_id") == user_id
    ]
    return {"ok": True, "sessions": sessions[:limit]}


def resume_session(session_id: str) -> dict:
    """미완료 세션의 현재 질문 또는 완료 세션의 최종 인사이트 반환."""
    if is_connected():
        try:
            row = execute_one("SELECT * FROM socrates_sessions WHERE session_id=%s", (session_id,))
            if not row:
                return {"ok": False, "error": "세션을 찾을 수 없습니다."}
            sess = dict(row)
            exchanges = json.loads(sess.get("exchanges") or "[]")
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        sess = _socrates_mem.get(session_id)
        if not sess:
            return {"ok": False, "error": "세션을 찾을 수 없습니다."}
        exchanges = sess.get("exchanges", [])

    if int(sess.get("completed") or 0):
        insight = sess.get("final_insight")
        if isinstance(insight, str):
            try:
                insight = json.loads(insight)
            except Exception:
                insight = {"text": insight}
        return {"ok": True, "completed": True, "session": _session_summary(sess), "insight": insight}

    current = next((e for e in reversed(exchanges) if e.get("a") is None), None)
    question = (current or exchanges[-1] if exchanges else {}).get("q", SOCRATES_STAGES[0])
    return {
        "ok": True,
        "completed": False,
        "session": _session_summary(sess),
        "question": question,
        "stage": int(sess.get("stage") or 0),
        "total_stages": int(sess.get("total_stages") or 5),
        "exchanges": exchanges,
    }


def _session_summary(sess: dict) -> dict:
    passage = sess.get("passage", "") or ""
    preview = passage[:40] + "..." if passage else ""
    return {
        "session_id": sess.get("session_id"),
        "book_title": sess.get("book_title", ""),
        "passage_preview": preview,
        "stage": int(sess.get("stage") or 0),
        "total_stages": int(sess.get("total_stages") or 5),
        "completed": bool(sess.get("completed")),
        "discussion_mode": sess.get("discussion_mode") or _mode_from_exchanges(sess),
        "created_at": str(sess.get("created_at") or ""),
    }


def force_connect(data: dict) -> dict:
    from app.services.gemini_service import _call_gemini, _parse_json_safe
    text_a  = data.get("text_a","")
    book_a  = data.get("book_a","")
    text_b  = data.get("text_b","")
    book_b  = data.get("book_b","")
    prompt  = f"""서로 다른 두 책의 생각을 연결해서 새로운 인사이트를 만들어주세요.
책A 《{book_a}》: {text_a}
책B 《{book_b}》: {text_b}
JSON 형식으로만:
{{"connection_type":"연결 유형","bridge":"연결 키워드","insight":"새로운 통찰 2-3문장",
  "metaphor":"비유 한 문장","strength":0.7,"quote":"핵심 한 줄"}}"""
    raw    = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None
    if parsed and "insight" in parsed:
        return {"ok": True, "insight": {**parsed, "book_a": book_a, "book_b": book_b}}
    return {"ok": True, "insight": {
        "connection_type":"보완","bridge":"인간의 이해 방식",
        "insight":f"《{book_a}》과 《{book_b}》은 서로 다른 방향에서 같은 진실을 가리킵니다.",
        "metaphor":"두 개의 산에서 각자 다른 길로 올라갔지만 정상에서 같은 하늘을 봅니다.",
        "strength":0.7,"quote":"다른 언어로 쓰인 같은 이야기.","book_a":book_a,"book_b":book_b,"source":"mock"
    }}


def add_dict_entry(user_id: str, data: dict) -> dict:
    from app.services.gemini_service import _call_gemini, _parse_json_safe
    concept   = data.get("concept","")
    sources   = data.get("sources",[])
    user_thought = data.get("user_thought","")
    entry_id  = f"dict_{uuid.uuid4().hex[:8]}"
    now       = datetime.now()

    prompt = f"""'{concept}'에 대한 나만의 정의를 만들어주세요.
수집한 생각: {[s.get('text','') for s in sources]}
사용자 생각: {user_thought}
JSON 형식으로만:
{{"concept":"{concept}","my_definition":"나만의 정의 2-3문장",
  "core_words":["단어1","단어2","단어3"],"opposite":"반대 개념",
  "personal_note":"삶에서의 의미","quote_to_live_by":"삶의 문장"}}"""
    raw    = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None
    if not parsed:
        parsed = {"concept": concept, "my_definition": f"{concept}란 여러 책을 통해 스스로 발견하고 정의해가는 것입니다.",
                  "core_words": [concept,"탐구","발견"], "opposite": f"고정된 {concept}",
                  "personal_note": "독서 여정에서 탄생한 나만의 정의입니다.",
                  "quote_to_live_by": f"{concept}은 찾는 것이 아니라 만들어가는 것이다."}

    core_words_str = json.dumps(parsed.get("core_words",[]), ensure_ascii=False)
    sources_str    = json.dumps(sources, ensure_ascii=False)

    if is_connected():
        try:
            execute_write(
                "INSERT INTO my_dictionary(entry_id,user_id,concept,my_definition,core_words,"
                "opposite,personal_note,quote_to_live,sources,created_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (entry_id, user_id, concept, parsed.get("my_definition",""),
                 core_words_str, parsed.get("opposite",""), parsed.get("personal_note",""),
                 parsed.get("quote_to_live_by",""), sources_str, now)
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        _dict_mem.append({"entry_id": entry_id, "user_id": user_id, "sources": sources,
                          "created_at": now.isoformat(), **parsed})

    return {"ok": True, "entry": {"entry_id": entry_id, "user_id": user_id, **parsed}}


def get_dict_entries(user_id: str) -> dict:
    if is_connected():
        try:
            rows = execute_all(
                "SELECT * FROM my_dictionary WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
            entries = []
            for r in rows:
                r = dict(r)
                r["core_words"] = json.loads(r.get("core_words") or "[]")
                r["sources"]    = json.loads(r.get("sources") or "[]")
                entries.append(r)
            return {"ok": True, "entries": entries}
        except Exception:
            return {"ok": True, "entries": []}
    return {"ok": True, "entries": [e for e in _dict_mem if e["user_id"] == user_id]}


def create_action_plan(user_id: str, data: dict) -> dict:
    from app.services.gemini_service import _call_gemini, _parse_json_safe
    insight    = data.get("insight","")
    book_title = data.get("book_title","")
    plan_id    = f"plan_{uuid.uuid4().hex[:8]}"
    now        = datetime.now()

    prompt = f"""독서 인사이트를 실천 계획으로 만들어주세요.
책: 《{book_title}》
인사이트: {insight}
JSON 형식으로만:
{{"summary":"실천 핵심 한 줄","today":"오늘 할 것 (구체적)","this_week":"이번 주 할 것","this_month":"이번 달 할 것","mindset":"필요한 마음가짐"}}"""
    raw    = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None
    if not parsed:
        parsed = {"summary":"작은 실천이 큰 변화를 만든다",
                  "today":"이 인사이트를 일기에 적고 오늘 하루 이 관점으로 세상 바라보기",
                  "this_week":"관련 주제로 주변 사람과 대화 나눠보기",
                  "this_month":"이 인사이트를 실제로 적용한 사례 3가지 만들기",
                  "mindset":"결과보다 과정을, 완벽보다 꾸준함을"}

    if is_connected():
        try:
            execute_write(
                "INSERT INTO action_plans(plan_id,user_id,book_title,insight,summary,"
                "today_action,week_action,month_action,mindset,created_at) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (plan_id, user_id, book_title, insight, parsed.get("summary",""),
                 parsed.get("today",""), parsed.get("this_week",""), parsed.get("this_month",""),
                 parsed.get("mindset",""), now)
            )
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        _plans_mem.append({"plan_id": plan_id, "user_id": user_id,
                           "book_title": book_title, "insight": insight,
                           "checked_in": False, "created_at": now.isoformat(), **parsed})

    plan = {"plan_id": plan_id, "user_id": user_id, "book_title": book_title,
            "insight": insight, "checked_in": False, **parsed}
    return {"ok": True, "plan": plan}


def get_action_plans(user_id: str) -> dict:
    if is_connected():
        try:
            rows = execute_all(
                "SELECT * FROM action_plans WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
            plans = []
            for r in rows:
                plan = dict(r)
                plan["today"] = plan.get("today_action", "")
                plan["this_week"] = plan.get("week_action", "")
                plan["this_month"] = plan.get("month_action", "")
                plan["checked_in"] = bool(plan.get("checked_in"))
                plans.append(plan)
            return {"ok": True, "plans": plans}
        except Exception:
            return {"ok": True, "plans": []}
    return {"ok": True, "plans": [p for p in _plans_mem if p["user_id"] == user_id]}


def checkin_plan(plan_id: str, note: str = "") -> dict:
    now = datetime.now()
    if is_connected():
        try:
            execute_write(
                "UPDATE action_plans SET checked_in=1, checkin_note=%s, checkin_at=%s WHERE plan_id=%s",
                (note, now, plan_id)
            )
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    plan = next((p for p in _plans_mem if p["plan_id"] == plan_id), None)
    if plan:
        plan.update({"checked_in": True, "checkin_note": note, "checkin_at": now.isoformat()})
    return {"ok": True}


# ── 내부 헬퍼 ────────────────────────────────────────────
def _mode_from_exchanges(sess: dict) -> str:
    try:
        exchanges = sess.get("exchanges") or []
        if isinstance(exchanges, str):
            exchanges = json.loads(exchanges or "[]")
        return (exchanges[0].get("discussion_mode") if exchanges else None) or "appreciation"
    except Exception:
        return "appreciation"


def _gen_question(passage: str, book: str, stage: int, prev: list, discussion_mode: str = "appreciation") -> str:
    from app.services.gemini_service import _call_gemini
    from app.services.socrates_discussion_service import get_mode_label, normalize_discussion_mode

    discussion_mode = normalize_discussion_mode(discussion_mode)
    ctx  = f"\n이전 답변: {prev[-1]['a']}" if prev and prev[-1].get('a') else ""
    prompt = (f"소크라테스 코치입니다. 책 《{book}》의 구절:\n\"{passage}\"\n"
              f"대화 모드: {get_mode_label(discussion_mode)}\n"
              f"현재 {stage+1}/5단계 심화 질문을 해주세요.{ctx}\n질문만 출력하세요.")
    q = _call_gemini(prompt)
    return (q or "").strip() or SOCRATES_STAGES[stage]


def _gen_insight(passage: str, book: str, exchanges: list) -> dict:
    from app.services.gemini_service import _call_gemini, _parse_json_safe
    history = "\n".join(f"Q: {e['q']}\nA: {e.get('a','')}" for e in exchanges if e.get('a'))
    prompt  = (f"소크라테스 5단계 완료. 최종 인사이트를 생성해주세요.\n"
               f"책: 《{book}》\n원문: {passage}\n대화: {history}\n"
               f'JSON만: {{"refined_thought":"정제된 생각","personal_meaning":"개인적 의미",'
               f'"my_sentence":"나만의 문장","tags":["태그1","태그2"],"next_action":"실천"}}')
    raw    = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None
    if parsed and "refined_thought" in parsed:
        return {**parsed, "source": "gemini"}
    return {"refined_thought": "이 구절과 나의 경험이 만나 새로운 이해를 만들었습니다.",
            "personal_meaning": "이 생각은 당신의 고유한 시각을 반영합니다.",
            "my_sentence": f"{passage[:40]}... — 그것은 결국 나에 관한 이야기였다.",
            "tags": ["독서","성찰","성장"], "next_action": "이 생각을 노트에 적고 일주일 후 다시 읽어보세요.",
            "source": "mock"}
