"""
LUMA — MySQL 연결 풀 관리
──────────────────────────────────────────────────────
- PyMySQL 기반 연결 풀
- MySQL 없을 때 Mock 모드 자동 전환
- context manager로 안전한 커밋/롤백
"""
import os
import time
import threading
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

# ── 연결 풀 상태 ────────────────────────────────────────
_pool: list  = []
_pool_lock   = threading.Lock()
_POOL_SIZE   = 5
_mysql_ok    = False
_DB_CONFIG: dict = {}


def _dotenv_paths() -> list[Path]:
    app_root = Path(__file__).resolve().parents[1]
    return [Path.cwd() / ".env", app_root / ".env", app_root.parent / ".env"]


def _load_config() -> dict:
    """Load DB settings after reading .env files."""
    try:
        from dotenv import load_dotenv
        for env_path in _dotenv_paths():
            if env_path.exists():
                load_dotenv(env_path, override=False)
    except ImportError:
        _parse_dotenv()

    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "db": os.getenv("MYSQL_DB", "luma_db"),
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
        "connect_timeout": 5,
        "autocommit": False,
    }


def _parse_dotenv():
    """Manual .env parser used when python-dotenv is unavailable."""
    for path in _dotenv_paths():
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v

def init_db() -> bool:
    """DB 초기화 — 앱 시작 시 한 번 호출"""
    global _mysql_ok, _DB_CONFIG
    try:
        import pymysql
        import pymysql.cursors
        _DB_CONFIG = _load_config()
        _DB_CONFIG["cursorclass"] = pymysql.cursors.DictCursor
    except ImportError:
        print("[WARN] PyMySQL 미설치 -> pip install PyMySQL")
        _mysql_ok = False
        return False

    host = _DB_CONFIG.get("host")
    port = _DB_CONFIG.get("port")
    db_name = _DB_CONFIG.get("db")
    last_error = None

    for attempt in range(1, 4):
        try:
            conn = pymysql.connect(**_DB_CONFIG)
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT VERSION() AS version")
                    row = cur.fetchone() or {}
                version = row.get("version", "unknown")
            finally:
                conn.close()

            _mysql_ok = True
            print(f"[OK] MySQL 연결 성공 -> {host}:{port}/{db_name} (version: {version})")
            return True
        except pymysql.err.OperationalError as e:
            last_error = e
            code = e.args[0] if e.args else None
            if code == 1049:
                try:
                    cfg = dict(_DB_CONFIG)
                    cfg.pop("db", None)
                    conn = pymysql.connect(**cfg)
                    try:
                        with conn.cursor() as cur:
                            cur.execute("SELECT VERSION() AS version")
                            row = cur.fetchone() or {}
                        version = row.get("version", "unknown")
                    finally:
                        conn.close()

                    _mysql_ok = True
                    print(
                        f"[OK] MySQL 서버 연결 성공 -> {host}:{port} "
                        f"(database `{db_name}` 생성 예정, version: {version})"
                    )
                    return True
                except Exception as server_error:
                    last_error = server_error
        except Exception as e:
            last_error = e

        print(f"[WARN] MySQL 연결 재시도 {attempt}/3 실패 -> {host}:{port}/{db_name}: {last_error}")
        if attempt < 3:
            time.sleep(1)

    if last_error:
        print(f"[WARN] MySQL 연결 실패 -> {host}:{port}/{db_name}: {last_error}")
        print("    Mock 모드로 실행합니다 (메모리 저장)")
    _mysql_ok = False
    return False


def is_connected() -> bool:
    return _mysql_ok


def _new_conn():
    """새 연결 생성"""
    import pymysql
    import pymysql.cursors
    cfg = dict(_DB_CONFIG)
    cfg["cursorclass"] = pymysql.cursors.DictCursor
    return pymysql.connect(**cfg)


@contextmanager
def get_db():
    """
    MySQL 연결 context manager
    
    사용법:
        with get_db() as db:
            db.execute("SELECT 1")
            rows = db.fetchall()
    
    커밋: context 종료 시 자동
    롤백: 예외 발생 시 자동
    """
    if not _mysql_ok:
        raise RuntimeError("MySQL이 연결되지 않았습니다. .env의 MYSQL_PASSWORD를 확인하세요.")

    conn = None
    try:
        conn = _new_conn()
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def execute_one(sql: str, params=None) -> Optional[dict]:
    """단일 행 조회"""
    with get_db() as db:
        db.execute(sql, params or ())
        return db.fetchone()


def execute_all(sql: str, params=None) -> list:
    """전체 행 조회"""
    with get_db() as db:
        db.execute(sql, params or ())
        return db.fetchall()


def execute_write(sql: str, params=None) -> int:
    """INSERT/UPDATE/DELETE → lastrowid 반환"""
    with get_db() as db:
        db.execute(sql, params or ())
        return db.lastrowid


def execute_many(sql: str, param_list: list) -> int:
    """executemany → 처리된 행 수"""
    with get_db() as db:
        db.executemany(sql, param_list)
        return db.rowcount
