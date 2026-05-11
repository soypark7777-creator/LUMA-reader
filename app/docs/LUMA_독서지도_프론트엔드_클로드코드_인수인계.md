# LUMA 독서지도 프런트엔드 인수인계

**대상 화면:** `app/templates/community.html` → `/community/#map` 섹션  
**백엔드 담당:** Codex (완료)  
**프런트 담당:** Claude Code (인수)

---

## 개요

Codex가 독서모임 장소 탐색·관리용 백엔드 API를 구현 완료했다. Claude Code는 해당 API를 기반으로 `/community/#map`을 오프라인 독서모임 장소 탐색/관리 화면으로 재구성한다.

핵심 변경 방향:

- 기존 도시 필터/유형 필터 중심 UI → **자연어 검색 중심** UI로 전환
- Google Maps + 좌우 패널 3단 레이아웃 구성
- 장소 저장, 메타데이터 편집, 후기 작성/조회 기능 추가

---

## 1. 백엔드 완료 현황

### 변경된 파일

| 파일 | 내용 |
|------|------|
| `app/schema.py` | `reading_places`, `reading_place_reviews` 테이블 추가 |
| `app/services/place_service.py` | Google Places 검색/상세, 저장 CRUD, 후기, Gemini 요약 fallback |
| `app/routes/places.py` | 프런트용 REST API |
| `tests/test_places_map.py` | 장소 검색·저장·수정·삭제·후기 테스트 |

### 테스트 결과

```bash
venv\Scripts\python.exe -m pytest -q
# 53 passed, 2 warnings
```

---

## 2. API 레퍼런스

### 우선 사용할 API (신규)

| 역할 | Method | Path |
|------|--------|------|
| 장소 검색 | GET | `/api/places/search` |
| Google 장소 상세 | GET | `/api/places/google/{google_place_id}` |
| 저장 장소 목록 | GET | `/api/places/saved` |
| 장소 저장 | POST | `/api/places/save` |
| 저장 장소 수정 | PUT | `/api/places/{place_id}` |
| 저장 장소 삭제 | DELETE | `/api/places/{place_id}` |
| 후기 조회 | GET | `/api/places/{place_id}/reviews` |
| 후기 작성 | POST | `/api/places/{place_id}/review` |
| 사진 URL 생성 | GET | `/api/places/photo` |

### 호환 유지 중인 기존 API

기존 지도/Mock API는 그대로 유지된다. 신규 프런트에서는 사용하지 않아도 된다.

- `GET /api/places/all`
- `GET /api/places/nearby`
- `GET /api/places/<place_id>`
- `POST /api/places/<place_id>/checkin`
- `POST /api/places/<place_id>/review`
- `GET /api/places/cities`
- `GET /api/places/status`

---

### 2.1 장소 검색

```http
GET /api/places/search?q=강남 카페&lat=37.5665&lng=126.978&radius=3000&limit=12
```

| 파라미터 | 필수 | 기본값 | 설명 |
|---------|------|--------|------|
| `q` | ✓ | — | 검색어 |
| `lat` | — | — | 현재 위도 |
| `lng` | — | — | 현재 경도 |
| `radius` | — | 3000 | 반경(m) |
| `limit` | — | 12 | 결과 개수 |

```json
{
  "ok": true,
  "places": [
    {
      "google_place_id": "ChIJ...",
      "name": "장소명",
      "address": "주소",
      "lat": 37.5665,
      "lng": 126.978,
      "google_rating": 4.5,
      "price_level": 2,
      "open_now": true,
      "place_types": ["cafe", "book_store"],
      "photo_url": "...",
      "distance_km": 1.2,
      "saved": false,
      "reading_score": 8.5,
      "source": "google"
    }
  ],
  "center": { "lat": 37.5665, "lng": 126.978 },
  "source": "google"
}
```

> Google API 키가 없거나 호출 실패 시 `source: "mock"`으로 fallback된다. Mock 응답도 동일 구조를 반환한다.

---

### 2.2 Google 장소 상세

```http
GET /api/places/google/{google_place_id}
```

