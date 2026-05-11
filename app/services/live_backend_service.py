import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional

from app.db import execute_all, execute_one, execute_write, get_db, is_connected


_rooms_mem: dict[str, dict] = {}

KEYWORDS = [
    "인생", "죽음", "행복", "자유", "사랑", "진리", "역사", "과학", "철학",
    "인류", "우주", "시간", "성장", "기억", "감정", "언어", "문화", "사회",
]


def _now() -> datetime:
    return datetime.now()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _check_password(password: str, password_hash: str) -> bool:
    return bool(password_hash) and _hash_password(password) == password_hash


def _json_loads(value, default):
    try:
        return json.loads(value) if value else default
    except Exception:
        return default


def _ensure_live_schema() -> None:
    if not is_connected():
        return
    wanted = {
        "is_private": "TINYINT(1) DEFAULT 0",
        "password_hash": "VARCHAR(255)",
        "discussion_topic": "VARCHAR(500)",
        "transcript": "LONGTEXT",
    }
    try:
        rows = execute_all("SHOW COLUMNS FROM live_rooms")
        existing = {row.get("Field") for row in rows}
        with get_db() as cur:
            for column, ddl in wanted.items():
                if column not in existing:
                    cur.execute(f"ALTER TABLE live_rooms ADD COLUMN {column} {ddl}")
    except Exception:
        pass


def _user_display(user_id: str, fallback_name: str = "독서인", fallback_emoji: str = "🌙") -> dict:
    if is_connected():
        try:
            row = execute_one(
                "SELECT display_name, emoji FROM users WHERE user_id=%s",
                (user_id,),
            )
            if row:
                return {
                    "display_name": row.get("display_name") or fallback_name,
                    "emoji": row.get("emoji") or fallback_emoji,
                }
        except Exception:
            pass
    return {"display_name": fallback_name, "emoji": fallback_emoji}


def _normalize_room(row: dict, member_count: int = 0, members: Optional[list] = None) -> dict:
    report = _json_loads(row.get("ai_report"), None)
    started_at = row.get("started_at")
    ended_at = row.get("ended_at")
    created_at = row.get("created_at")
    if not isinstance(started_at, str) and started_at:
        started_at = started_at.isoformat()
    if not isinstance(ended_at, str) and ended_at:
        ended_at = ended_at.isoformat()
    if not isinstance(created_at, str) and created_at:
        created_at = created_at.isoformat()
    return {
        "room_id": row.get("room_id"),
        "title": row.get("title") or "독서 모임",
        "book_title": row.get("book_title") or "",
        "book_author": row.get("book_author") or "",
        "host_id": row.get("host_id") or "",
        "max_members": int(row.get("max_members") or 8),
        "status": row.get("status") or "waiting",
        "is_private": bool(row.get("is_private")),
        "discussion_topic": row.get("discussion_topic") or "",
        "keywords": _json_loads(row.get("keywords"), []),
        "member_count": int(member_count or 0),
        "members": members or [],
        "participants": members or [],
        "participant_count": int(member_count or 0),
        "started_at": started_at,
        "ended_at": ended_at,
        "created_at": created_at,
        "report": report,
        "ai_report": report,
    }


def _get_room_row(room_id: str) -> Optional[dict]:
    if is_connected():
        _ensure_live_schema()
        row = execute_one("SELECT * FROM live_rooms WHERE room_id=%s", (room_id,))
        return dict(row) if row else None
    return _rooms_mem.get(room_id)


def _active_members(room_id: str) -> list[dict]:
    if is_connected():
        rows = execute_all(
            """SELECT peer_id, user_id, display_name, emoji, is_host, joined_at
               FROM live_members
               WHERE room_id=%s AND left_at IS NULL
               ORDER BY joined_at ASC""",
            (room_id,),
        )
        return [
            {
                "peer_id": row.get("peer_id"),
                "user_id": row.get("user_id"),
                "display_name": row.get("display_name") or "독서인",
                "name": row.get("display_name") or "독서인",
                "emoji": row.get("emoji") or "🌙",
                "is_host": bool(row.get("is_host")),
                "joined_at": str(row.get("joined_at") or ""),
            }
            for row in rows
        ]
    room = _rooms_mem.get(room_id, {})
    return list(room.get("members", {}).values())


def _room_view(room_id: str) -> Optional[dict]:
    row = _get_room_row(room_id)
    if not row:
        return None
    members = _active_members(room_id)
    return _normalize_room(row, len(members), members)


