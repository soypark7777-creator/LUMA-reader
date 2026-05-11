"""
MySQL 회원 서비스 — ZIP 파일 member_service.py 기반
Flask + pymysql 연동, Firebase Mock과 병렬 사용 가능
"""
import hashlib, os, uuid
from datetime import datetime
from typing import Optional

_mysql_ok = False
_DB_CONFIG = {}

try:
    import pymysql
    from app.core.config import settings
    _DB_CONFIG = {
        "host":        getattr(settings, 'MYSQL_HOST', 'localhost'),
        "port":        int(getattr(settings, 'MYSQL_PORT', 3306)),
        "user":        getattr(settings, 'MYSQL_USER', 'root'),
        "password":    getattr(settings, 'MYSQL_PASSWORD', ''),
        "db":          getattr(settings, 'MYSQL_DB', 'book_club_db'),
        "charset":     "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit":  False,
    }
    # 연결 테스트
    _test = pymysql.connect(**_DB_CONFIG)
    _test.close()
    _mysql_ok = True
    print("[OK] MySQL connected")
except ImportError:
    print("[WARN] pymysql not installed -> MySQL disabled")
except Exception as e:
    print(f"[WARN] MySQL connection failed: {e} -> mock mode")


def connect_db():
    if not _mysql_ok:
        raise RuntimeError("MySQL이 연결되지 않았습니다.")
    import pymysql
    return pymysql.connect(**_DB_CONFIG)


def _hash_pw(pw: str) -> str:
    """SHA-256 해시 (bcrypt 없을 때)"""
    try:
        import bcrypt
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        return hashlib.sha256(pw.encode()).hexdigest()


def _verify_pw(pw: str, hashed: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ImportError:
        return hashlib.sha256(pw.encode()).hexdigest() == hashed


def init_tables() -> bool:
    """DB 테이블 자동 생성"""
    if not _mysql_ok: return False
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{_DB_CONFIG['db']}` CHARACTER SET utf8mb4")
            cur.execute(f"USE `{_DB_CONFIG['db']}`")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    id             INT AUTO_INCREMENT PRIMARY KEY,
                    username       VARCHAR(50)  NOT NULL,
                    email          VARCHAR(255) NULL,
                    password       VARCHAR(255) NULL,
                    phone          VARCHAR(30)  NULL,
                    age            INT          NULL,
                    region         VARCHAR(50)  NULL,
                    genre          VARCHAR(100) NULL,
                    post_count     INT          DEFAULT 0,
                    likes_received INT          DEFAULT 0,
                    role           VARCHAR(20)  NOT NULL DEFAULT 'member',
                    is_active      TINYINT(1)   NOT NULL DEFAULT 1,
                    join_date      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE INDEX uniq_email (email)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reading_books (
                    id               INT AUTO_INCREMENT PRIMARY KEY,
                    member_email     VARCHAR(255) NOT NULL,
                    title            VARCHAR(255) NOT NULL,
                    author           VARCHAR(255) NULL,
                    genre            VARCHAR(80)  NULL,
                    progress_percent INT          NOT NULL DEFAULT 0,
                    memo_count       INT          NOT NULL DEFAULT 0,
                    is_finished      TINYINT(1)   NOT NULL DEFAULT 0,
                    last_read_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_rb_email (member_email)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS memos_log (
                    id           INT AUTO_INCREMENT PRIMARY KEY,
                    member_email VARCHAR(255) NOT NULL,
                    book_title   VARCHAR(255) NULL,
                    content      TEXT         NOT NULL,
                    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_ml_email (member_email)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        conn.commit()
        print("[OK] MySQL tables initialized")
        return True
    except Exception as e:
        print(f"[MySQL 테이블 생성 오류] {e}")
        return False
    finally:
        conn.close()


def register_member(name: str, email: str, password: str,
                    phone: str = None, age: int = None,
                    region: str = None, genre: str = None) -> dict:
    if not _mysql_ok:
        return {"ok": False, "error": "MySQL이 연결되지 않았습니다."}
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM members WHERE email=%s", (email,))
            if cur.fetchone():
                return {"ok": False, "error": "이미 사용 중인 이메일입니다."}
            pw_hash = _hash_pw(password)
            cur.execute(
                "INSERT INTO members (username,email,password,phone,age,region,genre) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (name, email, pw_hash, phone, age, region, genre)
            )
            conn.commit()
            return {"ok": True, "member_id": cur.lastrowid, "email": email}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def login_member(email: str, password: str) -> dict:
    if not _mysql_ok:
        return {"ok": False, "error": "MySQL이 연결되지 않았습니다."}
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM members WHERE email=%s AND is_active=1", (email,))
            member = cur.fetchone()
            if not member:
                return {"ok": False, "error": "이메일 또는 비밀번호가 올바르지 않습니다."}
            if not _verify_pw(password, member['password'] or ''):
                return {"ok": False, "error": "이메일 또는 비밀번호가 올바르지 않습니다."}
            member.pop('password', None)
            return {"ok": True, "member": member}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def get_member_by_email(email: str) -> Optional[dict]:
    if not _mysql_ok: return None
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,username,email,phone,age,region,genre,role,is_active,created_at FROM members WHERE email=%s", (email,))
            return cur.fetchone()
    finally:
        conn.close()


def get_all_members(limit: int = 50) -> list:
    if not _mysql_ok: return []
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,username,email,age,region,genre,post_count,likes_received,role,is_active,created_at FROM members ORDER BY created_at DESC LIMIT %s", (limit,))
            return cur.fetchall()
    finally:
        conn.close()


def get_mysql_status() -> dict:
    return {"connected": _mysql_ok, "mode": "mysql" if _mysql_ok else "disabled"}
