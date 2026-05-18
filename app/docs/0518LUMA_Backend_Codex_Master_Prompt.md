
# LUMA 백엔드 Codex용 마스터 프롬프트

Target: Codex  
Role: Senior Backend Engineer / Fullstack-aware Backend Architect  
Project: LUMA 독서모임 앱

---

## 0. 작업 목적

LUMA는 단순 독서 기록 앱이 아니라, 사용자가 책을 읽고, 생각을 남기고, 질문을 만들고, 사람들과 토론하고, 독서모임 장소까지 연결하는 **사유 기반 독서 커뮤니티 플랫폼**이다.

이번 백엔드 작업의 목표는 기존 코드를 최대한 유지하면서 아래 기능을 안정적으로 확장하는 것이다.

1. Lounge 도서 추천 데이터 정제 파이프라인
2. Community 카드형 피드 API
3. DeepDive YouTube 검색 기반 큐레이션 API
4. Profile 독서 우주 API
5. Places 독서모임 장소 찾기 저장 API
6. Socrates 토론 질문 확장 API
7. 모든 페이지 공통 네비게이션에 필요한 최소 데이터 제공

---

## 1. 절대 원칙

아래는 반드시 지킨다.

- 기존 route를 삭제하지 않는다.
- 기존 API 이름을 임의로 바꾸지 않는다.
- 기존 DB 구조를 무리하게 갈아엎지 않는다.
- 기존 로그인/auth/user/session 구조를 깨지 않는다.
- 프론트가 이미 쓰는 response shape를 깨지 않는다.
- 기존 기능을 제거하지 않는다.
- API key를 코드에 직접 하드코딩하지 않는다.
- 프론트엔드에 YouTube/Kakao/Google API key를 노출하지 않는다.
- 새 기능은 가능한 한 새 route/service 파일로 분리한다.
- route에는 request parsing과 validation만 두고, 비즈니스 로직은 service layer로 분리한다.
- 데이터가 없어도 mock/fallback 응답을 제공한다.
- 모든 응답은 `{ "ok": true }` 또는 `{ "ok": false, "error": "..." }` 형식을 유지한다.

---

## 2. 먼저 해야 할 Audit

코드 수정 전에 반드시 현재 구조를 먼저 확인하고 보고하라.

출력해야 할 것:

1. 현재 route 목록
2. 현재 templates 목록
3. 현재 static/css, static/js 목록
4. 현재 DB 관련 파일
5. 현재 auth/user 구조
6. 현재 Socrates/Lounge/Profile/Community/Places 관련 코드 존재 여부
7. 수정하지 말아야 할 위험 파일 목록
8. 새로 만들 파일 목록 제안

Audit 후 실제 구현을 시작한다.

---

## 3. 환경변수 규칙

.env 또는 config에서 아래 값을 읽을 수 있게 한다.

```env
YOUTUBE_API_KEY=
GOOGLE_BOOKS_API_KEY=
KAKAO_JS_KEY=
KAKAO_REST_KEY=
```

주의:

- `.env`는 GitHub에 올리지 않는다.
- `.env.example`에는 키 이름만 넣고 실제 값은 넣지 않는다.
- 프론트에는 Kakao JavaScript Key만 서버 템플릿 주입 방식으로 필요한 경우 전달한다.
- YouTube API Key는 반드시 백엔드에서만 사용한다.

---

## 4. Lounge 도서 데이터 정제 파이프라인

### 목표

`/lounge`를 “책 탐사 라운지”로 만들기 위해, 감정별/성향별/분야별/최신/클래식/평점/토론 적합도 기준으로 책을 추천할 수 있는 백엔드 구조를 만든다.

### 구현 단계

#### Step 1. 데이터 수집 Provider

우선 MVP는 아래 순서로 구현한다.

1. curated seed data
2. Google Books API
3. Open Library fallback
4. 나중에 Aladin/Naver 확장 가능 구조만 남김

생성 후보:

