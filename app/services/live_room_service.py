from typing import Optional
"""
라이브 독서방 서비스 — WebRTC 시그널링 + AI 요약
────────────────────────────────────────
- 방 생성/참가/퇴장
- 실시간 메시지 + 키워드 감지
- 모임 종료 후 AI 1장 요약 보고서
"""
import uuid
from datetime import datetime

# ── 방 저장소 ────────────────────────────────────────────
_rooms: dict[str, dict] = {}

EMOJI_POOL = ["📚", "✦", "🌿", "🔥", "🦋", "🌊", "⭐", "🎭", "🌸", "💫"]


def create_room(data: dict) -> dict:
    """새 라이브 독서방 생성"""
    room_id = f"room_{uuid.uuid4().hex[:6]}"
    room = {
        "room_id":     room_id,
        "title":       data.get("title", "독서 모임"),
        "book_title":  data.get("book_title", ""),
        "book_author": data.get("book_author", ""),
        "host_id":     data.get("host_id", "user_demo"),
        "max_members": data.get("max_members", 8),
        "status":      "waiting",       # waiting → live → ended
        "members":     {},              # peer_id → member 정보
        "messages":    [],              # 채팅 메시지
        "keywords":    [],              # AI 감지 키워드
        "transcripts": [],              # 음성 인식 텍스트
        "created_at":  datetime.now().isoformat(),
        "started_at":  None,
        "ended_at":    None,
        "report":      None,
    }
    _rooms[room_id] = room
    return room


def join_room(room_id: str, data: dict) -> dict:
    """방 참가"""
    room = _rooms.get(room_id)
    if not room:
        return {"ok": False, "error": "방을 찾을 수 없습니다."}
    if len(room["members"]) >= room["max_members"]:
        return {"ok": False, "error": "방이 꽉 찼습니다."}

    peer_id = data.get("peer_id") or f"peer_{uuid.uuid4().hex[:6]}"
    idx     = len(room["members"]) % len(EMOJI_POOL)
    member  = {
        "peer_id":     peer_id,
        "user_id":     data.get("user_id", "user_demo"),
        "display_name":data.get("display_name", "독서인"),
        "emoji":       EMOJI_POOL[idx],
        "joined_at":   datetime.now().isoformat(),
        "is_host":     data.get("user_id") == room["host_id"],
    }
    room["members"][peer_id] = member

    if room["status"] == "waiting" and len(room["members"]) >= 2:
        room["status"]     = "live"
        room["started_at"] = datetime.now().isoformat()

    return {"ok": True, "room": _room_summary(room), "member": member, "peer_id": peer_id}


def leave_room(room_id: str, peer_id: str) -> dict:
    room = _rooms.get(room_id)
    if not room:
        return {"ok": False}
    room["members"].pop(peer_id, None)
    if not room["members"] and room["status"] == "live":
        room["status"]   = "ended"
        room["ended_at"] = datetime.now().isoformat()
    return {"ok": True, "remaining": len(room["members"])}


def send_message(room_id: str, data: dict) -> dict:
    """채팅 메시지 + 키워드 자동 감지"""
    room = _rooms.get(room_id)
    if not room:
        return {"ok": False}

    msg = {
        "msg_id":   f"msg_{uuid.uuid4().hex[:6]}",
        "peer_id":  data.get("peer_id", ""),
        "name":     data.get("display_name", "독서인"),
        "emoji":    data.get("emoji", "⭐"),
        "text":     data.get("text", ""),
        "type":     data.get("type", "chat"),    # chat | quote | keyword | system
        "ts":       datetime.now().isoformat(),
    }
    room["messages"].append(msg)

    # 간단한 키워드 감지
    kw = _detect_keywords(msg["text"])
    for k in kw:
        if k not in room["keywords"]:
            room["keywords"].append(k)

    return {"ok": True, "message": msg, "new_keywords": kw}


def add_transcript(room_id: str, data: dict) -> dict:
    """음성 인식 텍스트 추가 (Web Speech API → 서버 전송)"""
    room = _rooms.get(room_id)
    if not room:
        return {"ok": False}
    entry = {
        "peer_id":  data.get("peer_id", ""),
        "name":     data.get("display_name", ""),
        "text":     data.get("text", ""),
        "ts":       datetime.now().isoformat(),
        "is_final": data.get("is_final", True),
    }
    room["transcripts"].append(entry)
    return {"ok": True}


def end_room(room_id: str) -> dict:
    """방 종료 + AI 요약 보고서 생성"""
    room = _rooms.get(room_id)
    if not room:
        return {"ok": False, "error": "방 없음"}

    room["status"]   = "ended"
    room["ended_at"] = datetime.now().isoformat()

    # 전체 대화 수집
    all_texts = [m["text"] for m in room["messages"] if m.get("text")]
    all_texts += [t["text"] for t in room["transcripts"] if t.get("text")]

    report = _generate_room_report(room, all_texts)
    room["report"] = report

    return {"ok": True, "report": report, "room": _room_summary(room)}