def create_room(data: dict, user_id: str) -> dict:
    title = (data.get("title") or "").strip()
    if not title:
        return {"ok": False, "error": "방 이름을 입력해주세요."}

    room_id = f"room_{uuid.uuid4().hex[:8]}"
    now = _now()
    max_members = max(2, min(int(data.get("max_members") or data.get("max_participants") or 8), 20))
    password = (data.get("password") or "").strip()
    is_private = bool(password or data.get("is_private"))
    password_hash = _hash_password(password) if password else ""
    profile = _user_display(user_id, data.get("display_name") or data.get("host_name") or "방장", data.get("emoji") or "🌙")

    if is_connected():
        _ensure_live_schema()
        try:
            execute_write(
                """INSERT INTO live_rooms
                   (room_id,title,book_title,book_author,host_id,max_members,status,keywords,
                    is_private,password_hash,discussion_topic,created_at)
                   VALUES(%s,%s,%s,%s,%s,%s,'waiting','[]',%s,%s,%s,%s)""",
                (
                    room_id,
                    title,
                    data.get("book_title", ""),
                    data.get("book_author", ""),
                    user_id,
                    max_members,
                    1 if is_private else 0,
                    password_hash,
                    data.get("discussion_topic", ""),
                    now,
                ),
            )
            _add_member(room_id, user_id, profile["display_name"], profile["emoji"], True)
            _add_system_message(room_id, "라이브 독서방이 열렸습니다.")
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        _rooms_mem[room_id] = {
            "room_id": room_id,
            "title": title,
            "book_title": data.get("book_title", ""),
            "book_author": data.get("book_author", ""),
            "host_id": user_id,
            "max_members": max_members,
            "status": "waiting",
            "keywords": [],
            "is_private": is_private,
            "password_hash": password_hash,
            "discussion_topic": data.get("discussion_topic", ""),
            "members": {},
            "messages": [],
            "transcript": [],
            "ai_report": None,
            "created_at": now.isoformat(),
            "started_at": None,
            "ended_at": None,
        }
        _add_member(room_id, user_id, profile["display_name"], profile["emoji"], True)
        _add_system_message(room_id, "라이브 독서방이 열렸습니다.")

    return {"ok": True, "room": _room_view(room_id)}


def list_rooms(status: str = "active") -> list[dict]:
    if status in {"active", "open", "live", ""}:
        statuses = ("waiting", "live")
    else:
        statuses = (status,)

    if is_connected():
        _ensure_live_schema()
        placeholders = ",".join(["%s"] * len(statuses))
        rows = execute_all(
            f"""SELECT r.*, COUNT(m.id) AS member_count
                FROM live_rooms r
                LEFT JOIN live_members m ON r.room_id=m.room_id AND m.left_at IS NULL
                WHERE r.status IN ({placeholders})
                GROUP BY r.id
                ORDER BY r.created_at DESC""",
            statuses,
        )
        return [_normalize_room(dict(row), row.get("member_count", 0)) for row in rows]

    rooms = []
    for room in _rooms_mem.values():
        if room.get("status") in statuses:
            rooms.append(_normalize_room(room, len(room.get("members", {})), list(room.get("members", {}).values())))
    return sorted(rooms, key=lambda r: r.get("created_at") or "", reverse=True)


def get_room(room_id: str) -> Optional[dict]:
    return _room_view(room_id)


def _find_active_peer(room_id: str, user_id: str) -> Optional[str]:
    if is_connected():
        row = execute_one(
            """SELECT peer_id FROM live_members
               WHERE room_id=%s AND user_id=%s AND left_at IS NULL
               ORDER BY joined_at DESC LIMIT 1""",
            (room_id, user_id),
        )
        return row.get("peer_id") if row else None
    room = _rooms_mem.get(room_id, {})
    for peer_id, member in room.get("members", {}).items():
        if member.get("user_id") == user_id:
            return peer_id
    return None


