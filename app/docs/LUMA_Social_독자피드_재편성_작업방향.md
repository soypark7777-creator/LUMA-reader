# LUMA Social 독자 피드 재편성 작업 방향

## 목표

`/social`은 단순 게시판이 아니라, 다양한 독서 파드와 독자들이 공개한 “자신의 책 이야기”를 이미지와 함께 소개하고, 서로 인사이트를 주고받는 공간이 되어야 한다.

핵심 방향:

- 사람 중심의 독서 피드
- 책 이야기 중심의 카드
- 이미지/책 표지/인용문이 함께 보이는 공유 경험
- 좋아요보다 “인사이트 주고받기”가 중심인 상호작용
- 독서 파드가 살아 있는 커뮤니티 구조

## 현재 확인된 문제

### 프론트엔드

- 로고 옆 노란 점 장식이 생겨 디자인을 훼손했다.
- 프론트는 `content`, `style`, `id`, `like_count`를 기대한다.
- 백엔드는 `passage`, `card_style`, `card_id`, `likes` 중심으로 응답한다.
- 이 필드 불일치 때문에 업로드/렌더링/댓글이 흔들릴 수 있다.
- 현재 카드는 인용문만 보여주고, 책 이미지나 사람의 이야기 맥락이 약하다.

### 백엔드

- `/api/social/cards`가 `passage`만 요구해서, 프론트의 `content` payload와 맞지 않았다.
- 댓글도 `text`만 요구해서, 프론트의 `content` payload와 맞지 않았다.
- 피드 서비스는 인메모리 기반이며 DB `feed_cards` 테이블과 완전히 통합되어 있지는 않다.
- 카드 응답에 프론트용 alias 필드가 부족했다.

## 이번에 정리된 호환성 방향

프론트와 백엔드가 모두 다음 필드를 안정적으로 사용할 수 있어야 한다.

```json
{
  "id": "fc_xxxxxx",
  "card_id": "fc_xxxxxx",
  "author_name": "독자 이름",
  "author_emoji": "🌙",
  "book_title": "책 제목",
  "content": "공개한 문장 또는 이야기",
  "passage": "공개한 문장 또는 이야기",
  "thought": "내 생각",
  "style": "cosmic",
  "card_style": "cosmic",
  "like_count": 12,
  "comment_count": 3,
  "created_at": "..."
}
```

## 재편성 화면 구조 제안

### 1. 상단 Hero: 오늘의 독서 광장

역할:

- 오늘 가장 활발한 책 이야기 1~2개 소개
- “지금 사람들이 어떤 문장 앞에서 멈췄는지” 보여주기

구성:

```text
오늘 많이 나뉜 책
대표 공개 문장
독자 한 줄 인사이트
참여 중인 파드
```

### 2. 독서 파드 영역

현재 왼쪽 사이드바의 “독서 모임”을 더 풍부하게 만든다.

파드 카드 정보:

```text
파드 이름
현재 함께 읽는 책
멤버 수
최근 올라온 인사이트 수
대표 감정 태그
입장하기 버튼
```

예:

```text
파친코 독서 파드
현재 책: 파친코
12명 참여
오늘 4개의 문장 공유
태그: 역사, 가족, 생존
```

### 3. 공개 책 이야기 피드

각 카드는 단순 인용문보다 “책 이야기 카드”가 되어야 한다.

카드 구성:

```text
작성자
책 표지 또는 이미지
책 제목 / 저자
공개한 구절
내 생각 / 인사이트
감정 태그
댓글 대신 인사이트 주고받기
```

가능한 카드 UI:

```text
[독자 아바타] 소연 · 사피엔스
[책 표지]
"인류가 지구를 지배할 수 있었던 이유는..."
화폐와 국가도 결국 함께 믿는 이야기라는 점이 무섭고 신비로웠다.

태그: 인류학, 허구, 협력
[공감] [내 생각 보태기] [파드로 가져가기]
```

### 4. 이미지 기반 공유

지원하고 싶은 이미지 유형:

- 책 표지 이미지
- 사용자가 업로드한 독서 사진
- OCR로 추출한 책 페이지 이미지
- 자동 생성된 quote card 이미지

백엔드 필드 제안:

```json
{
  "image_url": "",
  "cover_url": "",
  "image_type": "cover|photo|quote_card|ocr",
  "image_alt": "책 표지"
}
```

초기에는 `cover_url`만 붙여도 체감이 크다.

### 5. 인사이트 주고받기

댓글을 단순 댓글이 아니라 인사이트 타입으로 확장한다.

댓글 타입:

```text
공감
질문
다른 해석
연결된 책 추천
내 경험
```

API 구조 예:

```json
{
  "content": "저는 이 문장을 관계의 책임으로 읽었어요.",
  "type": "different_view",
  "book_title": "어린왕자"
}
```

프론트 표시:

```text
[다른 해석] 저는 이 문장을 관계의 책임으로 읽었어요.
```