def get_room(room_id: str) -> Optional[dict]:
    room = _rooms.get(room_id)
    return _room_summary(room) if room else None


def list_rooms(status: str = "live") -> list[dict]:
    return [_room_summary(r) for r in _rooms.values() if r["status"] == status]


# ── 내부 헬퍼 ────────────────────────────────────────────

_KEYWORDS = [
    "인생", "죽음", "행복", "자유", "사랑", "진리", "역사", "과학",
    "철학", "인류", "우주", "시간", "의미", "성장", "허구", "기억",
    "감정", "이성", "언어", "문화", "사회", "경제", "예술", "종교",
]

def _detect_keywords(text: str) -> list[str]:
    return [kw for kw in _KEYWORDS if kw in text]


def _room_summary(room: dict) -> dict:
    return {
        "room_id":     room["room_id"],
        "title":       room["title"],
        "book_title":  room["book_title"],
        "book_author": room["book_author"],
        "status":      room["status"],
        "member_count":len(room["members"]),
        "members":     list(room["members"].values()),
        "message_count":len(room["messages"]),
        "keywords":    room["keywords"][:10],
        "started_at":  room["started_at"],
        "ended_at":    room["ended_at"],
        "report":      room.get("report"),
    }


def _generate_room_report(room: dict, all_texts: list[str]) -> dict:
    """AI로 모임 요약 보고서 생성"""
    from app.services.gemini_service import _call_gemini, _parse_json_safe

    if len(all_texts) < 2:
        all_texts = ["책에 대한 이야기를 나눴습니다.", "서로의 생각을 공유하는 시간이었습니다."]

    participants = [m["display_name"] for m in room["members"].values()]
    duration_min = 30  # 기본값
    if room.get("started_at") and room.get("ended_at"):
        try:
            s = datetime.fromisoformat(room["started_at"])
            e = datetime.fromisoformat(room["ended_at"])
            duration_min = int((e - s).total_seconds() / 60)
        except Exception:
            pass

    prompt = f"""독서 모임 대화를 분석해서 1장 요약 보고서를 만들어주세요.

책: {room['book_title']}
참여자: {participants}
진행 시간: {duration_min}분
감지된 키워드: {room['keywords']}
대화 내용: {' | '.join(all_texts[:20])}

JSON 형식으로만 응답:
{{
  "title": "모임 제목",
  "one_line": "모임을 한 문장으로",
  "mood": "모임 분위기 (사색적/열정적/감성적/지적)",
  "mood_emoji": "분위기 이모지",
  "key_insights": ["핵심 인사이트1", "핵심 인사이트2", "핵심 인사이트3"],
  "highlight_quotes": ["인상적인 발언1", "인상적인 발언2"],
  "main_keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
  "next_questions": ["다음 모임 질문1", "다음 모임 질문2", "다음 모임 질문3"],
  "summary": "모임 전체 요약 3-4문장"
}}"""

    raw    = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and "summary" in parsed:
        return {
            **parsed,
            "book_title":    room["book_title"],
            "participants":  participants,
            "duration_min":  duration_min,
            "message_count": len(room["messages"]),
            "created_at":    datetime.now().isoformat(),
            "source":        "gemini",
        }

    return {
        "title":           f"《{room['book_title']}》 독서 모임 보고서",
        "one_line":        "책을 통해 서로의 생각을 나누고 새로운 시각을 얻은 소중한 시간이었습니다.",
        "mood":            "사색적",
        "mood_emoji":      "🌿",
        "key_insights":    ["책에서 발견한 새로운 관점을 공유했습니다.", "서로 다른 해석이 더 깊은 이해로 이어졌습니다.", "독서가 삶과 연결되는 순간들을 나눴습니다."],
        "highlight_quotes":["가장 인상 깊었던 구절을 함께 읽었습니다.", "각자의 경험과 책을 연결하는 이야기가 나왔습니다."],
        "main_keywords":   room["keywords"][:5] or ["독서", "공유", "성장"],
        "next_questions":  ["다음 장에서 작가는 무엇을 말하고 싶었을까요?", "이 책이 당신의 삶을 어떻게 바꿀 수 있을까요?", "비슷한 주제의 다른 책은 무엇이 있을까요?"],
        "summary":         f"총 {duration_min}분 동안 {len(participants)}명이 《{room['book_title']}》를 함께 읽고 이야기를 나눴습니다. {len(room['messages'])}개의 메시지가 오가며 깊은 독서 토론이 이루어졌습니다.",
        "book_title":      room["book_title"],
        "participants":    participants,
        "duration_min":    duration_min,
        "message_count":   len(room["messages"]),
        "created_at":      datetime.now().isoformat(),
        "source":          "mock",
    }


