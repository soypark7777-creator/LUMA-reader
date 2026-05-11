# LUMA 독서 지도 재구성 작업지시서
## 백엔드 Codex + 프런트엔드 Claude Code 전용 프롬프트

> 대상 화면: `http://localhost:5000/community/#map`  
> 목표: 오프라인 독서모임 장소를 정확히 검색, 비교, 저장, 수정, 삭제, 후기 작성할 수 있는 실사용 지도 페이지로 재구성한다.  
> 역할 분담: 백엔드는 Codex, 프런트엔드는 Claude Code가 담당한다.

---

## 공통 제품 방향

현재 `community/#map`은 독서모임 장소 탐색 도구라기보다 지도 위에 장소 핀을 올린 화면에 가깝다. 앞으로 이 화면은 “오프라인 독서모임 장소 찾기” 전용 공간이 되어야 한다.

사용자는 다음 일을 할 수 있어야 한다.

- 현재 위치 주변의 독서모임 장소를 찾는다.
- “성수 조용한 카페”, “강남역 6명 모임”, “서울 도서관 모임룸”처럼 검색한다.
- Google 지도 위에서 정확한 위치를 확인한다.
- 장소 사진, 주소, 영업시간, 평점, 웹사이트, 전화번호를 확인한다.
- LUMA에 독서모임 장소로 저장한다.
- 저장한 장소의 독서모임 적합 정보를 직접 수정한다.
- 저장한 장소를 삭제한다.
- 후기를 남기고, 다른 모임원이 판단할 수 있도록 돕는다.

중요한 원칙:

- 정확한 위치와 지도 표시는 Gemini가 아니라 Google Maps/Places API가 담당한다.
- Gemini는 장소 설명 요약, 독서모임 적합도 문장, 후기 요약 같은 보조 AI 기능에만 사용한다.
- Google API 실패 시 기존 Mock 장소 데이터로 fallback한다.
- 기존 공독의 장 라운지 기능은 깨뜨리지 않는다.

---

# PROMPT A · 백엔드 Codex 작업지시서

```text
# LUMA 백엔드 — 독서모임 장소 지도 API 재구성
# 담당: Codex
# 주요 파일:
# - app/schema.py
# - app/services/place_service.py
# - app/routes/places.py
# - app/routes/community.py
# - tests/test_all.py 또는 신규 tests/test_places_map.py

## 목표
`/community/#map` 프런트엔드가 실제 Google Places 기반 장소 검색, 상세 조회, 저장, 수정, 삭제, 후기 작성 기능을 사용할 수 있도록 백엔드 API와 DB 구조를 완성한다.

## 현재 상태
- `app/services/place_service.py`에 `_spots` Mock 장소 데이터가 있다.
- `app/routes/places.py`는 `/api/places/all`, `/nearby`, `/<place_id>`, `/<place_id>/checkin`, `/<place_id>/review`, `/cities`, `/status`를 제공한다.
- `community.html`은 `spots_json`을 받아 지도에 핀을 표시한다.
- `.env`에 `GOOGLE_MAPS_API_KEY`가 있다.
- Google Maps JavaScript는 프런트에서 쓰고 있으나, Places 검색/상세/사진/저장 관리는 백엔드 구조가 부족하다.

## 작업 1. DB 스키마 추가
`app/schema.py`에 다음 테이블을 추가한다.

### reading_places
- id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY
- place_id VARCHAR(36) NOT NULL UNIQUE
- google_place_id VARCHAR(255)
- name VARCHAR(255) NOT NULL
- address VARCHAR(500)
- lat DECIMAL(10,7) NOT NULL
- lng DECIMAL(10,7) NOT NULL
- phone VARCHAR(100)
- website TEXT
- google_rating DECIMAL(3,2)
- price_level TINYINT
- open_now TINYINT(1)
- opening_hours TEXT
- photo_reference TEXT
- photo_url TEXT
- place_types VARCHAR(500)
- source ENUM('google','manual','mock') DEFAULT 'google'
- reading_score DECIMAL(3,1) DEFAULT 0
- meeting_capacity TINYINT
- noise_level ENUM('quiet','moderate','lively','unknown') DEFAULT 'unknown'
- outlet_score TINYINT
- wifi_score TINYINT
- reservation_url TEXT
- memo TEXT
- created_by VARCHAR(36) DEFAULT 'user_demo'
- created_at DATETIME DEFAULT CURRENT_TIMESTAMP
- updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
- INDEX idx_google_place_id (google_place_id)
- INDEX idx_location (lat, lng)
- INDEX idx_created_by (created_by)

