# 🌿 LUMA — 다음 단계 작업계획서
## 백엔드(Codex) + 프론트엔드(Claude Code) 전용 프롬프트

> **현재 상태**: 페이지 12개 ✅ · API 21개 ✅ · Mock 모드 완전 동작
> **목표**: MySQL 실제 연결 · JWT 인증 완성 · 페이지-API 완전 연동 · UX 완성

---

## ✅ 2026-05-09 현재 완료된 기반 작업

### MySQL 연결 안정화 완료

- `app/db.py`의 `init_db()`는 MySQL 연결을 3회 재시도한다.
- DB가 아직 생성되지 않은 상태여도 MySQL 서버에 먼저 연결한 뒤 `app/schema.py`의 `create_database()`가 DB를 생성할 수 있다.
- 연결 성공 시 `SELECT VERSION()`으로 MySQL 버전을 출력한다.
- Windows CP949 콘솔에서도 앱 시작이 깨지지 않도록 DB 초기화 로그는 `[OK]`, `[WARN]` 형식으로 정리했다.

### 초기 데이터와 인증 기반 완료

- `app/schema.py`에 `seed_data()` 추가 완료.
- 앱 시작 시 테이블 생성 후 `user_demo`, 샘플 책 3권, 기본 서재 데이터가 자동 입력된다.
- `/api/v2/auth/login`, `/api/v2/auth/register`, `/api/v2/auth/refresh` 기준 JWT 흐름이 정리되었다.
- 프론트 공통 호출은 `localStorage.luma_token` + `Authorization: Bearer` 패턴을 사용한다.

### `/api/v2` 핵심 라우트 보강 완료

- 서재 검색: `/api/v2/shelf/books/search`
- 독서 진행률: `/api/v2/shelf/books/<book_id>/progress`
- 소크라테스 세션 목록/재개: `/api/v2/socrates/sessions`, `/api/v2/socrates/sessions/<session_id>/resume`
- 라이브 방 폴링/나가기: `/api/v2/live/rooms/<room_id>/poll`, `/api/v2/live/rooms/<room_id>/leave`
- `heart.html`, `socrates.html`, `live.html`은 핵심 호출을 `/api/v2` 기준으로 전환했다.
- `social.html`은 현재 구조상 `/api/social/*`를 유지하되 JWT 사용자 정보와 `authHeaders()`를 반영했다.

---

## 📊 현재 완성 수준 진단

| 영역 | 완성도 | 남은 작업 |
|------|--------|----------|
| Flask 서버 구조 | ✅ 100% | — |
| HTML 페이지 12개 | ✅ 100% | API 연동 완성 필요 |
| Mock API (인메모리) | ✅ 100% | — |
| MySQL API (/api/v2) | ✅ 95% | 화면별 실사용 검증 |
| JWT 로그인 흐름 | ✅ 85% | 만료/로그아웃 UX 검증 |
| 페이지 ↔ API 연동 | 🟡 75% | dashboard/social/mobile 보강 |
| Gemini AI 연동 | 🟡 70% | 별자리 테마/추천 고도화 |
| Google Maps | 🔴 30% | community.html 연동 필요 |
| 반응형 모바일 | 🟡 60% | 모바일 뷰 개선 필요 |

---

# 0. 현재 코드 기준 정리 원칙

## 라우트 전략

- 핵심 앱 데이터(인증, 서재, 감정, 별자리, 리포트, 소크라테스, 라이브)는 `/api/v2/*`를 표준으로 통일한다.
- 기존 `/api/heart/*`, `/api/live/*`, `/api/socrates/*`는 화면 전환이 끝날 때까지 호환용으로 유지한다.
- `social.html`은 현재 `app/routes/new_features.py`의 `/api/social/*` 구현이 살아 있으므로 당분간 `/api/social/*`를 유지한다.
- 소셜까지 MySQL/JWT 표준에 넣을 때는 별도 백엔드 작업으로 `/api/v2/social/*`를 먼저 신설한 뒤 프론트를 전환한다.

## JWT 우선순위 조정

- 프론트의 `authHeaders()`와 `localStorage.luma_token` 흐름이 모든 `/api/v2` 호출의 전제가 된다.
- 따라서 JWT refresh/decode/auth helper 정리는 Phase 3이 아니라 Phase 1에서 B-1 직후 진행한다.
- 개발 모드에서는 `user_demo` 폴백을 유지하되, 토큰이 명시적으로 들어왔는데 만료/오염된 경우에는 명확한 에러를 반환한다.

## 한 단계씩 진행 순서

