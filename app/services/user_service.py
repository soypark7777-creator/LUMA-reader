"""
LUMA — 회원 서비스 (MySQL + JWT)
──────────────────────────────────────────────────────
- 회원가입 / 로그인 / 로그아웃
- JWT 발급 및 검증
- 비밀번호 bcrypt 해시
- MySQL 없을 때 인메모리 Mock 자동 전환
"""
import hashlib
import json
import os
import uuid
from functools import wraps
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db import is_connected, get_db, execute_one, execute_write

# ── 인메모리 폴백 ────────────────────────────────────────
_users_mem: list[dict] = []


# ──────────────────────────────────────────────────────────
#  비밀번호
# ──────────────────────────────────────────────────────────
def _hash_pw(pw: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        return hashlib.sha256(pw.encode()).hexdigest()


def _check_pw(pw: str, hashed: str) -> bool:
    try:
        import bcrypt
        try:
            return bcrypt.checkpw(pw.encode(), hashed.encode())
        except Exception:
            return False
    except ImportError:
        return hashlib.sha256(pw.encode()).hexdigest() == hashed


# ──────────────────────────────────────────────────────────
#  JWT
# ──────────────────────────────────────────────────────────
def _secret() -> str:
    return os.getenv("SECRET_KEY", "luma-dev-secret")


def _expire_hours() -> int:
    return int(os.getenv("JWT_EXPIRE_HOURS", "24"))


def generate_token(user_id: str, email: str) -> str:
    try:
        import jwt
        payload = {
            "user_id": user_id,
            "email":   email,
            "exp":     datetime.now(timezone.utc) + timedelta(hours=_expire_hours()),
            "iat":     datetime.now(timezone.utc),
        }
        return jwt.encode(payload, _secret(), algorithm="HS256")
    except ImportError:
        # JWT 없으면 단순 토큰
        return f"mock_token_{user_id}_{int(datetime.now().timestamp())}"


def _decode_mock_token(token: str) -> Optional[dict]:
    if not token.startswith("mock_token_"):
        return None
    raw = token.removeprefix("mock_token_")
    user_id, _, _issued_at = raw.rpartition("_")
    if not user_id:
        return None
    return {"user_id": user_id, "email": ""}


def decode_token(token: str, verify_exp: bool = True) -> Optional[dict]:
    """JWT payload를 예외 없이 반환한다. 만료 검증 해제도 지원."""
    if not token:
        return None
    try:
        import jwt
        try:
            options = {} if verify_exp else {"verify_exp": False}
            return jwt.decode(token, _secret(), algorithms=["HS256"], options=options)
        except jwt.ExpiredSignatureError:
            try:
                return jwt.decode(
                    token,
                    _secret(),
                    algorithms=["HS256"],
                    options={"verify_exp": False},
                )
            except Exception:
                return None
        except Exception:
            return _decode_mock_token(token)
    except ImportError:
        return _decode_mock_token(token)


def verify_token(token: str) -> Optional[dict]:
    if not token:
        return None
    try:
        import jwt
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except Exception:
        return _decode_mock_token(token)


def token_status(token: str) -> tuple[str, Optional[dict]]:
    """라우터에서 만료/오염 토큰을 구분하기 위한 상태 확인."""
    if not token:
        return "missing", None
    try:
        import jwt
        payload = jwt.decode(token, _secret(), algorithms=["HS256"])
        return "ok", payload
    except ImportError:
        payload = _decode_mock_token(token)
        return ("ok", payload) if payload else ("invalid", None)
    except jwt.ExpiredSignatureError:
        payload = decode_token(token, verify_exp=False)
        return "expired", payload
    except Exception:
        payload = _decode_mock_token(token)
        return ("ok", payload) if payload else ("invalid", None)


def refresh_token(old_token: str) -> dict:
    """만료 1시간 이내 토큰이면 새 토큰을 발급한다."""
    status, payload = token_status(old_token)
    if status == "expired":
        return {"ok": False, "error": "토큰이 만료되었습니다.", "payload": payload}
    if status != "ok" or not payload:
        return {"ok": False, "error": "유효하지 않은 토큰입니다."}

    user_id = payload.get("user_id")
    email = payload.get("email", "")
    if not user_id:
        return {"ok": False, "error": "토큰에 사용자 정보가 없습니다."}

    exp = payload.get("exp")
    if not exp:
        return {"ok": True, "token": generate_token(user_id, email), "refreshed": True}

    exp_at = datetime.fromtimestamp(exp, timezone.utc)
    remaining = (exp_at - datetime.now(timezone.utc)).total_seconds()
    if remaining > 3600:
        return {"ok": True, "token": old_token, "refreshed": False}
    return {"ok": True, "token": generate_token(user_id, email), "refreshed": True}


def token_required(optional: bool = False):
    """Flask 라우트용 JWT 데코레이터. optional이면 user_demo 폴백 허용."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask import g, jsonify, request

            auth = request.headers.get("Authorization", "")
            token = auth[7:].strip() if auth.startswith("Bearer ") else ""
            if not token and optional:
                g.user_id = request.args.get("user_id", "user_demo")
                return fn(*args, **kwargs)
            if not token:
                return jsonify({"ok": False, "error": "인증 토큰이 필요합니다."}), 401

            status, payload = token_status(token)
            if status == "expired":
                return jsonify({"ok": False, "error": "토큰이 만료되었습니다."}), 401
            if status != "ok" or not payload:
                return jsonify({"ok": False, "error": "유효하지 않은 토큰입니다."}), 401

            g.user_id = payload.get("user_id", "user_demo")
            g.token_payload = payload
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ──────────────────────────────────────────────────────────
#  회원가입
# ──────────────────────────────────────────────────────────
def register(data: dict) -> dict:
    email        = (data.get("email") or "").strip().lower()
    display_name = (data.get("display_name") or "독서인").strip()
    password     = data.get("password", "")
    emoji        = data.get("emoji", "⭐")

    if not email or not password:
        return {"ok": False, "error": "이메일과 비밀번호를 입력하세요."}
    if len(password) < 4:
        return {"ok": False, "error": "비밀번호는 4자 이상이어야 합니다."}

    user_id   = str(uuid.uuid4())
    pw_hash   = _hash_pw(password)
    now       = datetime.now()

    if is_connected():
        # MySQL
        try:
            existing = execute_one("SELECT id FROM users WHERE email=%s", (email,))
            if existing:
                return {"ok": False, "error": "이미 사용 중인 이메일입니다."}
            execute_write(
                "INSERT INTO users(user_id,email,display_name,emoji,password_hash,created_at) "
                "VALUES(%s,%s,%s,%s,%s,%s)",
                (user_id, email, display_name, emoji, pw_hash, now)
            )
        except Exception as e:
            return {"ok": False, "error": f"DB 오류: {e}"}
    else:
        # Mock
        if any(u["email"] == email for u in _users_mem):
            return {"ok": False, "error": "이미 사용 중인 이메일입니다."}
        _users_mem.append({
            "user_id": user_id, "email": email,
            "display_name": display_name, "emoji": emoji,
            "password_hash": pw_hash, "created_at": now.isoformat(),
        })

    token = generate_token(user_id, email)
    return {
        "ok": True,
        "token": token,
        "user": {"user_id": user_id, "email": email, "display_name": display_name, "emoji": emoji},
    }


# ──────────────────────────────────────────────────────────
#  로그인
# ──────────────────────────────────────────────────────────
def login(email: str, password: str) -> dict:
    email = (email or "").strip().lower()
    if not email or not password:
        return {"ok": False, "error": "이메일과 비밀번호를 입력하세요."}

    if is_connected():
        try:
            user = execute_one(
                "SELECT user_id,email,display_name,emoji,password_hash FROM users WHERE email=%s",
                (email,)
            )
            if not user:
                return {"ok": False, "error": "이메일 또는 비밀번호가 올바르지 않습니다."}
            if not _check_pw(password, user["password_hash"]):
                return {"ok": False, "error": "이메일 또는 비밀번호가 올바르지 않습니다."}
            execute_write("UPDATE users SET last_login=%s WHERE email=%s", (datetime.now(), email))
        except Exception as e:
            return {"ok": False, "error": f"DB 오류: {e}"}
    else:
        user = next((u for u in _users_mem if u["email"] == email), None)
        if not user or not _check_pw(password, user["password_hash"]):
            return {"ok": False, "error": "이메일 또는 비밀번호가 올바르지 않습니다."}

    token = generate_token(user["user_id"], email)
    return {
        "ok": True,
        "token": token,
        "user": {
            "user_id":      user["user_id"],
            "email":        user["email"],
            "display_name": user["display_name"],
            "emoji":        user.get("emoji", "⭐"),
        },
    }


# ──────────────────────────────────────────────────────────
#  내 정보 조회
# ──────────────────────────────────────────────────────────
def get_me(user_id: str) -> Optional[dict]:
    if is_connected():
        try:
            row = execute_one(
                "SELECT user_id,email,display_name,emoji,bio,genre_prefs,created_at FROM users WHERE user_id=%s",
                (user_id,)
            )
            if row and row.get("genre_prefs"):
                try:
                    row["genre_prefs"] = json.loads(row["genre_prefs"])
                except Exception:
                    row["genre_prefs"] = []
            return row
        except Exception:
            return None
    return next((
        {k: v for k, v in u.items() if k != "password_hash"}
        for u in _users_mem if u["user_id"] == user_id
    ), None)


def update_profile(user_id: str, data: dict) -> dict:
    display_name = data.get("display_name", "").strip()
    bio          = data.get("bio", "")
    emoji        = data.get("emoji", "⭐")
    genre_prefs  = json.dumps(data.get("genre_prefs", []), ensure_ascii=False)

    if is_connected():
        try:
            execute_write(
                "UPDATE users SET display_name=%s, bio=%s, emoji=%s, genre_prefs=%s WHERE user_id=%s",
                (display_name, bio, emoji, genre_prefs, user_id)
            )
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    # Mock
    user = next((u for u in _users_mem if u["user_id"] == user_id), None)
    if user:
        user.update({"display_name": display_name, "bio": bio, "emoji": emoji})
    return {"ok": True}


def get_user_stats(user_id: str) -> dict:
    """프로필 페이지용 통계"""
    if not is_connected():
        return {"books_done": 2, "memos": 5, "emotions": 5, "connections": 3}
    try:
        r1 = execute_one(
            "SELECT COUNT(*) AS cnt FROM shelf_books WHERE user_id=%s AND status='done'", (user_id,))
        r2 = execute_one(
            "SELECT COUNT(*) AS cnt FROM memos WHERE user_id=%s", (user_id,))
        r3 = execute_one(
            "SELECT COUNT(*) AS cnt FROM emotions WHERE user_id=%s", (user_id,))
        r4 = execute_one(
            "SELECT COUNT(*) AS cnt FROM book_connections WHERE user_id=%s", (user_id,))
        return {
            "books_done":  (r1 or {}).get("cnt", 0),
            "memos":       (r2 or {}).get("cnt", 0),
            "emotions":    (r3 or {}).get("cnt", 0),
            "connections": (r4 or {}).get("cnt", 0),
        }
    except Exception:
        return {"books_done": 0, "memos": 0, "emotions": 0, "connections": 0}
