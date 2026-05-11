# 🌿 LUMA — 설치 및 실행 완전 가이드

> **"읽는 행위를 넘어, 생각의 우주를 연결하다."**
> 이 가이드를 따라 5분 안에 LUMA를 로컬에서 실행할 수 있습니다.

---

## 📋 목차

1. [사전 요구사항](#1-사전-요구사항)
2. [빠른 시작 (5분)](#2-빠른-시작-5분)
3. [API 키 설정 (선택)](#3-api-키-설정-선택)
4. [전체 페이지 안내](#4-전체-페이지-안내)
5. [API 엔드포인트 목록](#5-api-엔드포인트-목록)
6. [Docker로 배포](#6-docker로-배포)
7. [트러블슈팅](#7-트러블슈팅)
8. [프로젝트 구조](#8-프로젝트-구조)

---

## 1. 사전 요구사항

| 항목 | 버전 | 확인 명령어 |
|------|------|-------------|
| Python | 3.10 이상 | `python --version` |
| pip | 최신 | `pip --version` |
| Git | 최신 | `git --version` |

> ✅ **API 키 없이도 Mock 모드로 모든 기능 즉시 사용 가능!**

---

## 2. 빠른 시작 (5분)

### Step 1 — 프로젝트 다운로드

```bash
# ZIP 파일 압축 해제 후 폴더 진입
cd luma-backend

# 또는 Git으로 클론
git clone https://github.com/yourname/luma-backend.git
cd luma-backend
```

### Step 2 — 가상환경 생성

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate

# 활성화 확인: 터미널 앞에 (venv) 표시되면 성공 ✅
```

### Step 3 — 패키지 설치

```bash
pip install -r requirements.txt
```

> 설치 시간: 약 1~2분 소요

### Step 4 — 환경변수 설정

```bash
# 템플릿 복사
cp .env.example .env

# .env 파일은 지금 수정 안 해도 됩니다
# API 키 없이 Mock 모드로 모든 기능 실행 가능합니다
```

### Step 5 — 서버 실행

```bash
python app.py
```

성공 시 아래 배너가 출력됩니다:

```
╔══════════════════════════════════════════════════╗
║           🌿  LUMA  읽는 행위를 넘어              ║
║              생각의 우주를 연결하다                ║
╠══════════════════════════════════════════════════╣
║  환경    : development                           ║
║  Gemini  : ⚠️  Mock 모드                         ║
║  Firebase: ⚠️  Mock 모드                         ║
║  Maps    : ⚠️  Mock 모드                         ║
╠══════════════════════════════════════════════════╣
║  http://localhost:5000                           ║
╚══════════════════════════════════════════════════╝
```

### Step 6 — 브라우저에서 확인

| URL | 설명 |
|-----|------|
| **http://localhost:5000/landing** | 🏠 서비스 소개 랜딩 페이지 |
| **http://localhost:5000/auth/signup** | 📝 회원가입 |
| **http://localhost:5000/auth/login** | 🔑 로그인 |
| **http://localhost:5000** | ✦ 별자리 대시보드 |
| **http://localhost:5000/community** | 👥 공독의 장 + 독서 지도 |
| **http://localhost:5000/ocr** | 📷 OCR 스캔 |
| **http://localhost:5000/deepdive** | 🌙 딥다이브 독서 모드 |
| **http://localhost:5000/auth/profile** | 👤 내 프로필 |
| **http://localhost:5000/health** | 💚 헬스체크 |

---

## 3. API 키 설정 (선택)

`.env` 파일을 열어 아래 키를 입력하면 Mock → 실제 AI로 **자동 전환**됩니다.

### Gemini API 키 (AI 분석 활성화)

1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. **Create API Key** 클릭
3. `.env`에 입력:
```env
GEMINI_API_KEY=AIza...실제키...
```

**활성화되는 기능:**
- ✦ 메모 저장 시 Cross-domain Insight 자동 생성
- 🤖 심화 질문 / 주제 분석 / 강제연결
- 📋 독서 모임 자동 보고서
- 📷 OCR 텍스트 정제 + 메모 초안 생성

### Google Maps API 키 (지도 실시간 검색)

1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. **새 프로젝트 생성** → API 및 서비스 → 사용자 인증 정보
3. **Places API, Maps JavaScript API** 활성화
4. `.env`에 입력:
```env
GOOGLE_MAPS_API_KEY=AIza...실제키...
```

### Firebase 설정 (실시간 DB + 인증)

1. [Firebase Console](https://console.firebase.google.com) → 새 프로젝트 생성
2. 프로젝트 설정 → 서비스 계정 → **새 비공개 키 생성**
3. 다운로드한 JSON 파일을 프로젝트 루트에 `firebase-credentials.json`으로 저장
4. `.env`에 입력:
```env
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
```

> ⚠️ `firebase-credentials.json`은 절대 Git에 올리지 마세요! (`.gitignore`에 이미 등록됨)

---

## 4. 전체 페이지 안내

### 🏠 랜딩 페이지 (`/landing`)
서비스 소개 + 별자리 데모 + 후기 + 회원가입 유도

### 🔑 로그인/회원가입 (`/auth/login`, `/auth/signup`)
- 이메일/비밀번호 기반 인증
- JWT 토큰 쿠키 관리
- Mock 모드: 어떤 이메일/비밀번호도 동작

**테스트 계정:**
```
이메일: test@luma.io
비밀번호: Test1234!
```

### ✦ 별자리 대시보드 (`/`)
- D3.js Force-directed Graph로 메모 연결 시각화
- 좌측: 독서 통계 + 현재 읽는 책 + 장르 분포
- 중앙: 별자리 맵 (드래그/클릭 가능)
- 우측: AI 인사이트 + 강제연결 + 독서 모임
- `+ 버튼`: 메모 작성 모달 (저장 시 별 반짝임 효과)
- `✎ 버튼`: 메모 목록 슬라이드 패널

### 👥 공독의 장 + 독서 지도 (`/community`)
**라운지 탭:**
- 좌측 사이드바에서 독서 모임 선택/생성
- 카드 타입: 생각/인용/인사이트/질문/감상
- `✦ AI 토론 가이드`: AI 질문 카드 자동 생성
- `📋 보고서`: 모임 전체 대화 AI 자동 요약

**독서 지도 탭:**
- SVG 세계 지도에 전세계 13개 독서 명소 핀 표시
- 카페/도서관/서점카페 필터 + 도시 필터
- 핀 클릭 → 독서 적합도 + AI 태그 + 후기
- `📍 내 위치`: GPS 기반 주변 명소 자동 검색
- 체크인 + 후기 등록 기능

### 📷 OCR 스캔 (`/ocr`)
**파일 업로드 모드:**
- JPG/PNG 파일 드래그앤드롭 또는 클릭 업로드
- 텍스트 추출 → 메모 초안 자동 생성
- 관련 YouTube 영상 + 학술 자료 자동 검색

**카메라 모드:**
- 카메라 권한 허용 후 실시간 촬영
- 스캔 가이드라인으로 정확한 위치 안내
- 촬영 즉시 분석 시작

**책 표지 모드:**
- 표지 이미지로 제목/저자/출판사 자동 인식

**전체 파이프라인:**
스캔 → 텍스트 추출 → AI 교정 → 메모 초안 → 관련 자료 → 별자리 저장

### 🌙 딥다이브 독서 모드 (`/deepdive`)
- **포모도로 타이머**: 25분/45분/60분 프리셋
- **ASMR 사운드**: 빗소리/카페/화이트노이즈/자연
- **알림 차단**: 포커스 모드 ON 시 UI 숨김
- **실시간 메모**: 독서 중 빠른 메모 작성
- **배경색 테마**: 딥다이브 모드 시 더 어두운 화면

### 👤 프로필 (`/auth/profile`)
- 내 독서 통계 (읽은 책/메모/연속독서일/AI연결)
- 서재 (읽는 중 / 완독 목록 + 진행률)
- 최근 메모 목록
- 장르 분포 차트
- 이달의 목표 진행률

---

## 5. API 엔드포인트 목록

### 시스템
```
GET  /health              헬스체크
GET  /api/system/status   전체 API 연동 상태
```

### 인증
```
GET  /auth/login          로그인 페이지
GET  /auth/signup         회원가입 페이지
POST /auth/api/signup     회원가입 (JSON)
POST /auth/api/login      로그인 (JSON)
POST /auth/api/logout     로그아웃
GET  /auth/api/me         현재 사용자 정보
GET  /auth/api/check      이메일/닉네임 중복 확인
```

### 메모
```
POST /api/memos/save           메모 저장
GET  /api/memos/list           메모 목록 (?user_id=)
DELETE /api/memos/<id>         메모 삭제
GET  /api/memos/stats          독서 통계
```

### AI (Gemini)
```
POST /api/ai/analyze           메모 저장 + AI 분석 통합 ★
POST /api/ai/reframe           심화 질문 생성
POST /api/ai/cross-insight     두 메모 강제연결 인사이트
GET  /api/ai/connections       전체 메모 연결 맵
GET  /api/ai/status            Gemini 연결 상태
POST /api/ai/discussion        모임 토론 가이드
POST /api/ai/report            모임 자동 보고서
```

### 공독의 장
```
POST /community/api/create                    모임 생성
POST /community/api/<id>/join                 모임 참여
POST /community/api/<id>/cards                카드 작성
POST /community/api/cards/<id>/like           좋아요 토글
POST /community/api/cards/<id>/comment        댓글 추가
POST /community/api/<id>/ai-guide             AI 토론 가이드 카드
POST /community/api/<id>/report               AI 모임 보고서 생성
GET  /community/api/<id>/report               최신 보고서 조회
```

### 독서 장소 지도
```
GET  /api/places/all                  전체 명소 목록 (?type= ?city=)
GET  /api/places/nearby               위치 기반 검색 (?lat= ?lng= ?radius=)
GET  /api/places/<id>                 장소 상세
POST /api/places/<id>/checkin         체크인
POST /api/places/<id>/review          리뷰 추가
GET  /api/places/cities               도시 목록
GET  /api/places/status               Maps API 상태
```

### OCR 스캔
```
POST /api/ocr/scan             이미지 → 텍스트 추출
POST /api/ocr/enhance          텍스트 정제/교정
POST /api/ocr/book-cover       책 표지 정보 감지
POST /api/ocr/analyze-page     페이지 구조 분석
POST /api/ocr/generate-memo    텍스트 → 메모 초안
POST /api/ocr/full-pipeline    전체 파이프라인 ★ (스캔+메모+영상)
GET  /api/ocr/status           OCR 상태
```

### 요청 예시 (curl)

```bash
# 메모 저장 + AI 분석
curl -X POST http://localhost:5000/api/ai/analyze \
  -H "Content-Type: application/json" \
  -d '{"book_title":"사피엔스","content":"허구가 인류를 협력하게 했다","tags":["인류학"],"mood":"inspired"}'

# 장소 검색 (서울 기준)
curl "http://localhost:5000/api/places/nearby?lat=37.5665&lng=126.9780&radius=5000"

# OCR 이미지 업로드
curl -X POST http://localhost:5000/api/ocr/full-pipeline \
  -F "image=@/path/to/book_page.jpg" \
  -F "book_title=사피엔스"
```

---

## 6. Docker로 배포

### 개발 환경
```bash
# 이미지 빌드 + 실행
docker-compose up

# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f luma-app
```

### 프로덕션 (Nginx 포함)
```bash
# .env 파일에 프로덕션 설정 먼저 입력
# FLASK_ENV=production
# FLASK_DEBUG=false
# SECRET_KEY=강력한랜덤키

docker-compose --profile production up -d
```

### 직접 Docker 실행
```bash
docker build -t luma-app .
docker run -p 5000:5000 --env-file .env luma-app
```

---

## 7. 트러블슈팅

### ❌ `ModuleNotFoundError: No module named 'flask'`
```bash
# 가상환경이 활성화되어 있는지 확인
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
```

### ❌ `Address already in use` (포트 충돌)
```bash
# 다른 포트로 실행
python app.py --port 8000

# 또는 .env 에서 PORT 변경
PORT=8000
```

### ❌ 카메라가 작동하지 않음
- 브라우저에서 카메라 권한을 허용했는지 확인
- `http://` 에서는 카메라 미지원 → `https://` 또는 `localhost` 사용

### ❌ Gemini API 오류 (`API_KEY_INVALID`)
```bash
# .env 파일에서 키 확인
cat .env | grep GEMINI

# API 키 재발급: https://aistudio.google.com/app/apikey
```

### ❌ Firebase 연결 실패
```bash
# firebase-credentials.json 파일 위치 확인
ls firebase-credentials.json

# .env에서 경로 확인
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
```

### ❌ OCR 이미지 업로드 실패
- 이미지 크기가 10MB 이하인지 확인
- 지원 형식: JPG, PNG, WEBP
- Pillow 설치 확인: `pip install Pillow`

### ✅ 테스트로 전체 동작 확인
```bash
python -m pytest tests/ -v
# 50개 테스트 전부 PASSED 확인
```

---

## 8. 프로젝트 구조

```
luma-backend/
│
├── 📄 app.py                    ← 서버 진입점
├── 📄 .env.example              ← 환경변수 템플릿
├── 📄 .env                      ← 실제 환경변수 (직접 생성)
├── 📄 requirements.txt          ← Python 의존성
├── 📄 Dockerfile                ← Docker 이미지
├── 📄 docker-compose.yml        ← 컨테이너 구성
├── 📄 nginx.conf                ← 리버스 프록시
├── 📄 .gitignore
├── 📄 README.md
│
├── 📁 app/
│   ├── 📁 core/
│   │   └── config.py            ← 환경변수 관리
│   │
│   ├── factory.py               ← Flask 앱 팩토리
│   │
│   ├── 📁 routes/               ← API 라우터
│   │   ├── main.py              ← 대시보드 (별자리)
│   │   ├── auth.py              ← 로그인/회원가입
│   │   ├── memos.py             ← 메모 CRUD
│   │   ├── ai.py                ← Gemini AI 엔드포인트
│   │   ├── community.py         ← 공독의 장 통합
│   │   ├── places.py            ← 독서 장소 지도
│   │   ├── ocr.py               ← OCR 스캔
│   │   └── books.py             ← 책 검색
│   │
│   ├── 📁 services/             ← 비즈니스 로직
│   │   ├── firebase_service.py  ← Firestore DB
│   │   ├── gemini_service.py    ← Gemini AI
│   │   ├── embedding_service.py ← 메모 유사도
│   │   ├── auth_service.py      ← 인증 서비스
│   │   ├── club_service.py      ← 독서 모임
│   │   ├── place_service.py     ← 장소 검색
│   │   ├── ocr_service.py       ← OCR 처리
│   │   └── youtube_service.py   ← 관련 영상 검색
│   │
│   └── 📁 templates/            ← HTML 페이지
│       ├── landing.html         ← 서비스 소개
│       ├── auth.html            ← 로그인/회원가입
│       ├── profile.html         ← 내 프로필
│       ├── dashboard.html       ← 별자리 대시보드
│       ├── community.html       ← 공독의 장 + 지도
│       ├── ocr.html             ← OCR 스캔
│       └── deepdive.html        ← 딥다이브 모드
│
└── 📁 tests/
    ├── conftest.py              ← pytest 픽스처
    └── test_all.py              ← 전체 테스트 (50개)
```

---

## 🚀 구현 현황

| STEP | 기능 | 상태 |
|------|------|------|
| 1 | 프로젝트 구조 + Flask 기초 | ✅ 완료 |
| 2 | 메모 저장 + Firebase Mock | ✅ 완료 |
| 3 | Gemini AI 강제연결 | ✅ 완료 |
| 4+5 | 공독의 장 + 독서 지도 통합 | ✅ 완료 |
| 6 | OCR 스캔 (카메라 + 파일) | ✅ 완료 |
| 7 | 딥다이브 독서 모드 | ✅ 완료 |
| 8 | 회원가입/로그인/프로필 | ✅ 완료 |
| 9 | Docker + 테스트 + 배포 준비 | ✅ 완료 |

**테스트:** `pytest tests/ -v` → **50개 PASSED** ✅

---

<div align="center">
  <strong>🌿 LUMA</strong> — 읽는 행위를 넘어, 생각의 우주를 연결하다.<br><br>
  문의: <a href="mailto:hello@luma.io">hello@luma.io</a>
</div>
