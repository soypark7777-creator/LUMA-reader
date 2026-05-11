# 🌿 LUMA 프로젝트 완전 통합 가이드
## ZIP 파일 분석 + STEP 7·8 + MySQL 연동 + VS Code 설치 완전 정리

---

## 📦 1. 업로드된 ZIP 파일 분석 결과

### 핵심 발견사항
업로드된 `luma-backend.zip`은 **FastAPI** 기반으로 이미 구현된 별도 프로젝트입니다.
우리가 만든 Flask 프로젝트와 **다른 구조**이지만, 핵심 서비스 로직은 합칠 수 있습니다.

### ZIP 파일 구조 (핵심 파일만)
```
luma-backend/
├── main.py                          ← FastAPI 진입점 ✅
├── requirements.txt                 ← 의존성 목록
├── .env                             ← MySQL + API 키 설정
├── app/
│   ├── core/
│   │   ├── config.py                ← MySQL 설정 포함 ✅
│   │   ├── gemini.py                ← Gemini API 래퍼
│   │   └── firebase.py              ← Firebase 연동
│   ├── models/
│   │   ├── user.py                  ← 회원 Pydantic 모델 ✅
│   │   └── memo.py                  ← 메모 모델
│   ├── routers/
│   │   ├── web_pages.py             ← 회원가입/로그인 HTML 페이지 ✅
│   │   ├── members.py               ← 회원 CRUD API ✅
│   │   ├── admin_members.py         ← 관리자 API ✅
│   │   └── dashboard.py             ← 대시보드 API ✅
│   └── services/
│       ├── member_service.py        ← MySQL 회원 서비스 ✅ (핵심!)
│       ├── dashboard_service.py     ← 대시보드 통계 서비스 ✅
│       ├── face_auth_service.py     ← 얼굴인식 로그인 (OpenCV) ✅
│       └── ai_service.py            ← AI 서비스
└── tests/
    └── test_members.py              ← 회원 테스트
```

### ZIP 파일이 이미 구현한 기능
| 기능 | 상태 | 설명 |
|------|------|------|
| MySQL 연동 | ✅ 완성 | pymysql + 자동 테이블 생성 |
| 회원가입/로그인 | ✅ 완성 | bcrypt 비밀번호 + 이메일 인증 |
| 얼굴인식 로그인 | ✅ 완성 | OpenCV 기반 |
| 관리자 패널 | ✅ 완성 | 회원 CRUD |
| 대시보드 통계 | ✅ 완성 | 읽는 책, 메모, 알림 |
| FastAPI + Swagger | ✅ 완성 | /docs 자동 생성 |

---

## 🗄️ 2. MySQL 스키마 완전 정의

### MySQL 설치 및 DB 생성

```sql
-- MySQL 접속 후 실행
CREATE DATABASE IF NOT EXISTS book_club_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE book_club_db;
```

### 전체 테이블 스키마

