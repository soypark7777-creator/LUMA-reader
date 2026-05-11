"""
공독의 장 + 독서 지도 통합 라우터
GET  /community/            메인 페이지
GET  /community/<club_id>   특정 모임 라운지
POST /community/api/create  모임 생성
POST /community/api/<club_id>/cards      카드 작성
POST /community/api/cards/<id>/like      좋아요
POST /community/api/cards/<id>/comment   댓글
POST /community/api/<club_id>/ai-guide   AI 가이드
POST /community/api/<club_id>/report     보고서 생성
"""
import json
import os
from flask import Blueprint, request, jsonify, render_template
from app.services.club_service import (
    get_all_clubs, get_club, create_club, join_club,
    get_cards, create_card, toggle_like, add_comment,
    add_ai_card, save_report, get_latest_report,
)
from app.services.place_service import get_all_spots, get_cities
from app.services.gemini_service import generate_discussion_guide, summarize_meeting

community_bp = Blueprint('community', __name__)


def _render(club_id=None):
    """통합 페이지 렌더링 헬퍼"""
    clubs       = get_all_clubs("user_demo")
    active_club = get_club(club_id, "user_demo") if club_id else None
    active_cards= get_cards(club_id) if club_id else []
    spots       = get_all_spots(limit=50)
    cities      = get_cities()
    spots_json  = json.dumps(spots, ensure_ascii=False)
    maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    return render_template(
        'community.html',
        clubs=clubs,
        active_club=active_club,
        active_cards=active_cards,
        spots=spots,
        spots_json=spots_json,
        cities=cities,
        maps_api_key=maps_api_key,
    )


# ── 페이지 라우트 ──────────────────────────────────────────────
@community_bp.route('/')
def index():
    return _render(request.args.get("club"))


@community_bp.route('/<club_id>')
def club_detail(club_id):
    return _render(club_id)


# ── 모임 API ───────────────────────────────────────────────────
@community_bp.route('/api/create', methods=['POST'])
def api_create_club():
    data = request.get_json() or {}
    if not data.get('name', '').strip():
        return jsonify({"ok": False, "error": "모임 이름을 입력해주세요."}), 400
    club = create_club(data)
    return jsonify({"ok": True, "club": club, "club_id": club.get("club_id")}), 201


@community_bp.route('/api/<club_id>/join', methods=['POST'])
def api_join(club_id):
    data = request.get_json() or {}
    return jsonify(join_club(club_id, data.get('user_id', 'user_demo')))


# ── 카드 API ───────────────────────────────────────────────────
@community_bp.route('/api/<club_id>/cards', methods=['POST'])
def api_create_card(club_id):
    data    = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({"ok": False, "error": "내용을 입력해주세요."}), 400
    card = create_card(club_id, data)
    return jsonify({"ok": True, "card": card, "card_id": card.get("card_id")}), 201


@community_bp.route('/api/<club_id>/settings', methods=['POST'])
def api_update_settings(club_id):
    data = request.get_json() or {}
    club = get_club(club_id)
    if not club:
        return jsonify({"ok": False, "error": "모임을 찾을 수 없습니다."}), 404
    from app.services.club_service import update_club_settings
    return jsonify(update_club_settings(club_id, data))


@community_bp.route('/api/cards/<card_id>/like', methods=['POST'])
def api_like(card_id):
    data = request.get_json() or {}
    return jsonify(toggle_like(card_id, data.get('user_id', 'user_demo')))


@community_bp.route('/api/cards/<card_id>/comment', methods=['POST'])
def api_comment(card_id):
    data    = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({"ok": False, "error": "댓글 내용을 입력해주세요."}), 400
    return jsonify(add_comment(card_id, data))


# ── AI API ─────────────────────────────────────────────────────
@community_bp.route('/api/<club_id>/ai-guide', methods=['POST'])
def api_ai_guide(club_id):
    data  = request.get_json() or {}
    club  = get_club(club_id)
    if not club:
        return jsonify({"ok": False, "error": "모임을 찾을 수 없습니다."}), 404
    guide = generate_discussion_guide(
        club.get('current_book_title', ''),
        data.get('messages', []),
        data.get('guide_type', 'debate'),
    )
    card = add_ai_card(club_id, guide['question'])
    return jsonify({"ok": True, "guide": guide, "card": card})


@community_bp.route('/api/<club_id>/report', methods=['POST'])
def api_report(club_id):
    club = get_club(club_id)
    if not club:
        return jsonify({"ok": False, "error": "모임을 찾을 수 없습니다."}), 404
    cards    = get_cards(club_id, 50)
    messages = [c['content'] for c in cards if not c['is_ai']]
    parts    = list({c['user_name'] for c in cards if not c['is_ai']})
    if len(messages) < 2:
        return jsonify({"ok": False, "error": "카드가 2개 이상 필요합니다."}), 400
    report = summarize_meeting(club['current_book_title'], messages, parts)
    return jsonify({"ok": True, "report": save_report(club_id, report)})


@community_bp.route('/api/<club_id>/report', methods=['GET'])
def api_get_report(club_id):
    r = get_latest_report(club_id)
    if not r:
        return jsonify({"ok": False, "error": "보고서가 없습니다."}), 404
    return jsonify({"ok": True, "report": r})
