# LUMA Backend to Frontend Handoff Report

Date: 2026-05-18  
Target: Claude Code Frontend 작업 인수인계  
Project: LUMA 독서모임 앱

이 문서는 현재 `E:\독서모임앱\LUMA` 기준으로 백엔드/API 작업 내용을 프론트엔드 담당자가 바로 이어받을 수 있도록 정리한 작업 완료 보고서입니다.

---

## 1. 수정 파일 목록

### 수정된 주요 백엔드 파일

- `app/factory.py`
- `app/db.py`
- `app/schema.py`
- `app/routes/auth.py`
- `app/routes/main.py`
- `app/routes/mysql_api.py`
- `app/routes/ocr.py`
- `app/routes/places.py`
- `app/services/gemini_service.py`
- `app/services/ocr_service.py`
- `app/services/place_service.py`
- `app/services/profile_service.py`
- `app/services/reading_service.py`
- `app/services/social_feed_service.py`
- `app/services/socrates_discussion_service.py`
- `requirements.txt`
- `run_luma_server.py`
- `.gitignore`

### 수정된 프론트 템플릿/정적 파일

- `app/templates/base.html`
- `app/templates/landing.html`
- `app/templates/dashboard.html`
- `app/templates/lounge.html`
- `app/templates/community.html`
- `app/templates/social.html`
- `app/templates/profile.html`
- `app/templates/ocr.html`
- `app/templates/heart.html`
- `app/templates/live.html`
- `app/templates/deepdive.html`
- `app/templates/socrates.html`
- `app/templates/auth.html`
- `app/static/css/profile.css`
- `app/static/js/profile.js`

### 추가된 신규 파일/디렉터리

- `app/routes/community_api.py`
- `app/routes/lounge_books.py`
- `app/services/book_normalizer_service.py`
- `app/services/book_deduplicator_service.py`
- `app/services/book_scoring_service.py`
- `app/services/book_seed_service.py`
- `app/services/book_tagger_service.py`
- `app/services/community_feed_service.py`
- `app/services/google_vision_ocr.py`
- `app/services/lounge_recommendation_service.py`
- `app/docs/0518LUMA_Backend_Codex_Master_Prompt.md`
- `app/docs/0518LUMA_Frontend_ClaudeCode_Master_Prompt.md`
- `app/docs/0518LUMA_Project_Start_MASTER_INDEX.md`
- `app/docs/0518google_vision_ocr_codex_prompt.md`
- `app/docs/OCR_SETUP.md`
- `app/docs/rollout-2026-05-18T15-33-55-019e39ca-8c03-7550-9772-799eae8fec2c.jsonl`
- `app/asset/images/...`
- `app/asset/videos/book.mp4`
- `app/asset/videos/grory_light.mp4`
- `app/asset/videos/logo_moving.mp4`
- `app/asset/videos/night_stars.mp4`
- `scripts/`

---

## 2. 추가 route/API 목록

### 신규 등록된 Blueprint

- `app.routes.lounge_books` -> `/api/v2/lounge`
- `app.routes.community_api` -> `/api/v2/community`
- 기존 `mysql_api` -> `/api/v2`
- 기존 `ocr_bp` -> `/api/ocr`
- 루트 편의 라우트: `/ocr`, `/ocr/health`, `/health/ocr`

### Lounge v2 API

- `GET /api/v2/lounge/books/recommend`
- `GET /api/v2/lounge/books/recommend/contract`
- `GET /api/v2/lounge/books/detail/<book_id>`
- `POST /api/v2/lounge/books/save`
- `POST /api/v2/lounge/create-from-book`

### Community v2 API

- `GET /api/v2/community/feed`
- `GET /api/v2/community/questions`
- `GET /api/v2/community/quotes`
- `GET /api/v2/community/trending-books`
- `GET /api/v2/community/lounge-recruit`
- `POST /api/v2/community/post`
- `POST /api/v2/community/posts`
- `POST /api/v2/community/posts/<post_id>/like`
- `POST /api/v2/community/posts/<post_id>/save`
- `GET /api/v2/community/posts/<post_id>/comments`
- `POST /api/v2/community/posts/<post_id>/comments`
- `POST /api/v2/community/clubs`
- `POST /api/v2/community/clubs/<club_id>/join`
- `POST /api/v2/community/clubs/<club_id>/cards`
- `POST /api/v2/community/cards/<card_id>/like`
- `POST /api/v2/community/cards/<card_id>/comment`
- `POST /api/v2/community/clubs/<club_id>/settings`
- `POST /api/v2/community/clubs/<club_id>/ai-guide`
- `POST /api/v2/community/clubs/<club_id>/report`
- `GET /api/v2/community/clubs/<club_id>/report`

