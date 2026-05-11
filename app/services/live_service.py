"""
라이브 독서방 서비스
────────────────────────────────────────
- 방 생성 / 참여 / 나가기
- 실시간 메시지 (Socket.io 없이 폴링 방식)
- AI 실시간 키워드 추출
- 모임 종료 → 1장 자동 요약 보고서
"""
import uuid
from datetime import datetime
from typing import Optional

# ── 인메모리 저장소 ──────────────────────────────────────
_rooms: dict[str, dict] = {}         # room_id → room 데이터
_messages: dict[str, list] = {}      # room_id → 메시지 리스트
_transcripts: dict[str, list] = {}   # room_id → 음성 텍스트 리스트


# ══════════════════════════════════════════════════════════════
#  방 관리
# ══════════════════════════════════════════════════════════════

def create_room(host_id: str, data: dict) -> dict:
    """새 라이브 독서방 생성"""
    room_id = f"room_{uuid.uuid4().hex[:8]}"
    room = {
        "room_id":      room_id,
        "host_id":      host_id,
        "host_name":    data.get("host_name", "호스트"),
        "title":        data.get("title", "독서 모임"),
        "book_title":   data.get("book_title", ""),
        "book_author":  data.get("book_author", ""),
        "club_id":      data.get("club_id", ""),
        "max_members":  min(int(data.get("max_members", 8)), 8),
        "is_private":   data.get("is_private", False),
        "password":     data.get("password", ""),
        "status":       "waiting",   # waiting | live | ended
        "participants": {
            host_id: {
                "user_id":   host_id,
                "name":      data.get("host_name", "호스트"),
                "emoji":     data.get("host_emoji", "⭐"),
                "is_host":   True,
                "joined_at": datetime.now().isoformat(),
                "is_muted":  False,
                "is_video":  True,
            }
        },
        "created_at":  datetime.now().isoformat(),
        "started_at":  None,
        "ended_at":    None,
        "report":      None,
        "live_keywords": [],
        "discussion_topic": data.get("discussion_topic", ""),
    }
    _rooms[room_id] = room
    _messages[room_id] = []
    _transcripts[room_id] = []
    return _room_view(room)


def get_room(room_id: str) -> Optional[dict]:
    r = _rooms.get(room_id)
    return _room_view(r) if r else None


def get_active_rooms(club_id: str = "") -> list[dict]:
    """활성 방 목록 (club_id 필터 가능)"""
    rooms = []
    for r in _rooms.values():
        if r["status"] == "ended":
            continue
        if club_id and r["club_id"] != club_id:
            continue
        rooms.append(_room_view(r))
    return sorted(rooms, key=lambda x: x["created_at"], reverse=True)


def join_room(room_id: str, user_id: str, data: dict) -> dict:
    """방 참여"""
    r = _rooms.get(room_id)
    if not r:
        return {"ok": False, "error": "방을 찾을 수 없습니다."}
    if r["status"] == "ended":
        return {"ok": False, "error": "이미 종료된 모임입니다."}
    if len(r["participants"]) >= r["max_members"]:
        return {"ok": False, "error": f"정원({r['max_members']}명)이 초과되었습니다."}
    if r["is_private"] and data.get("password") != r["password"]:
        return {"ok": False, "error": "비밀번호가 틀렸습니다."}

    r["participants"][user_id] = {
        "user_id":   user_id,
        "name":      data.get("name", "참가자"),
        "emoji":     data.get("emoji", "📚"),
        "is_host":   False,
        "joined_at": datetime.now().isoformat(),
        "is_muted":  False,
        "is_video":  True,
    }
    # 시스템 메시지
    _add_system_msg(room_id, f"{data.get('name','참가자')}님이 입장했습니다.")
    return {"ok": True, "room": _room_view(r)}