1. B-1: MySQL 연결 개선 + `seed_data()` 추가
2. B-2: JWT `refresh_token`/`decode_token`/auth helper 정리 + `/api/v2/auth/refresh`
3. F-1/F-2: 로그인과 NAV를 `/api/v2/auth` 기준으로 통일
4. B-3/B-5/B-6: 프론트가 필요로 하는 `/api/v2` 누락 API 보강
5. F-3/F-4/F-5: `heart.html`, `socrates.html`, `live.html`을 화면 단위로 `/api/v2` 전환
6. F-6: 당분간 `/api/social/*` 유지. 이후 필요하면 `/api/v2/social/*` 신설 후 전환

---

# 1. 백엔드 작업 — Codex 전용 프롬프트

> **사용법**: VS Code에서 GitHub Copilot Chat(Codex) 열고 아래 프롬프트를 복붙

---

## TASK B-1 · MySQL 실제 연결 검증 및 시드 데이터

```
# LUMA 백엔드 — MySQL 연결 검증 및 초기 데이터
# 파일: app/db.py, app/schema.py

## 프로젝트 컨텍스트
- Flask 3.0 앱, 파일: luma-backend/
- app/db.py: PyMySQL 연결 풀, is_connected() / get_db() / execute_one/all/write()
- app/schema.py: 15개 테이블 DDL (CREATE TABLE IF NOT EXISTS)
- 이중 모드: MySQL 연결 시 실제 DB, 실패 시 인메모리 Mock 자동 전환

## 작업 요청
1. app/db.py의 init_db() 함수 개선:
   - 연결 실패 시 구체적인 오류 메시지 출력 (host/port/db명 포함)
   - 재시도 로직 추가 (3회, 1초 간격)
   - 연결 성공 시 MySQL 버전 출력

2. app/schema.py에 seed_data() 함수 추가:
   - users 테이블에 데모 유저 1명 INSERT IGNORE
     (user_id='user_demo', email='demo@luma.kr', display_name='소연', emoji='🦋')
   - books 테이블에 샘플 책 3권 INSERT IGNORE
     (사피엔스, 어린왕자, 코스모스 - cover_emoji 포함)
   - shelf_books에 user_demo의 서재 데이터 3개 INSERT IGNORE

3. factory.py의 init_db 블록에서 seed_data() 호출 추가

## 필수 규칙
- SQL은 항상 파라미터 바인딩 (%s), f-string 절대 금지
- INSERT IGNORE 사용 (중복 방지)
- json.dumps(ensure_ascii=False) 한글 JSON
- ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
- try-except로 감싸고 실패 시 Mock 모드 계속 유지
```

---

## TASK B-2 · JWT 인증 미들웨어 완성

```
# LUMA 백엔드 — JWT 인증 미들웨어
# 파일: app/services/user_service.py, app/routes/mysql_api.py

## 현재 상태
- user_service.py: generate_token(), verify_token() 구현됨
- mysql_api.py: _get_uid() 함수로 토큰 추출 중
- 문제: 인증 없는 엔드포인트도 user_demo 기본값으로 동작 (개발용)

## 작업 요청
1. app/services/user_service.py에 추가:
   - refresh_token(old_token) 함수 → 만료 1시간 전이면 새 토큰 발급
   - decode_token(token) → user_id, email, exp 딕셔너리 반환
   - token_required 데코레이터 (선택적 인증 모드 지원)

2. mysql_api.py의 _get_uid() 개선:
   - Authorization: Bearer {token} 헤더 우선 파싱
   - 없으면 쿼리 파라미터 user_id 사용
   - 없으면 'user_demo' 기본값 (개발 모드 허용)
   - 토큰 만료 시 {"ok": false, "error": "토큰이 만료되었습니다."} 반환

3. /api/v2/auth/refresh 엔드포인트 추가:
   POST body: {"token": "기존토큰"}
   반환: {"ok": true, "token": "새토큰"}

## 필수 규칙
- jwt.decode 실패 시 None 반환 (예외 던지지 않음)
- 만료된 토큰도 user_id는 추출 가능하게 (options={"verify_exp": False})
- 응답: {"ok": True/False, ...} 형식 통일
```

---

## TASK B-3 · 서재 API 완성 (shelf_service.py)