```text
app/services/book_providers/google_books_provider.py
app/services/book_providers/openlibrary_provider.py
app/services/book_seed_service.py
```

#### Step 2. 표준화 Normalizer

외부 API 응답을 내부 표준 구조로 바꾼다.

표준 필드:

```json
{
  "book_id": "internal_id",
  "isbn10": "",
  "isbn13": "",
  "title": "",
  "author": "",
  "publisher": "",
  "published_date": "",
  "cover_url": "",
  "description": "",
  "category": "",
  "sub_category": "",
  "rating": 0,
  "review_count": 0,
  "source": "google_books",
  "source_url": ""
}
```

생성 후보:

```text
app/services/book_normalizer_service.py
```

#### Step 3. 중복 제거 Deduplicator

중복 제거 기준:

1. isbn13 동일
2. isbn10 동일
3. title + author 유사도
4. 같은 책의 다른 edition은 edition_group으로 묶기

생성 후보:

```text
app/services/book_deduplicator_service.py
```

#### Step 4. 결측값 보정

- cover_url 없음 → fallback cover metadata 제공
- description 없음 → 다른 source 또는 seed description 사용
- published_date 없음 → null 허용
- category 없음 → rule-based 분류
- rating 없음 → popularity_score 또는 기본값

#### Step 5. 태깅

책마다 아래 태그를 만든다.

감정 태그:
```text
위로, 사색, 성장, 몰입, 평온, 용기, 고독, 회복, 호기심, 감동
```

분야 태그:
```text
문학, 에세이, 인문, 철학, 심리, 과학, 역사, 사회, 예술, 자기계발, 경제경영, 청소년
```

성향 태그:
```text
분석형, 감성형, 토론형, 실용형, 탐구형, 회복형
```

모임 적합도 태그:
```text
토론거리 많음, 찬반 가능, 인물 분석 가능, 입문자 가능, 깊이 읽기 좋음, 감정 나눔 가능
```

생성 후보:

```text
app/services/book_tagger_service.py
```

#### Step 6. 점수화

최종 점수 공식:

```text
final_score =
  0.25 * emotion_match
+ 0.20 * field_match
+ 0.15 * persona_match
+ 0.15 * rating_score
+ 0.15 * discussion_score
+ 0.10 * freshness_or_classic_score
```

필터가 선택된 경우 가중치를 조정한다.

#### Step 7. Lounge 추천 API

추가 API:

```text
GET /api/v2/lounge/books/recommend
```

Query 예시:

```text
emotion=calm
persona=INFJ
field=philosophy
mode=classic
limit=20
```

Response 예시:

```json
{
  "ok": true,
  "books": [
    {
      "book_id": "b_001",
      "title": "데미안",
      "author": "헤르만 헤세",
      "cover_url": "...",
      "description": "...",
      "tags": ["성장", "자아", "클래식", "토론추천"],
      "scores": {
        "final": 92,
        "discussion": 95,
        "emotion": 80,
        "rating": 88,
        "classic": 97,
        "freshness": 10
      },
      "recommend_reason": "자아와 성장에 대해 이야기하기 좋은 클래식입니다."
    }
  ]
}
```

추가 API:

```text
GET /api/v2/lounge/books/detail/<book_id>
POST /api/v2/lounge/books/save
POST /api/v2/lounge/create-from-book
```

---

## 5. Community 카드형 피드 API

### 목표

`/community` 또는 `/social`을 다양한 사람들이 책에 대한 생각을 올리는 **카드형 생각 피드**로 만든다.

### API

```text
GET /api/v2/community/feed
GET /api/v2/community/questions
GET /api/v2/community/quotes
GET /api/v2/community/trending-books
POST /api/v2/community/post
POST /api/v2/community/<post_id>/like
POST /api/v2/community/<post_id>/comment
```

---

## 6. DeepDive YouTube 검색 기반 큐레이션 API

### 목표

웹크롤링이 아니라 YouTube Data API v3 기반으로 책/주제 이해 영상을 추천한다.