### reading_place_reviews
- id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY
- review_id VARCHAR(36) NOT NULL UNIQUE
- place_id VARCHAR(36) NOT NULL
- user_id VARCHAR(36) NOT NULL
- display_name VARCHAR(100)
- emoji VARCHAR(10) DEFAULT '⭐'
- rating TINYINT
- noise_level ENUM('quiet','moderate','lively','unknown') DEFAULT 'unknown'
- group_size TINYINT
- visit_purpose VARCHAR(100)
- content TEXT NOT NULL
- created_at DATETIME DEFAULT CURRENT_TIMESTAMP
- INDEX idx_place_id (place_id)
- INDEX idx_user_id (user_id)

필수:
- `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`
- SQL 값은 항상 `%s` 파라미터 바인딩
- JSON 문자열은 `json.dumps(..., ensure_ascii=False)`
- Mock 모드 fallback 유지

## 작업 2. Google Places 연동 서비스 작성
`app/services/place_service.py`에 다음 함수를 추가 또는 개선한다.

### search_google_places(query, lat=None, lng=None, radius=3000, limit=12)
- `.env`의 `GOOGLE_MAPS_API_KEY` 사용
- Google Places Text Search API 또는 Places API 신버전 중 프로젝트 의존성에 맞는 방식을 사용
- 검색어, 현재 위치, 반경을 받아 장소 리스트 반환
- 반환 필드:
  - google_place_id
  - name
  - address
  - lat
  - lng
  - google_rating
  - price_level
  - open_now
  - place_types
  - photo_reference
  - distance_km
  - saved
  - reading_score
- API 실패 시 `_spots` Mock 검색 결과 반환
- requests 호출 시 `timeout=5`

### get_google_place_detail(google_place_id)
- Google Place Details API 호출
- 반환 필드:
  - google_place_id
  - name
  - address
  - lat
  - lng
  - phone
  - website
  - google_rating
  - user_ratings_total
  - price_level
  - open_now
  - opening_hours
  - photos
  - place_types
  - google_maps_url
- 실패 시 Mock 상세 반환

### get_google_photo_url(photo_reference, max_width=640)
- 프런트에서 바로 쓸 수 있는 이미지 URL 생성
- 키 노출이 부담되면 `/api/places/photo` 프록시를 사용해도 된다.

### save_reading_place(user_id, data)
- Google 장소 또는 수동 장소를 LUMA 장소로 저장
- 중복 기준: google_place_id 또는 place_id
- 저장 후 `{ok: True, place: ...}` 반환

### update_reading_place(place_id, user_id, data)
- LUMA 독서모임 메타데이터 수정
- 수정 가능 필드:
  - reading_score
  - meeting_capacity
  - noise_level
  - outlet_score
  - wifi_score
  - reservation_url
  - memo
  - photo_url
- 없는 장소면 `{ok: False, error: "장소를 찾을 수 없습니다."}`

### delete_reading_place(place_id, user_id)
- 저장 장소 삭제
- 관련 후기 삭제 또는 유지 정책을 정하고 문서화

### list_saved_reading_places(user_id, limit=50)
- 사용자가 저장한 장소 목록 반환

### add_place_review(place_id, user_id, data)
- 후기 저장
- rating, noise_level, group_size, visit_purpose, content 저장

### list_place_reviews(place_id, limit=20)
- 후기 목록 반환

### summarize_place_for_reading(place, reviews)
- Gemini 사용 가능 시 장소 설명/후기 기반 독서모임 적합 요약 생성
- Gemini 실패 시 규칙 기반 문장 반환
- 예외를 던지지 않는다.

## 작업 3. API 라우트 설계
`app/routes/places.py`에 다음 API를 추가한다.

### GET /api/places/search
query:
- q
- lat
- lng
- radius
- limit

반환:
{
  "ok": true,
  "places": [...],
  "center": {"lat": ..., "lng": ...},
  "source": "google|mock"
}

### GET /api/places/google/<google_place_id>
Google Place 상세 조회.

