"""
라이브 독서방 라우터
────────────────────────────────────────
GET  /live/                     라이브방 목록 페이지
GET  /live/<room_id>            특정 방 입장 페이지

POST /api/live/create           방 생성
GET  /api/live/rooms            활성 방 목록
GET  /api/live/<room_id>        방 정보
POST /api/live/<room_id>/join   참여
POST /api/live/<room_id>/leave  나가기
POST /api/live/<room_id>/start  시작 (호스트)
POST /api/live/<room_id>/end    종료 (호스트)
POST /api/live/<room_id>/chat   채팅 전송
GET  /api/live/<room_id>/poll   폴링 (상태+메시지)
POST /api/live/<room_id>/transcript  음성 텍스트 저장
GET  /api/live/<room_id>/report      보고서 조회
"""
from flask import Blueprint, request, jsonify, render_template
from app.services.live_service import (
    create_room, get_room, get_active_rooms,
    join_room, leave_room, start_room, end_room,
    send_message, get_live_state, add_transcript,
)

live_bp = Blueprint("live", __name__)


# ── 페이지 라우트 ──────────────────────────────────────────────
@live_bp.route("/")
def live_index():
    rooms = get_active_rooms()
    return render_template("live.html", rooms=rooms, room=None, mode="lobby")


@live_bp.route("/<room_id>")
def live_room(room_id):
    room = get_room(room_id)
    if not room:
        return render_template("live.html", rooms=get_active_rooms(), room=None,
                               mode="lobby", error="방을 찾을 수 없습니다.")
    return render_template("live.html", rooms=get_active_rooms(), room=room, mode="room")


# ── 방 관리 API ───────────────────────────────────────────────
@live_bp.route("/api/create", methods=["POST"])
def api_create():
    data = request.get_json() or {}
    if not data.get("title", "").strip():
        return jsonify({"ok": False, "error": "방 제목을 입력해주세요."}), 400
    room = create_room(data.get("user_id", "user_demo"), data)
    return jsonify({"ok": True, "room": room}), 201


@live_bp.route("/api/rooms", methods=["GET"])
def api_rooms():
    club_id = request.args.get("club_id", "")
    rooms = get_active_rooms(club_id)
    return jsonify({"ok": True, "rooms": rooms, "count": len(rooms)})


@live_bp.route("/api/<room_id>", methods=["GET"])
def api_room(room_id):
    room = get_room(room_id)
    if not room:
        return jsonify({"ok": False, "error": "방을 찾을 수 없습니다."}), 404
    return jsonify({"ok": True, "room": room})


@live_bp.route("/api/<room_id>/join", methods=["POST"])
def api_join(room_id):
    data = request.get_json() or {}
    result = join_room(room_id, data.get("user_id", "user_demo"), data)
    return jsonify(result), (200 if result["ok"] else 400)


@live_bp.route("/api/<room_id>/leave", methods=["POST"])
def api_leave(room_id):
    data = request.get_json() or {}
    result = leave_room(room_id, data.get("user_id", "user_demo"))
    return jsonify(result)


@live_bp.route("/api/<room_id>/start", methods=["POST"])
def api_start(room_id):
    data = request.get_json() or {}
    result = start_room(room_id, data.get("user_id", "user_demo"))
    return jsonify(result), (200 if result["ok"] else 403)


@live_bp.route("/api/<room_id>/end", methods=["POST"])
def api_end(room_id):
    data = request.get_json() or {}
    result = end_room(room_id, data.get("user_id", "user_demo"))
    return jsonify(result), (200 if result["ok"] else 403)


# ── 채팅 & 폴링 ──────────────────────────────────────────────
@live_bp.route("/api/<room_id>/chat", methods=["POST"])
def api_chat(room_id):
    data = request.get_json() or {}
    if not (data.get("content") or "").strip():
        return jsonify({"ok": False, "error": "내용을 입력해주세요."}), 400
    result = send_message(room_id, data.get("user_id", "user_demo"), data)
    return jsonify(result), (200 if result["ok"] else 400)


@live_bp.route("/api/<room_id>/poll", methods=["GET"])
def api_poll(room_id):
    user_id   = request.args.get("user_id", "user_demo")
    after_idx = int(request.args.get("after", 0))
    result    = get_live_state(room_id, user_id, after_idx)
    return jsonify(result), (200 if result["ok"] else 404)


# ── 음성 텍스트 & 보고서 ──────────────────────────────────────
@live_bp.route("/api/<room_id>/transcript", methods=["POST"])
def api_transcript(room_id):
    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "텍스트가 없습니다."}), 400
    result = add_transcript(room_id, data.get("user_id", "user_demo"), text)
    return jsonify(result)


@live_bp.route("/api/<room_id>/report", methods=["GET"])
def api_report(room_id):
    room = get_room(room_id)
    if not room:
        return jsonify({"ok": False, "error": "방 없음"}), 404
    report = room.get("report")
    if not report:
        return jsonify({"ok": False, "error": "보고서가 아직 없습니다. 모임을 종료하면 자동 생성됩니다."}), 404
    return jsonify({"ok": True, "report": report})
