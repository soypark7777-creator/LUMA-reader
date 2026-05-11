"""
STEP 8 — 사용자 인증 라우터 (MySQL 연동)
GET  /auth/             로그인/회원가입 페이지
POST /auth/api/signup   회원가입
POST /auth/api/login    로그인
GET  /auth/api/me       현재 사용자 정보
GET  /auth/api/status   DB 연결 상태
"""
from flask import Blueprint, request, jsonify, render_template, session
from app.services.mysql_service import (
    register_member, login_member, get_member_by_email,
    get_mysql_status, init_tables
)

auth_mysql_bp = Blueprint('auth_mysql', __name__)

# 인메모리 Mock 사용자 (MySQL 없을 때)
_MOCK_USERS = [
    {"id":1,"username":"데모 독서인","email":"demo@luma.kr","password":"demo1234","role":"member","is_active":1},
]

def _find_mock(email):
    return next((u for u in _MOCK_USERS if u['email']==email), None)


@auth_mysql_bp.route('/')
def auth_page():
    return render_template('auth.html')


@auth_mysql_bp.route('/api/status')
def api_status():
    st = get_mysql_status()
    return jsonify({"ok": True, "mysql": st["connected"], "mode": st["mode"]})


@auth_mysql_bp.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json() or {}
    name     = (data.get('name') or '').strip()
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password','')

    if not name:    return jsonify({"ok":False,"error":"이름을 입력해주세요."}), 400
    if not email:   return jsonify({"ok":False,"error":"이메일을 입력해주세요."}), 400
    if len(password) < 4: return jsonify({"ok":False,"error":"비밀번호는 4자 이상이어야 합니다."}), 400

    st = get_mysql_status()
    if st["connected"]:
        result = register_member(
            name=name, email=email, password=password,
            phone=data.get('phone'), age=data.get('age'),
            region=data.get('region'), genre=data.get('genre'),
        )
        return jsonify(result), 201 if result['ok'] else 400
    else:
        # Mock 모드
        if _find_mock(email):
            return jsonify({"ok":False,"error":"이미 사용 중인 이메일입니다."}), 400
        import hashlib
        _MOCK_USERS.append({
            "id": len(_MOCK_USERS)+1, "username": name, "email": email,
            "password": hashlib.sha256(password.encode()).hexdigest(),
            "role": "member", "is_active": 1,
        })
        return jsonify({"ok":True,"email":email,"mode":"mock"}), 201


@auth_mysql_bp.route('/api/login', methods=['POST'])
def api_login():
    data     = request.get_json() or {}
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password','')

    if not email or not password:
        return jsonify({"ok":False,"error":"이메일과 비밀번호를 입력해주세요."}), 400

    st = get_mysql_status()
    if st["connected"]:
        result = login_member(email, password)
    else:
        # Mock 모드
        import hashlib
        user = _find_mock(email)
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        if not user or (user['password'] != password and user['password'] != pw_hash):
            result = {"ok":False,"error":"이메일 또는 비밀번호가 올바르지 않습니다."}
        else:
            member = {k:v for k,v in user.items() if k != 'password'}
            result = {"ok":True,"member":member,"mode":"mock"}

    if result.get('ok'):
        session['user_email'] = email
        session['user_name']  = result.get('member',{}).get('username','')

    return jsonify(result), 200 if result.get('ok') else 401


@auth_mysql_bp.route('/api/me')
def api_me():
    email = session.get('user_email')
    if not email:
        return jsonify({"ok":False,"error":"로그인이 필요합니다."}), 401
    st = get_mysql_status()
    if st["connected"]:
        member = get_member_by_email(email)
        if member:
            return jsonify({"ok":True,"member":member})
    # Mock
    user = _find_mock(email)
    if user:
        return jsonify({"ok":True,"member":{k:v for k,v in user.items() if k!='password'},"mode":"mock"})
    return jsonify({"ok":False,"error":"사용자를 찾을 수 없습니다."}), 404


@auth_mysql_bp.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"ok":True,"message":"로그아웃되었습니다."})