```sql
-- ══════════════════════════════════════════════
--  1. 회원 테이블 (핵심)
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS members (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50)  NOT NULL,
    email           VARCHAR(255) NULL,
    password        VARCHAR(255) NULL,          -- bcrypt 해시
    phone           VARCHAR(30)  NULL,
    age             INT          NULL,
    region          VARCHAR(50)  NULL,
    genre           VARCHAR(100) NULL,          -- 선호 장르
    post_count      INT          DEFAULT 0,
    likes_received  INT          DEFAULT 0,
    role            VARCHAR(20)  NOT NULL DEFAULT 'member',  -- member|admin
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    join_date       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX uniq_members_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ══════════════════════════════════════════════
--  2. 현재 읽는 책 테이블
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS reading_books (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    member_email     VARCHAR(255) NOT NULL,
    title            VARCHAR(255) NOT NULL,
    author           VARCHAR(255) NULL,
    genre            VARCHAR(80)  NULL,
    progress_percent INT          NOT NULL DEFAULT 0,   -- 0~100
    memo_count       INT          NOT NULL DEFAULT 0,
    is_finished      TINYINT(1)   NOT NULL DEFAULT 0,
    last_read_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_reading_email (member_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ══════════════════════════════════════════════
--  3. 메모 로그 테이블
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS memos_log (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    member_email VARCHAR(255) NOT NULL,
    book_title   VARCHAR(255) NULL,
    content      TEXT         NOT NULL,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_memos_email (member_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ══════════════════════════════════════════════
--  4. 클럽 알림 테이블
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS club_alerts (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    member_email VARCHAR(255) NULL,
    title        VARCHAR(255) NOT NULL,
    message      VARCHAR(500) NOT NULL,
    is_live      TINYINT(1)   NOT NULL DEFAULT 0,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_alerts_email (member_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ══════════════════════════════════════════════
--  5. 독서 모임 테이블
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS reading_clubs (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    name             VARCHAR(100) NOT NULL,
    description      TEXT         NULL,
    host_email       VARCHAR(255) NOT NULL,
    current_book     VARCHAR(255) NULL,
    current_author   VARCHAR(255) NULL,
    emoji            VARCHAR(10)  DEFAULT '📚',
    is_private       TINYINT(1)   DEFAULT 0,
    is_live          TINYINT(1)   DEFAULT 0,
    member_count     INT          DEFAULT 1,
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_club_host (host_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ══════════════════════════════════════════════
--  6. 독서 카드 (공독의 장) 테이블
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS club_cards (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    club_id      INT          NOT NULL,
    user_email   VARCHAR(255) NOT NULL,
    user_name    VARCHAR(50)  NOT NULL,
    card_type    VARCHAR(20)  DEFAULT 'thought', -- thought|quote|insight|question|ai_question
    content      TEXT         NOT NULL,
    is_ai        TINYINT(1)   DEFAULT 0,
    like_count   INT          DEFAULT 0,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (club_id) REFERENCES reading_clubs(id) ON DELETE CASCADE,
    INDEX idx_card_club (club_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ══════════════════════════════════════════════
--  7. 독서 장소 테이블
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS reading_places (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    place_id       VARCHAR(50)  UNIQUE NOT NULL,
    name           VARCHAR(200) NOT NULL,
    address        VARCHAR(500) NULL,
    city           VARCHAR(50)  NULL,
    country        VARCHAR(50)  NULL,
    place_type     VARCHAR(30)  DEFAULT 'cafe',  -- cafe|library|bookstore_cafe
    ai_tags        JSON         NULL,             -- ["조용한","WiFi빠름",...]
    reading_score  FLOAT        DEFAULT 0.0,
    rating         FLOAT        DEFAULT 0.0,
    check_ins      INT          DEFAULT 0,
    lat            DOUBLE       NULL,
    lng            DOUBLE       NULL,
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ══════════════════════════════════════════════
--  8. 장소 체크인 기록
-- ══════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS place_checkins (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    place_id     VARCHAR(50)  NOT NULL,
    user_email   VARCHAR(255) NOT NULL,
    memo         VARCHAR(500) NULL,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_checkin_place (place_id),
    INDEX idx_checkin_user (user_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 🔗 3. 두 프로젝트 통합 방법

### 구조 비교
```
ZIP 파일 (FastAPI)          우리 프로젝트 (Flask)
─────────────────────       ────────────────────────
main.py (FastAPI)           app.py (Flask)
app/routers/                app/routes/
app/services/               app/services/
  member_service.py    →    MySQL 연동 핵심 (가져올 것)
  dashboard_service.py →    대시보드 데이터 (가져올 것)
  face_auth_service.py →    얼굴인식 (선택사항)
```

### 통합 전략 (권장)
**ZIP 파일의 MySQL 서비스를 우리 Flask 프로젝트에 합친다**

복사할 파일:
- `app/services/member_service.py` → MySQL 회원 관리
- `app/services/dashboard_service.py` → 대시보드 통계
- `app/models/user.py` → Pydantic 모델 참고
- `app/core/config.py` → MySQL 설정 참고

---

## 🎯 4. STEP 7 — 딥다이브 독서 모드

### 구현 내용
- ASMR 사운드 컨트롤러 (빗소리/카페/화이트노이즈)
- 알림 차단 몰입 모드
- 타이머 + 독서량 추적
- 다크모드 전환

### 라우터 추가 (`app/routes/deepdive.py`)
```python
from flask import Blueprint, render_template
deepdive_bp = Blueprint('deepdive', __name__)

@deepdive_bp.route('/deepdive')
def deepdive_page():
    return render_template('deepdive.html')
```

### factory.py에 등록
```python
from app.routes.deepdive import deepdive_bp
app.register_blueprint(deepdive_bp)
```

---

## 🔐 5. STEP 8 — 사용자 인증 (MySQL 연동)

### ZIP 파일의 member_service.py를 Flask에 적용

```python
# app/services/mysql_member_service.py
import pymysql
from app.core.config import settings