```
# LUMA 백엔드 — 서재 서비스 완성
# 파일: app/services/shelf_service.py, app/routes/mysql_api.py

## 현재 상태
- get_shelf(), add_book(), update_shelf_book(), delete_shelf_book() 구현됨
- Mock 모드: 인메모리 _books_mem, _shelf_mem 작동 중
- MySQL 모드: 기본 CRUD 작동 중

## 추가 작업 요청
1. get_shelf() 응답에 ok:True 추가 (현재 누락):
   return {"ok": True, "books": books, "stats": stats}

2. search_books_google(query) 함수 추가:
   - GOOGLE_BOOKS_API_KEY 환경변수 있으면 Google Books API 호출
   - https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5
   - 반환: [{"title","author","cover_url","isbn","total_pages"}]
   - API 키 없으면 Mock 검색 결과 반환

3. update_reading_progress(book_id, user_id, pages_read) 함수:
   - 읽은 페이지로 progress % 자동 계산
   - total_pages가 0이면 progress 그대로 유지
   - status가 'want'면 자동으로 'reading'으로 변경

4. /api/v2/shelf/books/search 엔드포인트:
   GET ?q=검색어&source=google|local
   Google Books와 로컬 DB 통합 검색

## 필수 규칙
- is_connected() 체크로 MySQL/Mock 이중 모드 유지
- requests.get() 호출 시 timeout=5 설정
- API 호출 실패 시 Mock 데이터로 폴백
- json.dumps(ensure_ascii=False)
```

---

## TASK B-4 · 감정-별자리 자동 연결 고도화

```
# LUMA 백엔드 — 감정 기록 시 별자리 자동 연결 강화
# 파일: app/services/reading_service.py

## 현재 상태
- add_emotion(): 감정 기록 → _auto_connect() 자동 약한 연결 생성
- get_constellation(): D3용 nodes/links 반환
- 문제: Gemini AI 연동이 안 된 상태

## 작업 요청
1. add_emotion() 호출 후 Gemini로 테마 자동 생성:
   - 두 책의 감정 메모를 Gemini에 전달
   - "이 두 책의 공통 주제를 한 줄로 표현해줘" 프롬프트
   - book_connections.theme 컬럼 자동 업데이트
   - Gemini 없으면 "연결 탐색 중" 기본값

2. get_constellation()에 월간 통계 추가:
   반환값에 추가:
   {
     "this_month_reads": 이번달 완독 수,
     "total_emotions": 전체 감정 기록 수,
     "top_genre": 가장 많이 읽은 장르
   }

3. auto_suggest_books(user_id) 함수 신규:
   - 사용자의 장르 분포, 감정 패턴 분석
   - Gemini에게 다음 읽을 책 3권 추천 요청
   - 반환: [{"title","author","reason","genre"}]
   - Mock 모드: 하드코딩된 추천 목록 반환

## 필수 규칙
- Gemini 호출: app/services/gemini_service.py의 _call_gemini() 사용
- 실패 시 Mock 응답 반환 (절대 예외 X)
- json.dumps(ensure_ascii=False)
- is_connected() 체크 필수
```

---

## TASK B-5 · 소크라테스 세션 DB 영속성 완성

```
# LUMA 백엔드 — 소크라테스 세션 MySQL 저장 완성
# 파일: app/services/live_socrates_service.py

## 현재 상태
- start_session(), answer_session(): MySQL/Mock 이중 모드 구현됨
- exchanges를 JSON으로 DB 저장 중
- 문제: 세션 목록 조회, 세션 재개 기능 없음

## 작업 요청
1. list_sessions(user_id, limit=10) 함수 추가:
   MySQL: SELECT * FROM socrates_sessions WHERE user_id=%s ORDER BY created_at DESC LIMIT %s
   Mock: _socrates_mem 딕셔너리에서 user_id 필터
   반환: [{"session_id","book_title","passage_preview","stage","completed","created_at"}]

2. resume_session(session_id) 함수 추가:
   - 미완료 세션을 불러와 현재 단계의 질문 반환
   - completed=True면 final_insight 반환
   - 없으면 {"ok": False, "error": "세션을 찾을 수 없습니다."}

3. /api/v2/socrates/sessions 엔드포인트 추가:
   GET ?user_id=xxx → list_sessions()
   
4. /api/v2/socrates/sessions/{session_id}/resume 엔드포인트:
   GET → resume_session()

## 필수 규칙
- exchanges 컬럼: JSON 문자열로 저장/로드 (json.dumps/loads)
- passage 미리보기: 40자 자르기 + "..."
- is_connected() 체크 필수
- 응답 통일: {"ok": True, ...}
```

---

## TASK B-6 · 실시간 라이브 방 폴링 API

