# LUMA Social 생각 피드 재편성 작업계획서

## 1. 목표

`/social`을 일반 SNS 게시판이 아니라 **생각 발견 피드**로 재편성한다.

사용자가 들어왔을 때 즉시 느껴야 하는 것:

- 이 사람은 이 책에서 이런 생각을 했구나.
- 이 책은 이런 감정과 질문을 남기는구나.
- 나도 이 질문으로 이야기해보고 싶다.

핵심 UX는 **책 표지, 짧은 생각, 질문, 감정 태그, 토론 연결**이다. 카드 하나만 봐도 어떤 책인지, 어떤 생각인지, 어떤 감정인지, 어떤 질문인지 바로 읽혀야 한다.

## 2. 현재 상태 점검

현재 `/social` 진입점:

- 라우트: `app/factory.py`의 `@app.route("/social")`
- 템플릿: `app/templates/social.html`
- 프론트 호출: 주로 `/api/social/*`
- v2 라우트: `app/routes/mysql_api.py`에 `/api/v2/social/*`가 있음
- 레거시 라우트: `app/routes/new_features.py`에 `/api/social/*`가 있음
- 서비스: `app/services/social_feed_service.py`

문제:

- `social_feed_service.py`는 현재 실제 DB 조회가 아니라 `_feed_cards`, `_comments`, `_book_clubs` 같은 메모리 mock 데이터 중심이다.
- `social.html`은 API 실패 시 `getDemoCards()`로 떨어져 실제 사용자 데이터와 mock 데이터가 섞여 보일 수 있다.
- `/api/social/*`와 `/api/v2/social/*`가 동시에 존재해 프론트/백엔드 계약이 불명확하다.
- 공개 메모 저장 흐름은 `reading_service.save_memo(... is_public=True)`에서 `social_feed_service.create_card()`를 호출하지만, DB 저장이 아니라 메모리 피드에만 추가된다.
- 카드 DTO에 책 표지, 질문, 감정 태그, 저장 여부, 소크라테스 연결, 모임 연결 정보가 부족하다.

## 3. 추천 컨셉

페이지 이름:

- 1순위: **생각 피드**
- 2순위: **독자 광장**

문구:

> 책으로 시작된 생각들이  
> 사람과 사람을 연결합니다.

또는:

> 사람들은 같은 책을 읽고도  
> 서로 다른 우주를 발견합니다.

디자인 톤:

- 조용한
- 사색적인
- 프리미엄 북클럽
- 큐레이션 매거진
- 생각 수집 공간

피해야 할 톤:

- 인스타그램식 이미지 SNS
- 페이스북식 게시판
- 단순 리스트형 커뮤니티
- 카드마다 비슷한 텍스트만 반복되는 피드

## 4. 추천 페이지 구조

### 4.1 상단 Hero

구성:

- 큰 제목: `생각 피드`
- 서브 문구: 위 추천 문구 중 하나
- 검색창: `지금 어떤 생각을 발견하고 싶나요?`
- 감정/주제 칩: `#철학`, `#우주`, `#고독`, `#성장`, `#관계`, `#불안`, `#자유`

목표:

- 페이지 정체성을 즉시 보여준다.
- 일반 게시판이 아니라 “생각을 찾는 공간”으로 느껴지게 한다.

### 4.2 오늘 많이 이야기되는 책

가로 캐러셀.

데이터:

- 책 표지
- 제목
- 저자
- 생각 수
- 질문 수
- 읽는 사람 수

API 후보:

- `GET /api/v2/community/trending-books`
- 내부 구현은 `books`, `shelf_books`, `memos`, `social_cards` 집계

### 4.3 핵심 생각 피드 카드 그리드

데스크톱:

- 좌측/중앙: masonry 또는 2-column responsive grid
- 우측 고정 패널: 오늘의 질문, 지금 많이 읽는 책, 독서모임 모집

모바일:

- Hero
- 트렌딩 책 가로 스크롤
- 생각 카드 세로 피드
- 하단 floating 글쓰기 버튼

카드 비율:

- 책 표지 영역 40%
- 생각/질문 영역 60%

카드 필수 요소:

- 책 표지 이미지
- 책 제목
- 저자
- 사용자 프로필
- 닉네임
- 관심 태그
- 짧은 생각
- 감정 태그
- 질문
- 공감
- 댓글
- 저장
- 소크라테스 토론
- 모임 연결

카드 예시 DTO:

```json
{
  "post_id": "p_1",
  "type": "thought",
  "user": {
    "user_id": "user_1",
    "display_name": "별빛 독자",
    "emoji": "✨",
    "tags": ["철학", "우주"]
  },
  "book": {
    "book_id": "book_1",
    "title": "코스모스",
    "author": "칼 세이건",
    "cover_url": "",
    "cover_emoji": "🌌"
  },
  "thought": "이 책은 인간이 왜 외로운지를 우주적으로 바라보게 만든다.",
  "question": "인간은 왜 자신의 위치를 알고 싶어할까?",
  "quote": "",
  "emotion_tags": ["고독", "우주", "철학"],
  "likes": 12,
  "comments": 3,
  "saved": false,
  "liked": false,
  "created_at": "2026-05-18T10:00:00"
}
```

