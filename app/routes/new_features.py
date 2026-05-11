"""
5대 기능 통합 API 라우터
────────────────────────────────────────
기능 1: /api/heart/   — 마음 서재
기능 2: /api/live/    — 라이브 독서방
기능 3: /api/places/  — (기존 확장)
기능 4: /api/socrates/— AI 소크라테스 대화
기능 5: /api/social/  — 소셜 피드
"""
from flask import Blueprint, request, jsonify

new_features_bp = Blueprint("new_features", __name__)


def _uid() -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.services.user_service import verify_token
            payload = verify_token(auth[7:].strip())
            if payload and payload.get("user_id"):
                return payload["user_id"]
        except Exception:
            pass
    data = request.get_json(silent=True) or {}
    return request.args.get("user_id") or data.get("user_id") or "user_demo"


def get_session(session_id: str):
    from app.services.live_socrates_service import resume_session
    result = resume_session(session_id)
    return result.get("session") if result.get("ok") else None


def get_my_dictionary(user_id: str):
    from app.services.live_socrates_service import get_dict_entries
    return get_dict_entries(user_id).get("entries", [])


def build_my_definition(data: dict):
    from app.services.live_socrates_service import add_dict_entry
    result = add_dict_entry(_uid(), data)
    return result.get("entry", {})


def create_action_plan(data: dict):
    from app.services.live_socrates_service import create_action_plan as _create_action_plan
    result = _create_action_plan(_uid(), data)
    return result.get("plan", {})


# ══════════════════════════════════════════════════════════════
#  기능 1 — 마음 서재
# ══════════════════════════════════════════════════════════════

@new_features_bp.route("/heart/shelf", methods=["GET"])
def heart_shelf():
    from app.services.heart_library_service import get_shelf
    user_id = request.args.get("user_id", "user_demo")
    return jsonify({"ok": True, **get_shelf(user_id)})


@new_features_bp.route("/heart/books", methods=["POST"])
def heart_add_book():
    from app.services.heart_library_service import add_book
    data = request.get_json() or {}
    if not data.get("title", "").strip():
        return jsonify({"ok": False, "error": "제목을 입력하세요."}), 400
    book = add_book(data.get("user_id", "user_demo"), data)
    return jsonify({"ok": True, "book": book}), 201


@new_features_bp.route("/heart/books/<book_id>", methods=["PUT"])
def heart_update_book(book_id):
    from app.services.heart_library_service import update_book
    data = request.get_json() or {}
    book = update_book(book_id, data)
    if not book:
        return jsonify({"ok": False, "error": "책을 찾을 수 없습니다."}), 404
    return jsonify({"ok": True, "book": book})


@new_features_bp.route("/heart/books/<book_id>", methods=["DELETE"])
def heart_delete_book(book_id):
    from app.services.heart_library_service import delete_book
    if delete_book(book_id):
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "책을 찾을 수 없습니다."}), 404


@new_features_bp.route("/heart/emotion", methods=["POST"])
def heart_add_emotion():
    from app.services.heart_library_service import add_emotion
    data = request.get_json() or {}
    if not data.get("book_id"):
        return jsonify({"ok": False, "error": "book_id가 필요합니다."}), 400
    em = add_emotion(data.get("user_id", "user_demo"), data)
    return jsonify({"ok": True, "emotion": em}), 201


@new_features_bp.route("/heart/timeline", methods=["GET"])
def heart_timeline():
    from app.services.heart_library_service import get_emotion_timeline, get_emotion_stats
    user_id = request.args.get("user_id", "user_demo")
    book_id = request.args.get("book_id")
    return jsonify({
        "ok":       True,
        "timeline": get_emotion_timeline(user_id, book_id),
        "stats":    get_emotion_stats(user_id),
    })


@new_features_bp.route("/heart/constellation", methods=["GET"])
def heart_constellation():
    from app.services.heart_library_service import get_constellation
    user_id = request.args.get("user_id", "user_demo")
    return jsonify({"ok": True, **get_constellation(user_id)})


@new_features_bp.route("/heart/constellation/connect", methods=["POST"])
def heart_connect():
    from app.services.heart_library_service import add_connection
    data = request.get_json() or {}
    if not (data.get("from_book_id") and data.get("to_book_id")):
        return jsonify({"ok": False, "error": "from_book_id, to_book_id 필요"}), 400
    return jsonify({"ok": True, "connection": add_connection(data)})


@new_features_bp.route("/heart/report", methods=["GET"])
def heart_monthly_report():
    from app.services.heart_library_service import get_monthly_report
    user_id     = request.args.get("user_id", "user_demo")
    year_month  = request.args.get("month")
    return jsonify({"ok": True, "report": get_monthly_report(user_id, year_month)})


