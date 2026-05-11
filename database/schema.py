"""
LUMA MySQL 데이터베이스 스키마
────────────────────────────────────────
실행: python database/schema.py
→ MySQL에 모든 테이블 자동 생성

테이블 목록:
  users           회원 정보
  user_sessions   로그인 세션
  books           도서 정보 (Google Books 연동)
  user_books      사용자 서재 (읽는 중 / 완료 / 위시리스트)
  memos           독서 메모 (텍스트 + OCR + 사진)
  memo_images     메모 첨부 이미지
  ai_insights     AI 강제연결 인사이트
  clubs           독서 모임
  club_members    모임 멤버
  club_cards      모임 카드 게시물
  card_likes      카드 좋아요
  card_comments   카드 댓글
  club_reports    AI 모임 보고서
  reading_places  독서 장소
  place_checkins  장소 체크인
  place_reviews   장소 리뷰
"""

import os
import sys

# MySQL 드라이버 자동 감지
try:
    import mysql.connector as mysql_driver
    DRIVER = "mysql-connector"
except ImportError:
    try:
        import pymysql as mysql_driver
        mysql_driver.install_as_MySQLdb()
        DRIVER = "pymysql"
    except ImportError:
        print("❌ MySQL 드라이버가 없습니다.")
        print("   pip install mysql-connector-python  또는")
        print("   pip install PyMySQL")
        sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

# ── DB 연결 설정 ────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER",     "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "charset":  "utf8mb4",
}
DB_NAME = os.getenv("DB_NAME", "luma_db")