### 4.4 질문 피드

질문 중심 카드.

예:

- 인간은 자유로울수록 행복할까?
- 인간은 왜 자신의 위치를 알고 싶어할까?
- 고독은 결핍일까, 사유의 조건일까?

연결:

- 댓글
- 소크라테스 토론
- Lounge/Community 모임 생성

API:

- `GET /api/v2/community/questions`

### 4.5 오늘의 문장

문장 저장형 카드.

예:

> 인간은 자유롭도록 선고받았다.

구성:

- 문장
- 책 제목
- 주제/감정 태그
- 이 문장으로 토론하기

API:

- `GET /api/v2/community/quotes`

### 4.6 감정 기반 추천 피드

섹션 예:

- 오늘 위로가 되는 책 이야기
- 오늘 깊게 생각하게 만드는 질문
- 오늘 조용히 읽고 싶은 문장

API:

- `GET /api/v2/community/feed?emotion=peaceful`
- `GET /api/v2/community/feed?emotion=curious`

### 4.7 같은 책 읽는 사람들

카드 예:

`지금 코스모스를 읽는 사람들`

- 김OO: 42%
- 박OO: 완독
- 이OO: 질문 12개 생성

버튼:

- 같이 이야기하기
- 이 책 모임 보기

API:

- `GET /api/v2/community/same-book-readers?book_id=...`

### 4.8 독서모임 모집 카드

기존 `/community/` 또는 `club_service`와 연결한다.

카드 예:

- 코스모스 같이 읽으실 분
- 6명 참여 중
- 질문 8개 생성
- 모임방 열기

API:

- `GET /api/v2/community/lounge-recruit`

## 5. API 통일 방향

추천 표준은 `/api/v2/community/*`이다.

이유:

- 사용자가 요청한 기능은 단순 social feed가 아니라 community 전체의 공개 생각, 질문, 문장, 독서모임 연결이다.
- 기존 `/community/`와 의미적으로 연결된다.
- 기존 `/api/v2/social/*`는 당분간 compatibility alias로 유지할 수 있다.

필수 API:

```text
GET  /api/v2/community/feed
GET  /api/v2/community/trending-books
GET  /api/v2/community/questions
GET  /api/v2/community/quotes
GET  /api/v2/community/same-book-readers
GET  /api/v2/community/lounge-recruit
POST /api/v2/community/posts
POST /api/v2/community/posts/<post_id>/like
GET  /api/v2/community/posts/<post_id>/comments
POST /api/v2/community/posts/<post_id>/comments
POST /api/v2/community/posts/<post_id>/save
```

호환 API:

```text
GET  /api/v2/social/feed -> /api/v2/community/feed
POST /api/v2/social/cards -> /api/v2/community/posts
POST /api/v2/social/cards/<id>/like -> /api/v2/community/posts/<id>/like
```

프론트는 신규 작업에서 `/api/v2/community/*`만 사용한다.

## 6. 백엔드 데이터 연결 원칙

최우선 데이터 소스:

- `memos`: 공개 메모, 문장, 생각 본문
- `books`: 책 제목, 저자, 표지
- `shelf_books`: 읽는 중/완독 상태, 같은 책 읽는 사람
- `users`: 닉네임, 이모지, 관심 태그
- 소셜 전용 테이블: likes, comments, saves, generated questions
- `club_service` 또는 이후 DB club 테이블: 독서모임 모집 카드

현재 확인된 주의점:

- `reading_service.save_memo()`는 `is_public`일 때 social card를 만들지만, 현재 `social_feed_service.create_card()`가 메모리 저장이다.
- 따라서 공개 메모를 진짜 피드로 쓰려면 DB 테이블을 추가하거나 `memos`를 직접 조회해 feed DTO를 만들어야 한다.

추천 단계:

1. 1차는 `memos` 직접 조회 기반으로 `feed`를 만든다.
2. likes/comments/saves만 소셜 전용 DB 테이블로 만든다.
3. 이후 필요하면 `community_posts` 테이블을 만들고 `memos`와 1:1 또는 N:1로 연결한다.

추천 테이블:

```sql
CREATE TABLE IF NOT EXISTS community_post_reactions (
  reaction_id VARCHAR(64) PRIMARY KEY,
  post_id VARCHAR(64) NOT NULL,
  user_id VARCHAR(64) NOT NULL,
  reaction_type VARCHAR(32) NOT NULL DEFAULT 'like',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_post_user_reaction (post_id, user_id, reaction_type)
);

CREATE TABLE IF NOT EXISTS community_post_comments (
  comment_id VARCHAR(64) PRIMARY KEY,
  post_id VARCHAR(64) NOT NULL,
  user_id VARCHAR(64) NOT NULL,
  content TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS community_post_saves (
  save_id VARCHAR(64) PRIMARY KEY,
  post_id VARCHAR(64) NOT NULL,
  user_id VARCHAR(64) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_post_user_save (post_id, user_id)
);
```

선택 테이블:

```sql
CREATE TABLE IF NOT EXISTS community_generated_questions (
  question_id VARCHAR(64) PRIMARY KEY,
  source_type VARCHAR(32) NOT NULL,
  source_id VARCHAR(64) NOT NULL,
  book_id VARCHAR(64),
  user_id VARCHAR(64),
  question TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 7. Feed DTO 생성 규칙

`GET /api/v2/community/feed`는 다음을 보장한다.

- mock이 아니라 DB 우선
- DB가 비어 있을 때만 안내용 empty state 반환
- 카드마다 `book.cover_url` 또는 `book.cover_emoji` 제공
- `thought`는 너무 길면 서버에서 220자 내외로 잘라 반환 가능
- `question`이 없으면 서버에서 규칙 기반 fallback 질문 생성
- `emotion_tags`는 memo tags, emotion, genre를 합쳐 생성
- `liked`, `saved`는 현재 로그인 사용자 기준

질문 fallback 예:

- `{book_title}은 우리에게 어떤 질문을 남길까?`
- `이 문장을 읽고 가장 먼저 떠오른 감정은 무엇일까?`
- `이 생각에 동의한다면, 그 이유는 무엇일까?`

## 8. 프론트 구현 원칙

기존 `social.html`은 전체 교체에 가깝게 정리한다.

해야 할 것:

- demo data fallback 제거 또는 개발 전용으로 격리
- `API_BASE = '/api/v2/community'`로 통일
- `authHeaders()` 공통화
- 카드 컴포넌트 normalize 함수 작성
- empty/loading/error 상태 명확히 분리
- 책 표지 fallback 구현
- 소크라테스 버튼은 `/socrates?question=...&book_id=...` 또는 POST 연결 준비
- 모임 연결 버튼은 `/community/?book_id=...` 또는 모임 생성 modal로 연결

하지 말 것:

- 일반 SNS 타임라인처럼 보이게 만들지 않는다.
- 작은 프로필 이미지와 텍스트만 있는 카드로 만들지 않는다.
- API 실패 시 조용히 mock 카드로 바꾸지 않는다.
- 카드 내부 텍스트가 넘치거나 버튼이 줄바꿈으로 깨지게 두지 않는다.

## 9. 구현 순서

1. 백엔드 계약 확정
2. `community_feed_service.py` 신설 또는 `social_feed_service.py` DB 기반으로 교체
3. `/api/v2/community/*` 라우트 추가
4. `/api/v2/social/*`는 호환 alias로 유지
5. `/social` 프론트 전체 레이아웃 재구성
6. 카드 action API 연결
7. 실제 DB 데이터로 smoke test
8. 모바일 레이아웃 점검
9. mock fallback 제거

## 10. 검증 체크리스트

백엔드:

- `GET /api/v2/community/feed`가 DB 기반 공개 메모/생각 카드를 반환한다.
- 각 카드에 user/book/thought/question/emotion_tags/counts가 포함된다.
- likes/comments/saves가 로그인 사용자 기준으로 동작한다.
- DB가 비어도 서버 오류가 아니라 empty response를 반환한다.
- `/api/v2/social/feed` alias가 깨지지 않는다.

프론트:

- `/social` 첫 화면에서 Hero, 검색, 트렌딩 책, 생각 카드가 보인다.
- 카드 표지가 크게 보인다.
- 카드 하나만 봐도 책/생각/감정/질문이 이해된다.
- 공감/댓글/저장/소크라테스/모임 연결 버튼이 있다.
- API 실패 시 mock이 아니라 오류/빈 상태가 표시된다.
- 모바일에서 버튼과 텍스트가 겹치지 않는다.

## 11. 프론트엔드 Claude Code용 프롬프트

```text
너는 LUMA 프론트엔드 구현 담당이다.

목표:
E:\독서모임앱\LUMA 의 /social 페이지를 “생각 발견 피드”로 재편성한다.

중요 컨셉:
- 페이지 이름은 “생각 피드” 또는 “독자 광장”이다.
- 일반 SNS, 인스타그램, 페이스북처럼 보이면 안 된다.
- 조용한 사색 공간, 프리미엄 북클럽, 큐레이션 매거진, 생각 아카이브 느낌이어야 한다.
- 카드 하나만 봐도 어떤 책인지, 어떤 생각인지, 어떤 감정인지, 어떤 질문인지 즉시 보여야 한다.

대상 파일:
- app/templates/social.html
- 필요하면 app/static/css 또는 app/static/js에 분리해도 되지만, 기존 프로젝트 패턴을 먼저 따를 것.

API 기준:
- 신규 프론트 호출은 /api/v2/community/* 로 통일한다.
- 사용할 API:
  - GET /api/v2/community/feed
  - GET /api/v2/community/trending-books
  - GET /api/v2/community/questions
  - GET /api/v2/community/quotes
  - GET /api/v2/community/same-book-readers
  - GET /api/v2/community/lounge-recruit
  - POST /api/v2/community/posts/<post_id>/like
  - GET /api/v2/community/posts/<post_id>/comments
  - POST /api/v2/community/posts/<post_id>/comments
  - POST /api/v2/community/posts/<post_id>/save

필수 화면 구조:
1. 상단 Hero
   - 문구: “책으로 시작된 생각들이 사람과 사람을 연결합니다.”
   - 검색창 placeholder: “지금 어떤 생각을 발견하고 싶나요?”
   - 주제 칩: #철학 #우주 #고독 #성장 #관계 #자유

2. 오늘 많이 이야기되는 책
   - 책 표지 중심 가로 캐러셀
   - 제목, 저자, 생각 수, 질문 수 표시

3. 생각 피드 카드 그리드
   - 책 표지 영역이 카드의 40% 정도 차지
   - 생각/질문 영역이 60% 정도 차지
   - 카드 필드:
     - book.cover_url 또는 cover_emoji
     - book.title
     - book.author
     - user.display_name
     - user.emoji
     - thought
     - question
     - emotion_tags
     - likes/comments/saved/liked
   - 카드 버튼:
     - 공감
     - 댓글
     - 저장
     - 소크라테스
     - 모임 연결

4. 오른쪽 패널
   - 오늘의 질문
   - 지금 많이 읽는 책
   - 독서모임 모집

5. 모바일
   - Hero
   - 트렌딩 책 가로 스크롤
   - 카드 세로 피드
   - 하단 floating 글쓰기 버튼

구현 원칙:
- 기존 social.html의 mock fallback을 제거하거나 dev-only 함수로 격리한다.
- API 실패 시 demo cards를 렌더링하지 말고 오류/빈 상태를 보여준다.
- authHeaders()를 만들어 Bearer token을 모든 요청에 적용한다.
- normalizePost(), renderThoughtCard(), loadFeed(), loadTrendingBooks(), loadQuestions(), loadQuotes(), loadRecruitCards()를 분리한다.
- 책 표지 이미지가 깨지면 cover_emoji fallback이 보이게 한다.
- 버튼 클릭은 optimistic update를 하되 실패 시 롤백한다.
- 텍스트가 버튼/카드 밖으로 넘치지 않게 CSS를 작성한다.
- 페이지의 색감은 LUMA 기존 어두운 프리미엄 톤과 맞추되, 지나친 보라/푸른 그라데이션 일변도는 피한다.

완료 전 검증:
- node 문법 검사 또는 브라우저 콘솔 오류 확인
- /social HTTP 200 확인
- 모바일 390px, 데스크톱 1440px에서 레이아웃 겹침 없음
- API가 빈 배열을 반환해도 화면이 깨지지 않음
```

## 12. 백엔드 Codex용 프롬프트

```text
너는 LUMA 백엔드 구현 담당이다.

목표:
E:\독서모임앱\LUMA 의 /social 재편성을 위해 실제 DB 기반 “생각 피드” API를 구축한다.

현재 문제:
- app/services/social_feed_service.py 는 _feed_cards, _comments 같은 메모리 mock 중심이다.
- app/templates/social.html 은 /api/social/* 를 호출하고 실패하면 demo cards를 보여준다.
- app/routes/mysql_api.py 에 /api/v2/social/* 는 있지만 내부 서비스가 mock 기반이다.
- reading_service.save_memo(is_public=True) 가 social_feed_service.create_card()를 호출하지만 DB에 실제 public feed가 저장되지 않는다.

목표 API:
신규 표준은 /api/v2/community/* 이다.

구현할 API:
- GET  /api/v2/community/feed
- GET  /api/v2/community/trending-books
- GET  /api/v2/community/questions
- GET  /api/v2/community/quotes
- GET  /api/v2/community/same-book-readers
- GET  /api/v2/community/lounge-recruit
- POST /api/v2/community/posts
- POST /api/v2/community/posts/<post_id>/like
- GET  /api/v2/community/posts/<post_id>/comments
- POST /api/v2/community/posts/<post_id>/comments
- POST /api/v2/community/posts/<post_id>/save

호환 alias:
- /api/v2/social/feed 는 /api/v2/community/feed 와 같은 shape를 반환한다.
- 기존 /api/v2/social/cards/<id>/like, comments 도 당분간 유지한다.

데이터 소스:
- users
- books
- shelf_books
- memos
- emotions
- 필요 시 신규 테이블:
  - community_post_reactions
  - community_post_comments
  - community_post_saves
  - community_generated_questions

Feed DTO shape:
{
  "post_id": "memo_xxx 또는 post_xxx",
  "type": "thought|question|quote",
  "user": {
    "user_id": "",
    "display_name": "",
    "emoji": "",
    "tags": []
  },
  "book": {
    "book_id": "",
    "title": "",
    "author": "",
    "cover_url": "",
    "cover_emoji": "📚"
  },
  "thought": "",
  "question": "",
  "quote": "",
  "emotion_tags": [],
  "likes": 0,
  "comments": 0,
  "saved": false,
  "liked": false,
  "created_at": ""
}

구현 지침:
1. app/services/community_feed_service.py 를 신설하는 것을 우선 검토한다.
2. DB 연결이 있으면 execute_all/execute_one/execute_write를 사용한다.
3. DB가 없으면 mock 카드가 아니라 기존 memory shelf/memos에서 가능한 실제 형태 데이터를 반환하되 source를 명시한다.
4. memos를 중심으로 feed를 구성한다.
   - 모든 사용자의 공개 가능한 메모가 대상이다.
   - 현재 memos 테이블에 is_public 컬럼이 없다면 1차 구현에서는 content가 있는 memos를 대상으로 하고, 이후 migration에 is_public을 추가한다.
   - 사용자 개인 메모 보호가 필요하므로 최종 설계에는 is_public 컬럼을 반드시 추가한다.
5. book join은 books.book_id로 하고 cover_url, cover_emoji를 반드시 반환한다.
6. user join은 users.user_id로 하고 display_name, emoji를 반환한다.
7. question이 비어 있으면 규칙 기반 fallback 질문을 생성한다.
8. tags는 memo.tags JSON, emotion_type, book.genre를 합쳐 emotion_tags로 반환한다.
9. like/comment/save는 현재 로그인 사용자 기준으로 liked/saved를 계산한다.
10. 모든 API는 {"ok": true, ...} shape를 유지한다.
11. 에러는 500을 숨기지 말고 {"ok": false, "error": "..."}로 반환한다.

검증:
- python -m py_compile 대상 파일들
- Flask test client 또는 Invoke-WebRequest로 다음 확인:
  - GET /api/v2/community/feed
  - GET /api/v2/community/trending-books
  - GET /api/v2/community/questions
  - GET /api/v2/community/quotes
  - POST /api/v2/community/posts/<id>/like
- /api/v2/social/feed alias가 같은 카드 shape를 반환하는지 확인
```

## 13. 최종 판단

`/social`은 지금 상태에서 바로 예쁜 프론트만 바꾸면 다시 mockup 페이지가 될 가능성이 높다.

따라서 추천 작업 방식은:

1. 백엔드에서 실제 DB 기반 `community feed DTO`를 먼저 만든다.
2. 프론트는 그 DTO만 바라보게 한다.
3. 기존 demo/mock fallback은 제거한다.
4. `/social`을 “생각 피드” UX로 전체 재구성한다.

이 순서가 코드가 꼬이지 않고 실제 사용자 데이터가 카드형 피드로 자연스럽게 보이는 가장 안전한 길이다.

## 14. 백엔드 1차 구현 결과

완료된 파일:

- `app/services/community_feed_service.py`
- `app/services/social_feed_service.py`
- `app/services/reading_service.py`
- `app/routes/mysql_api.py`

구현 내용:

- `community_feed_service.py`를 신설했다.
- 신규 표준 API `/api/v2/community/*`를 추가했다.
- `/api/v2/social/feed`는 `/api/v2/community/feed`와 같은 shape를 반환하도록 alias 처리했다.
- 기존 `/api/v2/social/cards`, `like`, `comments` 흐름도 새 community feed 서비스로 연결했다.
- `social_feed_service.py`는 기존 mock 중심 구현을 제거하고 새 community feed 서비스 호환 wrapper로 바꿨다.
- `reading_service.save_memo(is_public=True)`는 더 이상 메모리 mock social card를 중복 생성하지 않고, 기존 `memos` 기반 feed projection으로 노출되도록 조정했다.

추가된 신규 API:

```text
GET  /api/v2/community/feed
GET  /api/v2/community/trending-books
GET  /api/v2/community/questions
GET  /api/v2/community/quotes
GET  /api/v2/community/same-book-readers
GET  /api/v2/community/lounge-recruit
POST /api/v2/community/posts
POST /api/v2/community/posts/<post_id>/like
GET  /api/v2/community/posts/<post_id>/comments
POST /api/v2/community/posts/<post_id>/comments
POST /api/v2/community/posts/<post_id>/save
```

DB 연결 시 자동 생성되는 보조 테이블:

```text
community_post_reactions
community_post_comments
community_post_saves
community_generated_questions
```

검증 결과:

- `python -m py_compile` 통과
- Flask test client 기준 다음 API 응답 확인:
  - `GET /api/v2/community/feed`
  - `GET /api/v2/community/trending-books`
  - `GET /api/v2/community/questions`
  - `GET /api/v2/community/quotes`
  - `GET /api/v2/community/lounge-recruit`
  - `GET /api/v2/social/feed`
  - `POST /api/v2/community/posts`
  - `POST /api/v2/community/posts/<post_id>/like`
  - `POST /api/v2/community/posts/<post_id>/comments`
  - `GET /api/v2/community/posts/<post_id>/comments`

현재 로컬 검증 주의:

- 테스트 환경에서는 MySQL이 `Access denied for user 'root'@'localhost' (using password: NO)`로 연결되지 않아 memory 모드로 검증했다.
- MySQL `.env` 설정이 정상화되면 같은 서비스가 DB 기반으로 동작한다.

## 15. 앞으로 해야 할 업무

### 15.1 DB 마이그레이션 정리

`memos` 테이블에 공개 여부를 명확히 남기기 위해 다음 컬럼 추가를 권장한다.

```sql
ALTER TABLE memos
ADD COLUMN is_public TINYINT(1) NOT NULL DEFAULT 0,
ADD INDEX idx_public_created (is_public, created_at);
```

이후 `reading_service.save_memo()`에서 `is_public=True`일 때 해당 컬럼을 저장하도록 쿼리를 확장한다.

### 15.2 피드 공개 범위 보안

현재 1차 구현은 계획서 지침대로 `memos`에 `is_public` 컬럼이 없을 경우 content가 있는 메모를 feed 후보로 삼는다.

실서비스 전에는 반드시:

- `is_public=1`인 메모만 피드에 노출
- 비공개 사용자의 메모 제외
- 삭제/수정된 메모 반영

을 적용해야 한다.

### 15.3 프론트 `/social` 재구성

프론트는 이제 mock이 아니라 다음 API만 바라보게 재구성한다.

```text
API_BASE = /api/v2/community
```

우선 작업:

- `social.html`의 `/api/social/*` 호출 제거
- `getDemoCards()` fallback 제거
- `posts` DTO 기준 카드 렌더링
- 책 표지 중심 카드 UI 구현
- 공감/댓글/저장/소크라테스/모임 연결 버튼 연결

### 15.4 소크라테스/모임 연결

카드 버튼 연결 방식:

- 소크라테스: `post.question`, `post.thought`, `post.book`을 `/socrates` 초기 질문으로 전달
- 모임 연결: `post.book.book_id` 또는 `post.book.title`로 `/community/`의 모임 생성/추천 흐름에 전달

### 15.5 DB 연결 환경 점검

현재 로컬 테스트에서 MySQL 인증이 실패했다.

확인할 항목:

- `.env`의 `MYSQL_USER`
- `.env`의 `MYSQL_PASSWORD`
- `.env`의 `MYSQL_DB`
- MySQL 서버 실행 여부
- `python app.py` 또는 `run_luma_server.py` 실행 시 DB 연결 로그

### 15.6 후속 검증

DB 연결 후 다시 확인할 것:

```text
GET  /api/v2/community/feed
POST /api/v2/community/posts
POST /api/v2/community/posts/<post_id>/like
POST /api/v2/community/posts/<post_id>/comments
POST /api/v2/community/posts/<post_id>/save
GET  /api/v2/social/feed
```

그리고 `/social` 프론트 재편성 후:

- 카드 표지 표시
- 생각/질문/감정 태그 표시
- 댓글 카운트 반영
- 저장 상태 반영
- 모바일 레이아웃
- API 실패 시 empty/error state

까지 확인한다.

## 16. 프론트엔드 Claude Code 전달용 작업 지시서

이 섹션은 그대로 Claude Code에게 전달해도 되는 프론트엔드 인수인계 문서다.

### 16.1 작업 목표

`app/templates/social.html`을 기존 mock 기반 독자 피드에서 실제 백엔드 API 기반 **생각 피드**로 재구성한다.

프론트는 더 이상 `/api/social/*`와 `getDemoCards()`를 중심으로 움직이면 안 된다. 신규 기준은 아래 하나다.

```js
const API_BASE = '/api/v2/community';
```

완성된 `/social`은 다음 느낌이어야 한다.

- 조용한 사색 공간
- 프리미엄 북클럽
- 큐레이션 매거진
- 생각 아카이브
- 책 표지가 먼저 들어오는 카드형 피드

피해야 할 것:

- 인스타그램식 이미지 SNS
- 페이스북식 게시판
- 텍스트만 나열되는 일반 커뮤니티
- API 실패 시 가짜 demo 카드가 조용히 나타나는 구조

### 16.2 현재 백엔드 상태

백엔드는 1차 구현 완료 상태다.

사용 가능한 API:

```text
GET  /api/v2/community/feed
GET  /api/v2/community/trending-books
GET  /api/v2/community/questions
GET  /api/v2/community/quotes
GET  /api/v2/community/same-book-readers
GET  /api/v2/community/lounge-recruit
POST /api/v2/community/posts
POST /api/v2/community/posts/<post_id>/like
GET  /api/v2/community/posts/<post_id>/comments
POST /api/v2/community/posts/<post_id>/comments
POST /api/v2/community/posts/<post_id>/save
```

호환 alias는 있지만 신규 프론트에서는 쓰지 않는다.

```text
GET /api/v2/social/feed
```

### 16.3 Feed 응답 shape

`GET /api/v2/community/feed` 응답 예:

```json
{
  "ok": true,
  "posts": [
    {
      "post_id": "memo_xxx",
      "id": "memo_xxx",
      "card_id": "memo_xxx",
      "type": "thought",
      "user": {
        "user_id": "user_demo",
        "display_name": "독자",
        "emoji": "📚",
        "tags": []
      },
      "book": {
        "book_id": "book_001",
        "title": "코스모스",
        "author": "칼 세이건",
        "cover_url": "",
        "cover_emoji": "📚"
      },
      "thought": "이 책은 인간의 위치를 다시 묻게 만든다.",
      "content": "이 책은 인간의 위치를 다시 묻게 만든다.",
      "question": "코스모스는 우리에게 어떤 질문을 남길까?",
      "quote": "",
      "emotion_tags": ["우주", "철학"],
      "tags": ["우주", "철학"],
      "likes": 0,
      "like_count": 0,
      "comments": 0,
      "comment_count": 0,
      "saved": false,
      "liked": false,
      "is_liked": false,
      "created_at": "2026-05-18T01:08:42"
    }
  ],
  "cards": [],
  "total": 1,
  "page": 1,
  "has_next": false,
  "source": "db"
}
```

프론트는 `posts`를 우선 사용한다. `cards`는 호환용 필드다.

### 16.4 프론트 파일 작업 범위

주 대상:

```text
app/templates/social.html
```

선택:

```text
app/static/css/social.css
app/static/js/social.js
```

단, 현재 프로젝트가 페이지 단위 템플릿 안에 CSS/JS를 직접 포함하는 패턴이 많으므로, 불필요하게 구조를 크게 분리하지 않는다. 분리하더라도 `/social`에서 로딩되는지 반드시 확인한다.

### 16.5 필수 레이아웃

#### A. 상단 Hero

필수 요소:

- H1: `생각 피드`
- 문구: `책으로 시작된 생각들이 사람과 사람을 연결합니다.`
- 검색창 placeholder: `지금 어떤 생각을 발견하고 싶나요?`
- 칩: `#철학`, `#우주`, `#고독`, `#성장`, `#관계`, `#자유`

검색창 동작:

- Enter 입력 또는 검색 버튼 클릭 시 `/api/v2/community/feed?q=검색어`
- 칩 클릭 시 `/api/v2/community/feed?tag=철학`

#### B. 오늘 많이 이야기되는 책

API:

```text
GET /api/v2/community/trending-books
```

표시 필드:

- `cover_url` 또는 `cover_emoji`
- `title`
- `author`
- `thought_count`
- `question_count`
- `reader_count`

UI:

- 가로 스크롤 캐러셀
- 책 표지가 가장 크게 보여야 함
- 카드 클릭 시 해당 책 기준 같은 책 독자 또는 feed 필터를 호출할 수 있음

#### C. 생각 피드 카드 그리드

API:

```text
GET /api/v2/community/feed?page=1&limit=12
```

카드 필수 구조:

- 왼쪽 또는 상단 40%: 책 표지
- 오른쪽 또는 하단 60%: 생각/질문/사용자/액션

카드에 반드시 보여줄 것:

- 책 표지
- 책 제목
- 저자
- 사용자 닉네임
- 사용자 이모지
- 짧은 생각
- 질문
- 감정 태그
- 공감 수
- 댓글 수
- 저장 상태

카드 버튼:

```text
공감
댓글
저장
소크라테스
모임 연결
```

#### D. 오른쪽 패널

데스크톱에서만 넉넉히 표시하고, 모바일에서는 본문 아래로 내려도 된다.

섹션:

- 오늘의 질문: `GET /api/v2/community/questions`
- 오늘의 문장: `GET /api/v2/community/quotes`
- 독서모임 모집: `GET /api/v2/community/lounge-recruit`

#### E. 모바일

390px 폭에서 확인한다.

- Hero가 너무 길어지지 않아야 함
- 트렌딩 책은 가로 스크롤
- 피드 카드는 1열
- 버튼은 2줄까지 허용하되 겹치면 안 됨
- 하단 floating 글쓰기 버튼을 둘 수 있음

### 16.6 필수 JS 함수 구조

권장 함수:

```js
const API_BASE = '/api/v2/community';

function authHeaders(extra = {}) {}
function escapeHtml(value) {}
function normalizePost(raw) {}
function coverHtml(book, className = '') {}

async function apiGet(path, params = {}) {}
async function apiPost(path, body = {}) {}

async function loadInitialSocialPage() {}
async function loadFeed({ append = false, page = 1, tag = '', q = '', emotion = '' } = {}) {}
async function loadTrendingBooks() {}
async function loadQuestions() {}
async function loadQuotes() {}
async function loadRecruitCards() {}

function renderFeed(posts, { append = false } = {}) {}
function renderThoughtCard(post) {}
function renderTrendingBooks(books) {}
function renderQuestions(questions) {}
function renderQuotes(quotes) {}
function renderRecruitCards(recruits) {}

async function togglePostLike(postId, button) {}
async function togglePostSave(postId, button) {}
async function toggleComments(postId) {}
async function submitComment(postId) {}
function openSocratesFromPost(postId) {}
function openCommunityFromPost(postId) {}
```

### 16.7 API 연결 상세

공감:

```text
POST /api/v2/community/posts/<post_id>/like
```

응답:

```json
{
  "ok": true,
  "liked": true,
  "likes": 1,
  "like_count": 1
}
```

저장:

```text
POST /api/v2/community/posts/<post_id>/save
```

응답:

```json
{
  "ok": true,
  "saved": true,
  "saves": 1
}
```

댓글 조회:

```text
GET /api/v2/community/posts/<post_id>/comments
```

댓글 작성:

```text
POST /api/v2/community/posts/<post_id>/comments
Content-Type: application/json
```

body:

```json
{
  "content": "좋은 질문이에요."
}
```

글 작성:

```text
POST /api/v2/community/posts
```

body 예:

```json
{
  "content": "코스모스는 인간이 자기 위치를 다시 묻게 만든다.",
  "book_title": "코스모스",
  "tags": ["우주", "철학"],
  "question": "인간은 왜 자신의 위치를 알고 싶어할까?"
}
```

### 16.8 삭제하거나 격리할 기존 요소

`social.html`에서 반드시 정리할 것:

- `/api/social/feed` 직접 호출
- `/api/social/cards`
- `/api/social/cards/<id>/like`
- `/api/social/cards/<id>/comments`
- `getDemoCards()`
- `getDemoComments()`
- API 실패 시 demo data 렌더링
- mock 숫자 통계 고정값

개발 중 fallback이 필요하면 화면에는 표시하지 말고 console 경고 또는 명시적 empty state를 사용한다.

### 16.9 Empty / Loading / Error 상태

Loading:

- 피드: 카드 skeleton 또는 조용한 loading block
- 트렌딩 책: 작은 cover skeleton

Empty:

```text
아직 발견할 생각이 없습니다.
첫 생각을 남기거나 책 메모를 공개해보세요.
```

Error:

```text
생각 피드를 불러오지 못했습니다.
잠시 후 다시 시도해주세요.
```

중요:

- Error 상태에서 demo card를 보여주지 않는다.
- Empty 상태와 Error 상태를 구분한다.

### 16.10 디자인 가이드

전체 톤:

- LUMA 기존 다크 프리미엄 톤 유지
- 과한 보라/파랑 그라데이션 반복 금지
- 카드 내부 텍스트는 작고 조용하지만 읽기 쉬워야 함
- 책 표지는 크게
- 카드 radius는 8px 안팎 권장
- 버튼은 작은 pill 또는 icon+text로 명확하게

카드 레이아웃:

```text
[책 표지 40%] [생각 60%]
```

또는 모바일:

```text
[책 표지]
[책 제목/저자]
[생각]
[질문]
[태그]
[액션]
```

표지 fallback:

- `book.cover_url`이 있으면 이미지 사용
- 이미지 로딩 실패 또는 빈 값이면 `book.cover_emoji`와 책 제목 일부 표시

### 16.11 소크라테스 / 모임 연결

소크라테스 버튼:

1차 구현은 URL 이동으로 충분하다.

```js
const params = new URLSearchParams({
  question: post.question || '',
  book_id: post.book.book_id || '',
  book_title: post.book.title || '',
  thought: post.thought || ''
});
location.href = `/socrates?${params.toString()}`;
```

모임 연결 버튼:

```js
const params = new URLSearchParams({
  book_id: post.book.book_id || '',
  book_title: post.book.title || ''
});
location.href = `/community/?${params.toString()}`;
```

### 16.12 완료 조건

Claude Code 작업 완료 조건:

- `/social`이 HTTP 200으로 열린다.
- 브라우저 콘솔에 JS syntax error가 없다.
- `/api/v2/community/feed`의 `posts` 데이터를 카드로 렌더링한다.
- `/api/social/*` 의존이 제거된다.
- API 실패 시 demo 카드가 나오지 않는다.
- 공감 버튼이 `liked/likes`를 반영한다.
- 저장 버튼이 `saved`를 반영한다.
- 댓글 열기/작성/카운트 갱신이 동작한다.
- 트렌딩 책 캐러셀이 보인다.
- 오늘의 질문/오늘의 문장/독서모임 모집 패널이 보인다.
- 모바일 390px에서 레이아웃이 겹치지 않는다.
- 데스크톱 1440px에서 카드 그리드와 오른쪽 패널이 자연스럽다.

### 16.13 Claude Code에게 줄 최종 프롬프트

```text
너는 LUMA 프론트엔드 구현 담당이다.

E:\독서모임앱\LUMA 의 app/templates/social.html 을 “생각 피드”로 재편성해줘.

반드시 이 문서를 먼저 읽어:
app/docs/LUMA_Social_생각피드_재편성_작업계획서.md

백엔드 1차 구현은 완료되어 있고, 신규 프론트 기준 API는 /api/v2/community/* 이다.

핵심 요구:
- /api/social/* 호출을 제거하고 /api/v2/community/* 로 통일
- getDemoCards/getDemoComments 같은 mock fallback 제거
- API 실패 시 demo 카드 표시 금지
- 책 표지 중심 카드형 피드 구현
- 카드에는 책, 사용자, 생각, 질문, 감정 태그, 공감, 댓글, 저장, 소크라테스, 모임 연결이 보여야 함
- Hero, 트렌딩 책 캐러셀, 생각 피드 그리드, 오른쪽 패널을 구성
- 오른쪽 패널에는 오늘의 질문, 오늘의 문장, 독서모임 모집을 표시
- 모바일 390px와 데스크톱 1440px에서 겹침 없이 보여야 함

사용 API:
- GET /api/v2/community/feed
- GET /api/v2/community/trending-books
- GET /api/v2/community/questions
- GET /api/v2/community/quotes
- GET /api/v2/community/lounge-recruit
- POST /api/v2/community/posts/<post_id>/like
- GET /api/v2/community/posts/<post_id>/comments
- POST /api/v2/community/posts/<post_id>/comments
- POST /api/v2/community/posts/<post_id>/save

디자인 톤:
- 일반 SNS처럼 보이면 안 됨
- 조용한 사색 공간
- 프리미엄 북클럽
- 큐레이션 매거진
- 생각 아카이브

완료 전 검증:
- /social HTTP 200
- 브라우저 콘솔 오류 없음
- API empty/error 상태에서 화면 깨짐 없음
- 공감/댓글/저장 동작
- 모바일/데스크톱 레이아웃 확인
```