### 금지

- YouTube 영상 다운로드 금지
- 무단 크롤링 금지
- 자막 무단 추출 금지
- API key 프론트 노출 금지

### API

```text
GET /api/v2/youtube/search?q=...
GET /api/v2/deepdive/search?q=...
POST /api/v2/deepdive/save
```

카테고리:

```text
summary, review, lecture, reading, discussion, general
```

---

## 7. Profile 독서 우주 API

### 목표

`/profile`을 단순 계정 페이지가 아니라 **나의 독서 우주**로 만든다.

### API

```text
GET /api/v2/profile/summary
GET /api/v2/profile/constellation
GET /api/v2/profile/current-reading
GET /api/v2/profile/sentences
GET /api/v2/profile/timeline
GET /api/v2/profile/questions
GET /api/v2/profile/persona
GET /api/v2/profile/lounges
GET /api/v2/profile/similar-readers
```

---

## 8. Places 독서모임 장소 찾기 저장 API

### 목표

장소 검색 자체는 Kakao Map JS SDK가 프론트에서 담당하고, 백엔드는 저장/조회/라운지 연결을 담당한다.

### API

```text
POST /api/v2/places/save
GET /api/v2/places/saved?user_id=...
POST /api/v2/lounge/<lounge_id>/place
POST /api/v2/places/review
```

---

## 9. Socrates 토론 확장 API

기존 Socrates API는 유지하고 아래 API만 추가한다.

```text
POST /api/socrates/book-brief
POST /api/socrates/discussion-questions
POST /api/socrates/debate-topic
POST /api/socrates/lounge-card
```

기존 `/api/socrates/start`에는 선택적으로 `discussion_mode`를 받을 수 있게 한다.

기본값:

```text
appreciation
```

---

## 10. 이미지 처리 규칙

책 표지와 썸네일은 반드시 안정적으로 처리한다.

- cover_url 있으면 그대로 사용
- cover_url 없으면 fallback_cover 객체 반환
- broken image 대비 alt/title 제공
- YouTube thumbnail 없으면 fallback thumbnail 제공
- 프론트가 쉽게 렌더링하도록 `cover_url`, `thumbnail` 필드를 항상 포함
- 이미지 URL은 가능하면 https로 정규화

Fallback 예시:

```json
{
  "cover_url": "",
  "fallback_cover": {
    "title": "데미안",
    "initial": "데",
    "theme": "classic"
  }
}
```

---

## 11. 구현 파일 후보

현재 구조를 확인한 뒤 기존 패턴에 맞춰 생성한다.

```text
app/routes/lounge_books.py
app/routes/community.py
app/routes/deepdive.py
app/routes/youtube.py
app/routes/profile_v2.py
app/routes/places.py

app/services/book_provider_service.py
app/services/book_normalizer_service.py
app/services/book_deduplicator_service.py
app/services/book_tagger_service.py
app/services/book_scoring_service.py
app/services/lounge_recommendation_service.py
app/services/community_service.py
app/services/deepdive_service.py
app/services/youtube_service.py
app/services/profile_service.py
app/services/places_service.py
```

단, 기존 파일이 이미 있으면 새 파일을 무조건 만들지 말고 기존 구조에 맞춰 확장한다.

---

## 12. 테스트 방법

구현 후 아래를 테스트한다.

```text
GET /api/v2/lounge/books/recommend
GET /api/v2/community/feed
GET /api/v2/deepdive/search?q=코스모스
GET /api/v2/profile/summary
POST /api/v2/places/save
```

---

## 13. 작업 후 보고 형식

작업 완료 후 아래 형식으로 보고한다.

1. 수정 파일 목록
2. 추가 route/API 목록
3. 추가 service 목록
4. 도서 데이터 정제 파이프라인 설명
5. 이미지 fallback 처리 방식
6. mock fallback 설명
7. 프론트가 연결해야 할 endpoint 목록
8. 테스트 방법
9. 남은 TODO
