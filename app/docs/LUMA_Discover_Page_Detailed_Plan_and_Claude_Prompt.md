
# LUMA Discover Page 추가 구성 계획서 + Claude Code 상세 지시 프롬프트

## 문서 목적

이 문서는 기존 LUMA 독서모임 앱에 **Discover 페이지**를 추가하기 위한 상세 구성 계획서입니다.

Discover는 단순 검색 페이지가 아니라, 사용자가 **새로운 책을 발견하고, 감정과 주제에 맞는 책을 만나고, 내 서재로 자연스럽게 저장하는 탐색 허브**입니다.

디자인 방향은 “밀리의 서재처럼 책 표지 중심의 풍성한 추천 화면”을 참고하되, 그대로 복제하지 않고 LUMA의 우주 세계관으로 재해석합니다.

---

# 1. Discover 페이지의 핵심 역할

Discover는 사용자가 다음 행동을 하게 만드는 페이지입니다.

1. 새 책 발견
2. 감정/주제 기반 탐색
3. 책 표지 중심으로 빠른 훑어보기
4. 관심 책 상세 확인
5. 내 서재에 저장
6. 읽고 싶은 책으로 전환
7. 이후 Reflection / Library / Lounge와 연결

즉 Discover는 LUMA 안에서 **“새로운 책을 만나는 입구”** 역할을 합니다.

---

# 2. 사용자 흐름

## 기본 흐름

Home → Discover → 책 검색 또는 추천 확인 → 책 상세 보기 → 내 서재에 추가 → Library 또는 Reflection으로 이동

## 감정 기반 흐름

Reflection에서 감정 선택 → Discover 진입 → “오늘의 감정에 맞는 책” 추천 → 책 저장 → 감정 메모 작성

## 모임 기반 흐름

Lounge에서 특정 주제 발견 → Discover에서 관련 책 추천 → 책 저장 → 같은 책 읽는 모임 참여

---

# 3. 화면 전체 구조

Discover 페이지는 아래 7개 영역으로 구성합니다.

1. 상단 Hero 추천 영역
2. Search Dock
3. Filter Chips
4. 오늘의 추천 책
5. 새로 만나는 책
6. 인기 있는 책
7. 감정/생각 기반 추천 섹션

---

# 4. Discover 페이지 레이아웃

## Desktop 구조

상단:
- Global Navigation
- Discover Hero

중앙:
- Search Dock
- Filter Chips

메인:
- Hero Book Carousel
- Recommended Books
- Popular Books
- Emotion Based Books
- Thought Expansion Books

하단:
- BlackholeDock 또는 Library 저장 CTA

## Mobile 구조

상단:
- 짧은 Hero
- Search Dock

중앙:
- 수평 스크롤 Filter Chips
- Cover Card Carousel

하단:
- 추천 섹션 세로 스택
- 저장 버튼은 카드 내부에 배치

---

# 5. 화면별 상세 구성

## 5-1. Hero 추천 영역

### 목적
사용자가 들어오자마자 “읽고 싶은 책”을 느끼게 하는 영역입니다.

### 구성
- 큰 배경 이미지 또는 성운 배경
- 오늘의 추천 문장
- 대표 책 1권
- 책 표지
- 추천 이유
- CTA 버튼

### 예시 문구
- 오늘 당신의 생각을 넓혀줄 책
- 지금의 감정에 가장 가까운 문장
- 새로운 우주를 열어볼까요?

### 버튼
- 자세히 보기
- 내 서재에 담기
- 비슷한 책 보기

---

## 5-2. Search Dock

### 목적
책 제목, 저자, 키워드로 검색하는 영역입니다.

### 구성
- 검색 input
- 검색 버튼
- 최근 검색어
- 인기 검색어

### Placeholder 예시
책 제목, 저자, 생각 키워드를 검색해보세요