def leave_room(room_id: str, user_id: str) -> dict:
    """방 나가기"""
    r = _rooms.get(room_id)
    if not r:
        return {"ok": False, "error": "방 없음"}

    participant = r["participants"].pop(user_id, None)
    if participant:
        name = participant["name"]
        _add_system_msg(room_id, f"{name}님이 퇴장했습니다.")

    # 호스트가 나가면 방 종료
    if user_id == r["host_id"] and r["status"] != "ended":
        r["status"]   = "ended"
        r["ended_at"] = datetime.now().isoformat()

    return {"ok": True}


def start_room(room_id: str, host_id: str) -> dict:
    """모임 시작"""
    r = _rooms.get(room_id)
    if not r:
        return {"ok": False, "error": "방 없음"}
    if r["host_id"] != host_id:
        return {"ok": False, "error": "호스트만 시작할 수 있습니다."}
    r["status"]     = "live"
    r["started_at"] = datetime.now().isoformat()
    _add_system_msg(room_id, "📚 독서 모임이 시작되었습니다!")
    return {"ok": True, "room": _room_view(r)}


def end_room(room_id: str, host_id: str) -> dict:
    """모임 종료 → AI 보고서 자동 생성"""
    r = _rooms.get(room_id)
    if not r:
        return {"ok": False, "error": "방 없음"}
    if r["host_id"] != host_id:
        return {"ok": False, "error": "호스트만 종료할 수 있습니다."}

    r["status"]   = "ended"
    r["ended_at"] = datetime.now().isoformat()
    _add_system_msg(room_id, "모임이 종료되었습니다. AI 보고서를 생성 중...")

    # AI 보고서 생성
    report = _generate_report(room_id)
    r["report"] = report
    return {"ok": True, "report": report}


# ══════════════════════════════════════════════════════════════
#  채팅 메시지
# ══════════════════════════════════════════════════════════════

def send_message(room_id: str, user_id: str, data: dict) -> dict:
    """채팅 메시지 전송"""
    r = _rooms.get(room_id)
    if not r:
        return {"ok": False, "error": "방 없음"}

    participant = r["participants"].get(user_id, {})
    msg = {
        "msg_id":    f"msg_{uuid.uuid4().hex[:6]}",
        "room_id":   room_id,
        "user_id":   user_id,
        "name":      participant.get("name", data.get("name", "익명")),
        "emoji":     participant.get("emoji", "💬"),
        "type":      data.get("type", "chat"),   # chat | reaction | card
        "content":   data.get("content", "").strip(),
        "created_at": datetime.now().isoformat(),
        "is_system": False,
    }
    if not msg["content"]:
        return {"ok": False, "error": "내용을 입력해주세요."}

    _messages[room_id].append(msg)
    # 메시지 최대 200개 유지
    if len(_messages[room_id]) > 200:
        _messages[room_id] = _messages[room_id][-200:]
    return {"ok": True, "message": msg}


def get_messages(room_id: str, after_idx: int = 0) -> dict:
    """메시지 폴링"""
    msgs = _messages.get(room_id, [])
    return {
        "ok":       True,
        "messages": msgs[after_idx:],
        "total":    len(msgs),
        "next_idx": len(msgs),
    }


# ══════════════════════════════════════════════════════════════
#  AI 음성 텍스트 & 키워드
# ══════════════════════════════════════════════════════════════

def add_transcript(room_id: str, user_id: str, text: str) -> dict:
    """Web Speech API로 인식된 텍스트 저장"""
    r = _rooms.get(room_id)
    if not r:
        return {"ok": False}

    participant = r["participants"].get(user_id, {})
    entry = {
        "user_id":    user_id,
        "name":       participant.get("name", "참가자"),
        "text":       text,
        "timestamp":  datetime.now().isoformat(),
    }
    _transcripts[room_id].append(entry)

    # 실시간 키워드 추출 (간단한 Mock)
    keywords = _extract_keywords_mock(text)
    for kw in keywords:
        if kw not in r["live_keywords"]:
            r["live_keywords"].insert(0, kw)
    r["live_keywords"] = r["live_keywords"][:20]  # 최대 20개

    return {"ok": True, "keywords": r["live_keywords"]}