def _add_member(room_id: str, user_id: str, display_name: str, emoji: str, is_host: bool = False) -> str:
    existing = _find_active_peer(room_id, user_id)
    if existing:
        return existing
    peer_id = f"peer_{uuid.uuid4().hex[:8]}"
    now = _now()
    if is_connected():
        execute_write(
            """INSERT INTO live_members(room_id,user_id,peer_id,display_name,emoji,is_host,joined_at)
               VALUES(%s,%s,%s,%s,%s,%s,%s)""",
            (room_id, user_id, peer_id, display_name, emoji, 1 if is_host else 0, now),
        )
    else:
        room = _rooms_mem[room_id]
        room["members"][peer_id] = {
            "peer_id": peer_id,
            "user_id": user_id,
            "display_name": display_name,
            "name": display_name,
            "emoji": emoji,
            "is_host": is_host,
            "joined_at": now.isoformat(),
        }
    return peer_id


def join_room(room_id: str, data: dict, user_id: str) -> dict:
    row = _get_room_row(room_id)
    if not row:
        return {"ok": False, "error": "방을 찾을 수 없습니다."}
    if row.get("status") == "ended":
        return {"ok": False, "error": "이미 종료된 모임입니다."}

    members = _active_members(room_id)
    existing_peer = _find_active_peer(room_id, user_id)
    max_members = int(row.get("max_members") or 8)
    if not existing_peer and len(members) >= max_members:
        return {"ok": False, "error": f"정원({max_members}명)이 가득 찼습니다."}

    if row.get("is_private") and not existing_peer:
        password = (data.get("password") or "").strip()
        if not _check_password(password, row.get("password_hash") or ""):
            return {"ok": False, "error": "방 비밀번호가 맞지 않습니다."}

    profile = _user_display(user_id, data.get("display_name") or "독서인", data.get("emoji") or "🌙")
    peer_id = _add_member(room_id, user_id, profile["display_name"], data.get("emoji") or profile["emoji"], row.get("host_id") == user_id)
    room = _room_view(room_id)
    if room and room["status"] == "waiting" and room["member_count"] >= 1:
        start_room(room_id, user_id, auto=True)
        room = _room_view(room_id)
    _add_system_message(room_id, f"{profile['display_name']}님이 입장했습니다.")
    return {"ok": True, "room": room, "member": {"peer_id": peer_id, **profile}, "peer_id": peer_id}


def _require_member(room_id: str, user_id: str) -> tuple[bool, str]:
    peer_id = _find_active_peer(room_id, user_id)
    if not peer_id:
        return False, ""
    return True, peer_id


def start_room(room_id: str, user_id: str, auto: bool = False) -> dict:
    row = _get_room_row(room_id)
    if not row:
        return {"ok": False, "error": "방을 찾을 수 없습니다."}
    if not auto and row.get("host_id") != user_id:
        return {"ok": False, "error": "방장만 시작할 수 있습니다."}
    if row.get("status") == "ended":
        return {"ok": False, "error": "이미 종료된 모임입니다."}
    now = _now()
    if is_connected():
        execute_write("UPDATE live_rooms SET status='live', started_at=COALESCE(started_at,%s) WHERE room_id=%s", (now, room_id))
    else:
        room = _rooms_mem[room_id]
        room["status"] = "live"
        room["started_at"] = room.get("started_at") or now.isoformat()
    if not auto:
        _add_system_message(room_id, "독서 모임이 시작되었습니다.")
    return {"ok": True, "room": _room_view(room_id)}


def send_message(room_id: str, data: dict, user_id: str) -> dict:
    ok, peer_id = _require_member(room_id, user_id)
    if not ok:
        return {"ok": False, "error": "방에 입장한 회원만 메시지를 보낼 수 있습니다."}
    content = (data.get("content") or data.get("text") or "").strip()
    if not content:
        return {"ok": False, "error": "메시지 내용을 입력해주세요."}

    profile = _user_display(user_id, data.get("display_name") or "독서인", data.get("emoji") or "🌙")
    msg = _add_message(room_id, peer_id, profile["display_name"], data.get("emoji") or profile["emoji"], content, data.get("type") or data.get("msg_type") or "chat")
    kws = [kw for kw in KEYWORDS if kw in content]
    if kws:
        _merge_keywords(room_id, kws)
    return {"ok": True, "message": msg, "new_keywords": kws}