### UX 규칙
- 검색창은 단순 사각형이 아니라 유리 HUD 도크처럼 만든다.
- focus 시 은은한 glow를 넣는다.
- 검색 중에는 loading spinner 표시.
- 결과가 없으면 추천 키워드를 보여준다.

---

## 5-3. Filter Chips

### 목적
사용자가 책을 감정/주제/상태 기준으로 빠르게 탐색하게 합니다.

### 필터 그룹

감정:
- 평온
- 영감
- 감동
- 호기심
- 몰입
- 위로

주제:
- 문학
- 인문
- 과학
- 철학
- 자기계발
- 예술
- 사회
- 역사

상태:
- 베스트셀러
- 신간
- 사람들이 많이 저장한 책
- 내 생각과 연결된 책
- 모임에서 읽는 책

### UX 규칙
- 선택된 chip은 빛나는 행성처럼 강조한다.
- 여러 chip 선택 가능.
- 모바일에서는 가로 스크롤.

---

# 6. 책 카드 컴포넌트 상세

## BookCard 필드

- book_id
- title
- author
- cover_url
- description
- category
- rating
- source
- reason
- saved
- reading_status

## 카드 내부 구성

상단:
- cover image

중간:
- title
- author

하단:
- reason badge
- save button

## 이미지 fallback
cover_url이 없으면:
- 어두운 그라디언트 표지
- 제목 첫 글자
- LUMA 로고
- 장르 색상

---

# 7. 필요한 API 연결 구조

## 검색
GET /api/v2/books/search?q=...

## 추천
GET /api/v2/books/recommendations?user_id=...

## 인기
GET /api/v2/books/popular

## 감정 기반 추천
GET /api/v2/books/recommend-by-emotion?user_id=...

## 저장
POST /api/v2/shelf/books

## 상세
GET /api/v2/books/{book_id}

---

# 8. 상태 처리

## Loading
- skeleton book card
- shimmer animation

## Empty
문구:
검색 결과가 아직 없습니다.  
다른 키워드로 우주를 탐색해보세요.

## Error
문구:
책 정보를 불러오지 못했습니다.  
잠시 후 다시 시도해주세요.

## Retry
- 다시 불러오기 버튼

---

# 9. discover.html 구조 예시

```html
<section class="discover-page">
  <section class="discover-hero">
    <div class="hero-copy">
      <p class="eyebrow">오늘의 발견</p>
      <h1>새로운 책의 우주를 탐색하세요</h1>
      <p>감정과 생각을 따라, 지금의 나에게 맞는 책을 찾아드립니다.</p>
      <button class="btn-primary">추천 책 보기</button>
    </div>

    <div class="hero-book-card">
      <img src="" alt="추천 책 표지" />
      <div class="hero-book-meta">
        <strong>코스모스</strong>
        <span>칼 세이건</span>
      </div>
    </div>
  </section>

  <section class="search-dock">
    <input id="book-search-input" placeholder="책 제목, 저자, 생각 키워드를 검색해보세요" />
    <button id="book-search-btn">탐색</button>
  </section>

  <section class="filter-chip-row">
    <button class="chip active">평온</button>
    <button class="chip">영감</button>
    <button class="chip">문학</button>
    <button class="chip">과학</button>
  </section>

  <section class="book-section">
    <div class="section-header">
      <h2>오늘의 추천 책</h2>
      <button>전체 보기</button>
    </div>
    <div id="recommended-books" class="book-carousel"></div>
  </section>

  <section class="book-section">
    <div class="section-header">
      <h2>새로 만나는 책</h2>
    </div>
    <div id="new-books" class="book-carousel"></div>
  </section>

  <section class="book-section">
    <div class="section-header">
      <h2>많이 읽는 책</h2>
    </div>
    <div id="popular-books" class="book-grid"></div>
  </section>
</section>
```

---

# 10. discover.css 구현 지시

Claude Code에게 CSS 작성 시 아래를 반드시 지시합니다.

