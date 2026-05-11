"""
인증 라우터
GET  /auth/login      로그인 페이지
GET  /auth/signup     회원가입 페이지
POST /auth/login      로그인 처리
POST /auth/signup     회원가입 처리
POST /auth/logout     로그아웃
GET  /auth/me         현재 사용자 정보
GET  /auth/check      이메일/닉네임 중복 확인
"""
from flask import (Blueprint, request, jsonify,
                   render_template, redirect, url_for, make_response)
from app.services.auth_service import (
    register, login, logout, get_current_user,
    check_email_available, check_username_available,
)

auth_bp = Blueprint('auth', __name__)
TOKEN_COOKIE = "luma_token"


def _get_token() -> str:
    return (request.cookies.get(TOKEN_COOKIE)
            or request.headers.get("Authorization", "").replace("Bearer ", ""))


# ── 페이지 라우트 ──────────────────────────────────────────────
@auth_bp.route('/login')
def login_page():
    if get_current_user(_get_token()):
        return redirect('/')
    return render_template('auth.html', mode='login')


@auth_bp.route('/signup')
def signup_page():
    if get_current_user(_get_token()):
        return redirect('/')
    return render_template('auth.html', mode='signup')


# ── API ────────────────────────────────────────────────────────
@auth_bp.route('/api/signup', methods=['POST'])
def api_signup():
    data         = request.get_json() or {}
    email        = (data.get('email')        or '').strip()
    password     = (data.get('password')     or '').strip()
    username     = (data.get('username')     or '').strip()
    display_name = (data.get('display_name') or username).strip()

    if not all([email, password, username]):
        return jsonify({"ok": False, "error": "이메일, 비밀번호, 닉네임은 필수입니다."}), 400

    result = register(email, password, username, display_name)

    if not result["ok"]:
        return jsonify(result), 400

    # 가입 후 자동 로그인
    login_result = login(email, password, remember_me=True)
    if not login_result["ok"]:
        return jsonify(result), 201

    resp = make_response(jsonify({
        "ok":   True,
        "user": login_result["user"],
        "redirect": "/",
    }), 201)
    resp.set_cookie(TOKEN_COOKIE, login_result["token"],
                    max_age=30*24*3600, httponly=True, samesite='Lax')
    return resp


@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    data        = request.get_json() or {}
    email       = (data.get('email')    or '').strip()
    password    = (data.get('password') or '').strip()
    remember_me = data.get('remember_me', False)

    if not email or not password:
        return jsonify({"ok": False, "error": "이메일과 비밀번호를 입력해주세요."}), 400

    result = login(email, password, remember_me)

    if not result["ok"]:
        return jsonify(result), 401

    resp = make_response(jsonify({
        "ok":       True,
        "user":     result["user"],
        "redirect": "/",
    }))
    max_age = 30*24*3600 if remember_me else 24*3600
    resp.set_cookie(TOKEN_COOKIE, result["token"],
                    max_age=max_age, httponly=True, samesite='Lax')
    return resp


@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    token  = _get_token()
    result = logout(token)
    resp   = make_response(jsonify({"ok": True, "redirect": "/landing"}))
    resp.delete_cookie(TOKEN_COOKIE)
    return resp


@auth_bp.route('/api/me', methods=['GET'])
def api_me():
    token = _get_token()
    user  = get_current_user(token)
    if not user:
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401
    return jsonify({"ok": True, "user": user})


@auth_bp.route('/api/check', methods=['GET'])
def api_check():
    """이메일/닉네임 중복 확인 (실시간 검증용)"""
    email    = request.args.get('email', '').strip().lower()
    username = request.args.get('username', '').strip()

    result = {}
    if email:
        result['email_available'] = check_email_available(email)
    if username:
        result['username_available'] = check_username_available(username)

    return jsonify({"ok": True, **result})


@auth_bp.route('/profile')
def profile_page():
    from flask import render_template
    return render_template('profile.html')
