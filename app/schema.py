"""
LUMA — MySQL 스키마 DDL
──────────────────────────────────────────────────────
테이블 11개:
  users              회원 정보
  books              책 마스터 데이터
  shelf_books        유저별 서재 (책 상태·진행률)
  emotions           감정 타임라인
  book_connections   별자리 연결
  memos              독서 메모
  live_rooms         라이브 독서방
  live_messages      채팅 메시지
  socrates_sessions  소크라테스 세션
  my_dictionary      나만의 지식 사전
  action_plans       실천 액션 플랜

실행:
  from app.schema import create_all_tables
  create_all_tables()
"""
import json
import re

from app.db import get_db, is_connected


def _quote_identifier(name: str) -> str:
    """MySQL 식별자용 안전한 백틱 quoting."""
    if not re.fullmatch(r"[A-Za-z0-9_]+", name or ""):
        raise ValueError("허용되지 않는 DB 식별자입니다.")
    return "`" + name.replace("`", "``") + "`"

# ── DDL ─────────────────────────────────────────────
TABLES = {

"users": """
CREATE TABLE IF NOT EXISTS users (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id      VARCHAR(36)  NOT NULL UNIQUE,          -- UUID
    email        VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL DEFAULT '독서인',
    emoji        VARCHAR(10)  NOT NULL DEFAULT '⭐',
    password_hash VARCHAR(255) NOT NULL,
    bio          TEXT,
    genre_prefs  VARCHAR(500),                          -- JSON 배열
    role         ENUM('user','admin') DEFAULT 'user',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login   DATETIME,
    INDEX idx_email (email),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"books": """
CREATE TABLE IF NOT EXISTS books (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    book_id      VARCHAR(36)  NOT NULL UNIQUE,
    title        VARCHAR(300) NOT NULL,
    author       VARCHAR(200),
    publisher    VARCHAR(200),
    isbn         VARCHAR(20),
    cover_emoji  VARCHAR(10)  DEFAULT '📚',
    cover_url    TEXT,
    genre        VARCHAR(100),
    total_pages  INT DEFAULT 0,
    pub_year     YEAR,
    description  TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_book_id (book_id),
    INDEX idx_title (title(50)),
    FULLTEXT idx_ft_title (title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"shelf_books": """
CREATE TABLE IF NOT EXISTS shelf_books (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    shelf_id     VARCHAR(36)  NOT NULL UNIQUE,
    user_id      VARCHAR(36)  NOT NULL,
    book_id      VARCHAR(36)  NOT NULL,
    status       ENUM('want','reading','done') DEFAULT 'want',
    progress     TINYINT UNSIGNED DEFAULT 0,             -- 0~100%
    rating       TINYINT UNSIGNED,                       -- 1~5
    started_at   DATE,
    finished_at  DATE,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_book (user_id, book_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status  (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"emotions": """
CREATE TABLE IF NOT EXISTS emotions (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    emotion_id   VARCHAR(36)  NOT NULL UNIQUE,
    user_id      VARCHAR(36)  NOT NULL,
    book_id      VARCHAR(36)  NOT NULL,
    emotion_type ENUM('inspired','curious','sad','surprised','peaceful','excited') NOT NULL,
    intensity    TINYINT UNSIGNED NOT NULL DEFAULT 3,    -- 1~5
    note         TEXT,
    page_num     INT,
    recorded_at  DATE        NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id  (user_id),
    INDEX idx_book_id  (user_id, book_id),
    INDEX idx_date     (user_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"book_connections": """
CREATE TABLE IF NOT EXISTS book_connections (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conn_id      VARCHAR(36)  NOT NULL UNIQUE,
    user_id      VARCHAR(36)  NOT NULL,
    book_id_a    VARCHAR(36)  NOT NULL,
    book_id_b    VARCHAR(36)  NOT NULL,
    theme        VARCHAR(300),
    note         TEXT,
    strength     DECIMAL(3,2) DEFAULT 0.50,             -- 0.00~1.00
    auto_created TINYINT(1)   DEFAULT 0,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_conn (user_id, book_id_a, book_id_b),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"memos": """
CREATE TABLE IF NOT EXISTS memos (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    memo_id      VARCHAR(36)  NOT NULL UNIQUE,
    user_id      VARCHAR(36)  NOT NULL,
    book_id      VARCHAR(36),
    content      TEXT         NOT NULL,
    tags         VARCHAR(500),
    is_public    TINYINT(1) NOT NULL DEFAULT 0,                           -- JSON 배열
    source       ENUM('manual','ocr','voice','ai') DEFAULT 'manual',
    page_num     INT,
    ai_keywords  TEXT,                                   -- AI 추출 키워드 JSON
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_book_id (user_id, book_id),
    INDEX idx_public_created (is_public, created_at),
    FULLTEXT idx_ft_content (content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"live_rooms": """
CREATE TABLE IF NOT EXISTS live_rooms (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    room_id      VARCHAR(36)  NOT NULL UNIQUE,
    title        VARCHAR(200) NOT NULL,
    book_title   VARCHAR(300),
    book_author  VARCHAR(200),
    host_id      VARCHAR(36)  NOT NULL,
    max_members  TINYINT UNSIGNED DEFAULT 8,
    status       ENUM('waiting','live','ended') DEFAULT 'waiting',
    is_private   TINYINT(1)   DEFAULT 0,
    password_hash VARCHAR(255),
    discussion_topic VARCHAR(500),
    keywords     TEXT,                                   -- JSON 배열
    ai_report    LONGTEXT,                               -- JSON 보고서
    started_at   DATETIME,
    ended_at     DATETIME,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_host   (host_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"live_members": """
CREATE TABLE IF NOT EXISTS live_members (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    room_id      VARCHAR(36)  NOT NULL,
    user_id      VARCHAR(36)  NOT NULL,
    peer_id      VARCHAR(36)  NOT NULL UNIQUE,
    display_name VARCHAR(100),
    emoji        VARCHAR(10)  DEFAULT '⭐',
    is_host      TINYINT(1)   DEFAULT 0,
    joined_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    left_at      DATETIME,
    INDEX idx_room (room_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"live_messages": """
CREATE TABLE IF NOT EXISTS live_messages (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    msg_id       VARCHAR(36)  NOT NULL UNIQUE,
    room_id      VARCHAR(36)  NOT NULL,
    peer_id      VARCHAR(36),
    display_name VARCHAR(100),
    emoji        VARCHAR(10)  DEFAULT '⭐',
    content      TEXT         NOT NULL,
    msg_type     ENUM('chat','quote','system','keyword') DEFAULT 'chat',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_room (room_id),
    INDEX idx_created (room_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"socrates_sessions": """
CREATE TABLE IF NOT EXISTS socrates_sessions (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id   VARCHAR(36)  NOT NULL UNIQUE,
    user_id      VARCHAR(36)  NOT NULL,
    book_title   VARCHAR(300),
    passage      TEXT         NOT NULL,
    stage        TINYINT UNSIGNED DEFAULT 0,             -- 0~5
    total_stages TINYINT UNSIGNED DEFAULT 5,
    exchanges    LONGTEXT,                               -- JSON [{q,a,stage}]
    final_insight TEXT,                                  -- JSON
    completed    TINYINT(1)   DEFAULT 0,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"my_dictionary": """
CREATE TABLE IF NOT EXISTS my_dictionary (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    entry_id      VARCHAR(36)  NOT NULL UNIQUE,
    user_id       VARCHAR(36)  NOT NULL,
    concept       VARCHAR(200) NOT NULL,
    my_definition TEXT,
    core_words    VARCHAR(500),                          -- JSON 배열
    opposite      VARCHAR(200),
    personal_note TEXT,
    quote_to_live VARCHAR(500),
    sources       TEXT,                                  -- JSON [{book,text}]
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_concept (user_id, concept(50))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"action_plans": """
CREATE TABLE IF NOT EXISTS action_plans (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    plan_id      VARCHAR(36)  NOT NULL UNIQUE,
    user_id      VARCHAR(36)  NOT NULL,
    book_title   VARCHAR(300),
    insight      TEXT,
    summary      VARCHAR(500),
    today_action TEXT,
    week_action  TEXT,
    month_action TEXT,
    mindset      TEXT,
    checked_in   TINYINT(1)   DEFAULT 0,
    checkin_note TEXT,
    checkin_at   DATETIME,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"feed_cards": """
CREATE TABLE IF NOT EXISTS feed_cards (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    card_id      VARCHAR(36)  NOT NULL UNIQUE,
    user_id      VARCHAR(36)  NOT NULL,
    display_name VARCHAR(100),
    user_emoji   VARCHAR(10)  DEFAULT '⭐',
    book_title   VARCHAR(300),
    author       VARCHAR(200),
    passage      TEXT         NOT NULL,
    thought      TEXT,
    emotion      ENUM('inspired','curious','sad','surprised','peaceful','excited') DEFAULT 'inspired',
    tags         VARCHAR(500),                           -- JSON 배열
    card_style   ENUM('dark','warm','cosmic','forest','pure') DEFAULT 'dark',
    likes        INT UNSIGNED DEFAULT 0,
    comments_cnt INT UNSIGNED DEFAULT 0,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"feed_likes": """
CREATE TABLE IF NOT EXISTS feed_likes (
    id       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    card_id  VARCHAR(36) NOT NULL,
    user_id  VARCHAR(36) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_like (card_id, user_id),
    INDEX idx_card (card_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"feed_comments": """
CREATE TABLE IF NOT EXISTS feed_comments (
    id           BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    comment_id   VARCHAR(36)  NOT NULL UNIQUE,
    card_id      VARCHAR(36)  NOT NULL,
    user_id      VARCHAR(36)  NOT NULL,
    display_name VARCHAR(100),
    emoji        VARCHAR(10)  DEFAULT '⭐',
    content      TEXT         NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_card_id (card_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"reading_places": """
CREATE TABLE IF NOT EXISTS reading_places (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    place_id VARCHAR(36) NOT NULL UNIQUE,
    google_place_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    address VARCHAR(500),
    lat DECIMAL(10,7) NOT NULL,
    lng DECIMAL(10,7) NOT NULL,
    phone VARCHAR(100),
    website TEXT,
    google_rating DECIMAL(3,2),
    price_level TINYINT,
    open_now TINYINT(1),
    opening_hours TEXT,
    photo_reference TEXT,
    photo_url TEXT,
    place_types VARCHAR(500),
    source ENUM('google','manual','mock') DEFAULT 'google',
    reading_score DECIMAL(3,1) DEFAULT 0,
    meeting_capacity TINYINT,
    noise_level ENUM('quiet','moderate','lively','unknown') DEFAULT 'unknown',
    outlet_score TINYINT,
    wifi_score TINYINT,
    reservation_url TEXT,
    memo TEXT,
    created_by VARCHAR(36) DEFAULT 'user_demo',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_google_place_id (google_place_id),
    INDEX idx_location (lat, lng),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",

"reading_place_reviews": """
CREATE TABLE IF NOT EXISTS reading_place_reviews (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    review_id VARCHAR(36) NOT NULL UNIQUE,
    place_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    display_name VARCHAR(100),
    emoji VARCHAR(10) DEFAULT '⭐',
    rating TINYINT,
    noise_level ENUM('quiet','moderate','lively','unknown') DEFAULT 'unknown',
    group_size TINYINT,
    visit_purpose VARCHAR(100),
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_place_id (place_id),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""",
}


def create_database():
    """DB 없으면 먼저 생성"""
    import pymysql
    from app.db import _DB_CONFIG
    cfg = dict(_DB_CONFIG)
    db_name = cfg.pop("db", "luma_db")
    db_ident = _quote_identifier(db_name)
    cfg.pop("cursorclass", None)

    conn = pymysql.connect(**cfg)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE DATABASE IF NOT EXISTS "
                + db_ident
                + " CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"[OK] 데이터베이스 `{db_name}` 준비 완료")
    finally:
        conn.close()


def create_all_tables():
    """모든 테이블 생성 (IF NOT EXISTS — 안전)"""
    if not is_connected():
        print("[WARN] MySQL 미연결 -> 테이블 생성 건너뜀")
        return False

    ok = err = 0
    for name, ddl in TABLES.items():
        try:
            with get_db() as cur:
                cur.execute(ddl)
            print(f"  [OK] {name}")
            ok += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            err += 1

    ensure_memo_public_columns()

    print(f"\n테이블 생성 완료: {ok}개 성공, {err}개 실패")
    return err == 0



def ensure_memo_public_columns():
    """Add memos.is_public and its feed index to existing databases."""
    if not is_connected():
        return False
    try:
        with get_db() as cur:
            cur.execute("SHOW COLUMNS FROM memos LIKE 'is_public'")
            exists = cur.fetchone()
        if not exists:
            with get_db() as cur:
                cur.execute("ALTER TABLE memos ADD COLUMN is_public TINYINT(1) NOT NULL DEFAULT 0 AFTER tags")
    except Exception as e:
        print(f"  [WARN] memos.is_public migration skipped: {e}")
        return False
    try:
        with get_db() as cur:
            cur.execute("SHOW INDEX FROM memos WHERE Key_name='idx_public_created'")
            exists = cur.fetchone()
        if not exists:
            with get_db() as cur:
                cur.execute("CREATE INDEX idx_public_created ON memos (is_public, created_at)")
    except Exception as e:
        print(f"  [WARN] memos.idx_public_created migration skipped: {e}")
    return True

def seed_data():
    """개발/시연용 기본 데이터 입력 (중복 안전)."""
    if not is_connected():
        print("[WARN] MySQL 미연결 -> 시드 데이터 건너뜀")
        return False

    try:
        from app.services.user_service import _hash_pw

        demo_user = {
            "user_id": "user_demo",
            "email": "demo@luma.kr",
            "display_name": "소연",
            "emoji": "🦋",
            "password_hash": _hash_pw("demo1234"),
            "genre_prefs": json.dumps(["인문", "문학", "과학"], ensure_ascii=False),
        }
        books = [
            ("book_sapiens", "사피엔스", "유발 하라리", "🧬", "인문", 636),
            ("book_prince", "어린왕자", "생텍쥐페리", "🌹", "문학", 160),
            ("book_cosmos", "코스모스", "칼 세이건", "🌌", "과학", 719),
        ]
        shelf_books = [
            ("sh_demo_001", "user_demo", "book_sapiens", "done", 100, 5, "2026-01-05", "2026-01-25"),
            ("sh_demo_002", "user_demo", "book_prince", "done", 100, 5, "2026-02-01", "2026-02-03"),
            ("sh_demo_003", "user_demo", "book_cosmos", "reading", 62, None, "2026-03-10", None),
        ]
        memos = [
            (
                "memo_demo_001",
                "user_demo",
                "book_sapiens",
                "허구를 함께 믿는 능력이 인류를 거대한 규모로 협력하게 만들었다.",
                json.dumps(["협력", "문명", "상상력"], ensure_ascii=False),
                "manual",
                41,
            ),
            (
                "memo_demo_002",
                "user_demo",
                "book_prince",
                "가장 중요한 것은 눈에 보이지 않는다. 관계는 시간을 들인 만큼 의미를 얻는다.",
                json.dumps(["관계", "본질", "시간"], ensure_ascii=False),
                "manual",
                74,
            ),
            (
                "memo_demo_003",
                "user_demo",
                "book_cosmos",
                "우주는 우리 안에서도 자신을 이해하려고 깨어난다. 별을 보는 일은 나를 보는 일이다.",
                json.dumps(["우주", "자기이해", "경이"], ensure_ascii=False),
                "manual",
                12,
            ),
        ]

        with get_db() as cur:
            cur.execute(
                """
                INSERT IGNORE INTO users
                    (user_id, email, display_name, emoji, password_hash, genre_prefs)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    demo_user["user_id"],
                    demo_user["email"],
                    demo_user["display_name"],
                    demo_user["emoji"],
                    demo_user["password_hash"],
                    demo_user["genre_prefs"],
                ),
            )
            cur.executemany(
                """
                INSERT IGNORE INTO books
                    (book_id, title, author, cover_emoji, genre, total_pages)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                books,
            )
            cur.executemany(
                """
                INSERT IGNORE INTO shelf_books
                    (shelf_id, user_id, book_id, status, progress, rating, started_at, finished_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                shelf_books,
            )
            cur.executemany(
                """
                INSERT IGNORE INTO memos
                    (memo_id, user_id, book_id, content, tags, is_public, source, page_num)
                VALUES (%s, %s, %s, %s, %s, 1, %s, %s)
                """,
                memos,
            )

        print("[OK] 시드 데이터 준비 완료: user_demo, 샘플 책 3권, 서재 3개, 딥다이브 메모 3개")
        return True
    except Exception as e:
        print(f"[WARN] 시드 데이터 입력 실패 -> Mock 모드 유지 가능: {e}")
        return False


def drop_all_tables():
    """⚠️ 개발 전용 — 모든 테이블 삭제"""
    if not is_connected():
        return
    with get_db() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        for name in reversed(list(TABLES.keys())):
            cur.execute("DROP TABLE IF EXISTS " + _quote_identifier(name))
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    print("[WARN] 모든 테이블 삭제됨")