- `.discover-page`는 전체 우주 배경 위에 올라가는 구조
- `.discover-hero`는 큰 히어로 카드
- `.search-dock`은 glassmorphism 적용
- `.book-carousel`은 horizontal scroll + snap
- `.book-card`는 표지 중심
- `.book-card:hover`는 scale + glow
- 모바일에서는 1열 카드 또는 가로 캐러셀 유지
- 표지 이미지 비율은 2:3 유지

---

# 11. discover.js 구현 지시

Claude Code에게 JS 작성 시 아래를 반드시 지시합니다.

## 함수 목록

- initDiscoverPage()
- loadRecommendedBooks()
- loadPopularBooks()
- searchBooks(query)
- renderBookCards(containerId, books)
- saveBookToShelf(bookId)
- showDiscoverLoading(containerId)
- showDiscoverEmpty(containerId)
- showDiscoverError(containerId, message)

## 이벤트
- 검색 버튼 클릭
- Enter 검색
- chip 클릭
- 책 카드 클릭
- 저장 버튼 클릭

## fetch 규칙
- 공통 apiFetch 사용
- 실패 시 fallback mock 사용 가능
- cover_url 없으면 fallback 렌더링

---

# 12. Claude Code에 붙여넣는 최종 프롬프트

```md
# Prompt 08 — Discover Page 상세 구현

너는 LUMA 독서모임 앱의 시니어 프론트엔드 개발자다.

기존 앱에 Discover 페이지를 추가한다.
이 페이지는 단순 검색 페이지가 아니라, 사용자가 새로운 책을 발견하는 탐색 허브다.

디자인 방향:
- 밀리의 서재처럼 책 표지 중심의 풍성한 추천 화면
- 단, 그대로 복제하지 말고 LUMA의 우주 세계관으로 재해석
- 심우주 배경, 유리 HUD, 빛나는 책 카드, 수평 캐러셀 사용

반드시 구현할 영역:
1. Discover Hero
2. Search Dock
3. Filter Chips
4. 오늘의 추천 책
5. 새로 만나는 책
6. 인기 있는 책
7. 감정/생각 기반 추천

생성/수정 파일:
1. app/templates/discover.html
2. app/static/css/discover.css
3. app/static/js/discover.js

API 연결은 우선 구조만 만든다.
실제 endpoint는 아래를 기준으로 fetch 함수를 작성한다.

- GET /api/v2/books/search?q=...
- GET /api/v2/books/recommendations?user_id=...
- GET /api/v2/books/popular
- GET /api/v2/books/recommend-by-emotion?user_id=...
- POST /api/v2/shelf/books

필수 함수:
- initDiscoverPage()
- loadRecommendedBooks()
- loadPopularBooks()
- searchBooks(query)
- renderBookCards(containerId, books)
- saveBookToShelf(bookId)

상태 처리:
- loading
- empty
- error
- image fallback

모바일 대응:
- Hero는 세로형으로 변경
- 책 카드는 horizontal snap carousel
- filter chips는 가로 스크롤
- 검색창은 상단 고정에 가깝게 배치

금지:
- 일반 쇼핑몰 UI처럼 만들기
- 흰 배경 카드 위주 구성
- 책 표지를 작게 처리
- API 경로 임의 변경
- Jinja2와 충돌나는 {{ }} 사용

작업 후 출력:
1. 수정 파일 목록
2. discover.html 전체 코드
3. discover.css 전체 코드
4. discover.js 전체 코드
5. 모바일 대응 설명
6. 다음에 백엔드와 연결해야 할 API 목록
```

---

# 13. 완료 기준

Discover 페이지는 아래 조건을 만족해야 완료입니다.

- 검색창이 보인다
- filter chips가 보인다
- 추천 책 캐러셀이 보인다
- 책 표지 카드가 중심이다
- 인기 책 섹션이 있다
- 감정/생각 기반 추천 섹션이 있다
- 모바일에서 깨지지 않는다
- 책 이미지가 없어도 fallback이 보인다
- 저장 버튼이 있다
- API 연결 준비가 되어 있다
