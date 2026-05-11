from flask import Blueprint, request, jsonify, render_template
from app.services.club_service import (
    get_all_clubs, get_club, create_club, join_club,
    get_cards, create_card, toggle_like, add_comment,
    add_ai_card, save_report, get_latest_report,
)
from app.services.gemini_service import generate_discussion_guide, summarize_meeting

clubs_bp = Blueprint('clubs', __name__)

@clubs_bp.route('/')
def lounge_index():
    return render_template('lounge.html', clubs=get_all_clubs("user_demo"), active_club=None, active_cards=[])

@clubs_bp.route('/<club_id>')
def lounge_detail(club_id):
    club = get_club(club_id, "user_demo")
    if not club: return "모임을 찾을 수 없습니다.", 404
    return render_template('lounge.html', clubs=get_all_clubs("user_demo"), active_club=club, active_cards=get_cards(club_id))

@clubs_bp.route('/api/list', methods=['GET'])
def api_list_clubs():
    return jsonify({"ok":True,"clubs":get_all_clubs(request.args.get('user_id','user_demo'))})

@clubs_bp.route('/api/create', methods=['POST'])
def api_create_club():
    data = request.get_json()
    if not data.get('name','').strip(): return jsonify({"ok":False,"error":"모임 이름 필요"}), 400
    return jsonify({"ok":True,"club":create_club(data)}), 201

@clubs_bp.route('/api/<club_id>/join', methods=['POST'])
def api_join_club(club_id):
    data = request.get_json() or {}
    return jsonify(join_club(club_id, data.get('user_id','user_demo')))

@clubs_bp.route('/api/<club_id>/cards', methods=['GET'])
def api_get_cards(club_id):
    return jsonify({"ok":True,"cards":get_cards(club_id, int(request.args.get('limit',30)))})

@clubs_bp.route('/api/<club_id>/cards', methods=['POST'])
def api_create_card(club_id):
    data = request.get_json()
    if not (data.get('content') or '').strip(): return jsonify({"ok":False,"error":"내용 필요"}), 400
    return jsonify({"ok":True,"card":create_card(club_id, data)}), 201

@clubs_bp.route('/api/cards/<card_id>/like', methods=['POST'])
def api_toggle_like(card_id):
    data = request.get_json() or {}
    return jsonify(toggle_like(card_id, data.get('user_id','user_demo')))

@clubs_bp.route('/api/cards/<card_id>/comment', methods=['POST'])
def api_add_comment(card_id):
    data = request.get_json()
    if not (data.get('content') or '').strip(): return jsonify({"ok":False,"error":"댓글 내용 필요"}), 400
    return jsonify(add_comment(card_id, data))

@clubs_bp.route('/api/<club_id>/ai-guide', methods=['POST'])
def api_ai_guide(club_id):
    data = request.get_json() or {}
    club = get_club(club_id)
    if not club: return jsonify({"ok":False,"error":"모임 없음"}), 404
    guide = generate_discussion_guide(club.get('current_book_title',''), data.get('messages',[]), data.get('guide_type','debate'))
    card  = add_ai_card(club_id, guide['question'])
    return jsonify({"ok":True,"guide":guide,"card":card})

@clubs_bp.route('/api/<club_id>/report', methods=['POST'])
def api_generate_report(club_id):
    club = get_club(club_id)
    if not club: return jsonify({"ok":False,"error":"모임 없음"}), 404
    cards    = get_cards(club_id, 50)
    messages = [c['content'] for c in cards if not c['is_ai']]
    parts    = list({c['user_name'] for c in cards if not c['is_ai']})
    if len(messages) < 2: return jsonify({"ok":False,"error":"카드가 2개 이상 필요합니다."}), 400
    report = summarize_meeting(club['current_book_title'], messages, parts)
    return jsonify({"ok":True,"report":save_report(club_id, report)})

@clubs_bp.route('/api/<club_id>/report', methods=['GET'])
def api_get_report(club_id):
    r = get_latest_report(club_id)
    if not r: return jsonify({"ok":False,"error":"보고서 없음"}), 404
    return jsonify({"ok":True,"report":r})