```json
{
  "ok": true,
  "place": {
    "google_place_id": "ChIJ...",
    "name": "장소명",
    "address": "주소",
    "lat": 37.5665,
    "lng": 126.978,
    "phone": "02-000-0000",
    "website": "https://example.com",
    "google_rating": 4.5,
    "user_ratings_total": 120,
    "price_level": 2,
    "open_now": true,
    "opening_hours": ["월요일: 09:00-21:00"],
    "photo_url": "...",
    "place_types": ["cafe"],
    "google_maps_url": "https://maps.google.com/...",
    "saved": false,
    "reading_score": 8.5,
    "source": "google"
  },
  "summary": {
    "summary": "독서모임 장소로 검토할 만한 곳입니다.",
    "best_for": "소규모 독서모임",
    "caution": "방문 전 운영시간과 예약 가능 여부를 확인하세요.",
    "source": "gemini"
  }
}
```

---

### 2.3 저장 장소 목록

```http
GET /api/places/saved?user_id=user_demo&limit=50
```

```json
{ "ok": true, "places": [], "count": 0 }
```

---

### 2.4 장소 저장

```http
POST /api/places/save
```

```json
{
  "user_id": "user_demo",
  "google_place_id": "ChIJ...",
  "name": "독서모임 카페",
  "address": "서울시 종로구 ...",
  "lat": 37.5665,
  "lng": 126.978,
  "google_rating": 4.5,
  "price_level": 2,
  "open_now": true,
  "photo_url": "...",
  "place_types": ["cafe", "book_store"],
  "reading_score": 8.5,
  "meeting_capacity": 6,
  "noise_level": "quiet",
  "outlet_score": 4,
  "wifi_score": 5,
  "reservation_url": "",
  "memo": "독서모임하기 좋은 창가 자리"
}
```

응답:

```json
{ "ok": true, "place": { "place_id": "rp_xxxxx", "name": "독서모임 카페" } }
```

> 중복 저장이면 `duplicated: true`가 포함된다.

---

### 2.5 저장 장소 수정

```http
PUT /api/places/{place_id}
```

수정 가능 필드: `reading_score`, `meeting_capacity`, `noise_level`, `outlet_score`, `wifi_score`, `reservation_url`, `memo`, `photo_url`

```json
{
  "user_id": "user_demo",
  "reading_score": 9.1,
  "meeting_capacity": 8,
  "noise_level": "quiet",
  "memo": "4명 이하 독서모임에 특히 좋음"
}
```

---

### 2.6 저장 장소 삭제

```http
DELETE /api/places/{place_id}?user_id=user_demo
```

```json
{ "ok": true, "deleted": true, "review_policy": "deleted_with_place" }
```

> 장소 삭제 시 LUMA 내부 후기도 함께 삭제된다. Google 리뷰는 무관하다.

---

### 2.7 후기 조회

```http
GET /api/places/{place_id}/reviews?limit=20
```

```json
{
  "ok": true,
  "reviews": [
    {
      "review_id": "rv_xxxxx",
      "place_id": "rp_xxxxx",
      "user_id": "user_demo",
      "display_name": "소연",
      "emoji": "⭐",
      "rating": 5,
      "noise_level": "quiet",
      "group_size": 4,
      "visit_purpose": "offline_reading",
      "content": "조용하고 콘센트가 많아서 모임하기 좋았어요.",
      "created_at": "2026-05-09T..."
    }
  ],
  "count": 1
}
```

---

### 2.8 후기 작성

```http
POST /api/places/{place_id}/review
```

```json
{
  "user_id": "user_demo",
  "display_name": "소연",
  "emoji": "⭐",
  "rating": 5,
  "noise_level": "quiet",
  "group_size": 4,
  "visit_purpose": "offline_reading",
  "content": "조용하고 콘센트가 많아서 모임하기 좋았어요."
}
```

---

### 2.9 사진 URL 생성

```http
GET /api/places/photo?photo_reference=...&max_width=640
```

