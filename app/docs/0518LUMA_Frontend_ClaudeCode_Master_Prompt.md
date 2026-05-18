
# LUMA 프론트엔드 Claude Code용 마스터 프롬프트

Target: Claude Code  
Role: Senior UX/UI Designer + Frontend Engineer  
Project: LUMA 독서모임 앱

---

## 0. 작업 목적

LUMA의 프론트엔드는 단순 페이지 모음이 아니라, 책을 읽고 생각을 나누는 **프리미엄 독서 커뮤니티 UI**가 되어야 한다.

이번 프론트 작업의 목표는 기존 코드를 최대한 유지하면서 아래 페이지를 일관된 디자인과 네비게이션으로 연결하는 것이다.

1. Lounge 책 탐사 라운지
2. Community 카드형 생각 피드
3. DeepDive 책 이해 큐레이션
4. Profile 나의 독서 우주
5. Places 독서모임 장소 찾기
6. Socrates 철학 토론광장

---

## 1. 절대 원칙

아래는 반드시 지킨다.

- 기존 HTML/CSS/JS를 통째로 삭제하지 않는다.
- 기존 route와 API 경로를 임의로 바꾸지 않는다.
- 기존 기능을 제거하지 않는다.
- 백엔드 API key를 프론트에 직접 노출하지 않는다.
- CSS 전체를 무리하게 덮어쓰지 않는다.
- 페이지별 기존 구조를 먼저 audit하고 필요한 부분만 확장한다.
- 모바일 레이아웃을 반드시 고려한다.
- 모든 API 렌더링에는 loading, empty, error, retry 상태를 넣는다.
- 이미지가 없거나 깨져도 fallback UI가 보여야 한다.
- Jinja2와 충돌하는 `{{ }}` 문법을 JS 문자열 안에서 사용하지 않는다.

---

## 2. 공통 네비게이션 통일

모든 페이지에서 아래 흐름을 동일하게 맞춘다.

```text
LUMA
생각은 빛이 된다

[별자리 지도]
[마음 행성계]
[탐사 성운]
[독자 광장]
[라이브]
[소크라테스]
[딥다이브]
[프로필]
[모임 장소]
```

---

## 3. 공통 디자인 시스템

기존 `http://localhost:5000/`의 진녹색 배경, 탐사 장치 느낌을 기준으로 통일한다.

### 디자인 키워드

```text
deep forest green
premium reading club
exploration device
thought constellation
dark glass panel
gold accent
calm intellectual UI
```

### CSS Token

```css
:root {
  --bg: #07130f;
  --bg2: #0b1d16;
  --bg3: #10271e;

  --green-deep: #123524;
  --green-soft: #2f5d46;
  --green-glow: rgba(80,180,120,.22);

  --gold: #f5c86b;
  --gold-dim: rgba(245,200,107,.12);

  --text: #f3f7f0;
  --sub: #9aa89d;

  --panel: rgba(255,255,255,.055);
  --border: rgba(255,255,255,.09);
}
```

---

## 4. Lounge Frontend Filter UI

### 목표

`/lounge`를 감정별/성향별/분야별/최신/클래식/평점/토론 적합도 기준으로 책을 탐사하는 페이지로 만든다.

### 필터

감정:

```text
위로, 사색, 성장, 몰입, 평온, 용기, 고독, 회복, 호기심
```

성향:

```text
분석형, 감성형, 토론형, 실용형, 탐구형, 회복형
```

분야:

```text
문학, 에세이, 인문, 철학, 심리, 과학, 역사, 사회, 예술, 자기계발
```

기준:

```text
최신 발간, 클래식, 평점 높은 책, 토론하기 좋은 책, 입문자 추천
```

### API 연결

```text
GET /api/v2/lounge/books/recommend
```

### Book Card 필수 정보

- 책 표지
- 제목
- 저자
- 설명
- 추천 이유
- 태그
- 점수
- 책 상세
- 영상 보기
- 소크라테스 질문
- 이 책으로 모임 열기

### 이미지 처리

- `cover_url` 있으면 표시
- 없으면 fallback cover 표시
- 이미지 깨지면 fallback cover로 교체
- 표지 비율 2:3 유지
- lazy loading 적용 가능

### JS 함수 후보

```js
initLoungeExplorer()
loadRecommendedBooks(filters)
renderBookCards(books)
selectFilter(type, value)
openBookDetail(bookId)
saveBook(bookId)
createLoungeFromBook(bookId)
renderCoverFallback(book)
```

---

## 5. Community 카드형 피드 UI

### 목표