```
# LUMA 백엔드 — 라이브 독서방 실시간 업데이트
# 파일: app/services/live_socrates_service.py, app/routes/mysql_api.py

## 현재 상태
- create_room, join_room, send_message, end_room 구현됨
- 문제: 실시간 메시지 동기화 없음 (다른 참여자 메시지 못 받음)

## 작업 요청
1. get_room_updates(room_id, since_msg_id) 함수:
   - since_msg_id 이후의 새 메시지만 반환 (폴링용)
   MySQL: SELECT * FROM live_messages WHERE room_id=%s AND id > %s ORDER BY id
   Mock: _rooms_mem[room_id]["messages"]에서 index 이후 반환
   반환: {"messages": [...], "keywords": [...], "member_count": N}

2. /api/v2/live/rooms/{room_id}/poll 엔드포인트:
   GET ?since=마지막_msg_id
   → get_room_updates() 호출

3. leave_room(room_id, peer_id) MySQL 구현:
   UPDATE live_members SET left_at=NOW() WHERE peer_id=%s
   방에 남은 멤버 0명이면 room status='ended'

## 필수 규칙
- 폴링 간격: 프론트에서 3초마다 호출 예정
- LIMIT 50으로 최대 메시지 수 제한
- is_connected() 체크 필수
```

---

# 2. 프론트엔드 작업 — Claude Code 전용 프롬프트

> **사용법**: Claude Code(claude.ai)에서 파일을 업로드하거나 아래 프롬프트 사용

---

## TASK F-1 · 로그인/회원가입 → JWT 토큰 저장 연동

```
# LUMA 프론트엔드 — auth.html JWT 인증 완성
# 파일: app/templates/auth.html (현재 251줄)

## 현재 상태
- 로그인/회원가입 폼 UI 완성됨
- API 호출 없이 화면만 있는 상태

## 디자인 시스템 (변경 금지)
CSS 변수: --bg:#0B1612 --bg2:#0F1E18 --forest:#2D4A3E --amber:#C17F3B
--text:#E8DCC8 --sub:#8FA89A --border:rgba(255,255,255,.07)
폰트: DM Serif Display(제목) · Noto Serif KR(본문) · Pretendard(UI)

## 작업 요청
1. 로그인 폼 submit → POST /api/v2/auth/login 호출:
   body: {"email": ..., "password": ...}
   성공 시:
     localStorage.setItem('luma_token', d.token)
     localStorage.setItem('luma_user', JSON.stringify(d.user))
     window.location.href = '/heart'
   실패 시: 폼 아래 에러 메시지 표시 (빨간 텍스트)

2. 회원가입 폼 submit → POST /api/v2/auth/register 호출:
   body: {"email","password","display_name","emoji":"⭐"}
   성공 시: 자동 로그인 후 /heart로 이동
   실패 시: 에러 메시지 표시

3. 페이지 로드 시 이미 로그인된 경우 /heart로 리다이렉트:
   if (localStorage.getItem('luma_token')) window.location.href = '/heart'

4. 로딩 상태: 버튼 클릭 후 "로그인 중..." 텍스트로 변경 + disabled

## Jinja2 충돌 방지 (필수)
- JS에서 {{ }} 절대 사용 금지
- 객체: function getLabel(s) { return {done:'완독'}[s]; } 패턴 사용

## 에러 처리
- 네트워크 오류: "서버에 연결할 수 없습니다." 메시지
- 모든 오류: showToast(메시지, true) 함수로 표시
```

---

## TASK F-2 · 네비게이션 바 — 로그인 상태 반영

```
# LUMA 프론트엔드 — 공통 NAV 로그인 상태 표시
# 파일: 모든 HTML 파일의 <nav> 섹션

## 현재 상태
- 모든 페이지 nav 우측에 "⭐ 나" 하드코딩
- 로그인/로그아웃 버튼 없음

## 작업 요청
각 HTML 파일의 nav 우측 <div> 부분 수정:

1. 로그인된 경우 표시:
   <div class="nav-user">
     <span id="nav-emoji">⭐</span>
     <span id="nav-name">나</span>
     <button onclick="logout()" class="nav-logout">로그아웃</button>
   </div>

2. 미로그인 시:
   <a href="/auth/login" class="nav-login-btn">로그인</a>

3. JS 공통 함수 (각 페이지 script에 추가):
   function initNav() {
     const user = JSON.parse(localStorage.getItem('luma_user') || '{}')
     if (user.display_name) {
       document.getElementById('nav-name').textContent = user.display_name
       document.getElementById('nav-emoji').textContent = user.emoji || '⭐'
     }
   }
   function logout() {
     localStorage.removeItem('luma_token')
     localStorage.removeItem('luma_user')
     window.location.href = '/landing'
   }
   document.addEventListener('DOMContentLoaded', initNav)

4. API 호출 시 토큰 포함 헬퍼:
   function authHeaders() {
     const token = localStorage.getItem('luma_token')
     return token
       ? {'Content-Type':'application/json','Authorization':'Bearer '+token}
       : {'Content-Type':'application/json'}
   }

## CSS (기존 변수 사용)
.nav-logout { background:rgba(248,113,113,.08); border:1px solid rgba(248,113,113,.22);
  color:#F87171; padding:5px 12px; border-radius:8px; font-size:.72rem; cursor:pointer; }
.nav-login-btn { background:rgba(193,127,59,.12); border:1px solid rgba(193,127,59,.25);
  color:var(--amber); padding:6px 14px; border-radius:18px; font-size:.75rem; }
```