```json
{ "ok": true, "photo_url": "https://maps.googleapis.com/maps/api/place/photo?..." }
```

---

## 3. 프런트엔드 구현 가이드

### 3.1 레이아웃

```
┌──────────────┬──────────────────────┬──────────────────────┐
│  왼쪽 패널   │      중앙 지도        │   오른쪽 상세 패널   │
├──────────────┤                      ├──────────────────────┤
│ 검색창       │  Google Map          │ 대표 사진            │
│ 현재 위치 ▷  │  - 검색 결과 마커    │ 이름 / 주소 / 평점   │
│ ─────────── │  - 저장 장소 마커    │ 영업 상태 / 링크     │
│ [검색결과탭] │  - 현재 위치 마커    │ Gemini 요약          │
│ [저장목록탭] │                      │ 독서모임 메타 편집   │
│              │                      │ 저장 / 수정 / 삭제   │
│ 장소 카드    │                      │ 후기 작성 폼         │
│ 장소 카드    │                      │ 후기 목록            │
└──────────────┴──────────────────────┴──────────────────────┘
```

### 3.2 장소 카드 표시 항목

- 장소명
- 주소
- 거리(km)
- Google 평점
- 영업 중 여부
- 저장 여부 (북마크 아이콘)
- 독서모임 점수

### 3.3 상태 구조

```js
state = {
  query: "",
  userLocation: null,       // { lat, lng }
  searchResults: [],
  savedPlaces: [],
  selectedPlace: null,      // Google 상세 응답 전체
  selectedSavedPlaceId: null,
  mode: "search",           // "search" | "saved"
  loading: false,
  error: null
}
```

### 3.4 장소 선택 흐름

1. 검색 결과 카드 클릭
2. `google_place_id`로 `/api/places/google/{google_place_id}` 호출
3. 오른쪽 패널에 상세 표시 + 지도 중심 이동
4. **저장** → `POST /api/places/save` → 응답의 `place_id` 저장
5. **수정/삭제/후기** → `place_id` 기준으로 호출

### 3.5 지도 좌표 규칙

- 좌표는 반드시 Google Places 응답의 `lat`, `lng`만 사용한다 (Gemini 금지).
- 현재 위치는 브라우저 `Geolocation API`를 사용한다.
- 검색 시 현재 위치가 있으면 `lat`, `lng`, `radius`를 함께 전송한다.
- 검색 결과 클릭 시 지도 중심을 해당 장소 좌표로 이동한다.

### 3.6 방어 코드

Google Places 응답은 필드가 없을 수 있다. optional chaining 또는 기본값을 사용한다.

```js
const name    = place.name         || "이름 없는 장소";
const photoUrl = place.photo_url   || defaultPlaceImage;
const rating  = place.google_rating ?? "-";
```

`source: "mock"` 시 Google 전용 필드가 누락될 수 있지만, 검색 결과 표시·지도 마커·저장·후기 작성은 모두 동작해야 한다.

---

## 4. 개발 환경

### 서버 재시작

Codex 백엔드 수정 후 Flask 서버를 재시작해야 변경사항이 반영된다.

```powershell
# 실행 중인 서버 확인
Get-Process python -ErrorAction SilentlyContinue

# 필요 시 종료
Stop-Process -Name python -Force

# 재시작
venv\Scripts\python.exe app.py
```

### 확인 URL

```
http://localhost:5000/community/#map
```

---

## 5. 완료 기준

- [ ] `/community/#map` 진입 시 Google 지도 정상 표시
- [ ] 현재 위치 버튼 → 현재 위치 기준 검색
- [ ] 자연어 검색어로 Google Places 결과 표시
- [ ] 검색 결과 클릭 → 지도 + 오른쪽 패널 동기화
- [ ] 장소 저장 가능
- [ ] 저장한 장소 재조회 가능
- [ ] 저장한 장소의 독서모임 메타데이터 수정 가능
- [ ] 저장한 장소 삭제 가능
- [ ] 후기 작성 및 조회 가능
- [ ] Google API 실패 또는 키 누락 시 Mock 결과로 화면 정상 표시