# ══════════════════════════════════════════════════════════════
#  DDL 정의 (테이블 생성 SQL)
# ══════════════════════════════════════════════════════════════
TABLES: list[tuple[str, str]] = [

    # ── 1. 회원 ────────────────────────────────────────────────
    ("users", """
    CREATE TABLE IF NOT EXISTS users (
        user_id       CHAR(36)        NOT NULL DEFAULT (UUID()),
        email         VARCHAR(255)    NOT NULL,
        password_hash VARCHAR(255)    NOT NULL COMMENT 'bcrypt 해시',
        username      VARCHAR(50)     NOT NULL,
        display_name  VARCHAR(100)    NOT NULL,
        bio           TEXT            COMMENT '자기소개',
        avatar_emoji  VARCHAR(10)     NOT NULL DEFAULT '📚',
        avatar_url    VARCHAR(500)    COMMENT '프로필 이미지 URL',
        birth_year    SMALLINT        COMMENT '출생연도 (연령대 필터용)',
        reading_goal  TINYINT         NOT NULL DEFAULT 12 COMMENT '연간 독서 목표 권수',
        preferred_genres JSON         COMMENT '["소설","철학","과학"]',
        is_active     TINYINT(1)      NOT NULL DEFAULT 1,
        is_admin      TINYINT(1)      NOT NULL DEFAULT 0,
        streak_days   SMALLINT        NOT NULL DEFAULT 0 COMMENT '연속 독서 일수',
        total_pages   INT             NOT NULL DEFAULT 0 COMMENT '누적 독서 페이지',
        last_read_at  DATETIME        COMMENT '마지막 독서 시각',
        created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id),
        UNIQUE KEY uk_email    (email),
        UNIQUE KEY uk_username (username),
        INDEX idx_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='LUMA 회원 정보'
    """),

    # ── 2. 로그인 세션 ──────────────────────────────────────────
    ("user_sessions", """
    CREATE TABLE IF NOT EXISTS user_sessions (
        session_id   CHAR(64)     NOT NULL COMMENT 'SHA-256 토큰',
        user_id      CHAR(36)     NOT NULL,
        ip_address   VARCHAR(45)  COMMENT 'IPv4/IPv6',
        user_agent   VARCHAR(500),
        expires_at   DATETIME     NOT NULL,
        created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY  (session_id),
        INDEX idx_user   (user_id),
        INDEX idx_expire (expires_at),
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      COMMENT='로그인 세션 토큰'
    """),

    # ── 3. 도서 ────────────────────────────────────────────────
    ("books", """
    CREATE TABLE IF NOT EXISTS books (
        book_id          CHAR(36)     NOT NULL DEFAULT (UUID()),
        isbn             VARCHAR(20)  COMMENT 'ISBN-13',
        isbn10           VARCHAR(20)  COMMENT 'ISBN-10',
        google_books_id  VARCHAR(50)  COMMENT 'Google Books volumeId',
        title            VARCHAR(500) NOT NULL,
        subtitle         VARCHAR(500),
        authors          JSON         NOT NULL COMMENT '["저자1","저자2"]',
        publisher        VARCHAR(200),
        published_date   VARCHAR(20)  COMMENT 'YYYY 또는 YYYY-MM-DD',
        description      TEXT,
        page_count       SMALLINT,
        genres           JSON         COMMENT '["소설","현대문학"]',
        language         VARCHAR(10)  NOT NULL DEFAULT 'ko',
        cover_image_url  VARCHAR(1000) COMMENT '표지 이미지 URL',
        cover_image_s    VARCHAR(1000) COMMENT '소형 표지',
        cover_image_m    VARCHAR(1000) COMMENT '중형 표지',
        cover_image_l    VARCHAR(1000) COMMENT '대형 표지',
        avg_rating       DECIMAL(3,2) COMMENT '평균 평점 (0.00~5.00)',
        ratings_count    INT          NOT NULL DEFAULT 0,
        created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (book_id),
        UNIQUE KEY uk_isbn          (isbn),
        UNIQUE KEY uk_google_books  (google_books_id),
        INDEX idx_title  (title(100)),
        FULLTEXT idx_ft_title_author (title, description)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='도서 정보 (Google Books 연동)'
    """),

    # ── 4. 사용자 서재 ──────────────────────────────────────────
    ("user_books", """
    CREATE TABLE IF NOT EXISTS user_books (
        user_book_id    CHAR(36)       NOT NULL DEFAULT (UUID()),
        user_id         CHAR(36)       NOT NULL,
        book_id         CHAR(36)       NOT NULL,
        status          ENUM('reading','completed','wishlist','paused','dropped')
                                       NOT NULL DEFAULT 'wishlist' COMMENT '독서 상태',
        current_page    SMALLINT       NOT NULL DEFAULT 0,
        total_pages     SMALLINT       COMMENT '이 사용자 기준 총 페이지',
        progress_pct    TINYINT        NOT NULL DEFAULT 0 COMMENT '진행률 0-100',
        start_date      DATE           COMMENT '독서 시작일',
        end_date        DATE           COMMENT '독서 완료일',
        rating          TINYINT        COMMENT '별점 1-5',
        personal_review TEXT           COMMENT '개인 감상',
        is_favorite     TINYINT(1)     NOT NULL DEFAULT 0,
        reading_minutes INT            NOT NULL DEFAULT 0 COMMENT '누적 독서 시간(분)',
        created_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY  (user_book_id),
        UNIQUE KEY   uk_user_book (user_id, book_id),
        INDEX idx_user   (user_id),
        INDEX idx_status (status),
        FOREIGN KEY (user_id) REFERENCES users(user_id)  ON DELETE CASCADE,
        FOREIGN KEY (book_id) REFERENCES books(book_id)  ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      COMMENT='사용자 서재 (읽는 중/완료/위시리스트)'
    """),

    # ── 5. 메모 ────────────────────────────────────────────────
    ("memos", """
    CREATE TABLE IF NOT EXISTS memos (
        memo_id          CHAR(36)       NOT NULL DEFAULT (UUID()),
        user_id          CHAR(36)       NOT NULL,
        book_id          CHAR(36)       NOT NULL,
        user_book_id     CHAR(36),
        content          TEXT           NOT NULL COMMENT '메모 본문',
        highlighted_text TEXT           COMMENT 'OCR 또는 복사한 원문',
        page_number      SMALLINT       COMMENT '해당 페이지',
        input_method     ENUM('typing','ocr','paste','photo')
                                        NOT NULL DEFAULT 'typing'
                                        COMMENT '입력 방식',
        mood             ENUM('inspired','emotional','curious','neutral','excited','thoughtful')
                                        NOT NULL DEFAULT 'neutral',
        tags             JSON           COMMENT '["철학","인류학"]',
        ai_keywords      JSON           COMMENT 'AI 추출 키워드',
        ai_theme         VARCHAR(50)    COMMENT 'AI 분류 주제',
        ai_depth_score   TINYINT        COMMENT '사유 깊이 점수 1-10',
        embedding_vector JSON           COMMENT 'Gemini 임베딩 벡터',
        is_public        TINYINT(1)     NOT NULL DEFAULT 0,
        like_count       INT            NOT NULL DEFAULT 0,
        created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY  (memo_id),
        INDEX idx_user       (user_id),
        INDEX idx_book       (book_id),
        INDEX idx_created    (created_at),
        INDEX idx_public     (is_public),
        FULLTEXT idx_ft_content (content, highlighted_text),
        FOREIGN KEY (user_id) REFERENCES users(user_id)      ON DELETE CASCADE,
        FOREIGN KEY (book_id) REFERENCES books(book_id)      ON DELETE CASCADE,
        FOREIGN KEY (user_book_id) REFERENCES user_books(user_book_id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='독서 메모 (텍스트/OCR/사진)'
    """),

    # ── 6. 메모 첨부 이미지 ─────────────────────────────────────
    ("memo_images", """
    CREATE TABLE IF NOT EXISTS memo_images (
        image_id     CHAR(36)      NOT NULL DEFAULT (UUID()),
        memo_id      CHAR(36)      NOT NULL,
        user_id      CHAR(36)      NOT NULL,
        image_url    VARCHAR(1000) NOT NULL COMMENT '저장된 이미지 URL',
        ocr_text     LONGTEXT      COMMENT 'OCR 추출 텍스트',
        image_type   ENUM('book_page','note','highlight','other')
                                   NOT NULL DEFAULT 'book_page',
        file_size    INT           COMMENT '파일 크기 (bytes)',
        width        SMALLINT,
        height       SMALLINT,
        created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY  (image_id),
        INDEX idx_memo (memo_id),
        FOREIGN KEY (memo_id) REFERENCES memos(memo_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      COMMENT='메모 첨부 이미지 및 OCR 결과'
    """),

    # ── 7. AI 인사이트 (강제연결) ───────────────────────────────
    ("ai_insights", """
    CREATE TABLE IF NOT EXISTS ai_insights (
        insight_id       CHAR(36)     NOT NULL DEFAULT (UUID()),
        user_id          CHAR(36)     NOT NULL,
        memo_a_id        CHAR(36)     NOT NULL COMMENT '원본 메모',
        memo_b_id        CHAR(36)     NOT NULL COMMENT '연결된 메모',
        book_a_id        CHAR(36)     NOT NULL,
        book_b_id        CHAR(36)     NOT NULL,
        insight_text     TEXT         NOT NULL COMMENT 'AI 생성 인사이트',
        connection_type  ENUM('유추','심화','대립','역설','순환')
                                      NOT NULL DEFAULT '유추',
        strength         DECIMAL(3,2) NOT NULL DEFAULT 0.70 COMMENT '연결 강도 0.00-1.00',
        reframe_question TEXT         COMMENT 'AI 심화 질문',
        similarity_score DECIMAL(4,3) COMMENT '벡터 유사도 점수',
        is_saved         TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '사용자 저장 여부',
        created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY  (insight_id),
        INDEX idx_user   (user_id),
        INDEX idx_memo_a (memo_a_id),
        INDEX idx_memo_b (memo_b_id),
        FOREIGN KEY (user_id)   REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (memo_a_id) REFERENCES memos(memo_id) ON DELETE CASCADE,
        FOREIGN KEY (memo_b_id) REFERENCES memos(memo_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      COMMENT='AI 강제연결 인사이트'
    """),

    # ── 8. 독서 모임 ────────────────────────────────────────────
    ("clubs", """
    CREATE TABLE IF NOT EXISTS clubs (
        club_id              CHAR(36)     NOT NULL DEFAULT (UUID()),
        host_user_id         CHAR(36)     NOT NULL,
        name                 VARCHAR(100) NOT NULL,
        description          TEXT,
        emoji                VARCHAR(10)  NOT NULL DEFAULT '📚',
        current_book_id      CHAR(36)     COMMENT '현재 읽는 책',
        current_book_title   VARCHAR(500) COMMENT '비정규화 캐시',
        current_book_author  VARCHAR(200) COMMENT '비정규화 캐시',
        is_private           TINYINT(1)   NOT NULL DEFAULT 0,
        is_live              TINYINT(1)   NOT NULL DEFAULT 0 COMMENT 'LIVE 진행 중',
        max_members          TINYINT      NOT NULL DEFAULT 20,
        tags                 JSON         COMMENT '["철학","인문학"]',
        meeting_schedule     JSON         COMMENT '{"day":5,"time":"19:00","freq":"weekly"}',
        total_meetings       SMALLINT     NOT NULL DEFAULT 0,
        total_cards          INT          NOT NULL DEFAULT 0,
        created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY  (club_id),
        INDEX idx_host    (host_user_id),
        INDEX idx_public  (is_private),
        FOREIGN KEY (host_user_id)    REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (current_book_id) REFERENCES books(book_id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='독서 모임'
    """),

    # ── 9. 모임 멤버 ────────────────────────────────────────────
    ("club_members", """
    CREATE TABLE IF NOT EXISTS club_members (
        member_id  CHAR(36)  NOT NULL DEFAULT (UUID()),
        club_id    CHAR(36)  NOT NULL,
        user_id    CHAR(36)  NOT NULL,
        role       ENUM('host','moderator','member') NOT NULL DEFAULT 'member',
        joined_at  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY  (member_id),
        UNIQUE KEY   uk_club_user (club_id, user_id),
        INDEX idx_club (club_id),
        INDEX idx_user (user_id),
        FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      COMMENT='모임 멤버 목록'
    """),

    # ── 10. 모임 카드 ───────────────────────────────────────────
    ("club_cards", """
    CREATE TABLE IF NOT EXISTS club_cards (
        card_id      CHAR(36)    NOT NULL DEFAULT (UUID()),
        club_id      CHAR(36)    NOT NULL,
        user_id      CHAR(36)    NOT NULL COMMENT 'ai_luma 포함',
        user_name    VARCHAR(50) NOT NULL,
        user_emoji   VARCHAR(10) NOT NULL DEFAULT '⭐',
        card_type    ENUM('thought','quote','insight','question','review','ai_question')
                                 NOT NULL DEFAULT 'thought',
        content      TEXT        NOT NULL,
        book_page    SMALLINT    COMMENT '관련 페이지',
        is_ai        TINYINT(1)  NOT NULL DEFAULT 0,
        like_count   INT         NOT NULL DEFAULT 0,
        comment_count INT        NOT NULL DEFAULT 0,
        created_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY  (card_id),
        INDEX idx_club    (club_id),
        INDEX idx_user    (user_id),
        INDEX idx_created (created_at),
        FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='모임 카드 게시물'
    """),

    # ── 11. 카드 좋아요 ─────────────────────────────────────────
    ("card_likes", """
    CREATE TABLE IF NOT EXISTS card_likes (
        like_id    CHAR(36)  NOT NULL DEFAULT (UUID()),
        card_id    CHAR(36)  NOT NULL,
        user_id    CHAR(36)  NOT NULL,
        created_at DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY  (like_id),
        UNIQUE KEY   uk_card_user (card_id, user_id),
        FOREIGN KEY (card_id) REFERENCES club_cards(card_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id)      ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      COMMENT='카드 좋아요'
    """),

    # ── 12. 카드 댓글 ───────────────────────────────────────────
    ("card_comments", """
    CREATE TABLE IF NOT EXISTS card_comments (
        comment_id  CHAR(36)     NOT NULL DEFAULT (UUID()),
        card_id     CHAR(36)     NOT NULL,
        user_id     CHAR(36)     NOT NULL,
        user_name   VARCHAR(50)  NOT NULL,
        user_emoji  VARCHAR(10)  NOT NULL DEFAULT '⭐',
        content     TEXT         NOT NULL,
        created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (comment_id),
        INDEX idx_card (card_id),
        FOREIGN KEY (card_id) REFERENCES club_cards(card_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id)      ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='카드 댓글'
    """),

    # ── 13. AI 모임 보고서 ──────────────────────────────────────
    ("club_reports", """
    CREATE TABLE IF NOT EXISTS club_reports (
        report_id         CHAR(36)  NOT NULL DEFAULT (UUID()),
        club_id           CHAR(36)  NOT NULL,
        book_id           CHAR(36),
        book_title        VARCHAR(500),
        summary           TEXT      NOT NULL COMMENT 'AI 생성 요약',
        key_insights      JSON      COMMENT '["인사이트1","인사이트2"]',
        highlight_quotes  JSON      COMMENT '["명언1","명언2"]',
        next_questions    JSON      COMMENT '다음 모임 예상 질문',
        mood              VARCHAR(20) COMMENT '모임 분위기',
        participants      JSON      COMMENT '["이름1","이름2"]',
        card_count        SMALLINT  NOT NULL DEFAULT 0,
        pdf_url           VARCHAR(1000) COMMENT 'PDF 보고서 URL',
        created_at        DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY  (report_id),
        INDEX idx_club    (club_id),
        INDEX idx_created (created_at),
        FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='AI 모임 보고서'
    """),

    # ── 14. 독서 장소 ───────────────────────────────────────────
    ("reading_places", """
    CREATE TABLE IF NOT EXISTS reading_places (
        place_id         CHAR(36)     NOT NULL DEFAULT (UUID()),
        google_place_id  VARCHAR(100) COMMENT 'Google Maps Place ID',
        name             VARCHAR(200) NOT NULL,
        address          VARCHAR(500),
        city             VARCHAR(100),
        country          VARCHAR(100) NOT NULL DEFAULT '한국',
        latitude         DECIMAL(10,7),
        longitude        DECIMAL(10,7),
        place_type       ENUM('cafe','library','bookstore_cafe','restaurant','other')
                                      NOT NULL DEFAULT 'cafe',
        description      TEXT,
        photo_emoji      VARCHAR(10)  NOT NULL DEFAULT '📍',
        open_hours       VARCHAR(500),
        price_level      TINYINT      COMMENT '0=무료, 1-4=가격대',
        avg_rating       DECIMAL(3,2),
        reading_score    DECIMAL(4,2) COMMENT 'AI 독서 적합도 0-10',
        ai_tags          JSON         COMMENT '["조용한","WiFi빠름"]',
        check_in_count   INT          NOT NULL DEFAULT 0,
        is_verified      TINYINT(1)   NOT NULL DEFAULT 0,
        created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (place_id),
        UNIQUE KEY uk_google (google_place_id),
        INDEX idx_city    (city),
        INDEX idx_type    (place_type),
        INDEX idx_score   (reading_score),
        SPATIAL INDEX idx_geo (POINT(latitude, longitude))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='독서 장소 정보'
    """),

    # ── 15. 장소 체크인 ─────────────────────────────────────────
    ("place_checkins", """
    CREATE TABLE IF NOT EXISTS place_checkins (
        checkin_id  CHAR(36)     NOT NULL DEFAULT (UUID()),
        place_id    CHAR(36)     NOT NULL,
        user_id     CHAR(36)     NOT NULL,
        memo        VARCHAR(500) COMMENT '체크인 메모',
        book_id     CHAR(36)     COMMENT '읽고 있던 책',
        created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (checkin_id),
        INDEX idx_place   (place_id),
        INDEX idx_user    (user_id),
        INDEX idx_created (created_at),
        FOREIGN KEY (place_id) REFERENCES reading_places(place_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id)  REFERENCES users(user_id)           ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
      COMMENT='장소 체크인 기록'
    """),

    # ── 16. 장소 리뷰 ───────────────────────────────────────────
    ("place_reviews", """
    CREATE TABLE IF NOT EXISTS place_reviews (
        review_id   CHAR(36)  NOT NULL DEFAULT (UUID()),
        place_id    CHAR(36)  NOT NULL,
        user_id     CHAR(36)  NOT NULL,
        user_name   VARCHAR(50) NOT NULL,
        user_emoji  VARCHAR(10) NOT NULL DEFAULT '⭐',
        content     TEXT      NOT NULL,
        score       TINYINT   NOT NULL DEFAULT 8 COMMENT '독서 적합도 점수 1-10',
        created_at  DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (review_id),
        INDEX idx_place (place_id),
        FOREIGN KEY (place_id) REFERENCES reading_places(place_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id)  REFERENCES users(user_id)           ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='장소 독서 리뷰'
    """),
]