`/community`를 여러 사람의 책 소개와 생각을 한눈에 보는 카드형 피드로 재편성한다.

### 섹션

1. Hero
2. 오늘 많이 이야기되는 책
3. 생각 피드 카드 그리드
4. 오늘의 문장
5. 질문 피드
6. 같은 책 읽는 사람들
7. 독서모임 모집 카드

### Feed Card 필수 구성

- 사용자 프로필
- 책 표지
- 책 제목/저자
- 짧은 생각
- 마음에 남은 문장
- 질문
- 감정 태그
- 공감
- 댓글
- 저장
- 소크라테스 토론
- 모임 연결

### API

```text
GET /api/v2/community/feed
GET /api/v2/community/questions
GET /api/v2/community/quotes
GET /api/v2/community/trending-books
```

---

## 6. DeepDive UI

### 목표

책 제목이나 주제를 입력하면 관련 책과 YouTube 영상을 함께 보여주는 “책 이해 딥다이브” 페이지를 만든다.

### 섹션

1. Hero
2. Search Panel
3. Related Books
4. YouTube Curation
5. Video Category Tabs
6. Thought Expansion Questions
7. Save / Discuss CTA

### Video Card

- 썸네일
- 제목
- 채널명
- 영상 길이 가능 시 표시
- 카테고리 태그
- 영상 보기
- 나중에 보기
- 이 영상으로 토론 질문 만들기

### 금지

- YouTube 크롤링 직접 구현 금지
- 영상 다운로드 기능 금지
- API key 노출 금지

### API

```text
GET /api/v2/deepdive/search?q=...
GET /api/v2/youtube/search?q=...
POST /api/v2/deepdive/save
```

---

## 7. Profile UI

### 목표

`/profile`을 단순 계정 페이지가 아니라 “나의 독서 우주”로 만든다.

### 섹션

1. 상단 Hero
2. 프로필 카드
3. 생각의 별자리
4. 현재 읽는 책
5. 내 문장 아카이브
6. 독서 타임라인
7. 내 질문들
8. 독서 성향 분석
9. 참여 중인 Lounge
10. 비슷한 독자 추천

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

## 8. Places 지도 UI

### 목표

독서모임 장소 찾기 페이지를 만든다. 최우선순위는 내 위치와 주변 카페/도서관 검색이다.

### 핵심 기능

1. Kakao Map SDK 로드
2. 내 위치 인식
3. 현재 위치 마커 표시
4. 카페/도서관/스터디카페/북카페/서점 검색
5. 검색 결과 마커 표시
6. 장소 리스트 표시
7. 리스트 클릭 시 지도 이동
8. 마커 클릭 시 상세 패널 표시
9. 장소 저장
10. Lounge 연결 준비

### 중요 설정

Kakao JavaScript SDK 도메인에는 반드시 아래를 등록해야 한다.

```text
http://localhost:5000
http://127.0.0.1:5000
```

### API

```text
POST /api/v2/places/save
GET /api/v2/places/saved
POST /api/v2/lounge/<lounge_id>/place
```

---

## 9. Socrates UI

### 목표

`/socrates`를 철학적 독서 토론광장으로 정리한다.

### 반드시 유지

- 구절 입력
- 책 제목 입력
- 빠른 시작 칩
- 5단계 질문
- 진행률
- 채팅
- 인사이트 카드
- 내 사전
- 실행 계획
- 세션 기록

### 추가 UI

- 대화 모드 선택
- 책 이해 카드
- 토론 질문 카드
- 찬반 주제 카드
- Lounge 공유 카드

---

## 10. 공통 이미지 처리

모든 책 카드/영상 카드에서 다음을 구현한다.

```js
function handleImageError(img, fallbackType) {
  // 이미지 깨질 때 fallback UI로 전환
}
```

규칙:

- 책 표지는 2:3
- YouTube 썸네일은 16:9
- alt 필수
- skeleton loading
- fallback title cover
- lazy loading 가능

---

## 11. 작업 순서

1. 현재 파일 구조 audit
2. 공통 navigation 확인
3. Lounge filter UI 구현
4. Community card feed 구현
5. DeepDive curation UI 구현
6. Profile 독서 우주 UI 구현
7. Places 지도 UI 구현
8. Socrates 토론광장 UI 보완
9. API 연결
10. fallback/empty/error/mobile 최종 확인

---

## 12. 작업 후 보고 형식

1. 수정 파일 목록
2. 변경한 페이지 구조
3. 추가한 CSS 클래스
4. 추가한 JS 함수
5. API 연결 목록
6. 이미지 fallback 처리
7. 모바일 대응
8. 남은 TODO