@new_features_bp.route("/heart/persona", methods=["GET"])
def heart_persona():
    from app.services.heart_library_service import get_reading_persona
    user_id = request.args.get("user_id", "user_demo")
    return jsonify({"ok": True, "persona": get_reading_persona(user_id)})


# ══════════════════════════════════════════════════════════════
#  기능 2 — 라이브 독서방
# ══════════════════════════════════════════════════════════════

@new_features_bp.route("/live/rooms", methods=["GET"])
def live_list():
    from app.services.live_backend_service import list_rooms
    status = request.args.get("status", "active")
    return jsonify({"ok": True, "rooms": list_rooms(status)})


@new_features_bp.route("/live/rooms", methods=["POST"])
def live_create():
    from app.services.live_backend_service import create_room
    data = request.get_json() or {}
    if not data.get("title", "").strip():
        return jsonify({"ok": False, "error": "방 이름을 입력하세요."}), 400
    result = create_room(data, _uid())
    return jsonify(result), 201 if result.get("ok") else 400


@new_features_bp.route("/live/rooms/<room_id>", methods=["GET"])
def live_get(room_id):
    from app.services.live_backend_service import get_room
    room = get_room(room_id)
    if not room:
        return jsonify({"ok": False, "error": "방 없음"}), 404
    return jsonify({"ok": True, "room": room})


@new_features_bp.route("/live/rooms/<room_id>/join", methods=["POST"])
def live_join(room_id):
    from app.services.live_backend_service import join_room
    data = request.get_json() or {}
    result = join_room(room_id, data, _uid())
    return jsonify(result), 200 if result.get("ok") else 400


@new_features_bp.route("/live/rooms/<room_id>/leave", methods=["POST"])
def live_leave(room_id):
    from app.services.live_backend_service import leave_room
    data = request.get_json() or {}
    result = leave_room(room_id, data, _uid())
    return jsonify(result), 200 if result.get("ok") else 400


@new_features_bp.route("/live/rooms/<room_id>/message", methods=["POST"])
def live_message(room_id):
    from app.services.live_backend_service import send_message
    data = request.get_json() or {}
    if not (data.get("text") or data.get("content") or "").strip():
        return jsonify({"ok": False, "error": "메시지 내용 필요"}), 400
    result = send_message(room_id, data, _uid())
    return jsonify(result), 200 if result.get("ok") else 400


@new_features_bp.route("/live/rooms/<room_id>/transcript", methods=["POST"])
def live_transcript(room_id):
    from app.services.live_backend_service import add_transcript
    data = request.get_json() or {}
    result = add_transcript(room_id, data, _uid())
    return jsonify(result), 200 if result.get("ok") else 400


@new_features_bp.route("/live/rooms/<room_id>/end", methods=["POST"])
def live_end(room_id):
    from app.services.live_backend_service import end_room
    result = end_room(room_id, _uid())
    return jsonify(result), 200 if result.get("ok") else 403


@new_features_bp.route("/live/<room_id>/join", methods=["POST"])
def live_join_legacy(room_id):
    return live_join(room_id)


@new_features_bp.route("/live/<room_id>/leave", methods=["POST"])
def live_leave_legacy(room_id):
    return live_leave(room_id)


@new_features_bp.route("/live/<room_id>/chat", methods=["POST"])
def live_chat_legacy(room_id):
    return live_message(room_id)


@new_features_bp.route("/live/<room_id>/poll", methods=["GET"])
def live_poll_legacy(room_id):
    from app.services.live_backend_service import get_room_updates
    result = get_room_updates(room_id, request.args.get("since", "0"), _uid())
    return jsonify(result), 200 if result.get("ok") else 404


@new_features_bp.route("/live/<room_id>/transcript", methods=["POST"])
def live_transcript_legacy(room_id):
    return live_transcript(room_id)


@new_features_bp.route("/live/<room_id>/end", methods=["POST"])
def live_end_legacy(room_id):
    return live_end(room_id)


@new_features_bp.route("/live/<room_id>/report", methods=["GET"])
def live_report_legacy(room_id):
    from app.services.live_backend_service import get_report
    report = get_report(room_id)
    if not report:
        return jsonify({"ok": False, "error": "아직 생성된 리포트가 없습니다."}), 404
    return jsonify({"ok": True, "report": report})


# ══════════════════════════════════════════════════════════════
#  기능 4 — AI 소크라테스 대화
# ══════════════════════════════════════════════════════════════