# ── SPATIAL INDEX 예외 처리 (MySQL 버전 호환) ──────────────────
TABLES_NO_SPATIAL: list[tuple[str, str]] = []
for name, ddl in TABLES:
    if name == "reading_places":
        ddl = ddl.replace(
            ",\n        SPATIAL INDEX idx_geo (POINT(latitude, longitude))", ""
        )
    TABLES_NO_SPATIAL.append((name, ddl))


# ══════════════════════════════════════════════════════════════
#  초기 데이터 (샘플)
# ══════════════════════════════════════════════════════════════
SEED_SQL = [
    # 기본 독서 장소 (서울)
    """INSERT IGNORE INTO reading_places
       (place_id, name, address, city, country, latitude, longitude,
        place_type, description, photo_emoji, reading_score, ai_tags, check_in_count)
    VALUES
       ('place-kr-001','어니언 성수','서울 성동구 아차산로9길 8','서울','한국',
        37.5443,127.0557,'cafe','성수동 감성의 대형 베이커리 카페','🏭',9.1,
        '["오래앉기좋음","분위기좋음","넓은좌석","자연채광"]',247),
       ('place-kr-002','북앤레스트 삼청점','서울 종로구 삼청로 130','서울','한국',
        37.5824,126.9811,'bookstore_cafe','삼청동의 아늑한 서점 카페','📚',9.6,
        '["조용한","모임룸","WiFi빠름","오래앉기좋음"]',412),
       ('place-kr-003','국립중앙도서관','서울 서초구 반포대로 201','서울','한국',
        37.4944,127.0072,'library','대한민국 대표 도서관','🏛️',9.8,
        '["조용한","넓은좌석","WiFi빠름","자연채광"]',892)
    """,
]