---

## TASK F-3 · heart.html — 서재 API 완전 연동

```
# LUMA 프론트엔드 — 마음 서재 API 연동 완성
# 파일: app/templates/heart.html (현재 1,167줄)

## 현재 상태
- 5개 패널 UI 완성 (서재/감정/별자리/리포트/성향)
- D3.js 별자리 렌더링 함수 있음
- API 호출 일부 구현됨
- 문제: 토큰 인증 미연동, 일부 API 경로 불일치

## 작업 요청

### 서재 패널 수정
- loadShelf() 함수: GET /api/v2/shelf?user_id=${UID}
  headers: authHeaders() 포함
  성공 시: d.books로 renderBooks() 호출

- saveBook() 함수: POST /api/v2/shelf/books
  body: {title, author, genre, total_pages, cover_emoji, status, user_id:UID}
  성공 시: 폼 초기화 + loadShelf() 재호출 + showToast('책이 추가되었습니다! 📚')

- deleteBook(bookId): DELETE /api/v2/shelf/books/${bookId}?user_id=${UID}
  confirm() 후 실행

### 감정 타임라인 패널 수정
- loadTimeline(): GET /api/v2/emotions?user_id=${UID}
  d.timeline → renderTimeline() 호출
  d.stats → renderEmStats() 호출
  d.stats.total → document.getElementById('stat-emotions') 업데이트

- saveEmotion(): POST /api/v2/emotions
  body: {user_id:UID, book_id, emotion, intensity, note}
  성공 시: 폼 닫기 + loadTimeline() + showToast('감정이 기록되었습니다! 💙')

### 별자리 패널 수정
- loadConstellation(): GET /api/v2/constellation?user_id=${UID}
  d.nodes, d.links → renderConstellation() 호출 (이미 구현된 D3 함수 사용)

- addConnection(): POST /api/v2/constellation/connect
  body: {from_book_id, to_book_id, theme, user_id:UID}

### 리포트 패널 수정
- loadReport(month): GET /api/v2/report/monthly?user_id=${UID}&month=${month}
  d.report → renderReport() 호출 (이미 구현된 함수 사용)

### 성향 패널 수정
- loadPersona(): GET /api/heart/persona?user_id=${UID}
  d.persona → renderPersona() 호출

## Jinja2 충돌 방지
function statusLabel(s) { return {done:'완독',reading:'읽는 중',want:'읽고 싶어'}[s]||s; }

## 공통 헬퍼 (파일 상단)
const UID = JSON.parse(localStorage.getItem('luma_user')||'{}').user_id || 'user_demo'
function authHeaders() {
  const t = localStorage.getItem('luma_token')
  return t ? {'Content-Type':'application/json','Authorization':'Bearer '+t}
           : {'Content-Type':'application/json'}
}
```

---

## TASK F-4 · socrates.html — AI 대화 연동 완성