### OCR API

- `GET /api/ocr/status`
- `GET /api/ocr/health`
- `POST /api/ocr`
- `POST /api/ocr/scan`
- `POST /api/ocr/enhance`
- `POST /api/ocr/book-cover`
- `POST /api/ocr/analyze-page`
- `POST /api/ocr/generate-memo`
- `POST /api/ocr/save-memo`
- `POST /api/ocr/full-pipeline`

---

## 3. 추가 service 목록

### 도서 추천/정제 관련

- `book_seed_service.py`  
  초기 추천 후보 도서 seed 제공

- `book_normalizer_service.py`  
  외부/내부 도서 데이터를 공통 book contract로 정규화

- `book_deduplicator_service.py`  
  ISBN 또는 제목+저자 기준 중복 제거

- `book_tagger_service.py`  
  분야, 감정, 토론성 태그 추론

- `book_scoring_service.py`  
  감정/분야/persona/평점/토론성/신간·고전 기준 점수 계산

- `lounge_recommendation_service.py`  
  Lounge 추천 파이프라인 통합

### 커뮤니티/OCR 관련

- `community_feed_service.py`  
  커뮤니티 피드, 질문, 인용문, 트렌딩 도서, 댓글, 좋아요, 저장 처리

- `google_vision_ocr.py`  
  Google Vision OCR credential/status 및 OCR 실행

- 기존 `ocr_service.py`, `gemini_service.py`, `reading_service.py`, `profile_service.py`, `social_feed_service.py`도 연동 확장됨

---

## 4. 도서 데이터 정제 파이프라인 설명

Lounge 추천 API의 핵심 파이프라인은 다음 순서입니다.

```text
seed books
-> external provider search
-> normalize
-> dedupe
-> tag
-> score
-> sort
-> frontend contract shape
```

세부 동작:

- `get_seed_books()`로 기본 후보 도서를 먼저 확보합니다.
- 필터값에 따라 검색 query를 만듭니다.
  - `emotion`: `calm`, `growth`, `lonely`, `curious`, `warm`
  - `field`: `literature`, `philosophy`, `science`, `history`, `humanities`, `psychology` 등
  - `mode`: `classic`, `new`, `fresh`
  - `sort`: `score`, `rating`, `reviews`, `recent`, `shuffle`
- `search_books_naver`, `search_books_google`, `search_books` 등 기존 provider를 호출합니다.
- `normalize_book()`에서 도서 데이터를 통일합니다.
  - `book_id`
  - `isbn10`
  - `isbn13`
  - `isbn`
  - `title`
  - `author`
  - `publisher`
  - `published_date`
  - `cover_url`
  - `thumbnail`
  - `thumbnail_url`
  - `description`
  - `category`
  - `genre`
  - `rating`
  - `review_count`
  - `source`
  - `source_url`
  - `fallback_cover`
- `dedupe_books()`에서 ISBN 우선, 없으면 제목+저자 기준으로 중복 제거합니다.
- `tag_book()`에서 분야/감정/토론 추천 태그를 붙입니다.
- `score_book()`에서 최종 추천 점수를 계산합니다.
- `shape_lounge_book()`에서 프론트가 그대로 쓰기 쉬운 응답 형태로 변환합니다.

Lounge 추천 응답 기본 형태:

```json
{
  "ok": true,
  "books": [],
  "count": 0,
  "filters": {},
  "meta": {
    "source": "lounge_pipeline",
    "pipeline": ["seed", "providers", "normalize", "dedupe", "tag", "score"],
    "contract_version": "2026-05-18"
  }
}
```

---

## 5. 이미지 fallback 처리 방식

도서 표지 fallback은 `book_normalizer_service.py`에서 처리합니다.

우선순위:

1. 외부 데이터의 `cover_url`
2. `thumbnail_url`
3. `thumbnail`
4. `image`
5. `image_url`
6. ISBN이 있으면 OpenLibrary cover URL 생성
7. 그래도 없으면 `fallback_cover` 객체 사용

OpenLibrary cover URL 형식:

```text
https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg
```

`fallback_cover` 형태:

```json
{
  "title": "책 제목",
  "initial": "책",
  "theme": "classic",
  "label": "분야",
  "background": "#173127",
  "accent": "#C17F3B",
  "source_url": ""
}
```