@new_features_bp.route("/socrates/start", methods=["POST"])
def socrates_start():
    from app.services.live_socrates_service import start_session
    from app.services.socrates_discussion_service import normalize_discussion_mode
    data = request.get_json() or {}
    data["user_id"] = _uid()
    data["discussion_mode"] = normalize_discussion_mode(data.get("discussion_mode"))
    if not data.get("passage", "").strip():
        return jsonify({"ok": False, "error": "구절(passage)이 필요합니다."}), 400
    result = start_session(data)
    return jsonify(result), 201 if result.get("ok") else 400


@new_features_bp.route("/socrates/book-brief", methods=["POST"])
def socrates_book_brief():
    from app.services.socrates_discussion_service import generate_book_brief

    data = request.get_json() or {}
    passage = (data.get("passage") or "").strip()
    if not passage:
        return jsonify({"ok": False, "error": "구절(passage)이 필요합니다."}), 400
    brief = generate_book_brief(
        passage=passage,
        book_title=data.get("book_title", ""),
        user_id=_uid(),
    )
    return jsonify({"ok": True, "brief": brief})


@new_features_bp.route("/socrates/discussion-questions", methods=["POST"])
def socrates_discussion_questions():
    from app.services.socrates_discussion_service import (
        generate_discussion_questions,
        normalize_discussion_mode,
    )

    data = request.get_json() or {}
    questions = generate_discussion_questions(
        session_id=data.get("session_id", ""),
        passage=data.get("passage", ""),
        book_title=data.get("book_title", ""),
        insight=data.get("insight", ""),
        discussion_mode=normalize_discussion_mode(data.get("discussion_mode")),
        user_id=_uid(),
    )
    return jsonify({"ok": True, "questions": questions})


@new_features_bp.route("/socrates/debate-topic", methods=["POST"])
def socrates_debate_topic():
    from app.services.socrates_discussion_service import generate_debate_topic

    data = request.get_json() or {}
    debate = generate_debate_topic(
        passage=data.get("passage", ""),
        book_title=data.get("book_title", ""),
        insight=data.get("insight", ""),
        user_id=_uid(),
    )
    return jsonify({"ok": True, "debate": debate})


@new_features_bp.route("/socrates/lounge-card", methods=["POST"])
def socrates_lounge_card():
    from app.services.socrates_discussion_service import build_lounge_card

    data = request.get_json() or {}
    card = build_lounge_card(
        passage=data.get("passage", ""),
        book_title=data.get("book_title", ""),
        insight=data.get("insight", ""),
        discussion_questions=data.get("discussion_questions") or data.get("questions") or [],
        debate=data.get("debate") or {},
        user_id=_uid(),
    )
    return jsonify({"ok": True, "card": card})


@new_features_bp.route("/socrates/answer", methods=["POST"])
def socrates_answer():
    from app.services.live_socrates_service import answer_session
    data       = request.get_json() or {}
    session_id = data.get("session_id", "")
    answer     = data.get("answer", "").strip()
    if not session_id or not answer:
        return jsonify({"ok": False, "error": "session_id와 answer 필요"}), 400
    return jsonify(answer_session(session_id, answer))


@new_features_bp.route("/socrates/session/<session_id>", methods=["GET"])
def socrates_session(session_id):
    from app.services.live_socrates_service import resume_session
    s = get_session(session_id)
    if not s:
        return jsonify({"ok": False, "error": "세션 없음"}), 404
    return jsonify({"ok": True, "session": s})


@new_features_bp.route("/socrates/connect", methods=["POST"])
def socrates_connect():
    from app.services.live_socrates_service import force_connect
    data = request.get_json() or {}
    if not (data.get("text_a") and data.get("text_b")):
        return jsonify({"ok": False, "error": "text_a, text_b 필요"}), 400
    return jsonify({"ok": True, "insight": force_connect(data)})


@new_features_bp.route("/socrates/dictionary", methods=["GET"])
def socrates_get_dict():
    from app.services.live_socrates_service import get_dict_entries
    user_id = request.args.get("user_id", "user_demo")
    return jsonify({"ok": True, "entries": get_my_dictionary(user_id)})


@new_features_bp.route("/socrates/dictionary", methods=["POST"])
def socrates_add_dict():
    from app.services.live_socrates_service import add_dict_entry
    data = request.get_json() or {}
    if not data.get("concept", "").strip():
        return jsonify({"ok": False, "error": "concept 필요"}), 400
    return jsonify({"ok": True, "entry": build_my_definition(data)}), 201


@new_features_bp.route("/socrates/action", methods=["POST"])
def socrates_action():
    from app.services.live_socrates_service import create_action_plan as _create_action_plan
    data = request.get_json() or {}
    if not data.get("insight", "").strip():
        return jsonify({"ok": False, "error": "insight 필요"}), 400
    result = _create_action_plan(_uid(), data)
    return jsonify(result), 201 if result.get("ok") else 400