```
# LUMA 프론트엔드 — AI 소크라테스 대화 완전 연동
# 파일: app/templates/socrates.html (현재 753줄)

## 현재 상태
- 4가지 모드 UI 완성 (소크라테스/강제연결/액션플랜/사전)
- 타이핑 인디케이터, 진행바, 인사이트 카드 렌더러 구현됨
- API 호출 일부 구현

## 작업 요청

### 소크라테스 대화 모드
1. startSession(passage, book): POST /api/v2/socrates/start
   body: {passage, book_title:book, user_id:UID}
   성공 시: curSession = {session_id, stage:0}
            addAiMsg(d.question, 1, 5)
            updateProgress(1, 5)
            showDialogue() 호출

2. sendAnswer(): POST /api/v2/socrates/answer
   body: {session_id: curSession.session_id, answer}
   d.completed=true 시: addInsightCard(d.insight) + 자동 액션플랜 생성
   d.completed=false 시: addAiMsg(d.question, d.stage+1, 5)

### 강제 연결 모드
3. doConnect(): POST /api/v2/socrates/connect
   body: {text_a, book_a, text_b, book_b}
   성공 시: addConnectResult(d.insight) 호출

### 지식 사전
4. addDictEntry(): POST /api/v2/socrates/dictionary
   body: {concept, user_thought, user_id:UID, sources:[]}
   성공 시: renderDictList() + showToast('사전에 추가됨 📓')

5. loadDictFromServer(): GET /api/v2/socrates/dictionary?user_id=${UID}
   d.entries → renderDictListLeft() + renderDictList()

### 액션 플랜
6. quickActionPlan(insight, book): POST /api/v2/socrates/action
   body: {insight, book_title:book, user_id:UID}
   성공 시: renderActionPlans() + showToast('실천 플랜 생성! 🎯')

7. checkinPlan(planId): POST /api/v2/socrates/action/${planId}/checkin
   body: {note:''}
   성공 시: showToast('훌륭합니다! ✅') + renderActionPlans()

## 공통 헬퍼
const UID = JSON.parse(localStorage.getItem('luma_user')||'{}').user_id || 'user_demo'
function authHeaders() { ... }  // 동일 패턴
```

---

## TASK F-5 · live.html — WebRTC + 폴링 완성

```
# LUMA 프론트엔드 — 라이브 독서방 실시간 연동
# 파일: app/templates/live.html (현재 679줄)

## 현재 상태
- 방 목록/생성/참가 UI 완성
- WebRTC getUserMedia() 카메라 연결 구현됨
- Web Speech API 음성인식 구현됨
- API 호출 일부 구현

## 작업 요청

1. loadRooms() 수정:
   Promise.all([
     fetch('/api/v2/live/rooms?status=live').then(r=>r.json()),
     fetch('/api/v2/live/rooms?status=waiting').then(r=>r.json())
   ]) → 두 결과 합쳐서 renderRoomList()

2. createAndJoin() 수정:
   POST /api/v2/live/rooms
   body: {title, book_title, book_author, host_id:UID}
   d.room.room_id로 enterRoom() 호출

3. enterRoom(roomId) 후 폴링 시작:
   let lastMsgId = 0
   pollInterval = setInterval(async () => {
     const d = await fetch(`/api/v2/live/rooms/${roomId}/poll?since=${lastMsgId}`)
                     .then(r=>r.json())
     if (d.ok) {
       d.messages?.forEach(m => { if(m.peer_id !== myPeerId) addMsg(m) })
       if (d.messages?.length) lastMsgId = d.messages.at(-1).msg_id
       updateMemberCount(d.member_count)
       addKeywords(d.keywords || [])
     }
   }, 3000)

4. sendChat() 수정:
   POST /api/v2/live/rooms/${roomId}/message
   body: {peer_id:myPeerId, display_name:myName, emoji:myEmoji, text}

5. endRoom() 수정:
   clearInterval(pollInterval)
   POST /api/v2/live/rooms/${roomId}/end
   d.report → renderReport(d.report) + switchTab('report')

## 중요: WebRTC 참고사항
- 현재 WebRTC는 카메라 ON/OFF만 구현 (P2P 실제 연결은 시그널링 서버 필요)
- 폴링으로 텍스트 채팅은 완전 동작
- 카메라는 로컬 미리보기만 (실제 상대 화면은 향후 구현)
```

---

## TASK F-6 · social.html — 소셜 피드 완전 연동

```
# LUMA 프론트엔드 — 소셜 피드 완전 연동
# 파일: app/templates/social.html (현재 514줄)

## 현재 상태
- 카드 작성 UI, 피드 렌더링, 좋아요/댓글 UI 완성
- API 호출 대부분 구현됨
- 문제: 토큰 미연동, 일부 경로 오류

## 작업 요청

1. 모든 API 호출에 authHeaders() 추가

2. postCard() 수정:
   POST /api/v2/social/cards (기존 /api/social/cards → /api/v2로 변경)
   또는 /api/social/cards (new_features.py 라우터 사용)
   어느 것이 동작하는지 테스트 후 선택

3. 무한 스크롤 추가:
   window.addEventListener('scroll', () => {
     if (window.innerHeight + scrollY >= document.body.offsetHeight - 200) {
       if (!isLoading && hasMore) loadMoreCards()
     }
   })
   page 변수로 페이지네이션 관리

4. 카드 스타일 미리보기:
   style-btn 클릭 시 compose 영역 배경색 즉시 변경
   curStyle 변수로 현재 선택 스타일 추적

5. 댓글 인라인 패널 개선:
   댓글 달기 후 카운터 즉시 업데이트 (화면 새로고침 없이)
   document.getElementById('cc-'+cardId).textContent = d.total_comments

## 공통 헬퍼 동일 패턴 적용
const UID = JSON.parse(localStorage.getItem('luma_user')||'{}').user_id || 'user_demo'
```