### GET /api/places/saved
query: user_id, limit

### POST /api/places/save
body:
{
  "user_id": "user_demo",
  "google_place_id": "...",
  "name": "...",
  "address": "...",
  "lat": 37.0,
  "lng": 127.0,
  "reading_score": 8.5,
  ...
}

### PUT /api/places/<place_id>
저장 장소 수정.

### DELETE /api/places/<place_id>
저장 장소 삭제.

### GET /api/places/<place_id>/reviews
후기 조회.

### POST /api/places/<place_id>/review
후기 작성. 기존 API와 호환되게 유지.

### GET /api/places/photo
query: photo_reference, max_width
Google photo URL 반환 또는 redirect/proxy.

## 작업 4. community 라우트 보강
`app/routes/community.py`에서 `maps_api_key`를 템플릿으로 전달하되, Places 검색은 백엔드 API를 사용하도록 한다.

## 작업 5. 테스트
다음 테스트를 추가 또는 보강한다.
- `/api/places/search?q=서울 카페`가 200을 반환한다.
- Google API 키가 없거나 실패해도 mock 결과가 반환된다.
- 저장 장소 생성/조회/수정/삭제가 된다.
- 후기 작성/조회가 된다.
- 기존 `pytest -q` 전체 테스트가 통과한다.

## 주의
- Gemini는 지도 좌표 정확도에 사용하지 않는다.
- Google Places API 응답은 언제든 필드가 없을 수 있으므로 `.get()` 기반으로 안전하게 파싱한다.
- 프런트가 쓰기 쉬운 단일 응답 스키마를 유지한다.
- 기존 `/api/places/all`, `/nearby`, `/<place_id>` API는 호환 유지한다.
```

---

# PROMPT B · 프런트엔드 Claude Code 작업지시서

```text
# LUMA 프런트엔드 — community/#map 독서모임 장소 지도 재디자인
# 담당: Claude Code
# 주요 파일:
# - app/templates/community.html
# 권장 분리:
# - app/static/js/community-map.js
# - app/static/css/community-map.css

## 목표
`http://localhost:5000/community/#map`을 오프라인 독서모임 장소를 정확히 검색하고 비교하는 지도 화면으로 재구성한다.

## 현재 문제
- 지도 핀이 정확한 실제 지도 UX로 느껴지지 않는다.
- 지도 위 팝업과 핀 라벨이 겹쳐 가독성이 떨어진다.
- 왼쪽 패널의 도시 필터/유형 필터는 탐색에 큰 도움이 안 된다.
- 오른쪽 상세 패널은 Google 장소 사진, 주소, 영업시간, 저장/수정/삭제 흐름이 부족하다.
- 독서모임에 적합한지 판단할 정보가 부족하다.

## 작업 1. 지도 탭 레이아웃 재구성
`community.html`의 지도 탭을 3단 레이아웃으로 재구성한다.

### 왼쪽 패널
목적: 장소 검색과 결과 비교.

구성:
- 검색창
  - placeholder: "지역, 장소, 조건 검색..."
  - 예: "성수 조용한 카페", "강남역 6명 모임", "서울 도서관 모임룸"
- 현재 위치 버튼
- 빠른 조건 칩
  - 내 주변
  - 조용한 곳
  - 4명 이상
  - 예약 가능
  - 저녁 영업
  - 콘센트
  - 도서관
  - 서점/북카페
- 검색 결과 리스트
  - 장소명
  - 거리
  - Google 평점
  - LUMA 독서모임 점수
  - 영업 상태
  - 저장 여부

삭제:
- 기존 도시 필터
- 기존 유형 필터

### 중앙 지도
목적: 정확한 위치 확인.

구성:
- Google Map 실제 지도
- 내 위치 마커
- 장소 마커
- 선택 장소 마커 강조
- 지도 이동 후 "이 지역에서 다시 검색" 버튼
- Google Maps 로딩 실패 시 fallback 안내

주의:
- 지도 위에 큰 정보 팝업을 띄우지 않는다.
- 마커 클릭 시 오른쪽 상세 패널을 업데이트한다.
- 마커 라벨은 짧게 유지하거나 선택된 마커에만 표시한다.

### 오른쪽 상세 패널
목적: 장소 판단과 LUMA 저장/후기 작성.