# ══════════════════════════════════════════════════════════════
#  메인 실행
# ══════════════════════════════════════════════════════════════
def create_database(conn, cursor):
    """DB 생성"""
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                   f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"USE `{DB_NAME}`")
    print(f"✅ 데이터베이스 '{DB_NAME}' 준비 완료")


def create_tables(cursor):
    """전체 테이블 생성"""
    print("\n📋 테이블 생성 시작...")
    for name, ddl in TABLES_NO_SPATIAL:
        try:
            cursor.execute(ddl)
            print(f"  ✅ {name:<20} 생성 완료")
        except Exception as e:
            print(f"  ⚠️  {name:<20} 건너뜀: {e}")


def insert_seed_data(cursor):
    """초기 데이터 삽입"""
    print("\n🌱 초기 데이터 삽입...")
    for sql in SEED_SQL:
        try:
            cursor.execute(sql)
            print(f"  ✅ 장소 샘플 데이터 삽입")
        except Exception as e:
            print(f"  ⚠️  삽입 건너뜀: {e}")


def show_summary(cursor):
    """생성 결과 요약"""
    cursor.execute("""
        SELECT TABLE_NAME, TABLE_ROWS, TABLE_COMMENT
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s
        ORDER BY TABLE_NAME
    """, (DB_NAME,))
    rows = cursor.fetchall()
    print(f"\n{'━'*60}")
    print(f"{'테이블명':<25} {'행수':>8}  {'설명'}")
    print(f"{'━'*60}")
    for row in rows:
        name    = row[0] if isinstance(row, (list, tuple)) else row['TABLE_NAME']
        count   = row[1] if isinstance(row, (list, tuple)) else row['TABLE_ROWS']
        comment = row[2] if isinstance(row, (list, tuple)) else row['TABLE_COMMENT']
        print(f"  {name:<23} {(count or 0):>6}행  {comment or ''}")
    print(f"{'━'*60}")
    print(f"  총 {len(rows)}개 테이블 생성 완료")


def main():
    print("╔══════════════════════════════════════╗")
    print("║   🌿  LUMA MySQL 스키마 생성기        ║")
    print("╚══════════════════════════════════════╝\n")
    print(f"  접속 정보: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"  데이터베이스: {DB_NAME}\n")

    try:
        conn = mysql_driver.connect(**DB_CONFIG)
        cursor = conn.cursor()

        create_database(conn, cursor)
        create_tables(cursor)
        insert_seed_data(cursor)
        conn.commit()
        show_summary(cursor)

        cursor.close()
        conn.close()

        print("\n🎉 LUMA 데이터베이스 준비 완료!")
        print(f"   MySQL: {DB_CONFIG['user']}@{DB_CONFIG['host']}/{DB_NAME}")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("\n확인사항:")
        print("  1. MySQL 서버가 실행 중인지 확인")
        print("  2. .env 파일의 DB_HOST, DB_USER, DB_PASSWORD 확인")
        print("  3. pip install mysql-connector-python 설치 확인")
        raise


if __name__ == "__main__":
    main()
