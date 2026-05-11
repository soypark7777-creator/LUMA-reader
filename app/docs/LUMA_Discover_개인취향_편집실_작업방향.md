# LUMA Discover 개인 취향 기반 편집실 작업 방향

## 목적

`/lounge`는 단순 도서 검색 페이지가 아니라, 사용자의 독서 페르소나에 맞는 책을 선별해 보여주는 Discover 편집실이 되어야 한다.

핵심 목표는 다음과 같다.

- 검색 결과를 그대로 노출하지 않는다.
- 사용자의 독서 기록, 감정 기록, 메모, 선호 장르를 바탕으로 후보 책을 선별한다.
- 신간, 평판, 페르소나 적합도, 감정/장르/MBTI 적합도를 함께 반영한다.
- 영문판, 만화, 문제집, 학습서, 수험서, 오래된 무관한 판본을 최대한 걸러낸다.
- 책 카드에는 공통 문구 대신 실제 책의 줄거리/평/추천 이유를 보여준다.

## 현재 문제

현재 `/lounge`는 `/api/v2/books/search`와 `/api/v2/discover/today` 결과를 화면에 뿌리는 구조다.

문제점:

- 네이버/구글 검색 결과가 그대로 섞이면 원서, 만화, 학습서, 오래된 판본이 함께 나온다.
- “국내 도서 검색에서 발견한 생각의 씨앗입니다.” 같은 반복 문구가 많아 책의 개별성이 약하다.
- “오늘 당신 안에 심어질 새로운 문장”의 hero 책 선정 기준이 충분히 개인화되어 있지 않다.
- 카드에 출간일, 작가, 출판사, 장르 같은 탐색 정보가 부족하다.
- 표지 fallback의 책 제목 폰트가 감성적이지만 안정성과 가독성이 약하다.
- 감정/장르/MBTI 칩이 실제 취향 필터라기보다 검색어 변경에 가까워 보일 수 있다.

## 목표 화면 개념

`/lounge`는 다음 섹션으로 재구성한다.

```text
1. 오늘의 책 Hero
   - 내 페르소나에 맞는 신간 중 평판이 좋은 책 1권
   - 표지, 제목, 저자, 출판사, 출간일, 장르
   - 왜 지금 나에게 맞는지 1문장
   - 씨앗 심기 / 자세히 보기

2. 오늘의 독서 레이더
   - 감정 / 장르 / MBTI 기반 취향 탐색
   - 칩 선택 시 정제된 큐레이션 결과 노출

3. 내 독서 페르소나 추천
   - 내 서재, 메모, 감정 기록 기반

4. 신간 탐색
   - 최근 출간 도서 중심
   - 원서, 만화, 수험서, 학습서 필터링

5. 깊이 탐색 모달
   - 줄거리
   - 저자/출판사/출간일/장르
   - 추천 이유
   - 관련 질문
   - 서재 담기
```

## 핵심 백엔드 방향

검색 API 위에 “큐레이션 레이어”를 둔다.

권장 함수 구조:

```python
def build_reader_persona(user_id: str) -> dict:
    ...

def build_discover_queries(mode: str, value: str, persona: dict) -> list[str]:
    ...

def search_candidate_books(queries: list[str], limit: int) -> list[dict]:
    ...

def filter_discover_books(books: list[dict], policy: dict) -> list[dict]:
    ...

def score_discover_book(book: dict, persona: dict, context: dict) -> float:
    ...

def build_book_reason(book: dict, persona: dict, context: dict) -> str:
    ...
```

이 레이어는 `app/services/discover_service.py`에 추가하거나, 규모가 커지면 `app/services/discover_curation_service.py`로 분리한다.

## Reader Persona 설계

사용자 페르소나는 다음 데이터를 조합한다.

```text
서재:
- 읽은 책
- 읽는 중인 책
- 담아둔 책
- 장르 분포

감정 기록:
- 자주 기록한 감정
- 강도가 높은 감정
- 최근 감정

메모:
- 자주 등장하는 키워드
- 책 제목
- 문장 길이와 관심 주제

행동:
- 씨앗 심기한 책
- 최근 클릭/상세 보기한 책
```

페르소나 예시:

```json
{
  "top_genres": ["인문", "문학", "심리"],
  "top_emotions": ["curious", "inspired"],
  "keywords": ["자유", "불안", "성장", "관계"],
  "tone": "사색형",
  "preferred_depth": "deep",
  "avoid_categories": ["수험서", "문제집", "어린이"]
}
```

## 오늘의 책 Hero 선정 기준