구성:
- 장소 사진
- 장소명
- 주소
- 거리
- Google 평점
- 영업 상태와 영업시간
- 전화번호
- 웹사이트
- Google 길찾기 버튼
- LUMA 독서모임 적합 정보
  - 조용함
  - 좌석 여유
  - 콘센트
  - 와이파이
  - 추천 인원
  - 예약 링크
  - 운영 메모
- 버튼
  - 저장
  - 수정
  - 삭제
- 후기 영역
  - 후기 리스트
  - 후기 작성 폼
  - 별점
  - 모임 인원
  - 방문 목적
  - 소음 수준

## 작업 2. API 연동
백엔드 Codex가 제공하는 다음 API를 사용한다.

- `GET /api/places/search?q=...&lat=...&lng=...&radius=...`
- `GET /api/places/google/<google_place_id>`
- `GET /api/places/saved?user_id=user_demo`
- `POST /api/places/save`
- `PUT /api/places/<place_id>`
- `DELETE /api/places/<place_id>`
- `GET /api/places/<place_id>/reviews`
- `POST /api/places/<place_id>/review`

프런트 상태:
- `map`
- `markers`
- `currentLocation`
- `searchResults`
- `selectedPlace`
- `savedPlaces`
- `activeFilters`
- `isLoading`
- `mapError`

## 작업 3. 검색 UX
동작:
1. 사용자가 검색어 입력 후 Enter
2. `/api/places/search` 호출
3. 지도 중심 이동
4. 검색 결과 리스트 갱신
5. 마커 갱신
6. 첫 번째 결과 또는 사용자가 클릭한 결과를 오른쪽 패널에 표시

현재 위치:
- 브라우저 Geolocation 사용
- 성공 시 좌표와 정확도 표시
- 실패 시 권한 안내와 서울 기본값 fallback

지도 이동:
- 사용자가 지도를 드래그하면 "이 지역에서 다시 검색" 버튼 표시
- 버튼 클릭 시 현재 지도 중심 기준으로 검색

## 작업 4. 저장/수정/삭제 UX
저장:
- Google 검색 결과를 LUMA 장소로 저장
- 저장 후 버튼 상태를 "저장됨"으로 변경
- 저장 장소 목록에 반영

수정:
- 오른쪽 패널에서 "수정" 클릭
- 작은 편집 폼 또는 모달 표시
- 수정 필드:
  - 독서모임 점수
  - 추천 인원
  - 소음 수준
  - 콘센트 점수
  - 와이파이 점수
  - 예약 링크
  - 운영 메모
- 저장 후 상세 패널 갱신

삭제:
- 확인창 후 삭제
- 마커/목록/상세 상태 갱신

## 작업 5. 후기 UX
후기 작성 폼:
- 별점
- 모임 인원
- 방문 목적
- 소음 수준
- 후기 내용

후기 리스트:
- 작성자
- 별점
- 방문 목적
- 모임 인원
- 작성일
- 내용

비어 있을 때:
- "아직 후기가 없습니다. 첫 독서모임 경험을 남겨주세요."

## 작업 6. 디자인 방향
톤:
- 공독의 장과 어울리는 차분하고 집중감 있는 UI
- 지도는 실용성을 우선한다.
- 장식보다 검색, 비교, 판단이 쉬워야 한다.

피해야 할 것:
- 지도 위에 큰 흰 팝업을 띄우는 구조
- 핀 라벨이 겹쳐서 장소명이 읽히지 않는 구조
- 카드 안에 카드가 반복되는 과한 장식
- 도시/유형 필터처럼 단순하지만 실제 탐색에 도움 적은 UI

권장:
- 왼쪽 결과 리스트는 조밀하지만 읽기 쉽게
- 오른쪽 상세는 사진과 핵심 정보를 먼저
- 저장/수정/삭제 버튼은 명확하게
- 모바일은 목록/지도/상세 탭 전환

## 완료 기준
- `/community/#map` 진입 시 실제 Google Map이 보인다.
- 현재 위치 버튼이 동작하고 지도 중심이 이동한다.
- 검색 결과가 지도와 왼쪽 리스트에 동시에 반영된다.
- 장소 클릭 시 오른쪽 상세 패널이 갱신된다.
- Google 사진, 주소, 영업시간, 평점이 표시된다.
- 저장/수정/삭제가 가능하다.
- 후기를 작성하고 목록에서 확인할 수 있다.
- Google Maps 실패 시 사용자에게 명확한 fallback 메시지가 보인다.
```

---

# PROMPT C · 백엔드-프런트 API 계약 확인용

```text
# LUMA 독서 지도 API 계약 점검
# 담당: Codex + Claude Code 공동 확인

