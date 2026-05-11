# LUMA Discover — Backend / Frontend 작업 프롬프트

## 전제

`LUMA_Discover_Page_Detailed_Plan_and_Claude_Prompt.md`의 책 탐색 허브 구조를 따르되, 우주 콘셉트는 제거한다.

`LUMA_Discover_Seed_To_Tree_Concept_Rework.md` 기준으로 Discover는 “새로운 생각의 씨앗을 발견하는 정원”이다.

- 책 = 씨앗
- 저장 = 씨앗 심기
- 읽기/감정/메모 = 성장
- 개인 독서 기록 = 나만의 숲

---

## Backend 구현 완료 상태

아래 백엔드 작업은 현재 코드에 반영되어 있다.

- `app/services/shelf_service.py`
  - `search_books_naver(query, limit)` 추가
  - `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 기반 네이버 책 검색 연동
  - 네이버 응답 HTML 태그 제거
  - 네이버 `image` → `cover_url` 매핑
  - 네이버 `isbn`에서 13자리 ISBN 우선 추출
  - 네트워크/API/key 실패 시 빈 배열 반환으로 안전 fallback

- `app/routes/mysql_api.py`
  - `/api/v2/books/search?q=&source=&limit=`에서 `source=naver` 지원
  - `source=all`일 때 local → naver → google 순서로 결과 병합
  - ISBN 또는 `title + author` 기준 중복 제거
  - Discover 프론트가 쓰는 표준 book schema 반환

- 테스트
  - `tests/test_discover_books.py`
  - 네이버 응답 mapping/HTML cleanup/route 동작 검증

현재 Discover 프론트는 아래 API를 바로 호출할 수 있다.

```txt
GET /api/v2/books/search?q=데미안&source=naver&limit=12
GET /api/v2/books/search?q=데미안&source=all&limit=12
GET /api/v2/books/popular?limit=12
GET /api/v2/books/recommendations?user_id=user_demo
GET /api/v2/books/recommend-by-emotion?user_id=user_demo&emotion=성장
POST /api/v2/shelf/books
```

---

## Backend Prompt — Discover API 완성

```md
너는 LUMA 독서모임 앱의 백엔드 엔지니어다.

목표:
Discover 페이지가 새로운 책을 탐색하고, 감정/취향 기반 추천을 받고, 선택한 책을 내 서재에 저장할 수 있도록 `/api/v2` 백엔드를 완성한다.

기존 구조:
- Flask app factory: `app/factory.py`
- 통합 API blueprint: `app/routes/mysql_api.py`
- 책/서재 서비스: `app/services/shelf_service.py`
- 감정/추천 서비스: `app/services/reading_service.py`
- Gemini 보조 서비스: `app/services/gemini_service.py`
- MySQL 유무에 따라 Mock fallback을 유지해야 한다.
- `.env`에는 아래 값이 준비되어 있다.
  - `NAVER_CLIENT_ID`
  - `NAVER_CLIENT_SECRET`

핵심 검색 전략:
- `/api/v2/books/search`는 **네이버 책 검색 API를 1순위 provider**로 사용한다.
- 한국어/국내 도서 품질을 위해 기본 `source=all`일 때 provider 순서는 다음과 같다.
  1. local cache / local DB
  2. Naver Book Search API
  3. Google Books API
  4. mock fallback
- 단, `source=naver`, `source=google`, `source=local`이 명시되면 해당 provider를 우선 사용한다.
- 네이버 키가 없거나 요청 실패/한도 초과/빈 결과면 예외를 터뜨리지 말고 다음 provider로 fallback한다.
- 프론트에는 항상 같은 book schema를 반환한다.

네이버 API 연결 규칙:
- endpoint: `https://openapi.naver.com/v1/search/book.json`
- method: `GET`
- query params:
  - `query`: 검색어
  - `display`: limit와 연결하되 네이버 허용 범위 안에서 사용
  - `start`: 기본 1
  - `sort`: 기본 `sim`
- headers:
  - `X-Naver-Client-Id: os.getenv("NAVER_CLIENT_ID")`
  - `X-Naver-Client-Secret: os.getenv("NAVER_CLIENT_SECRET")`
- timeout은 4~5초로 짧게 둔다.
- 네이버 응답 HTML 태그(`<b>...</b>`)는 제거해서 저장/렌더링한다.
- `image` 필드는 `cover_url`로 매핑한다.
- `isbn`은 공백으로 10자리/13자리가 함께 올 수 있으므로 원본 문자열도 보존하고, 가능하면 13자리 ISBN을 대표값으로 고른다.

네이버 응답 매핑:
- `title` → `title`
- `author` → `author`
- `image` → `cover_url`
- `description` → `description`
- `publisher` → `publisher`
- `pubdate` → `published_date`
- `isbn` → `isbn`
- `link` → `external_url`
- 고정/추론 필드:
  - `source: "naver"`
  - `cover_emoji: "🌱"`
  - `category/genre`: 없으면 빈 문자열
  - `reason`: `"국내 도서 검색에서 발견한 생각의 씨앗입니다."`

추천 구현 위치:
- `app/services/shelf_service.py`에 `search_books_naver(query: str, limit: int = 10) -> list` 추가
- `search_books_google()`와 비슷하게 네트워크 오류를 내부에서 처리하고 빈 배열 반환
- provider 통합 함수가 필요하면 `search_books_external(query, source, limit)`처럼 작은 헬퍼로 분리
- `app/routes/mysql_api.py`의 `/books/search`에서 local + naver + google 결과를 합쳐 표준화
- 중복 제거 기준은 ISBN 우선, ISBN이 없으면 `title + author` lower-case 기준