Hero 책은 “가장 내게 맞는 신간 중 평이 좋고 페르소나에 잘 맞는 책”이어야 한다.

점수 설계:

```text
hero_score =
  신간성 점수
  + 평판 점수
  + 페르소나 적합도
  + 장르 적합도
  + 감정 적합도
  + 표지/메타데이터 완성도
  - 오래된 책 패널티
  - 원서/영문판 패널티
  - 만화/학습서/수험서 패널티
  - 제목/저자 불명확 패널티
```

권장 기준:

```text
신간성:
- 최근 24개월 이내 가산점
- 최근 6개월 이내 추가 가산점
- 5년 이상 오래된 책은 hero 후보에서 제외 또는 강한 패널티

평판:
- review_count가 있으면 가산점
- rating이 있으면 가산점
- 네이버에는 별점이 제한적일 수 있으므로 리뷰 수/검색 순위/메타 완성도도 활용

페르소나 적합도:
- 사용자 top_genres와 book.genre/category 매칭
- 사용자 memo keywords와 description/title 매칭
- 사용자 top_emotions와 책 소개 문장 매칭
```

## 필터링 규칙

Discover 품질은 필터가 결정한다.

### 제외 키워드

제목, 설명, 카테고리, 출판사, 저자 필드에 아래 키워드가 있으면 제외 또는 강한 패널티를 준다.

```text
영문판, 원서, 영어판, imported, paperback, hardcover, mass market
만화, 코믹스, comic, comics, manga, 웹툰
학습, 문제집, 수험서, 교재, 자격증, 기출, 모의고사, 해설집
초등, 중등, 고등, 어린이, 유아, 아동, 스티커북, 컬러링북
노트, 다이어리, 캘린더, 필사책, 쓰기책
```

### 예외

사용자가 명시적으로 해당 카테고리를 선택한 경우에는 필터를 완화한다.

예:

```text
mode=genre, value=만화
mode=learning, value=영어공부
```

기본 Discover에서는 위 카테고리를 제외한다.

## 감정/장르/MBTI 레이더 설계

칩은 단순 검색어가 아니라 “검색 전략”이어야 한다.

### 감정 예시

```json
{
  "emotion": "위로",
  "queries": ["위로 에세이", "마음 회복", "불안 치유", "따뜻한 한국 소설"],
  "preferred_genres": ["에세이", "문학", "심리"],
  "exclude": ["문제집", "만화", "원서", "어린이"]
}
```

### 장르 예시

```json
{
  "genre": "인문",
  "queries": ["인문 신간", "철학 에세이", "사회 인문 추천"],
  "preferred_genres": ["인문", "철학", "사회"],
  "exclude": ["수험서", "학습서", "원서"]
}
```

### MBTI 예시

```json
{
  "mbti": "INFJ",
  "queries": ["자기이해", "관계 심리", "철학 에세이", "내면 성장"],
  "preferred_genres": ["심리", "문학", "인문"],
  "exclude": ["문제집", "원서", "만화"]
}
```

## 책 카드 정보 구조

책 카드는 다음 정보를 보여준다.

```text
표지
제목
저자
출판사
출간일
장르/카테고리
평판 정보 또는 신뢰도
책 소개 한 문장
씨앗 심기 버튼
```

공통 문구는 지양한다.

지양:

```text
국내 도서 검색에서 발견한 생각의 씨앗입니다.
당신의 독서 페르소나를 넓혀줄 추천입니다.
```

대신 다음 우선순위로 문장을 만든다.

```text
1. description에서 첫 핵심 문장 추출
2. description이 길면 60~90자로 요약
3. description이 없으면 제목/장르/페르소나 기반 reason 생성
4. Gemini 사용 가능 시 짧은 추천평 생성
5. 실패 시 mock reason 생성
```

예시:

```text
자기 발견과 성장의 불안을 섬세하게 따라가는 소설입니다.
관계의 회복을 따뜻한 일상 언어로 풀어낸 이야기입니다.
불안과 선택의 문제를 지금의 삶과 연결해 생각하게 합니다.
```

## 표지 fallback 디자인

책 이미지가 없을 때 카드 안 제목 폰트는 더 안정적이고 깔끔해야 한다.

권장 CSS:

```css
.book-cover-fallback-initial,
.book-cover-fallback-label {
  font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.25;
}
```

fallback에는 긴 제목 전체를 넣기보다 다음 중 하나를 사용한다.

```text
제목 첫 글자
짧은 제목 2줄
장르 아이콘
```

## API 개선 아이디어

현재:

```text
GET /api/v2/books/search?q=&source=&limit=&sort=
GET /api/v2/discover/today?user_id=
```

추가 또는 확장 제안:

```text
GET /api/v2/discover/curated
```

Query:

```text
user_id=user_demo
mode=emotion|genre|mbti|new|persona
value=위로|인문|INFJ
limit=18
sort=match|recent|rating|reviews
include=default
```

Response:

```json
{
  "ok": true,
  "mode": "emotion",
  "value": "위로",
  "persona": {
    "top_genres": ["인문", "문학"],
    "keywords": ["자유", "불안", "성장"]
  },
  "books": [
    {
      "title": "책 제목",
      "author": "저자",
      "publisher": "출판사",
      "published_date": "20260410",
      "genre": "에세이",
      "cover_url": "...",
      "rating": 4.7,
      "review_count": 120,
      "match_score": 86,
      "reason": "불안과 회복의 감각을 따뜻하게 다루는 책입니다.",
      "source": "naver"
    }
  ]
}
```

## 프론트엔드 개선 아이디어

### Hero

Hero 카드는 다음을 표시한다.

```text
책 제목
저자
출판사
출간일
장르
추천 이유
씨앗 심기
자세히 보기
```

### 카드 메타

기존 카드의 별점/리뷰 UI는 유지하되, 정확한 데이터가 없을 경우 “정확도 별점”처럼 보이지 않게 한다.

권장:

```text
평판 4.5
리뷰 128
출간 2026.03.18
네이버 도서
```

rating이 실제 별점이 아니라 내부 기본값이면 `추천 적합도` 또는 `LUMA 점수`로 표기한다.

### 소개 문구

카드 아래 소개는 `reason` 또는 `summary_sentence`를 사용한다.

```text
줄거리 기반 한 문장
평판 기반 한 문장
페르소나 기반 추천 이유
```

## 구현 우선순위

1. 백엔드 큐레이션 필터 추가
2. Hero 책 선정 로직 개선
3. 책별 소개 문장 생성 로직 개선
4. `/api/v2/discover/curated` 추가 또는 `/api/v2/books/search` 확장
5. `/lounge` 카드 메타 정보 UI 개선
6. 표지 fallback 폰트 개선
7. 감정/장르/MBTI 레이더를 검색 전략 기반으로 전환

## 개발 체크리스트

- [ ] 네이버 검색 결과에서 원서/만화/문제집/학습서 제외
- [ ] 신간 hero는 최근 출간 도서 중심으로 선정
- [ ] 사용자 페르소나 기반 점수 계산
- [ ] 책 카드에 저자/출판사/출간일/장르 표시
- [ ] 공통 reason 문구 제거
- [ ] description 기반 한 문장 소개 생성
- [ ] fallback 표지 폰트 안정화
- [ ] 감정/장르/MBTI 칩별 검색 전략 정의
- [ ] Gemini 실패 시 mock reason 유지
- [ ] `/lounge`가 빈 화면이 되지 않도록 fallback 유지

## 테스트 아이디어

### API 테스트

```text
GET /api/v2/books/search?q=데미안&source=naver&limit=10
GET /api/v2/discover/today?user_id=user_demo
GET /api/v2/discover/curated?user_id=user_demo&mode=emotion&value=위로
GET /api/v2/discover/curated?user_id=user_demo&mode=mbti&value=INFJ
```

확인할 것:

- `source=naver` 책이 실제로 반환되는가
- 표지 URL이 있는가
- 원서/문제집/만화가 기본 결과에서 제외되는가
- `reason`이 공통 문구가 아니라 책별 문장인가
- `published_date`, `publisher`, `author`가 표시 가능한가

### 화면 테스트

```text
http://localhost:5000/lounge
```

확인할 것:

- Hero 책이 개인화된 신간처럼 보이는가
- 카드 제목/표지 fallback이 안정적으로 보이는가
- 카드 아래 메타 정보가 충분한가
- 감정/장르/MBTI 선택 시 결과 품질이 좋아지는가
- 오래된 원서/학습서/만화가 과도하게 섞이지 않는가

## 주의사항

- 외부 API 실패 시 fallback은 유지한다.
- 필터가 너무 강해서 결과가 0개가 되면 안 된다.
- 처음에는 soft penalty 방식으로 시작하고, 확실한 제외 키워드만 hard exclude한다.
- 네이버 API 결과는 `description`이 길 수 있으므로 프론트에서 반드시 줄임 처리한다.
- rating/review_count가 실제 데이터인지 내부 추정값인지 UI에서 혼동되지 않게 한다.
