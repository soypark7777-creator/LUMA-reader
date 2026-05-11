"""
LUMA 인증 서비스
회원가입 / 로그인 / 세션 관리 / 로그아웃
bcrypt 해싱 + 안전한 세션 토큰
MySQL 없으면 인메모리 Mock으로 자동 폴백
"""
import hashlib
import os
import secrets
import re
from datetime import datetime, timedelta
from typing import Optional

# ── bcrypt (없으면 sha256 폴백) ────────────────────────────────
try:
    import bcrypt
    def _hash_pw(pw: str) -> str:
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(12)).decode()
    def _check_pw(pw: str, hashed: str) -> bool:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    print("[OK] bcrypt loaded")
except ImportError:
    import hmac
    def _hash_pw(pw: str) -> str:
        salt = secrets.token_hex(16)
        h = hmac.new(salt.encode(), pw.encode(), hashlib.sha256).hexdigest()
        return f"sha256${salt}${h}"
    def _check_pw(pw: str, hashed: str) -> bool:
        parts = hashed.split("$")
        if len(parts) != 3 or parts[0] != "sha256":
            return False
        salt = parts[1]
        h = hmac.new(salt.encode(), pw.encode(), hashlib.sha256).hexdigest()
        return secrets.compare_digest(h, parts[2])
    print("[WARN] bcrypt not installed -> SHA-256 dev mode")

# ── 인메모리 Mock 저장소 ────────────────────────────────────────
import uuid as _uuid

_users: dict[str, dict] = {}       # email → user dict
_sessions: dict[str, dict] = {}    # token → session dict
_users_by_id: dict[str, dict] = {} # user_id → user dict

# 데모 계정 사전 생성
_demo_id = "user-demo-0001"
_demo_pw_hash = _hash_pw("demo1234")
_demo_user = {
    "user_id":      _demo_id,
    "email":        "demo@luma.app",
    "password_hash":_demo_pw_hash,
    "username":     "lumademo",
    "display_name": "LUMA 데모",
    "bio":          "독서로 세상을 연결합니다 🌿",
    "avatar_emoji": "🌿",
    "avatar_url":   None,
    "reading_goal": 24,
    "streak_days":  12,
    "total_pages":  6840,
    "preferred_genres": ["철학", "과학", "소설"],
    "is_active":    True,
    "created_at":   datetime.now().isoformat(),
}
_users["demo@luma.app"] = _demo_user
_users_by_id[_demo_id] = _demo_user


# ══════════════════════════════════════════════════════════════
#  유효성 검사
# ══════════════════════════════════════════════════════════════
def _validate_email(email: str) -> bool:
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

def _validate_password(pw: str) -> tuple[bool, str]:
    if len(pw) < 8:
        return False, "비밀번호는 8자 이상이어야 합니다."
    if not re.search(r'[A-Za-z]', pw):
        return False, "영문자를 포함해야 합니다."
    if not re.search(r'[0-9]', pw):
        return False, "숫자를 포함해야 합니다."
    return True, ""

def _validate_username(name: str) -> tuple[bool, str]:
    if len(name) < 2:
        return False, "닉네임은 2자 이상이어야 합니다."
    if len(name) > 20:
        return False, "닉네임은 20자 이하여야 합니다."
    if not re.match(r'^[가-힣a-zA-Z0-9_]+$', name):
        return False, "닉네임은 한글, 영문, 숫자, _만 사용 가능합니다."
    return True, ""


# ══════════════════════════════════════════════════════════════
#  회원가입
# ══════════════════════════════════════════════════════════════
def register(email: str, password: str, username: str,
             display_name: str = "", reading_goal: int = 12) -> dict:
    """
    회원가입 처리
    반환: {"ok": True, "user": {...}} 또는 {"ok": False, "error": "..."}
    """
    email = email.strip().lower()
    username = username.strip()
    display_name = display_name.strip() or username

    # 유효성 검사
    if not _validate_email(email):
        return {"ok": False, "error": "올바른 이메일 형식이 아닙니다."}

    valid_pw, pw_err = _validate_password(password)
    if not valid_pw:
        return {"ok": False, "error": pw_err}

    valid_un, un_err = _validate_username(username)
    if not valid_un:
        return {"ok": False, "error": un_err}

    # 중복 확인
    if email in _users:
        return {"ok": False, "error": "이미 사용 중인 이메일입니다."}
    if any(u["username"] == username for u in _users.values()):
        return {"ok": False, "error": "이미 사용 중인 닉네임입니다."}

    # 계정 생성
    user_id = str(_uuid.uuid4())
    user = {
        "user_id":       user_id,
        "email":         email,
        "password_hash": _hash_pw(password),
        "username":      username,
        "display_name":  display_name,
        "bio":           "",
        "avatar_emoji":  "📚",
        "avatar_url":    None,
        "reading_goal":  reading_goal,
        "streak_days":   0,
        "total_pages":   0,
        "preferred_genres": [],
        "is_active":     True,
        "created_at":    datetime.now().isoformat(),
    }
    _users[email] = user
    _users_by_id[user_id] = user

    return {"ok": True, "user": _safe_user(user)}


# ══════════════════════════════════════════════════════════════
#  로그인
# ══════════════════════════════════════════════════════════════
def login(email: str, password: str,
          remember_me: bool = False) -> dict:
    """
    로그인 처리
    반환: {"ok": True, "token": "...", "user": {...}}
    """
    email = email.strip().lower()
    user = _users.get(email)

    if not user:
        return {"ok": False, "error": "이메일 또는 비밀번호가 올바르지 않습니다."}

    if not user.get("is_active", True):
        return {"ok": False, "error": "비활성화된 계정입니다."}

    if not _check_pw(password, user["password_hash"]):
        return {"ok": False, "error": "이메일 또는 비밀번호가 올바르지 않습니다."}

    # 세션 토큰 생성
    token = secrets.token_urlsafe(48)
    expires = datetime.now() + timedelta(days=30 if remember_me else 1)

    _sessions[token] = {
        "token":      token,
        "user_id":    user["user_id"],
        "expires_at": expires.isoformat(),
        "created_at": datetime.now().isoformat(),
    }

    return {"ok": True, "token": token, "user": _safe_user(user),
            "expires_at": expires.isoformat()}


# ══════════════════════════════════════════════════════════════
#  세션 검증
# ══════════════════════════════════════════════════════════════
def get_current_user(token: str) -> Optional[dict]:
    """토큰으로 현재 사용자 조회. 만료/없으면 None"""
    if not token:
        return None
    session = _sessions.get(token)
    if not session:
        return None
    expires = datetime.fromisoformat(session["expires_at"])
    if datetime.now() > expires:
        del _sessions[token]
        return None
    user = _users_by_id.get(session["user_id"])
    return _safe_user(user) if user else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    user = _users_by_id.get(user_id)
    return _safe_user(user) if user else None


# ══════════════════════════════════════════════════════════════
#  로그아웃
# ══════════════════════════════════════════════════════════════
def logout(token: str) -> dict:
    """세션 토큰 삭제"""
    if token in _sessions:
        del _sessions[token]
    return {"ok": True}


# ══════════════════════════════════════════════════════════════
#  유틸
# ══════════════════════════════════════════════════════════════
def _safe_user(user: dict) -> dict:
    """비밀번호 해시 제거한 안전한 사용자 객체"""
    if not user:
        return {}
    return {k: v for k, v in user.items() if k != "password_hash"}


def check_email_available(email: str) -> bool:
    return email.strip().lower() not in _users

def check_username_available(username: str) -> bool:
    return not any(u["username"] == username for u in _users.values())