---

## TASK F-7 · dashboard.html — 별자리 대시보드 연동

```
# LUMA 프론트엔드 — 메인 대시보드 API 연동
# 파일: app/templates/dashboard.html (현재 1,413줄)

## 현재 상태
- D3.js 별자리 시각화 완성
- 좌측 통계, 중앙 별자리, 우측 AI 메시지 레이아웃 완성
- API 연동 없이 하드코딩된 데이터 표시 중

## 작업 요청

1. 페이지 로드 시 API 데이터로 대시보드 초기화:
   async function initDashboard() {
     const [shelf, constellation, timeline] = await Promise.all([
       fetch(`/api/v2/shelf?user_id=${UID}`).then(r=>r.json()),
       fetch(`/api/v2/constellation?user_id=${UID}`).then(r=>r.json()),
       fetch(`/api/v2/emotions?user_id=${UID}`).then(r=>r.json()),
     ])
     updateStats(shelf.stats)
     renderConstellationD3(constellation.nodes, constellation.links)
     renderRecentEmotions(timeline.timeline?.slice(0,3))
   }

2. 좌측 통계 업데이트 함수:
   function updateStats(stats) {
     document.getElementById('stat-done').textContent    = stats.done || 0
     document.getElementById('stat-reading').textContent = stats.reading || 0
     document.getElementById('stat-total').textContent   = stats.total || 0
   }

3. 우측 AI 코칭 메시지:
   GET /api/heart/persona?user_id=${UID}
   d.persona.next_book_hint → 우측 패널에 표시
   d.persona.persona_name  → "오늘의 독서 성향" 섹션에 표시

4. 빠른 감정 기록 버튼:
   우측 하단 "지금 읽고 있는 책" 섹션에 감정 기록 미니 폼
   POST /api/v2/emotions 연동
```

---

## TASK F-8 · 반응형 모바일 UX 개선

```
# LUMA 프론트엔드 — 모바일 반응형 개선
# 파일: heart.html, social.html, socrates.html, live.html

## 작업 요청
각 파일의 <style> 섹션 끝에 미디어 쿼리 추가:

/* 태블릿 (1024px 이하) */
@media (max-width: 1024px) {
  .app-body { grid-template-columns: 180px 1fr; }
  .sidebar-right { display: none; }
  .right { display: none; }  /* live.html */
}

/* 모바일 (768px 이하) */
@media (max-width: 768px) {
  .app-body, .main, .app { grid-template-columns: 1fr !important; }
  .sidebar, .left-panel, .sidebar-left { display: none; }
  .nav { padding: 0 14px; height: 52px; }
  .nav-links { gap: 1px; }
  .npill { padding: 4px 8px; font-size: .65rem; }
  .panel-scroll { padding: 14px 16px; }
  .webcam-grid { grid-template-columns: repeat(2,1fr); }
}

/* 모바일 하단 네비게이션 */
@media (max-width: 768px) {
  .bottom-nav {
    display: flex;
    position: fixed; bottom: 0; left: 0; right: 0;
    height: 56px;
    background: rgba(11,22,18,.97);
    border-top: 1px solid var(--border);
    z-index: 100;
  }
  .bn-item {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    font-size: .6rem; color: var(--sub);
    text-decoration: none; gap: 3px;
  }
  .bn-item.active { color: var(--amber); }
  .bn-icon { font-size: 1.1rem; }
  body { padding-bottom: 56px; }
}

모바일 하단 네비게이션 HTML (body 끝에 추가):
<nav class="bottom-nav">
  <a href="/" class="bn-item"><span class="bn-icon">✦</span>별자리</a>
  <a href="/heart" class="bn-item"><span class="bn-icon">📖</span>서재</a>
  <a href="/social" class="bn-item active"><span class="bn-icon">📱</span>피드</a>
  <a href="/live" class="bn-item"><span class="bn-icon">🎥</span>라이브</a>
  <a href="/socrates" class="bn-item"><span class="bn-icon">🧠</span>AI</a>
</nav>
```

---

# 3. 앞으로 해야 할 작업계획서