## 목적
백엔드와 프런트가 같은 응답 스키마를 보고 작업하도록 API 계약을 확정한다.

## Place List Item
{
  "place_id": "rp_xxx 또는 mock/google id",
  "google_place_id": "ChIJ...",
  "name": "장소명",
  "address": "주소",
  "lat": 37.123,
  "lng": 127.123,
  "distance_km": 1.2,
  "google_rating": 4.5,
  "price_level": 2,
  "open_now": true,
  "photo_url": "https://...",
  "place_types": ["cafe", "book_store"],
  "saved": false,
  "reading_score": 8.7,
  "summary": "조용한 4인 독서모임에 적합한 장소입니다."
}

## Place Detail
{
  "place_id": "rp_xxx",
  "google_place_id": "ChIJ...",
  "name": "장소명",
  "address": "주소",
  "lat": 37.123,
  "lng": 127.123,
  "phone": "02-...",
  "website": "https://...",
  "google_maps_url": "https://maps.google.com/...",
  "google_rating": 4.5,
  "user_ratings_total": 120,
  "price_level": 2,
  "open_now": true,
  "opening_hours": ["월 10:00-22:00", "..."],
  "photos": ["https://..."],
  "place_types": ["cafe", "book_store"],
  "saved": true,
  "reading_score": 8.7,
  "meeting_capacity": 6,
  "noise_level": "quiet",
  "outlet_score": 4,
  "wifi_score": 4,
  "reservation_url": "https://...",
  "memo": "평일 저녁 4-6명 모임 추천",
  "reviews": []
}

## Review Item
{
  "review_id": "rv_xxx",
  "place_id": "rp_xxx",
  "user_id": "user_demo",
  "display_name": "소연",
  "emoji": "🦋",
  "rating": 5,
  "noise_level": "quiet",
  "group_size": 4,
  "visit_purpose": "문학 모임",
  "content": "조용하고 테이블 간격이 넓어서 좋았습니다.",
  "created_at": "2026-05-09 12:00:00"
}

## 공통 응답 규칙
- 성공: `{ "ok": true, ... }`
- 실패: `{ "ok": false, "error": "..." }`
- Google 실패 시에도 가능한 한 `ok: true, source: "mock"`으로 fallback
- 인증이 없어도 개발 모드에서는 `user_demo` 사용
```

---

# PROMPT D · QA 점검 체크리스트

```text
# LUMA 독서 지도 QA 체크리스트

## 기본 렌더링
- `/community/#map` 접속 시 지도 탭이 바로 열린다.
- Google 지도가 실제 지도로 보인다.
- Google Maps 로딩 실패 시 fallback 메시지가 보인다.

## 위치
- 내 위치 권한 허용 시 현재 위치 마커가 표시된다.
- 정확도, 좌표, 검색 반경이 상태 메시지에 표시된다.
- 위치 권한 거부 시 서울 기본값 fallback이 동작한다.

## 검색
- "성수 카페" 검색 시 지도와 목록이 갱신된다.
- "도서관 모임룸" 검색 시 관련 장소가 나온다.
- 검색 결과가 없을 때 빈 상태가 명확하다.

## 상세
- 장소 클릭 시 오른쪽 패널이 갱신된다.
- 사진, 주소, 평점, 영업시간, 웹사이트, 길찾기가 표시된다.
- 선택 마커가 강조된다.

## 저장/수정/삭제
- 장소 저장이 된다.
- 저장 장소가 saved 상태로 표시된다.
- 독서모임 메타데이터 수정이 된다.
- 삭제 후 목록과 지도에서 상태가 갱신된다.

## 후기
- 후기를 작성할 수 있다.
- 작성 후 목록에 바로 표시된다.
- 새로고침 후에도 후기가 유지된다.

## 회귀
- 공독의 장 라운지 탭이 기존처럼 동작한다.
- 기존 테스트 `venv\Scripts\python.exe -m pytest -q`가 통과한다.
```

