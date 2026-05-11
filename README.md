# 🌿 LUMA — AI 기반 차세대 독서 소셜 플랫폼

> **"읽는 행위를 넘어, 생각의 우주를 연결하다."**

---

## 📌 서비스 소개

LUMA는 독서 메모를 AI가 분석하여 **별자리처럼 연결**하고,  
독서 모임을 **카드형 라운지**로 운영하며,  
세계 어디서든 **독서하기 좋은 장소**를 추천하는 플랫폼입니다.

| 기능 | 설명 |
|------|------|
| ✦ 별자리 지도 | 메모 간 연관관계를 Force-directed Graph로 시각화 |
| 🤖 AI 강제연결 | 다른 책의 메모를 AI가 연결해 Cross-domain Insight 생성 |
| 👥 공독의 장 | 카드형 독서 모임 라운지 + AI 토론 가이드 + 자동 보고서 |
| 🗺 독서 지도 | 전세계 독서 명소 지도 + 체크인 + AI 리뷰 태그 |

---

## 🚀 빠른 시작 (5분 안에 실행)

### 1단계 — 프로젝트 클론 & 환경 설정

```bash
git clone https://github.com/yourname/luma-backend.git
cd luma-backend

# 환경변수 파일 생성
cp .env.example .env
```

### 2단계 — 가상환경 생성 & 패키지 설치

```bash
# 가상환경 생성
python -m venv venv

# 활성화 (Windows)
venv\Scripts\activate

# 활성화 (Mac/Linux)
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

### 3단계 — 서버 실행

```bash
python app.py
```

### 4단계 — 브라우저에서 확인

| URL | 페이지 |
|-----|--------|
| `http://localhost:5000` | ✦ 별자리 대시보드 |
| `http://localhost:5000/community` | 👥 공독의 장 + 🗺 독서 지도 |
| `http://localhost:5000/health` | 헬스체크 |
| `http://localhost:5000/api/system/status` | API 연동 상태 |

> ✅ API 키 없이도 **Mock 모드**로 모든 기능 즉시 사용 가능!

---

## 🔑 API 키 연동 (선택 — 실제 AI 기능 활성화)

`.env` 파일에 키를 입력하면 Mock → 실제 AI로 **자동 전환**됩니다.

```env
# Gemini AI (메모 분석, 강제연결, 보고서 생성)
# 발급: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=AIza...실제키...

# Google Maps (독서 장소 실시간 검색)
# 발급: https://console.cloud.google.com
GOOGLE_MAPS_API_KEY=AIza...실제키...

# Firebase (실시간 DB + 인증)
# Firebase Console → 서비스 계정 → JSON 다운로드
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
```

---

## 🗂 프로젝트 구조

```
luma-backend/
│
├── app.py                      ← 엔트리포인트
├── .env.example                ← 환경변수 템플릿
├── requirements.txt            ← Python 의존성
├── Dockerfile                  ← Docker 이미지
├── docker-compose.yml          ← 멀티 컨테이너 설정
├── nginx.conf                  ← 리버스 프록시
│
├── app/
│   ├── core/
│   │   └── config.py           ← 환경변수 설정 관리
│   │
│   ├── factory.py              ← Flask 앱 팩토리
│   │
│   ├── routes/                 ← API 라우터
│   │   ├── main.py             ← 대시보드 (별자리)
│   │   ├── memos.py            ← 메모 CRUD
│   │   ├── ai.py               ← Gemini AI 엔드포인트
│   │   ├── community.py        ← 공독의 장 + 지도 통합
│   │   └── places.py           ← 독서 장소 API
│   │
│   ├── services/               ← 비즈니스 로직
│   │   ├── firebase_service.py ← Firestore DB (Mock 폴백)
│   │   ├── gemini_service.py   ← Gemini AI (Mock 폴백)
│   │   ├── embedding_service.py← 메모 유사도 계산
│   │   ├── club_service.py     ← 독서 모임 서비스
│   │   └── place_service.py    ← 장소 검색 서비스
│   │
│   └── templates/
│       ├── dashboard.html      ← 별자리 대시보드
│       └── community.html      ← 공독의 장 + 독서 지도
│
└── tests/
    ├── conftest.py             ← pytest 공용 픽스처
    └── test_all.py             ← 전체 테스트 (38개)
```

---

## 🌐 API 엔드포인트 전체 목록

### 시스템
| Method | URL | 설명 |
|--------|-----|------|
| GET | `/health` | 헬스체크 |
| GET | `/api/system/status` | 전체 API 연동 상태 |