def get_live_state(room_id: str, user_id: str, after_idx: int = 0) -> dict:
    """폴링: 방 상태 + 새 메시지 + 키워드 한번에"""
    r = _rooms.get(room_id)
    if not r:
        return {"ok": False, "error": "방 없음"}
    msgs = _messages.get(room_id, [])
    return {
        "ok":          True,
        "room":        _room_view(r),
        "messages":    msgs[after_idx:],
        "next_idx":    len(msgs),
        "live_keywords": r.get("live_keywords", []),
        "participant_count": len(r["participants"]),
    }


# ══════════════════════════════════════════════════════════════
#  내부 헬퍼
# ══════════════════════════════════════════════════════════════

def _room_view(r: dict) -> dict:
    """외부에 노출할 방 정보 (비밀번호 제외)"""
    view = {k: v for k, v in r.items() if k != "password"}
    view["participant_count"] = len(r["participants"])
    view["participant_list"]  = list(r["participants"].values())
    return view


def _add_system_msg(room_id: str, text: str):
    msg = {
        "msg_id":    f"sys_{uuid.uuid4().hex[:4]}",
        "room_id":   room_id,
        "user_id":   "system",
        "name":      "시스템",
        "emoji":     "🔔",
        "type":      "system",
        "content":   text,
        "created_at": datetime.now().isoformat(),
        "is_system": True,
    }
    _messages.setdefault(room_id, []).append(msg)


STOP_WORDS = {"이","그","저","것","수","때","말","사람","어떤","같은","않","있","하","을","를","이","가","은","는"}

def _extract_keywords_mock(text: str) -> list[str]:
    """간단한 키워드 추출 (Gemini 없을 때 fallback)"""
    words = [w.strip(".,!?\"'") for w in text.split() if len(w) > 1]
    return [w for w in words if w not in STOP_WORDS][:3]


def _generate_report(room_id: str) -> dict:
    """모임 종료 시 AI 보고서 생성"""
    from app.services.gemini_service import summarize_meeting

    r = _rooms.get(room_id, {})
    transcripts = _transcripts.get(room_id, [])
    messages    = _messages.get(room_id, [])

    # 텍스트 수집
    texts = [t["text"] for t in transcripts if t.get("text")]
    chat_texts = [m["content"] for m in messages if not m.get("is_system") and m["type"]=="chat"]
    all_texts = texts + chat_texts

    participants = list({
        p["name"] for p in r.get("participants", {}).values()
    })

    book_title = r.get("book_title", "")

    if len(all_texts) >= 2:
        report = summarize_meeting(book_title, all_texts, participants)
    else:
        # Mock 보고서
        report = {
            "summary":          f"『{book_title}』을 중심으로 {len(participants)}명이 모여 깊은 독서 토론을 나눴습니다.",
            "key_insights":     [
                "책의 핵심 주제에 대해 다양한 시각이 공유되었습니다.",
                "참가자들의 개인적 경험과 책 내용이 연결되는 순간이 인상적이었습니다.",
                "다음 모임에서 이어갈 토론 주제가 자연스럽게 도출되었습니다.",
            ],
            "highlight_quotes": chat_texts[:2] if chat_texts else [],
            "next_questions":   [
                f"다음 장에서는 어떤 변화가 기다리고 있을까요?",
                "오늘 나눈 이야기 중 가장 오래 기억에 남을 것은 무엇인가요?",
            ],
            "mood":             "사색적",
            "created_at":       datetime.now().isoformat(),
            "book_title":       book_title,
            "duration_minutes": _calc_duration(r),
            "participant_names": participants,
        }

    report["room_id"]   = room_id
    report["ended_at"]  = r.get("ended_at", datetime.now().isoformat())
    return report


def _calc_duration(r: dict) -> int:
    try:
        start = datetime.fromisoformat(r["started_at"])
        end   = datetime.fromisoformat(r.get("ended_at") or datetime.now().isoformat())
        return int((end - start).total_seconds() / 60)
    except Exception:
        return 0
