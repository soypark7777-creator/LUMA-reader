"""Community v2 API routes.

Stable frontend contract under /api/v2/community:
- GET  /feed
- GET  /questions
- GET  /quotes
- GET  /trending-books
- POST /post
- POST /posts/<post_id>/like
- GET  /posts/<post_id>/comments
- POST /posts/<post_id>/comments
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request


community_api_bp = Blueprint("community_api", __name__)


@community_api_bp.route("/clubs", methods=["GET"])
def list_clubs_alias():
    """Compatibility alias for preflight and frontend club list checks."""
    from flask import jsonify, request

    user_id = request.args.get("user_id", "user_demo")
    try:
        from app.services import club_service

        for name in ("list_clubs", "get_clubs", "list_user_clubs", "get_user_clubs"):
            fn = getattr(club_service, name, None)
            if callable(fn):
                result = fn(user_id)
                if isinstance(result, dict):
                    return jsonify({"ok": True, **result})
                return jsonify({"ok": True, "clubs": result or []})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc), "source": "community_clubs_alias"}), 500
    return jsonify({"ok": True, "clubs": [], "source": "community_clubs_alias"})


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
    body = request.get_json(silent=True) or {}
    return request.args.get("user_id") or body.get("user_id") or "user_demo"


def _limit(default: int = 12, maximum: int = 50) -> int:
    try:
        value = int(request.args.get("limit", str(default)) or default)
    except ValueError:
        value = default
    return max(1, min(value, maximum))


def _page() -> int:
    try:
        value = int(request.args.get("page", "1") or 1)
    except ValueError:
        value = 1
    return max(1, value)


@community_api_bp.route("/feed", methods=["GET"])
def feed():
    from app.services.community_feed_service import get_feed

    result = get_feed(
        user_id=_uid(),
        page=_page(),
        limit=_limit(12, 50),
        tag=request.args.get("tag", "").strip(),
        q=request.args.get("q", "").strip(),
        emotion=request.args.get("emotion", "").strip(),
    )
    posts = result.get("posts") or result.get("cards") or []
    return jsonify(
        {
            "ok": bool(result.get("ok", True)),
            "feed": posts,
            "posts": posts,
            "cards": posts,
            "total": int(result.get("total") or len(posts)),
            "page": int(result.get("page") or _page()),
            "has_next": bool(result.get("has_next")),
            "source": result.get("source", "community_feed_service"),
            **({"error": result["error"]} if result.get("error") else {}),
        }
    )


@community_api_bp.route("/questions", methods=["GET"])
def questions():
    from app.services.community_feed_service import get_questions

    result = get_questions(user_id=_uid(), limit=_limit(12, 50))
    return jsonify(
        {
            "ok": bool(result.get("ok", True)),
            "questions": result.get("questions") or [],
            "source": result.get("source", "community_feed_service"),
            **({"error": result["error"]} if result.get("error") else {}),
        }
    )


@community_api_bp.route("/quotes", methods=["GET"])
def quotes():
    from app.services.community_feed_service import get_quotes

    result = get_quotes(user_id=_uid(), limit=_limit(12, 50))
    return jsonify(
        {
            "ok": bool(result.get("ok", True)),
            "quotes": result.get("quotes") or [],
            "source": result.get("source", "community_feed_service"),
            **({"error": result["error"]} if result.get("error") else {}),
        }
    )


@community_api_bp.route("/trending-books", methods=["GET"])
def trending_books():
    from app.services.community_feed_service import get_trending_books

    result = get_trending_books(user_id=_uid(), limit=_limit(12, 30))
    return jsonify(
        {
            "ok": bool(result.get("ok", True)),
            "books": result.get("books") or [],
            "source": result.get("source", "community_feed_service"),
            **({"error": result["error"]} if result.get("error") else {}),
        }
    )


@community_api_bp.route("/lounge-recruit", methods=["GET"])
def lounge_recruit():
    from app.services.community_feed_service import get_lounge_recruit

    result = get_lounge_recruit(user_id=_uid(), limit=_limit(8, 30))
    return jsonify(
        {
            "ok": bool(result.get("ok", True)),
            "recruits": result.get("recruits") or result.get("clubs") or [],
            "clubs": result.get("clubs") or result.get("recruits") or [],
            "source": result.get("source", "community_feed_service"),
            **({"error": result["error"]} if result.get("error") else {}),
        }
    )


@community_api_bp.route("/post", methods=["POST"])
@community_api_bp.route("/posts", methods=["POST"])
def create_post():
    data = request.get_json(silent=True) or {}
    from app.services.community_feed_service import create_post as create

    result = create(_uid(), data)
    return jsonify(result), 201 if result.get("ok") else 400


@community_api_bp.route("/posts/<path:post_id>/like", methods=["POST"])
@community_api_bp.route("/post/<path:post_id>/like", methods=["POST"])
def like_post(post_id: str):
    from app.services.community_feed_service import toggle_like

    result = toggle_like(post_id, _uid())
    return jsonify(result), 200 if result.get("ok") else 400


@community_api_bp.route("/posts/<path:post_id>/save", methods=["POST"])
@community_api_bp.route("/post/<path:post_id>/save", methods=["POST"])
def save_post(post_id: str):
    from app.services.community_feed_service import toggle_save

    result = toggle_save(post_id, _uid())
    return jsonify(result), 200 if result.get("ok") else 400


@community_api_bp.route("/posts/<path:post_id>/comments", methods=["GET"])
@community_api_bp.route("/post/<path:post_id>/comments", methods=["GET"])
def list_comments(post_id: str):
    from app.services.community_feed_service import get_comments

    comments = get_comments(post_id, _limit(50, 100))
    return jsonify({"ok": True, "comments": comments, "count": len(comments)})


@community_api_bp.route("/posts/<path:post_id>/comments", methods=["POST"])
@community_api_bp.route("/post/<path:post_id>/comments", methods=["POST"])
def create_comment(post_id: str):
    data = request.get_json(silent=True) or {}
    if not (data.get("content") or data.get("text") or "").strip():
        return jsonify({"ok": False, "error": "댓글 내용을 입력하세요."}), 400
    from app.services.community_feed_service import add_comment

    result = add_comment(post_id, data, _uid())
    return jsonify(result), 201 if result.get("ok") else 400


@community_api_bp.route("/clubs", methods=["POST"])
def create_club():
    data = request.get_json(silent=True) or {}
    if not (data.get("name") or "").strip():
        return jsonify({"ok": False, "error": "모임방 이름을 입력하세요."}), 400
    from app.services.club_service import create_club as create

    data.setdefault("user_id", _uid())
    club = create(data)
    return jsonify({"ok": True, "club": club, "club_id": club.get("club_id")}), 201


@community_api_bp.route("/clubs/<path:club_id>/join", methods=["POST"])
def join_club(club_id: str):
    from app.services.club_service import join_club as join

    return jsonify(join(club_id, _uid()))


@community_api_bp.route("/clubs/<path:club_id>/cards", methods=["POST"])
def create_club_card(club_id: str):
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "내용을 입력하세요."}), 400
    from app.services.club_service import create_card

    data.setdefault("user_id", _uid())
    card = create_card(club_id, data)
    return jsonify({"ok": True, "card": card, "card_id": card.get("card_id")}), 201


@community_api_bp.route("/cards/<path:card_id>/like", methods=["POST"])
def like_card(card_id: str):
    from app.services.club_service import toggle_like as toggle_card_like

    return jsonify(toggle_card_like(card_id, _uid()))


@community_api_bp.route("/cards/<path:card_id>/comment", methods=["POST"])
def comment_card(card_id: str):
    data = request.get_json(silent=True) or {}
    if not (data.get("content") or "").strip():
        return jsonify({"ok": False, "error": "댓글 내용을 입력하세요."}), 400
    from app.services.club_service import add_comment as add_card_comment

    data.setdefault("user_id", _uid())
    return jsonify(add_card_comment(card_id, data))


@community_api_bp.route("/clubs/<path:club_id>/settings", methods=["POST"])
def update_club_settings(club_id: str):
    data = request.get_json(silent=True) or {}
    from app.services.club_service import get_club, update_club_settings as update_settings

    if not get_club(club_id):
        return jsonify({"ok": False, "error": "모임을 찾을 수 없습니다."}), 404
    return jsonify(update_settings(club_id, data))


@community_api_bp.route("/clubs/<path:club_id>", methods=["DELETE"])
def delete_club(club_id: str):
    from app.services.club_service import delete_club as delete

    result = delete(club_id, _uid())
    return jsonify(result), 200 if result.get("ok") else 404


@community_api_bp.route("/clubs/<path:club_id>/ai-guide", methods=["POST"])
def club_ai_guide(club_id: str):
    data = request.get_json(silent=True) or {}
    from app.services.club_service import add_ai_card, get_club
    from app.services.gemini_service import generate_discussion_guide

    club = get_club(club_id)
    if not club:
        return jsonify({"ok": False, "error": "모임을 찾을 수 없습니다."}), 404
    guide = generate_discussion_guide(
        club.get("current_book_title", ""),
        data.get("messages", []),
        data.get("guide_type", "debate"),
    )
    card = add_ai_card(club_id, guide["question"])
    return jsonify({"ok": True, "guide": guide, "card": card})


@community_api_bp.route("/clubs/<path:club_id>/report", methods=["POST"])
def create_club_report(club_id: str):
    from app.services.club_service import get_cards, get_club, save_report
    from app.services.gemini_service import summarize_meeting

    club = get_club(club_id)
    if not club:
        return jsonify({"ok": False, "error": "모임을 찾을 수 없습니다."}), 404
    cards = get_cards(club_id, 50)
    messages = [c["content"] for c in cards if not c.get("is_ai")]
    parts = list({c.get("user_name", "독자") for c in cards if not c.get("is_ai")})
    if len(messages) < 2:
        return jsonify({"ok": False, "error": "카드가 2개 이상 필요합니다."}), 400
    report = summarize_meeting(club.get("current_book_title", ""), messages, parts)
    return jsonify({"ok": True, "report": save_report(club_id, report)})


@community_api_bp.route("/clubs/<path:club_id>/report", methods=["GET"])
def get_club_report(club_id: str):
    from app.services.club_service import get_latest_report

    report = get_latest_report(club_id)
    if not report:
        return jsonify({"ok": False, "error": "보고서가 없습니다."}), 404
    return jsonify({"ok": True, "report": report})