### 6. 파드 연결

같은 책이 일정 횟수 이상 공유되면 자동으로 파드를 제안한다.

현재 백엔드에는 `check_and_create_bookclub(book_title)`가 있으므로 이를 확장한다.

확장 방향:

```text
같은 책 공유 2명 이상 → 미니 파드 제안
같은 책 공유 5명 이상 → 공식 파드 노출
같은 태그 공유 증가 → 주제 파드 제안
```

## 백엔드 확장 아이디어

### 1. 카드 정규화 레이어

서비스에서 `_normalize_card()`를 유지하고 확장한다.

필수 보장 필드:

```text
id
card_id
author_name
author_emoji
book_title
author
cover_url
image_url
content
passage
thought
tags
style
like_count
comment_count
created_at
```

### 2. DB 저장 전환

현재 `feed_cards`, `feed_comments`, `feed_likes` 테이블이 schema에 있으므로 장기적으로는 인메모리 대신 MySQL 기반으로 전환한다.

우선순위:

```text
1. create_card DB insert
2. get_feed DB select
3. add_comment DB insert
4. toggle_like DB upsert/delete
5. mock fallback 유지
```

### 3. 책 표지 보강

카드 생성 시 `book_title`이 있고 `cover_url`이 없으면 네이버 도서 검색으로 표지를 보강한다.

```python
if book_title and not cover_url:
    found = search_books_naver(book_title, 1)
    cover_url = found[0]["cover_url"] if found else ""
```

### 4. 인사이트 댓글 타입 추가

`feed_comments`에 당장 컬럼을 추가하지 않더라도 응답 필드에는 추가할 수 있다.

```json
{
  "type": "question",
  "label": "질문",
  "content": "왜 이 문장이 마음에 남았나요?"
}
```

## 프론트엔드 개선 아이디어

### 로고

- 불필요한 장식 점 제거
- 다른 페이지와 동일한 LUMA 로고 패턴 유지

### 피드 카드

현재:

```text
작성자
책 배지
인용문
좋아요/댓글
```

개선:

```text
작성자
책 표지 + 책 제목/저자
공개 구절
내 생각
태그
공감/인사이트/댓글
```

### 작성 폼

필드를 분리한다.

```text
책 제목
공유할 구절
내 생각
감정 태그
카드 스타일
이미지/표지 자동 연결
```

초기에는 textarea 하나를 유지하더라도 placeholder를 더 명확히 한다.

```text
책에서 마음에 남은 구절을 적어주세요.
아래에 내 생각을 덧붙이면 더 좋은 카드가 됩니다.
```

### 필터 칩

현재 필터:

```text
전체, 철학, 문학...
```

개선:

```text
전체
내가 읽은 책
질문이 많은 글
인사이트가 많은 글
같은 책 독자
파드 모집 중
```

## 추천 API 방향

현재 유지:

```text
GET  /api/social/feed
POST /api/social/cards
POST /api/social/cards/<card_id>/like
GET  /api/social/cards/<card_id>/comments
POST /api/social/cards/<card_id>/comments
GET  /api/social/clubs
GET  /api/social/match
GET  /api/social/challenge
GET  /api/social/badges
```

추가 후보:

```text
GET  /api/social/pods
GET  /api/social/pods/<pod_id>
POST /api/social/cards/<card_id>/insights
GET  /api/social/trending-books
POST /api/social/cards/<card_id>/share-to-pod
```

## 구현 우선순위

1. 로고 옆 노란 점 제거
2. 프론트/백엔드 카드 필드명 호환 정리
3. 카드 업로드 정상화
4. 댓글 payload 호환 정리
5. 파드 fallback 데이터 제공
6. 카드에 책 표지/저자/생각 영역 추가
7. 네이버 검색으로 `cover_url` 자동 보강
8. 인사이트 댓글 타입 추가
9. DB 기반 피드 저장으로 전환
10. 페이지 전체를 “독자 피드”에서 “독서 파드와 인사이트 광장”으로 재편성

## 테스트 체크리스트

```text
http://localhost:5000/social
```

확인할 것:

- 로고 옆 노란 점이 사라졌는가
- 피드 카드가 실제 API 응답으로 렌더링되는가
- 새 글 작성이 201로 성공하는가
- 작성한 카드가 즉시 피드 상단에 보이는가
- 좋아요 수가 증가/감소하는가
- 댓글 작성 후 댓글 목록에 보이는가
- 독서 파드 목록이 비어 보이지 않는가
- 오른쪽 추천 독자 영역이 API 응답과 맞는가

## 장기 컨셉 문장

`/social`은 “사람들이 책을 읽었다”를 보여주는 곳이 아니라, 사람들이 책을 통해 어떤 생각을 얻었고 그 생각이 다른 사람 안에서 어떻게 이어지는지 보여주는 공간이어야 한다.

피드의 핵심 단위는 게시물이 아니라 “공개된 독서 인사이트”다.