DB_CONFIG = {
    "host":        settings.MYSQL_HOST,
    "port":        settings.MYSQL_PORT,
    "user":        settings.MYSQL_USER,
    "password":    settings.MYSQL_PASSWORD,
    "db":          settings.MYSQL_DB,
    "charset":     "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit":  False,
}

def connect_db():
    return pymysql.connect(**DB_CONFIG)

def create_member(name, email, password_hash):
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO members (username, email, password) VALUES (%s, %s, %s)",
                (name, email, password_hash)
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()

def find_member_by_email(email):
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM members WHERE email=%s", (email,))
            return cur.fetchone()
    finally:
        conn.close()
```

---

## 🖥️ 6. VS Code 완전 설치 가이드

### STEP 1 — 프로젝트 폴더 준비

```
📁 내 문서/
  📁 luma-backend/          ← 이 폴더를 VS Code로 열기
    📄 app.py
    📄 requirements.txt
    📄 .env
    📄 Dockerfile
    📄 docker-compose.yml
    📄 README.md
    📁 app/
      📁 core/
      📁 routes/
      📁 services/
      📁 templates/
      📁 static/
    📁 tests/
```

### STEP 2 — VS Code에서 열기

```bash
# 방법 1: 터미널에서
code C:\Users\사용자명\Documents\luma-backend

# 방법 2: VS Code 메뉴
# File → Open Folder → luma-backend 폴더 선택
```

### STEP 3 — Python 가상환경 설정

```bash
# VS Code 터미널 열기: Ctrl + `

# 1. 가상환경 생성
python -m venv venv

# 2. 활성화 (Windows)
.\venv\Scripts\activate

# 3. 활성화 (Mac/Linux)
source venv/bin/activate

# 터미널 앞에 (venv) 표시 확인!
```

### STEP 4 — 패키지 설치

```bash
# Flask 버전 (우리 프로젝트)
pip install flask python-dotenv google-generativeai \
            requests Pillow pymysql cryptography \
            pytest firebase-admin

# 또는 requirements.txt로 한번에
pip install -r requirements.txt
```

### STEP 5 — MySQL 설치 및 설정

```bash
# Windows: MySQL Community Server 다운로드
# https://dev.mysql.com/downloads/mysql/

# 설치 후 MySQL Workbench 또는 터미널에서:
mysql -u root -p
# 비밀번호 입력 후:
CREATE DATABASE book_club_db CHARACTER SET utf8mb4;
```

### STEP 6 — .env 파일 설정

```env
# luma-backend/.env 파일 수정
APP_NAME=LUMA
FLASK_ENV=development
FLASK_DEBUG=true
PORT=5000
SECRET_KEY=나만의_비밀키_여기에_입력

# Gemini AI (선택)
GEMINI_API_KEY=AIza...실제키...

# MySQL (필수 - 로컬 MySQL 정보로 변경)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=내_MySQL_비밀번호
MYSQL_DB=book_club_db
MYSQL_CHARSET=utf8mb4

# 나머지는 나중에
GOOGLE_MAPS_API_KEY=
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
```

### STEP 7 — 서버 실행

```bash
# Flask 프로젝트 실행
python app.py

# 또는 ZIP 파일(FastAPI) 실행
uvicorn main:app --reload --port 8000
```

### STEP 8 — 브라우저 확인

| 프레임워크 | URL | 설명 |
|-----------|-----|------|
| Flask | http://localhost:5000 | 별자리 대시보드 |
| Flask | http://localhost:5000/community | 공독의 장 |
| Flask | http://localhost:5000/ocr | OCR 스캔 |
| FastAPI | http://localhost:8000/docs | Swagger API 문서 |
| FastAPI | http://localhost:8000/signup | 회원가입 페이지 |

---

## 📋 7. VS Code 필수 확장 프로그램

VS Code 좌측 Extensions(Ctrl+Shift+X)에서 설치:

```
1. Python                    (Microsoft)
2. Pylance                   (Microsoft)
3. Python Debugger           (Microsoft)
4. Flask Snippets             
5. HTML CSS Support          (ecmel)
6. Jinja                     (wholroyd)
7. SQLTools                  (Matheus Teixeira) ← MySQL 연결용
8. SQLTools MySQL/MariaDB    (Matheus Teixeira)
9. GitLens                   (GitKraken)
10. Thunder Client           (REST API 테스트용)
```

---

## 🔧 8. VS Code 설정 파일

### `.vscode/settings.json` 생성
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe",
  "python.terminal.activateEnvironment": true,
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/venv": true,
    "**/.pytest_cache": true
  },
  "emmet.includeLanguages": {
    "jinja-html": "html"
  }
}
```