필수 API:
1. `GET /api/v2/books/search?q=&source=&limit=`
   - local, naver, google, all source 지원
   - 기본값은 `source=all`
   - `all`일 때 local → naver → google → mock 순서로 결과를 구성
   - Naver 실패 시 Google Books/local/mock으로 fallback
   - 응답 book 필드 표준화:
     `book_id,title,author,cover_url,cover_emoji,genre,category,rating,source,reason,saved,reading_status,total_pages,description,isbn,publisher,published_date,external_url`
   - 검색어가 비어 있으면 400이 아니라 `{ok:true, books:[]}`를 반환한다.

2. `GET /api/v2/books/recommendations?user_id=`
   - 사용자 장르/감정 패턴 기반 추천
   - Gemini 사용 가능 시 추천 reason 생성
   - Gemini 실패 또는 키 없음이면 품질 좋은 mock reason 반환

3. `GET /api/v2/books/popular?limit=`
   - MySQL이면 shelf 저장 수 기준 정렬
   - Mock이면 `_books_mem` 기반 반환

4. `GET /api/v2/books/recommend-by-emotion?user_id=&emotion=`
   - 감정 태그에 맞는 추천 reason 생성
   - emotion 미입력 시 사용자 dominant emotion 사용

5. `GET /api/v2/books/<book_id>`
   - 책 상세 정보 반환

6. `POST /api/v2/shelf/books`
   - Discover의 “씨앗 심기” 버튼에서 호출
   - 중복 저장은 실패가 아니라 기존 shelf 상태를 반환하거나 ok 처리

완료 기준:
- 모든 API는 `{ok:true}` 또는 `{ok:false,error}` 형태를 지킨다.
- Authorization Bearer 토큰이 있으면 해당 user_id를 사용하고, 없으면 개발용 `user_demo` fallback을 유지한다.
- MySQL 연결/비연결 양쪽에서 동작한다.
- `.env`에 네이버 키가 없을 때도 앱이 정상 실행된다.
- 네이버 키가 있을 때 `/api/v2/books/search?q=데미안&source=naver`가 실제 표지/저자/설명 정보를 반환한다.
- 네이버 결과의 HTML 태그가 제거되어 프론트에 표시된다.
- 같은 책이 local/naver/google에 중복으로 잡혀도 한 번만 반환된다.
- 테스트는 Flask test_client로 검색, 추천, 인기, 감정추천, 저장 흐름을 확인한다.
- 네이버 API는 테스트에서 실제 네트워크를 호출하지 말고 monkeypatch/mock으로 응답을 주입한다.
- Discover 프론트가 네트워크 실패 없이 렌더링할 수 있도록 빈 배열 대신 fallback 데이터를 안정적으로 반환한다.
```

---

## Frontend Prompt — lounge.html을 Discover 정원으로 전환

```md
너는 LUMA 독서모임 앱의 프론트엔드 엔지니어다.

목표:
기존 `app/templates/lounge.html`의 라운지 UI를 제거하고, Discover 페이지로 전면 교체한다.
이 페이지는 새로운 책을 탐색하는 허브이며, 콘셉트는 “씨앗이 나무가 되는 독서 정원”이다.

디자인 방향:
- 숲속 독서 공간
- 따뜻한 종이 질감
- 햇빛과 나무 그림자
- 책 표지 중심 UI
- 책 = 씨앗
- 저장 = 씨앗 심기
- 저장 완료 = 자라는 중

금지:
- 우주/성운/별자리/SF/HUD/네온 콘셉트
- 차가운 블루/퍼플 중심 팔레트
- 쇼핑몰식 상품 리스트
- 책 표지를 작게 처리하는 UI

필수 화면 구성:
1. Discover Hero
   - 문구: “오늘 당신 안에 심어질 새로운 문장”
   - 대표 책 카드
   - CTA: 오늘의 씨앗 보기, 생각의 씨앗 찾기

2. Search Dock
   - placeholder: “어떤 생각의 씨앗을 찾고 있나요?”
   - Enter와 버튼 검색 지원
   - `/api/v2/books/search?q=...` 연결

3. Filter Chips
   - 평온, 위로, 성장, 용기, 호기심, 사색, 문학, 과학, 철학
   - 선택 시 검색 또는 감정 추천 호출

4. 추천 섹션
   - 오늘의 씨앗
   - 새로운 숲을 여는 책
   - 많은 사람들이 키우는 책
   - 지금 당신에게 필요한 문장

5. Book Seed Card
   - cover_url 있으면 이미지 렌더
   - 없으면 cover_emoji와 제목 fallback
   - title, author, reason 표시
   - “씨앗 심기” 버튼
   - 저장 후 “자라는 중” 상태

필수 JS 함수:
- initDiscoverPage()
- searchBooks(query)
- render(containerId, books)
- plantSeed(book, button)
- showToast(message)
- setHero(book)

API:
- `GET /api/v2/books/search?q=...`
- `GET /api/v2/books/recommendations?user_id=...`
- `GET /api/v2/books/popular`
- `GET /api/v2/books/recommend-by-emotion?user_id=...`
- `POST /api/v2/shelf/books`

완료 기준:
- `/lounge`와 `/discover`에서 Discover 페이지가 열린다.
- 라운지 문구와 공독 모임 UI가 보이지 않는다.
- 모바일에서 Hero, Search Dock, Chips, Book Cards가 겹치지 않는다.
- API 실패 시 fallback book card가 보인다.
- 저장 버튼 클릭 시 토스트가 뜨고 버튼 상태가 바뀐다.
```