@new_features_bp.route("/socrates/action/<plan_id>/checkin", methods=["POST"])
def socrates_checkin(plan_id):
    from app.services.live_socrates_service import checkin_plan
    data = request.get_json() or {}
    return jsonify(checkin_plan(plan_id, data.get("note", "")))


@new_features_bp.route("/socrates/actions", methods=["GET"])
def socrates_actions():
    from app.services.live_socrates_service import get_action_plans
    return jsonify(get_action_plans(_uid()))


@new_features_bp.route("/socrates/sessions", methods=["GET"])
def socrates_sessions():
    from app.services.live_socrates_service import list_sessions
    limit = int(request.args.get("limit", "10"))
    return jsonify(list_sessions(_uid(), limit))


@new_features_bp.route("/socrates/sessions/<session_id>/resume", methods=["GET"])
def socrates_resume(session_id):
    from app.services.live_socrates_service import resume_session
    result = resume_session(session_id)
    return jsonify(result), 200 if result.get("ok") else 404


# ══════════════════════════════════════════════════════════════
#  기능 5 — 소셜 피드
# ══════════════════════════════════════════════════════════════

@new_features_bp.route("/social/feed", methods=["GET"])
def social_feed():
    from app.services.social_feed_service import get_feed
    page  = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    tag   = request.args.get("tag")
    return jsonify({"ok": True, **get_feed(page, limit, tag)})


@new_features_bp.route("/social/cards", methods=["POST"])
def social_create_card():
    from app.services.social_feed_service import create_card, check_and_create_bookclub
    data = request.get_json() or {}
    content = (data.get("passage") or data.get("content") or data.get("text") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "구절(passage)이 필요합니다."}), 400
    data["passage"] = content
    card = create_card(data.get("user_id", "user_demo"), data)
    # 북클럽 자동 생성 체크
    club = check_and_create_bookclub(data.get("book_title", ""))
    return jsonify({"ok": True, "card": card, "new_club": club}), 201


@new_features_bp.route("/social/cards/<card_id>/like", methods=["POST"])
def social_like(card_id):
    from app.services.social_feed_service import toggle_like
    data = request.get_json() or {}
    return jsonify(toggle_like(card_id, data.get("user_id", "user_demo")))


@new_features_bp.route("/social/cards/<card_id>/comments", methods=["GET"])
def social_comments(card_id):
    from app.services.social_feed_service import get_comments
    return jsonify({"ok": True, "comments": get_comments(card_id)})


@new_features_bp.route("/social/cards/<card_id>/comments", methods=["POST"])
def social_add_comment(card_id):
    from app.services.social_feed_service import add_comment
    data = request.get_json() or {}
    content = (data.get("text") or data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "댓글 내용 필요"}), 400
    data["text"] = content
    return jsonify(add_comment(card_id, data))


@new_features_bp.route("/social/match", methods=["GET"])
def social_match():
    from app.services.social_feed_service import find_reading_buddies
    user_id = request.args.get("user_id", "user_demo")
    genres  = request.args.get("genres", "철학,역사,과학").split(",")
    books   = request.args.get("books", "사피엔스,어린왕자").split(",")
    return jsonify({"ok": True, "matches": find_reading_buddies(user_id, genres, books)})


@new_features_bp.route("/social/clubs", methods=["GET"])
def social_clubs():
    from app.services.social_feed_service import get_bookclubs
    clubs = get_bookclubs()
    if not clubs:
        clubs = [
            {"club_id": "pod_pachinko", "name": "파친코 독서 파드", "member_count": 12, "current_book": "파친코"},
            {"club_id": "pod_cosmos", "name": "코스모스 사유 파드", "member_count": 9, "current_book": "코스모스"},
            {"club_id": "pod_lit", "name": "한국문학 문장 파드", "member_count": 15, "current_book": "채식주의자"},
        ]
    return jsonify({"ok": True, "clubs": clubs})


@new_features_bp.route("/social/challenge", methods=["GET"])
def social_challenge():
    from app.services.social_feed_service import get_challenge_status
    user_id     = request.args.get("user_id", "user_demo")
    books_read  = int(request.args.get("books_read", 3))
    memos       = int(request.args.get("memos", 5))
    return jsonify({"ok": True, **get_challenge_status(user_id, books_read, memos)})


@new_features_bp.route("/social/badges", methods=["GET"])
def social_badges():
    from app.services.social_feed_service import get_user_badges
    user_id = request.args.get("user_id", "user_demo")
    return jsonify({"ok": True, "badges": get_user_badges(user_id)})