### `.vscode/launch.json` (디버그 설정)
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Flask 실행",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/app.py",
      "env": {
        "FLASK_ENV": "development",
        "FLASK_DEBUG": "true"
      },
      "jinja": true
    }
  ]
}
```

---

## 🗂️ 9. 최종 통합 파일 배치 구조

```
luma-backend/                        ← VS Code에서 여는 폴더
│
├── 📄 app.py                         ← Flask 진입점 (우리 프로젝트)
├── 📄 main.py                        ← FastAPI 진입점 (ZIP 파일) 
├── 📄 requirements.txt
├── 📄 .env                           ← API 키 + MySQL 설정
├── 📄 .env.example                   ← 템플릿
├── 📄 .gitignore
├── 📄 Dockerfile
├── 📄 docker-compose.yml
├── 📄 nginx.conf
├── 📄 README.md
│
├── 📁 app/                           ← Flask 앱
│   ├── 📁 core/
│   │   ├── config.py                 ← MySQL 설정 추가
│   │   └── factory.py
│   ├── 📁 routes/
│   │   ├── main.py                   ← 대시보드
│   │   ├── memos.py
│   │   ├── ai.py
│   │   ├── community.py
│   │   ├── places.py
│   │   ├── ocr.py
│   │   ├── deepdive.py               ← STEP 7 새로 추가
│   │   └── auth.py                   ← STEP 8 (MySQL 연동)
│   ├── 📁 services/
│   │   ├── firebase_service.py
│   │   ├── gemini_service.py
│   │   ├── embedding_service.py
│   │   ├── club_service.py
│   │   ├── place_service.py
│   │   ├── ocr_service.py
│   │   ├── youtube_service.py
│   │   └── mysql_member_service.py   ← ZIP에서 가져온 MySQL 서비스
│   └── 📁 templates/
│       ├── dashboard.html
│       ├── community.html
│       ├── ocr.html
│       ├── deepdive.html             ← STEP 7 새로 추가
│       └── auth.html                 ← STEP 8 새로 추가
│
└── 📁 tests/
    ├── conftest.py
    └── test_all.py                   ← 50개 테스트 통과
```

---

## ⚠️ 10. 주의사항 & 자주 발생하는 오류

### 오류 1: pymysql 연결 실패
```
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")

해결:
1. MySQL 서비스 실행 확인 (Windows: 서비스 → MySQL 시작)
2. .env의 MYSQL_PASSWORD 확인
3. MySQL root 권한 확인
```

### 오류 2: 모듈 없음
```
ModuleNotFoundError: No module named 'flask'

해결:
(venv)가 활성화됐는지 확인!
pip install -r requirements.txt
```

### 오류 3: 포트 충돌
```
OSError: [Errno 98] Address already in use: 5000

해결:
# 다른 포트 사용
python app.py  (PORT=5001로 .env 변경)
# 또는 기존 프로세스 종료
netstat -ano | findstr :5000  (Windows)
```

### 오류 4: venv 활성화 안 됨 (Windows)
```
.\venv\Scripts\activate 실행 오류

해결 (PowerShell):
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\activate
```

---

## 🚀 11. 빠른 시작 체크리스트

```
□ 1. Python 3.12 설치 확인  →  python --version
□ 2. MySQL 설치 + 실행 확인 →  mysql -u root -p
□ 3. book_club_db 데이터베이스 생성
□ 4. luma-backend 폴더를 VS Code로 열기
□ 5. 터미널에서 python -m venv venv
□ 6. venv\Scripts\activate  (Windows)
□ 7. pip install flask python-dotenv pymysql Pillow
□ 8. .env 파일의 MySQL 비밀번호 수정
□ 9. python app.py 실행
□ 10. 브라우저에서 http://localhost:5000 확인
□ 11. http://localhost:5000/health → {"status":"healthy"} 확인
```

---

*LUMA v1.0 — 읽는 행위를 넘어, 생각의 우주를 연결하다* 🌿
