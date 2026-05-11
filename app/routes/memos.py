"""
메모 호환 API 라우터
────────────────────────────────────────
기존 /api/memos/* 호출도 MySQL 기반 /api/v2/memos와 같은 저장소를 사용한다.
"""
from flask import Blueprint, request, jsonify

memos_bp = Blueprint("memos", __name__)


def _uid() -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.services.user_service import verify_token
            payload = verify_token(auth[7:])
            if payload:
                return payload.get("user_id", "user_demo")
        except Exception:
            pass
    data = request.get_json(silent=True) or {}
    return request.args.get("user_id") or data.get("user_id") or "user_demo"


@memos_bp.route("/save", methods=["POST"])
def api_save_memo():
    data = request.get_json() or {}
    if data.get("page_number") and not data.get("page_num"):
        data["page_num"] = data.get("page_number")
    from app.services.reading_service import save_memo
    result = save_memo(_uid(), data)
    return jsonify(result), 201 if result.get("ok") else 400


@memos_bp.route("/list", methods=["GET"])
def api_list_memos():
    user_id = _uid()
    book_id = request.args.get("book_id")
    limit = int(request.args.get("limit", 20))
    from app.services.reading_service import list_memos
    result = list_memos(user_id, book_id, limit)
    result["count"] = result.get("total", len(result.get("memos", [])))
    return jsonify(result)


@memos_bp.route("/<memo_id>", methods=["PUT"])
def api_update_memo(memo_id):
    data = request.get_json() or {}
    if data.get("page_number") and not data.get("page_num"):
        data["page_num"] = data.get("page_number")
    from app.services.reading_service import update_memo
    result = update_memo(_uid(), memo_id, data)
    return jsonify(result), 200 if result.get("ok") else 404


@memos_bp.route("/<memo_id>", methods=["DELETE"])
def api_delete_memo(memo_id):
    from app.services.reading_service import delete_memo
    result = delete_memo(_uid(), memo_id)
    return jsonify(result), 200 if result.get("ok") else 404


@memos_bp.route("/stats", methods=["GET"])
def api_get_stats():
    from app.services.reading_service import get_memo_stats
    result = get_memo_stats(_uid())
    return jsonify({"ok": True, "stats": {"total_memos": result.get("total", 0)}, **result})