## Phase 0 — 완료된 기반 작업
```
우선순위  작업                          담당
───────────────────────────────────────────────
✅ 1      B-1 MySQL 연결/시드 데이터     Codex
✅ 2      B-2 JWT helper/refresh 정리    Codex
✅ 3      F-1 로그인/JWT 토큰 저장       Codex
✅ 4      F-2 NAV 로그인 상태 반영       Codex
✅ 5      B-3/B-5/B-6 /api/v2 보강      Codex
✅ 6      F-3/F-4/F-5 핵심 화면 전환    Codex
✅ 7      F-6 social /api/social 유지 보완 Codex
```

## Phase 1 — 실행 검증과 오류 정리 (우선)
```
우선순위  작업                          담당
───────────────────────────────────────────────
🔴 1      실제 브라우저에서 로그인→서재→감정→별자리 플로우 점검 Codex
🔴 2      `/api/v2` 요청 실패 시 토스트/리다이렉트 UX 정리       Codex
🔴 3      Windows CP949 콘솔에서 깨지는 기존 이모지 로그 제거    Codex
🔴 4      `requirements.txt` 설치는 venv 기준으로 재정리          Codex
```

## Phase 2 — 대시보드와 소셜 완성
```
우선순위  작업                          담당
───────────────────────────────────────────────
✅ 5      F-7 dashboard.html을 `/api/v2` 데이터로 초기화 Codex
✅ 6      social.html 무한스크롤/댓글 카운터/카드 미리보기 완성 Codex
✅ 7      social을 계속 `/api/social/*`로 둘지 `/api/v2/social/*` 신설할지 결정 Codex
✅ 8      `/api/v2/social/*` 신설 시 feed_cards/likes/comments Mock 우선 연동 Codex
```

## Phase 3 — AI 기능 고도화
```
우선순위  작업                          담당
───────────────────────────────────────────────
✅ 9      B-4 감정 기록 후 Gemini로 별자리 연결 테마 생성 Codex
✅ 10     사용자 장르/감정 패턴 기반 `auto_suggest_books()` 구현 Codex
✅ 11     Gemini 실패 시 Mock 응답 품질 개선 Codex
✅ 12     Google Books 검색 결과를 Discover 씨앗 심기/서재 추가 흐름과 연결 Codex
```

## Phase 4 — 모바일/배포/테스트
```
우선순위  작업                          담당
───────────────────────────────────────────────
🟢 13     F-8 heart/social/socrates/live 모바일 하단 NAV 정리 Codex
🟢 14     Playwright 또는 Flask test_client 기반 핵심 API 테스트 작성 Codex
🟢 15     `.env.example`에 MySQL/JWT/Gemini/Google Books 키 설명 보강 Codex
🟢 16     Railway/Supabase 배포 전 `INSTALL.md`와 README 실행 절차 갱신 Codex
```

---

# 4. 공통 개발 규칙 요약

## 백엔드 (Codex) 필수 패턴
```python
# 1. 이중 모드 (가장 중요)
if is_connected():
    try:
        return execute_one("SELECT...", (param,))
    except Exception as e:
        return {"ok": False, "error": str(e)}
else:
    return {"ok": True, "data": _mock_data}

# 2. 응답 형식 통일
{"ok": True, "data": ...}   # 성공
{"ok": False, "error": "..."}  # 실패

# 3. SQL 인젝션 방지
execute_one("SELECT * FROM t WHERE id=%s", (id,))  # ✅
f"SELECT * WHERE id='{id}'"                         # ❌

# 4. 한글 JSON
json.dumps(data, ensure_ascii=False)
```

## 프론트엔드 (Claude Code) 필수 패턴
```javascript
// 1. Jinja2 충돌 방지
function statusLabel(s) { return {done:'완독'}[s]; }  // ✅
const x = ${{key:val}}  // ❌

// 2. API 호출 표준
const UID = JSON.parse(localStorage.getItem('luma_user')||'{}').user_id || 'user_demo'
function authHeaders() {
  const t = localStorage.getItem('luma_token')
  return t ? {'Content-Type':'application/json','Authorization':'Bearer '+t}
           : {'Content-Type':'application/json'}
}
async function apiCall(url, method='GET', body=null) {
  const r = await fetch(url, {
    method, headers: authHeaders(),
    body: body ? JSON.stringify(body) : null
  })
  return r.json()
}

// 3. 에러 처리
const d = await apiCall('/api/v2/shelf')
if (!d.ok) { showToast(d.error, true); return; }

// 4. CSS 변수 (변경 금지)
--amber:#C17F3B  --forest:#2D4A3E  --bg:#0B1612
```

---

*LUMA — 읽는 행위를 넘어, 생각의 우주를 연결하다 🌿*