프론트 처리 권장:

- `cover_url || thumbnail_url || thumbnail` 순서로 실제 이미지를 시도합니다.
- 이미지 로드 실패 시 `fallback_cover`로 카드형 대체 표지를 렌더링합니다.
- `initial`, `theme`, `background`, `accent`, `label`을 사용하면 백엔드 fallback 의도와 맞습니다.
- `fallback_cover`는 항상 내려가도록 설계되어 있습니다.

---

## 6. mock fallback 설명

현재 백엔드는 외부 API나 DB가 없어도 페이지가 깨지지 않도록 mock/data fallback을 유지합니다.

주요 fallback:

- DB 초기화 실패 시 앱은 Mock 모드로 계속 실행합니다.
  - `factory.py`에서 DB 초기화 실패를 잡고 서버 실행 유지
- 인증 토큰이 없거나 검증 실패 시 `user_demo`를 사용합니다.
  - Lounge, Community, OCR 등에서 공통적으로 사용
- Lounge 추천
  - 외부 provider 검색 실패 시 seed books 기반으로 응답 가능
  - 실패 시에도 `{ "ok": false, "books": [] }` 형태 유지
- Community feed
  - DB 데이터가 없거나 실패할 경우 memory/mock post 형태 사용
  - 응답 키를 `feed`, `posts`, `cards`로 중복 제공해서 프론트 호환성 확보
- OCR
  - Google Vision credential이 없어도 `ocr_service.py`의 Gemini/mock OCR 흐름으로 fallback 가능
  - `/api/ocr/status`, `/api/ocr/health`에서 상태 확인 가능
- Places
  - Google Maps key가 없으면 mock place/search 데이터로 fallback
- YouTube/DeepDive
  - API key가 없으면 mock resource/search 결과 사용

---

## 7. 프론트가 연결해야 할 endpoint 목록

### Lounge 화면 우선 연결

```text
GET  /api/v2/lounge/books/recommend
GET  /api/v2/lounge/books/recommend/contract
GET  /api/v2/lounge/books/detail/<book_id>
POST /api/v2/lounge/books/save
POST /api/v2/lounge/create-from-book
```

추천 필터 query 예시:

```text
/api/v2/lounge/books/recommend?emotion=calm&persona=INFJ&field=philosophy&mode=classic&sort=score&limit=20
```

### Community 화면 연결

```text
GET  /api/v2/community/feed?page=1&limit=12&tag=&q=&emotion=
GET  /api/v2/community/questions?limit=12
GET  /api/v2/community/quotes?limit=12
GET  /api/v2/community/trending-books?limit=12
GET  /api/v2/community/lounge-recruit?limit=8
POST /api/v2/community/posts
POST /api/v2/community/posts/<post_id>/like
POST /api/v2/community/posts/<post_id>/save
GET  /api/v2/community/posts/<post_id>/comments
POST /api/v2/community/posts/<post_id>/comments
```

### OCR 화면 연결

```text
GET  /api/ocr/status
GET  /api/ocr/health
POST /api/ocr/scan
POST /api/ocr/enhance
POST /api/ocr/book-cover
POST /api/ocr/analyze-page
POST /api/ocr/generate-memo
POST /api/ocr/save-memo
POST /api/ocr/full-pipeline
```

### Profile 화면 연결

```text
GET /api/v2/profile/summary
GET /api/v2/profile/current-reading
GET /api/v2/profile/constellation
GET /api/v2/profile/sentences
GET /api/v2/profile/timeline
GET /api/v2/profile/questions
GET /api/v2/profile/persona
GET /api/v2/profile/lounges
GET /api/v2/profile/similar-readers
```

### Social 화면 연결

```text
GET  /api/v2/social/feed
POST /api/v2/social/cards
POST /api/v2/social/cards/<card_id>/like
GET  /api/v2/social/cards/<card_id>/comments
POST /api/v2/social/cards/<card_id>/comments
GET  /api/v2/social/match
GET  /api/v2/social/clubs
GET  /api/v2/social/challenge
GET  /api/v2/social/badges
```

### Places 화면 연결

```text
GET    /api/places/search
GET    /api/places/google/<google_place_id>
GET    /api/places/saved
POST   /api/places/save
GET    /api/places/photo
GET    /api/places/all
GET    /api/places/nearby
GET    /api/places/<place_id>
PUT    /api/places/<place_id>
DELETE /api/places/<place_id>
POST   /api/places/<place_id>/checkin
GET    /api/places/<place_id>/reviews
POST   /api/places/<place_id>/review
GET    /api/places/cities
GET    /api/places/status
```