def _add_message(room_id: str, peer_id: str, display_name: str, emoji: str, content: str, msg_type: str = "chat") -> dict:
    msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    now = _now()
    if is_connected():
        row_id = execute_write(
            """INSERT INTO live_messages(msg_id,room_id,peer_id,display_name,emoji,content,msg_type,created_at)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
            (msg_id, room_id, peer_id, display_name, emoji, content, msg_type, now),
        )
    else:
        room = _rooms_mem[room_id]
        row_id = len(room["messages"]) + 1
        room["messages"].append({
            "id": row_id,
            "msg_id": msg_id,
            "peer_id": peer_id,
            "display_name": display_name,
            "name": display_name,
            "emoji": emoji,
            "content": content,
            "text": content,
            "msg_type": msg_type,
            "type": msg_type,
            "ts": now.isoformat(),
            "created_at": now.isoformat(),
        })
    return {
        "id": row_id,
        "msg_id": msg_id,
        "peer_id": peer_id,
        "display_name": display_name,
        "name": display_name,
        "emoji": emoji,
        "content": content,
        "text": content,
        "msg_type": msg_type,
        "type": msg_type,
        "ts": now.isoformat(),
        "created_at": now.isoformat(),
    }


def _add_system_message(room_id: str, content: str) -> None:
    try:
        _add_message(room_id, "system", "시스템", "✦", content, "system")
    except Exception:
        pass


def _merge_keywords(room_id: str, new_keywords: list[str]) -> list[str]:
    row = _get_room_row(room_id)
    if not row:
        return []
    merged = []
    for kw in _json_loads(row.get("keywords"), []) + new_keywords:
        if kw and kw not in merged:
            merged.append(kw)
    merged = merged[:20]
    if is_connected():
        execute_write("UPDATE live_rooms SET keywords=%s WHERE room_id=%s", (json.dumps(merged, ensure_ascii=False), room_id))
    else:
        _rooms_mem[room_id]["keywords"] = merged
    return merged


def add_transcript(room_id: str, data: dict, user_id: str) -> dict:
    ok, _peer_id = _require_member(room_id, user_id)
    if not ok:
        return {"ok": False, "error": "방에 입장한 회원만 기록할 수 있습니다."}
    text = (data.get("text") or "").strip()
    if not text:
        return {"ok": False, "error": "기록할 텍스트가 없습니다."}
    profile = _user_display(user_id, data.get("display_name") or "독서인", data.get("emoji") or "🌙")
    entry = {"user_id": user_id, "display_name": profile["display_name"], "text": text, "created_at": _now().isoformat()}
    row = _get_room_row(room_id)
    transcript = _json_loads(row.get("transcript"), []) if row else []
    transcript.append(entry)
    if is_connected():
        execute_write("UPDATE live_rooms SET transcript=%s WHERE room_id=%s", (json.dumps(transcript, ensure_ascii=False), room_id))
    else:
        _rooms_mem[room_id]["transcript"] = transcript
    keywords = _merge_keywords(room_id, [kw for kw in KEYWORDS if kw in text])
    return {"ok": True, "entry": entry, "keywords": keywords}


def get_room_updates(room_id: str, since=0, user_id: Optional[str] = None) -> dict:
    if user_id:
        ok, _peer_id = _require_member(room_id, user_id)
        if not ok:
            return {"ok": False, "error": "방에 입장한 회원만 조회할 수 있습니다."}
    room = _room_view(room_id)
    if not room:
        return {"ok": False, "error": "방을 찾을 수 없습니다."}
    since_id = int(since) if str(since or "0").isdigit() else 0
    if is_connected():
        rows = execute_all(
            """SELECT id,msg_id,peer_id,display_name,emoji,content,msg_type,created_at
               FROM live_messages
               WHERE room_id=%s AND id>%s
               ORDER BY id ASC
               LIMIT 100""",
            (room_id, since_id),
        )
        messages = [
            {
                "id": row.get("id"),
                "msg_id": row.get("msg_id"),
                "peer_id": row.get("peer_id") or "",
                "display_name": row.get("display_name") or "",
                "name": row.get("display_name") or "",
                "emoji": row.get("emoji") or "🌙",
                "content": row.get("content") or "",
                "text": row.get("content") or "",
                "msg_type": row.get("msg_type") or "chat",
                "type": row.get("msg_type") or "chat",
                "ts": str(row.get("created_at") or ""),
            }
            for row in rows
        ]
    else:
        messages = [msg for msg in _rooms_mem.get(room_id, {}).get("messages", []) if int(msg.get("id") or 0) > since_id][:100]
    return {
        "ok": True,
        "room": room,
        "messages": messages,
        "next_idx": messages[-1]["id"] if messages else since_id,
        "keywords": room["keywords"],
        "live_keywords": room["keywords"],
        "member_count": room["member_count"],
        "participant_count": room["member_count"],
        "participants": room["members"],
    }


def leave_room(room_id: str, data: dict, user_id: str) -> dict:
    peer_id = data.get("peer_id") or _find_active_peer(room_id, user_id)
    if not peer_id:
        return {"ok": False, "error": "입장 기록을 찾을 수 없습니다."}
    now = _now()
    if is_connected():
        execute_write("UPDATE live_members SET left_at=%s WHERE room_id=%s AND peer_id=%s", (now, room_id, peer_id))
    else:
        _rooms_mem.get(room_id, {}).get("members", {}).pop(peer_id, None)
    room = _room_view(room_id)
    if room and room["member_count"] == 0:
        _end_room_status(room_id, now)
    return {"ok": True, "member_count": room["member_count"] if room else 0}


def end_room(room_id: str, user_id: str) -> dict:
    row = _get_room_row(room_id)
    if not row:
        return {"ok": False, "error": "방을 찾을 수 없습니다."}
    if row.get("host_id") != user_id:
        return {"ok": False, "error": "방장만 종료할 수 있습니다."}
    _end_room_status(room_id, _now())
    report = _generate_report(room_id)
    if is_connected():
        execute_write("UPDATE live_rooms SET ai_report=%s WHERE room_id=%s", (json.dumps(report, ensure_ascii=False), room_id))
    else:
        _rooms_mem[room_id]["ai_report"] = report
    _add_system_message(room_id, "독서 모임이 종료되었습니다.")
    return {"ok": True, "report": report, "room": _room_view(room_id)}


def _end_room_status(room_id: str, ended_at: datetime) -> None:
    if is_connected():
        execute_write("UPDATE live_rooms SET status='ended', ended_at=%s WHERE room_id=%s", (ended_at, room_id))
    else:
        room = _rooms_mem.get(room_id)
        if room:
            room["status"] = "ended"
            room["ended_at"] = ended_at.isoformat()


def get_report(room_id: str) -> Optional[dict]:
    row = _get_room_row(room_id)
    if not row:
        return None
    return _json_loads(row.get("ai_report"), None)


def _generate_report(room_id: str) -> dict:
    room = _room_view(room_id) or {}
    if is_connected():
        msg_rows = execute_all("SELECT content FROM live_messages WHERE room_id=%s AND msg_type='chat' ORDER BY id ASC", (room_id,))
        messages = [row.get("content", "") for row in msg_rows if row.get("content")]
        transcript = _json_loads((_get_room_row(room_id) or {}).get("transcript"), [])
    else:
        raw = _rooms_mem.get(room_id, {})
        messages = [m.get("content", "") for m in raw.get("messages", []) if m.get("msg_type") == "chat"]
        transcript = raw.get("transcript", [])
    texts = messages + [t.get("text", "") for t in transcript if t.get("text")]
    participants = [m.get("display_name", "독서인") for m in room.get("members", [])]
    try:
        from app.services.gemini_service import summarize_meeting
        if len(texts) >= 2:
            report = summarize_meeting(room.get("book_title", ""), texts, participants)
        else:
            report = None
    except Exception:
        report = None
    if not report:
        report = {
            "title": f"{room.get('book_title') or room.get('title') or '라이브'} 독서 모임 기록",
            "one_line": "함께 읽은 문장을 바탕으로 생각을 나눈 시간입니다.",
            "mood": "차분한 대화",
            "mood_emoji": "✦",
            "key_insights": [
                "각자의 독서 경험이 같은 책을 다른 각도에서 비추었습니다.",
                "대화 중 나온 키워드가 다음 모임의 질문으로 이어질 수 있습니다.",
            ],
            "highlight_quotes": messages[:2],
            "main_keywords": room.get("keywords", [])[:5] or ["독서", "대화", "질문"],
            "next_questions": [
                "오늘 나온 생각 중 다음 모임에서 더 깊게 다뤄보고 싶은 것은 무엇인가요?",
                "이 책이 각자의 일상에 남긴 한 문장은 무엇인가요?",
            ],
            "summary": f"{len(participants)}명이 참여했고 {len(messages)}개의 채팅과 {len(transcript)}개의 음성 기록이 남았습니다.",
        }
    report.update({
        "room_id": room_id,
        "book_title": room.get("book_title", ""),
        "participants": participants,
        "created_at": _now().isoformat(),
    })
    return report