### 메모
| Method | URL | 설명 |
|--------|-----|------|
| POST | `/api/memos/save` | 메모 저장 |
| GET | `/api/memos/list` | 메모 목록 |
| DELETE | `/api/memos/<id>` | 메모 삭제 |
| GET | `/api/memos/stats` | 독서 통계 |

### AI (Gemini)
| Method | URL | 설명 |
|--------|-----|------|
| POST | `/api/ai/analyze` | 메모 저장 + AI 분석 통합 |
| POST | `/api/ai/reframe` | 심화 질문 생성 |
| POST | `/api/ai/cross-insight` | 두 메모 강제연결 인사이트 |
| GET | `/api/ai/connections` | 전체 메모 연결 맵 |
| GET | `/api/ai/status` | Gemini 연결 상태 |
| POST | `/api/ai/discussion` | 모임 토론 가이드 |
| POST | `/api/ai/report` | 모임 자동 보고서 |

### 공독의 장 (독서 모임)
| Method | URL | 설명 |
|--------|-----|------|
| POST | `/community/api/create` | 모임 생성 |
| POST | `/community/api/<id>/join` | 모임 참여 |
| POST | `/community/api/<id>/cards` | 카드 작성 |
| POST | `/community/api/cards/<id>/like` | 좋아요 토글 |
| POST | `/community/api/cards/<id>/comment` | 댓글 추가 |
| POST | `/community/api/<id>/ai-guide` | AI 토론 가이드 카드 |
| POST | `/community/api/<id>/report` | AI 모임 보고서 생성 |

### 독서 장소 지도
| Method | URL | 설명 |
|--------|-----|------|
| GET | `/api/places/all` | 전체 명소 목록 |
| GET | `/api/places/nearby` | 위치 기반 주변 검색 |
| GET | `/api/places/<id>` | 장소 상세 |
| POST | `/api/places/<id>/checkin` | 체크인 |
| POST | `/api/places/<id>/review` | 리뷰 추가 |
| GET | `/api/places/cities` | 도시 목록 |
| GET | `/api/places/status` | Maps API 상태 |

---

## 🧪 테스트 실행

```bash
# 전체 테스트 (38개)
pytest tests/ -v

# 특정 클래스만
pytest tests/test_all.py::TestAIAPI -v

# 커버리지 포함
pytest tests/ --cov=app --cov-report=term-missing
```

---

## 🐳 Docker 배포

### 개발 환경
```bash
docker-compose up
```

### 프로덕션 (Nginx 포함)
```bash
# .env 파일에 프로덕션 설정 입력 후
docker-compose --profile production up -d
```

### 직접 빌드
```bash
docker build -t luma-app .
docker run -p 5000:5000 --env-file .env luma-app
```

---

## 🛠 기술 스택

| 분류 | 기술 |
|------|------|
| **Backend** | Python 3.12, Flask 3.0 |
| **AI** | Google Gemini 1.5 Flash |
| **Database** | Firebase Firestore (Mock 폴백) |
| **지도** | Google Maps Platform (Mock 폴백) |
| **시각화** | D3.js v7 (Force-directed Graph) |
| **프론트** | Jinja2, Vanilla JS, CSS Grid |
| **배포** | Docker, Gunicorn, Nginx |
| **테스트** | pytest |

---

## 📋 개발 로드맵

| STEP | 기능 | 상태 |
|------|------|------|
| 1 | 프로젝트 구조 + FastAPI 기초 | ✅ 완료 |
| 2 | 메모 저장 + Firebase Mock | ✅ 완료 |
| 3 | Gemini AI 강제연결 | ✅ 완료 |
| 4 | 공독의 장 카드형 라운지 | ✅ 완료 |
| 5 | Google Maps 독서 지도 | ✅ 완료 |
| 9 | Docker + 배포 준비 + 테스트 | ✅ 완료 |
| 6 | OCR 스캔 (카메라 → 텍스트) | 🔜 예정 |
| 7 | 딥다이브 독서 모드 (ASMR) | 🔜 예정 |
| 8 | 사용자 인증 (로그인/회원가입) | 🔜 예정 |

---

## 🎨 디자인 가이드

| 컬러 | HEX | 용도 |
|------|-----|------|
| Forest Green | `#2D4A3E` | Primary |
| Amber Gold | `#C17F3B` | Accent |
| Cream | `#F5E6C8` | Background Light |
| Deep Dark | `#0D1B14` | Background Dark |

**폰트:** Noto Serif KR (제목) + Pretendard (본문) + DM Serif Display (로고)

---

## 📄 라이센스

MIT License — 자유롭게 사용하세요.

---

<div align="center">
  <strong>🌿 LUMA</strong> — 읽는 행위를 넘어, 생각의 우주를 연결하다.<br>
  Made with ❤️ and Python
</div>