---

## 8. 테스트 방법

### Python 문법 검사

아래 명령으로 주요 신규/수정 백엔드 파일 문법 검사를 완료했습니다.

```powershell
py -m py_compile app\factory.py app\routes\lounge_books.py app\routes\community_api.py app\routes\ocr.py app\services\lounge_recommendation_service.py app\services\book_normalizer_service.py app\services\book_deduplicator_service.py app\services\book_scoring_service.py app\services\book_tagger_service.py app\services\community_feed_service.py app\services\google_vision_ocr.py
```

결과: 통과.

### 서버 실행 테스트

```powershell
py run_luma_server.py
```

또는 프로젝트 방식에 따라:

```powershell
flask --app app.factory:create_app run --debug
```

### 브라우저 확인

```text
http://localhost:5000/
http://localhost:5000/lounge
http://localhost:5000/community
http://localhost:5000/ocr
http://localhost:5000/profile
```

### API 수동 확인 예시

```powershell
Invoke-WebRequest "http://localhost:5000/api/v2/lounge/books/recommend?emotion=calm&field=philosophy&mode=classic&sort=score&limit=8"
Invoke-WebRequest "http://localhost:5000/api/v2/lounge/books/recommend/contract"
Invoke-WebRequest "http://localhost:5000/api/v2/community/feed?limit=5"
Invoke-WebRequest "http://localhost:5000/api/ocr/status"
Invoke-WebRequest "http://localhost:5000/health"
```

### 프론트 테스트 포인트

- 이미지 URL이 없거나 깨졌을 때 fallback cover가 표시되는지 확인
- Lounge 필터 변경 시 추천 결과가 바뀌는지 확인
- `books`, `count`, `filters`, `meta` 응답을 정상 사용 가능한지 확인
- Community 응답에서 `feed`, `posts`, `cards` 중 하나만 의존하지 않고 호환 처리하는지 확인
- OCR 업로드, 텍스트 보정, 메모 생성, 메모 저장 흐름이 끊기지 않는지 확인
- 모바일에서 카드/필터/이미지 fallback이 깨지지 않는지 확인

---

## 9. 남은 TODO

아래 TODO는 프론트엔드 Claude Code에게 넘기기 전에 Backend Codex가 먼저 처리/확인할 항목과, 프론트에서 바로 진행할 항목을 분리했습니다.

### 9-1. Backend Codex 처리/확인 완료 항목

- API 응답에 노출되는 깨진 한글 문자열을 정리했습니다.
  - 처리 파일:
    - `app/routes/lounge_books.py`
    - `app/routes/ocr.py`
    - `app/services/lounge_recommendation_service.py`
    - `app/services/book_normalizer_service.py`
    - `app/services/book_scoring_service.py`
    - `app/services/book_tagger_service.py`
    - `app/services/ocr_service.py`
    - `app/services/google_vision_ocr.py`
  - 처리 내용:
    - `error`, `message`, `status`, `recommend_reason`, OCR 안내 문구를 정상 한글로 정리했습니다.
    - Lounge 추천 이유 문구도 프론트 카드에 바로 노출 가능한 문장으로 정리했습니다.
    - 예: `코스모스는 소개, 평점, 토론 가능성을 함께 보았을 때 오늘의 라운지에 잘 맞는 책입니다.`

- 백엔드 API contract를 고정했습니다.
  - `/api/v2/lounge/books/recommend/contract`
  - `/api/v2/lounge/books/recommend`
  - `/api/v2/community/*`
  - `/api/ocr/*`
  - 고정 기준:
    - 모든 주요 응답은 `ok`를 포함합니다.
    - 실패 응답은 `error`를 포함합니다.
    - fallback/debug 구분을 위해 `source`, `engine`, `meta.source`, `pipeline` 계열 값을 유지합니다.

- Lounge 추천 응답의 fallback 필드를 최종 확인했습니다.
  - `cover_url`
  - `thumbnail`
  - `thumbnail_url`
  - `fallback_cover.background`
  - `fallback_cover.accent`
  - `fallback_cover.initial`
  - `fallback_cover.label`
  - 검증 결과:
    - 이미지가 없는 책도 항상 프론트가 렌더링 가능한 `fallback_cover`를 갖습니다.
    - 예시 fallback:

```json
{
  "accent": "#6EC6FF",
  "background": "#102A3D",
  "initial": "코",
  "label": "과학",
  "source_url": "",
  "theme": "science",
  "title": "코스모스"
}
```

- mock fallback 응답에 `source` 또는 `meta.source`를 안정적으로 내려주도록 확인했습니다.
  - Lounge: `meta.source = lounge_pipeline`
  - Community: `source = db | memory | db_error`
  - OCR: `engine`, `source`, `pipeline`
  - Books: `mode = google_books | mock`
  - Places: `mode = google_maps | mock`
  - YouTube: `source = youtube | mock`

- 실제 외부 API key 환경 및 fallback contract를 smoke test로 확인했습니다.
  - Books status: `/api/books/status`
  - Places status: `/api/places/status`
  - Google Vision status: `/api/ocr/status`, `/api/ocr/health`
  - YouTube search: `/api/v2/youtube/search?q=코스모스&limit=2`
  - 완료 기준:
    - key가 있으면 실제 API mode/source가 내려옵니다.
    - key가 없거나 실패해도 mock/fallback contract가 유지됩니다.

- Backend Codex 검증 명령:

```powershell
py -m py_compile app\routes\lounge_books.py app\routes\community_api.py app\routes\ocr.py app\routes\places.py app\routes\mysql_api.py app\services\lounge_recommendation_service.py app\services\book_normalizer_service.py app\services\book_deduplicator_service.py app\services\book_scoring_service.py app\services\book_tagger_service.py app\services\community_feed_service.py app\services\ocr_service.py app\services\google_vision_ocr.py app\services\place_service.py app\services\deepdive_service.py app\services\youtube_service.py
```

결과: 통과.

- Backend Codex smoke test 결과:

```text
GET  /api/v2/lounge/books/recommend/contract                         200 ok=True
GET  /api/v2/lounge/books/recommend?...                              200 ok=True source=lounge_pipeline
GET  /api/v2/community/feed?limit=2                                  200 ok=True source=db
GET  /api/ocr/status                                                 200 ok=True engine=google-vision
POST /api/ocr/full-pipeline                                          200 ok=True source=ocr_full_pipeline
GET  /api/books/status                                               200 ok=True mode=google_books
GET  /api/places/status                                              200 ok=True mode=google_maps
GET  /api/v2/youtube/search?q=코스모스&limit=2                       200 ok=True source=youtube
```

결론: 9-1 항목은 Backend Codex 기준으로 처리 완료되었습니다. 이제 프론트엔드 Claude Code는 아래 9-2 항목을 기준으로 UI 연결 작업을 진행하면 됩니다.

### 9-2. Frontend Claude Code가 이어서 작업할 항목

- Lounge 프론트는 `/api/v2/lounge/books/recommend/contract`를 기준으로 필터 UI와 응답 렌더링을 맞춰야 합니다.

- 도서 표지 fallback UI를 구현해야 합니다.
  - `fallback_cover.background`
  - `fallback_cover.accent`
  - `fallback_cover.initial`
  - `fallback_cover.label`

- 외부 이미지 로드 실패 이벤트를 처리해야 합니다.
  - `img.onerror`에서 fallback cover로 전환

- Community 프론트는 신규 `/api/v2/community/*` 엔드포인트로 점진 교체해야 합니다.

- OCR 프론트는 아래 두 방식 중 하나를 UX 기준으로 선택해야 합니다.
  - 한 번에 처리: `/api/ocr/full-pipeline`
  - 단계별 처리: `/api/ocr/scan -> /api/ocr/enhance -> /api/ocr/generate-memo -> /api/ocr/save-memo`

- Google Vision credential이 없을 때도 화면에서 "사용 불가"가 아니라 "대체 OCR/mock 모드"로 안내해야 합니다.

### 9-3. 백엔드/프론트 공동 검증 항목

- 프론트 작업 전후로 동일한 API contract를 기준으로 통합 테스트를 해야 합니다.

- 서버 실행 후 아래 화면에서 실제 렌더링을 확인해야 합니다.
  - `/lounge`
  - `/community`
  - `/ocr`
  - `/profile`
  - `/social`

- 모바일 화면에서 카드, 필터, 이미지 fallback, loading/empty/error state가 깨지지 않는지 확인해야 합니다.

- 현재 `git status` 기준 변경량이 크므로, 프론트 작업 전 백엔드 API contract를 먼저 고정하고 이후 UI 작업을 진행하는 것이 좋습니다.
