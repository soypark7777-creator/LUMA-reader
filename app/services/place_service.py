"""
독서 장소 서비스 — LUMA 글로벌 독서 지도
Google Maps API 키 없으면 인메모리 Mock으로 자동 폴백
"""
import os, uuid, math, json
from datetime import datetime
from typing import Optional

MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
_maps_ok = bool(MAPS_API_KEY and MAPS_API_KEY != "여기에_입력")

# ══════════════════════════════════════════════════════════════
#  전세계 독서 명소 Mock 데이터
# ══════════════════════════════════════════════════════════════
_spots: list[dict] = [
    # ── 서울 ──
    {"place_id":"place_kr_001","name":"어니언 성수","address":"서울 성동구 아차산로9길 8","lat":37.5443,"lng":127.0557,"type":"cafe","city":"서울","country":"한국","ai_tags":["오래앉기좋음","분위기좋음","넓은좌석","자연채광"],"reading_score":9.1,"rating":4.7,"price_level":3,"check_ins":247,"photo_emoji":"🏭","description":"성수동 감성의 대형 베이커리 카페. 높은 천장과 자연광이 독서에 최적.","reviews":[{"user":"독서왕","emoji":"📚","text":"오래 앉아 있기 정말 좋아요. 음악도 조용해서 집중이 잘 돼요.","score":9}],"open_hours":"월-금 08:00-22:00 / 주말 09:00-22:00"},
    {"place_id":"place_kr_002","name":"북앤레스트 삼청점","address":"서울 종로구 삼청로 130","lat":37.5824,"lng":126.9811,"type":"bookstore_cafe","city":"서울","country":"한국","ai_tags":["조용한","모임룸","WiFi빠름","오래앉기좋음","콘센트多"],"reading_score":9.6,"rating":4.9,"price_level":2,"check_ins":412,"photo_emoji":"📚","description":"삼청동 골목의 아늑한 서점 카페. 독서 모임 전용 공간 보유.","reviews":[{"user":"철학소녀","emoji":"🌿","text":"이 곳에서 읽은 책만 20권이 넘어요. 조용하고 책 내음이 나서 집중이 저절로 돼요.","score":10}],"open_hours":"화-일 10:00-21:00 (월 휴무)"},
    {"place_id":"place_kr_003","name":"국립중앙도서관","address":"서울 서초구 반포대로 201","lat":37.4944,"lng":127.0072,"type":"library","city":"서울","country":"한국","ai_tags":["조용한","넓은좌석","WiFi빠름","자연채광","혼잡하지않음"],"reading_score":9.8,"rating":4.8,"price_level":0,"check_ins":892,"photo_emoji":"🏛️","description":"대한민국 대표 도서관. 광대한 장서와 쾌적한 독서 환경.","reviews":[{"user":"논문쓰는사람","emoji":"🎓","text":"최고의 독서 환경. 무료에 와이파이까지!","score":10}],"open_hours":"화-일 09:00-21:00 (월 휴무)"},
    {"place_id":"place_kr_004","name":"카페 마리아주 이태원","address":"서울 용산구 이태원로27가길 17","lat":37.5348,"lng":126.9928,"type":"cafe","city":"서울","country":"한국","ai_tags":["조용한","자연채광","분위기좋음","오래앉기좋음"],"reading_score":8.8,"rating":4.5,"price_level":3,"check_ins":183,"photo_emoji":"🫖","description":"이태원 골목의 프랑스풍 티 카페. 조용하고 우아한 독서 분위기.","reviews":[{"user":"홍차애호가","emoji":"🍵","text":"차 종류가 많고 너무 조용해서 책 읽기 최적이에요.","score":9}],"open_hours":"매일 11:00-22:00"},
    {"place_id":"place_kr_005","name":"부산 F1963 복합문화공간","address":"부산 수영구 구락로123번길 20","lat":35.1666,"lng":129.0989,"type":"bookstore_cafe","city":"부산","country":"한국","ai_tags":["넓은좌석","자연채광","분위기좋음","오래앉기좋음","모임룸"],"reading_score":9.3,"rating":4.8,"price_level":2,"check_ins":634,"photo_emoji":"🏗️","description":"와이어 공장을 개조한 복합문화공간. YES24 서점과 카페가 함께 있는 독서 성지.","reviews":[{"user":"부산독서인","emoji":"🌊","text":"넓고 탁 트인 공간에서 책 읽으면 기분이 너무 좋아요.","score":10}],"open_hours":"화-일 10:00-20:00"},
    # ── 도쿄 ──
    {"place_id":"place_jp_001","name":"蔦屋書店 代官山","address":"東京都渋谷区猿楽町17-5","lat":35.6490,"lng":139.7021,"type":"bookstore_cafe","city":"도쿄","country":"일본","ai_tags":["분위기좋음","조용한","오래앉기좋음","자연채광","모임룸"],"reading_score":9.9,"rating":4.9,"price_level":3,"check_ins":1243,"photo_emoji":"🏯","description":"다이칸야마의 전설적인 서점. 스타벅스와 연결된 독서 성지.","reviews":[{"user":"도쿄여행자","emoji":"🗼","text":"세상에서 가장 아름다운 서점이에요.","score":10}],"open_hours":"매일 07:00-02:00"},
    {"place_id":"place_jp_002","name":"銀座 蔦屋書店","address":"東京都中央区銀座6-10-1","lat":35.6694,"lng":139.7632,"type":"bookstore_cafe","city":"도쿄","country":"일본","ai_tags":["조용한","넓은좌석","밝은조명","WiFi빠름","분위기좋음"],"reading_score":9.4,"rating":4.7,"price_level":3,"check_ins":876,"photo_emoji":"✨","description":"긴자 GINZA SIX 내 고급 서점. 아트북과 외국 잡지 컬렉션이 풍부.","reviews":[{"user":"긴자산책","emoji":"👔","text":"쇼핑 중간에 들러서 책 읽기 딱 좋아요.","score":9}],"open_hours":"매일 10:30-21:00"},
    # ── 파리 ──
    {"place_id":"place_fr_001","name":"Shakespeare and Company","address":"37 Rue de la Bûcherie, Paris","lat":48.8527,"lng":2.3470,"type":"bookstore_cafe","city":"파리","country":"프랑스","ai_tags":["분위기좋음","조용한","오래앉기좋음","자연채광"],"reading_score":9.5,"rating":4.7,"price_level":2,"check_ins":3841,"photo_emoji":"📗","description":"센강변의 전설적인 영문 서점. 파리 문학 역사의 중심지.","reviews":[{"user":"파리지앵","emoji":"🥐","text":"노트르담을 바라보며 영문학을 읽는 경험은 평생 잊지 못해요.","score":10}],"open_hours":"월-금 10:00-22:00 / 주말 10:00-23:00"},
    {"place_id":"place_fr_002","name":"Café de Flore","address":"172 Boulevard Saint-Germain, Paris","lat":48.8539,"lng":2.3329,"type":"cafe","city":"파리","country":"프랑스","ai_tags":["분위기좋음","오래앉기좋음","자연채광","조용한"],"reading_score":8.9,"rating":4.5,"price_level":4,"check_ins":2156,"photo_emoji":"🥂","description":"생제르맹의 역사적 카페. 사르트르와 보부아르의 단골 아지트.","reviews":[{"user":"철학카페","emoji":"🫖","text":"실존주의 철학자들이 철학을 논하던 바로 그 자리에서 책을 읽었어요.","score":9}],"open_hours":"매일 07:30-01:30"},
    # ── 뉴욕 ──
    {"place_id":"place_us_001","name":"The New York Public Library","address":"476 5th Ave, New York","lat":40.7532,"lng":-73.9822,"type":"library","city":"뉴욕","country":"미국","ai_tags":["조용한","넓은좌석","밝은조명","혼잡하지않음","자연채광"],"reading_score":9.9,"rating":4.9,"price_level":0,"check_ins":5672,"photo_emoji":"🏛️","description":"뉴욕 5번가의 상징. 로즈 메인 리딩룸은 세계 최고의 독서 공간.","reviews":[{"user":"NYer","emoji":"🗽","text":"로즈 메인 리딩룸은 세계에서 가장 아름다운 독서 공간 중 하나예요.","score":10}],"open_hours":"월-수 10:00-20:00 / 목-금 10:00-18:00 / 주말 10:00-17:00"},
    {"place_id":"place_us_002","name":"Strand Book Store","address":"828 Broadway, New York","lat":40.7332,"lng":-73.9909,"type":"bookstore_cafe","city":"뉴욕","country":"미국","ai_tags":["분위기좋음","조용한","오래앉기좋음","WiFi빠름"],"reading_score":9.2,"rating":4.6,"price_level":2,"check_ins":1893,"photo_emoji":"📚","description":"뉴욕 최고의 독립 서점. 18마일 분량의 책.","reviews":[{"user":"책벌레","emoji":"🐛","text":"18마일의 책! 중고책 탐험이 끝나면 카페에서 새 책 첫 장을 열어보세요.","score":9}],"open_hours":"매일 09:30-22:30"},
    # ── 런던 ──
    {"place_id":"place_uk_001","name":"British Library","address":"96 Euston Rd, London","lat":51.5296,"lng":-0.1271,"type":"library","city":"런던","country":"영국","ai_tags":["조용한","넓은좌석","자연채광","혼잡하지않음","WiFi빠름"],"reading_score":9.8,"rating":4.8,"price_level":0,"check_ins":4231,"photo_emoji":"🏛️","description":"대영도서관. 마르크스가 자본론을 집필한 바로 그 공간.","reviews":[{"user":"런던생활자","emoji":"☔","text":"이 공간에서 읽는 것 자체가 지식의 역사 속으로 들어가는 느낌이에요.","score":10}],"open_hours":"월-목 09:30-20:00 / 금-토 09:30-17:00"},
    {"place_id":"place_uk_002","name":"Daunt Books Marylebone","address":"83 Marylebone High St, London","lat":51.5203,"lng":-0.1543,"type":"bookstore_cafe","city":"런던","country":"영국","ai_tags":["분위기좋음","조용한","자연채광","오래앉기좋음"],"reading_score":9.4,"rating":4.8,"price_level":2,"check_ins":1567,"photo_emoji":"🎩","description":"런던 최고의 독립 서점. 에드워드 시대 건물의 우아한 인테리어.","reviews":[{"user":"런던서점순례","emoji":"🌹","text":"지하 갤러리 서가에서 책을 고르는 경험이 정말 특별해요.","score":10}],"open_hours":"월-토 09:00-19:30 / 일 11:00-18:00"},
]

_checkins: list[dict] = []
_saved_places_mem: dict[str, dict] = {}
_place_reviews_mem: dict[str, list[dict]] = {}


# ══════════════════════════════════════════════════════════════
#  거리 계산
# ══════════════════════════════════════════════════════════════
def _haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2-lat1); dλ = math.radians(lng2-lng1)
    a  = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


# ══════════════════════════════════════════════════════════════
#  독서 적합도 점수 계산
# ══════════════════════════════════════════════════════════════
TAG_WEIGHTS = {
    "조용한":0.25,"오래앉기좋음":0.20,"넓은좌석":0.15,
    "WiFi빠름":0.10,"콘센트多":0.10,"자연채광":0.08,
    "분위기좋음":0.07,"모임룸":0.05,
}

def calc_reading_score(spot: dict) -> float:
    tags  = spot.get("ai_tags", [])
    base  = spot.get("rating", 4.0) * 1.5
    bonus = sum(TAG_WEIGHTS.get(t, 0) * 10 for t in tags)
    return round(min(10.0, base + bonus), 1)


# ══════════════════════════════════════════════════════════════
#  핵심 API 함수
# ══════════════════════════════════════════════════════════════
def search_nearby(lat: float, lng: float, radius_km=50.0,
                  spot_type="all", limit=20) -> list[dict]:
    """위치 기반 주변 독서 명소 검색"""
    results = []
    for s in _spots:
        dist = _haversine(lat, lng, s["lat"], s["lng"])
        if dist > radius_km: continue
        if spot_type != "all" and s["type"] != spot_type: continue
        results.append({**s, "distance_km": round(dist, 1),
                        "reading_score": s.get("reading_score") or calc_reading_score(s)})
    results.sort(key=lambda x: (x["distance_km"], -x["reading_score"]))
    return results[:limit]


def get_all_spots(spot_type="all", city="all", limit=20) -> list[dict]:
    """전체 명소 목록 (필터 가능)"""
    results = []
    for s in _spots:
        if spot_type != "all" and s["type"] != spot_type: continue
        if city != "all" and s["city"] != city: continue
        results.append({**s, "reading_score": s.get("reading_score") or calc_reading_score(s)})
    results.sort(key=lambda x: -x["reading_score"])
    return results[:limit]


def get_spot(place_id: str) -> Optional[dict]:
    """단일 장소 상세"""
    s = next((x for x in _spots if x["place_id"]==place_id), None)
    if not s: return None
    return {**s, "reading_score": s.get("reading_score") or calc_reading_score(s),
            "checkin_count": len([c for c in _checkins if c["place_id"]==place_id])}


def checkin_spot(place_id: str, user_id: str, memo: str = "") -> dict:
    """장소 체크인"""
    spot = next((x for x in _spots if x["place_id"]==place_id), None)
    if not spot: return {"ok": False, "error": "장소 없음"}
    doc = {"checkin_id": f"ci_{uuid.uuid4().hex[:6]}", "place_id": place_id,
           "user_id": user_id, "memo": memo, "created_at": datetime.now().isoformat()}
    _checkins.insert(0, doc)
    spot["check_ins"] = spot.get("check_ins", 0) + 1
    return {"ok": True, "checkin": doc, "total": spot["check_ins"]}


def add_review(place_id: str, data: dict) -> dict:
    """리뷰 추가"""
    spot = next((x for x in _spots if x["place_id"]==place_id), None)
    if not spot: return {"ok": False, "error": "장소 없음"}
    review = {"user": data.get("user","익명"), "emoji": data.get("emoji","⭐"),
              "text": data.get("text",""), "score": data.get("score", 8)}
    spot.setdefault("reviews", []).insert(0, review)
    return {"ok": True, "review": review}


def get_cities() -> list[str]:
    """등록된 도시 목록"""
    return sorted(list({s["city"] for s in _spots}))


def get_map_status() -> dict:
    return {"maps_api": _maps_ok, "mode": "google_maps" if _maps_ok else "mock",
            "total_spots": len(_spots)}


# ---------------------------------------------------------------------------
# Google Places + saved reading-place API
# ---------------------------------------------------------------------------

def _load_maps_key() -> str:
    if os.getenv("LUMA_DISABLE_GOOGLE_PLACES"):
        return ""
    if os.getenv("PYTEST_CURRENT_TEST") and not os.getenv("LUMA_ALLOW_EXTERNAL_GOOGLE"):
        return ""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    return os.getenv("GOOGLE_MAPS_API_KEY", "").strip()


def _safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _json_text(value) -> str:
    return json.dumps(value or [], ensure_ascii=False)


def _json_loads(value, fallback=None):
    if not value:
        return fallback if fallback is not None else []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback if fallback is not None else []


def _spot_to_place(spot: dict, lat=None, lng=None, saved=False) -> dict:
    distance = None
    if lat is not None and lng is not None:
        distance = round(_haversine(float(lat), float(lng), spot["lat"], spot["lng"]), 2)
    return {
        "place_id": spot.get("place_id"),
        "google_place_id": spot.get("google_place_id"),
        "name": spot.get("name"),
        "address": spot.get("address"),
        "lat": spot.get("lat"),
        "lng": spot.get("lng"),
        "google_rating": spot.get("google_rating", spot.get("rating")),
        "rating": spot.get("rating"),
        "price_level": spot.get("price_level"),
        "open_now": spot.get("open_now"),
        "place_types": spot.get("place_types", [spot.get("type")] if spot.get("type") else []),
        "photo_reference": spot.get("photo_reference"),
        "photo_url": spot.get("photo_url"),
        "distance_km": distance,
        "saved": saved,
        "reading_score": spot.get("reading_score") or calc_reading_score(spot),
        "source": spot.get("source", "mock"),
    }


def _mock_search_places(query="", lat=None, lng=None, radius=3000, limit=12) -> list[dict]:
    q = (query or "").lower()
    lat = _safe_float(lat)
    lng = _safe_float(lng)
    radius_km = max((_safe_float(radius, 3000) or 3000) / 1000, 1)
    results = []
    for spot in _spots:
        text = " ".join(str(spot.get(k, "")) for k in ("name", "address", "type", "city", "country")).lower()
        if q and q not in text:
            matched_category = False
            if "카페" in query or "cafe" in q:
                matched_category = spot.get("type") in ("cafe", "bookstore_cafe")
            elif "도서관" in query or "library" in q:
                matched_category = spot.get("type") == "library"
            elif "독서" in query or "모임" in query or "reading" in q or "book" in q:
                matched_category = True
            if not matched_category:
                continue
        if lat is not None and lng is not None:
            dist = _haversine(lat, lng, spot["lat"], spot["lng"])
            if dist > radius_km and q:
                continue
        results.append(_spot_to_place(spot, lat, lng))
    if not results and lat is not None and lng is not None:
        candidates = [_spot_to_place(spot, lat, lng) for spot in _spots]
        candidates.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] or 999999, -x["reading_score"]))
        return candidates[:limit]
    results.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] or 999999, -x["reading_score"]))
    return results[:limit]


def _reading_score_from_google(item: dict) -> float:
    rating = float(item.get("rating") or 4.0)
    types = set(item.get("types") or [])
    score = rating * 1.55
    if "library" in types:
        score += 1.8
    if "book_store" in types:
        score += 1.2
    if "cafe" in types:
        score += 0.8
    if item.get("opening_hours", {}).get("open_now"):
        score += 0.2
    return round(min(10.0, score), 1)


def _google_item_to_place(item: dict, lat=None, lng=None, saved_ids=None) -> dict:
    location = item.get("geometry", {}).get("location", {})
    p_lat = location.get("lat")
    p_lng = location.get("lng")
    photos = item.get("photos") or []
    photo_reference = photos[0].get("photo_reference") if photos else None
    distance = None
    if lat is not None and lng is not None and p_lat is not None and p_lng is not None:
        distance = round(_haversine(lat, lng, float(p_lat), float(p_lng)), 2)
    google_place_id = item.get("place_id")
    return {
        "google_place_id": google_place_id,
        "name": item.get("name"),
        "address": item.get("formatted_address") or item.get("vicinity"),
        "lat": p_lat,
        "lng": p_lng,
        "google_rating": item.get("rating"),
        "price_level": item.get("price_level"),
        "open_now": item.get("opening_hours", {}).get("open_now"),
        "place_types": item.get("types") or [],
        "photo_reference": photo_reference,
        "photo_url": get_google_photo_url(photo_reference) if photo_reference else "",
        "distance_km": distance,
        "saved": google_place_id in (saved_ids or set()),
        "reading_score": _reading_score_from_google(item),
        "source": "google",
    }


def _google_places_text_search(requests, key, query, lat=None, lng=None, radius=3000) -> list[dict]:
    params = {
        "query": query,
        "key": key,
        "language": "ko",
        "region": "kr",
    }
    if lat is not None and lng is not None:
        params["location"] = f"{lat},{lng}"
        params["radius"] = radius
    resp = requests.get(
        "https://maps.googleapis.com/maps/api/place/textsearch/json",
        params=params,
        timeout=5,
    )
    payload = resp.json()
    if resp.status_code != 200 or payload.get("status") not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(payload.get("error_message") or payload.get("status") or resp.status_code)
    return payload.get("results", [])


def _google_places_nearby_search(requests, key, lat, lng, radius=3000) -> list[dict]:
    if lat is None or lng is None:
        return []
    all_items = []
    for place_type, keyword in (
        ("library", "도서관 독서"),
        ("cafe", "조용한 카페 독서"),
        ("book_store", "서점 북카페"),
    ):
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            params={
                "location": f"{lat},{lng}",
                "radius": radius,
                "type": place_type,
                "keyword": keyword,
                "language": "ko",
                "key": key,
            },
            timeout=5,
        )
        payload = resp.json()
        if resp.status_code != 200 or payload.get("status") not in ("OK", "ZERO_RESULTS"):
            continue
        all_items.extend(payload.get("results", []))
    return all_items


def _saved_google_ids(user_id="user_demo") -> set[str]:
    try:
        from app.db import execute_all, is_connected
        if is_connected():
            rows = execute_all(
                "SELECT google_place_id FROM reading_places WHERE created_by=%s AND google_place_id IS NOT NULL",
                (user_id,),
            )
            return {r["google_place_id"] for r in rows if r.get("google_place_id")}
    except Exception:
        pass
    return {p.get("google_place_id") for p in _saved_places_mem.values() if p.get("created_by") == user_id and p.get("google_place_id")}


def _row_to_place(row: dict) -> dict:
    if not row:
        return {}
    place = dict(row)
    for key in ("lat", "lng", "google_rating", "reading_score"):
        if place.get(key) is not None:
            place[key] = float(place[key])
    for key in ("price_level", "open_now", "meeting_capacity", "outlet_score", "wifi_score"):
        if place.get(key) is not None:
            place[key] = int(place[key])
    place["place_types"] = _json_loads(place.get("place_types"), [])
    place["opening_hours"] = _json_loads(place.get("opening_hours"), [])
    place["saved"] = True
    return place


def _find_saved_place(place_id: str) -> Optional[dict]:
    try:
        from app.db import execute_one, is_connected
        if is_connected():
            row = execute_one(
                "SELECT * FROM reading_places WHERE place_id=%s OR google_place_id=%s",
                (place_id, place_id),
            )
            return _row_to_place(row) if row else None
    except Exception:
        pass
    return _saved_places_mem.get(place_id) or next(
        (p for p in _saved_places_mem.values() if p.get("google_place_id") == place_id),
        None,
    )


def get_google_photo_url(photo_reference, max_width=640) -> str:
    if not photo_reference:
        return ""
    key = _load_maps_key()
    if not key:
        return ""
    width = max(100, min(_safe_int(max_width, 640) or 640, 1600))
    return (
        "https://maps.googleapis.com/maps/api/place/photo"
        f"?maxwidth={width}&photo_reference={photo_reference}&key={key}"
    )


def search_google_places(query, lat=None, lng=None, radius=3000, limit=12) -> dict:
    key = _load_maps_key()
    limit = max(1, min(_safe_int(limit, 12) or 12, 40))
    lat_f = _safe_float(lat)
    lng_f = _safe_float(lng)
    radius_i = max(100, min(_safe_int(radius, 3000) or 3000, 50000))
    saved_ids = _saved_google_ids()

    if not key:
        return {"source": "mock", "places": _mock_search_places(query, lat_f, lng_f, radius_i, limit)}

    try:
        import requests
        items = []
        items.extend(_google_places_text_search(requests, key, query or "독서모임하기 좋은 카페 도서관 북카페", lat_f, lng_f, radius_i))
        if lat_f is not None and lng_f is not None:
            items.extend(_google_places_nearby_search(requests, key, lat_f, lng_f, radius_i))

        by_id = {}
        for item in items:
            place_id = item.get("place_id")
            if place_id and place_id not in by_id:
                by_id[place_id] = item

        places = [_google_item_to_place(item, lat_f, lng_f, saved_ids) for item in by_id.values()]
        places = [p for p in places if p.get("name") and p.get("lat") and p.get("lng")]
        places.sort(key=lambda x: (
            x["distance_km"] is None,
            x["distance_km"] or 999999,
            -float(x.get("reading_score") or 0),
            -float(x.get("google_rating") or 0),
        ))
        return {"source": "google", "places": places[:limit]}
    except Exception as e:
        print(f"[WARN] Google Places search failed -> mock fallback: {e}")
        return {"source": "mock", "places": _mock_search_places(query, lat_f, lng_f, radius_i, limit)}


def get_google_place_detail(google_place_id) -> dict:
    saved = _find_saved_place(google_place_id)
    key = _load_maps_key()
    if not key:
        mock = saved or get_spot(google_place_id) or (_mock_search_places(str(google_place_id), limit=1) or [{}])[0]
        return {"ok": True, "source": "mock", "place": mock}

    try:
        import requests
        fields = ",".join([
            "place_id", "name", "formatted_address", "geometry", "formatted_phone_number",
            "website", "rating", "user_ratings_total", "price_level", "opening_hours",
            "photos", "types", "url", "editorial_summary", "reviews",
        ])
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={
                "place_id": google_place_id,
                "fields": fields,
                "language": "ko",
                "key": key,
            },
            timeout=5,
        )
        payload = resp.json()
        if resp.status_code != 200 or payload.get("status") != "OK":
            raise RuntimeError(payload.get("error_message") or payload.get("status") or resp.status_code)
        item = payload.get("result") or {}
        location = item.get("geometry", {}).get("location", {})
        photos = [
            {
                "photo_reference": p.get("photo_reference"),
                "width": p.get("width"),
                "height": p.get("height"),
                "photo_url": get_google_photo_url(p.get("photo_reference")),
            }
            for p in item.get("photos", [])[:5]
            if p.get("photo_reference")
        ]
        place = {
            "google_place_id": item.get("place_id") or google_place_id,
            "name": item.get("name"),
            "address": item.get("formatted_address"),
            "lat": location.get("lat"),
            "lng": location.get("lng"),
            "phone": item.get("formatted_phone_number"),
            "website": item.get("website"),
            "google_rating": item.get("rating"),
            "user_ratings_total": item.get("user_ratings_total"),
            "description": (item.get("editorial_summary") or {}).get("overview") or "",
            "price_level": item.get("price_level"),
            "open_now": item.get("opening_hours", {}).get("open_now"),
            "opening_hours": item.get("opening_hours", {}).get("weekday_text") or [],
            "photos": photos,
            "photo_reference": photos[0]["photo_reference"] if photos else None,
            "photo_url": photos[0]["photo_url"] if photos else "",
            "place_types": item.get("types") or [],
            "google_maps_url": item.get("url"),
            "saved": bool(saved),
            "reading_score": saved.get("reading_score") if saved else round(min(10, float(item.get("rating") or 4.0) * 1.8), 1),
            "source": "google",
            "google_reviews": [
                {
                    "display_name": r.get("author_name") or "Google 사용자",
                    "rating": r.get("rating"),
                    "content": r.get("text") or "",
                    "relative_time": r.get("relative_time_description") or "",
                }
                for r in (item.get("reviews") or [])[:5]
            ],
        }
        if saved:
            place.update({k: saved.get(k) for k in (
                "place_id", "meeting_capacity", "noise_level", "outlet_score",
                "wifi_score", "reservation_url", "memo",
            ) if saved.get(k) is not None})
        return {"ok": True, "source": "google", "place": place}
    except Exception as e:
        print(f"[WARN] Google Places detail failed -> mock fallback: {e}")
        mock = saved or get_spot(google_place_id) or (_mock_search_places(str(google_place_id), limit=1) or [{}])[0]
        return {"ok": True, "source": "mock", "place": mock}


def save_reading_place(user_id, data) -> dict:
    user_id = user_id or data.get("user_id") or "user_demo"
    google_place_id = data.get("google_place_id")
    place_id = data.get("place_id") or f"rp_{uuid.uuid4().hex[:12]}"
    name = (data.get("name") or "").strip()
    lat = _safe_float(data.get("lat"))
    lng = _safe_float(data.get("lng"))
    if not name or lat is None or lng is None:
        return {"ok": False, "error": "장소명과 좌표가 필요합니다."}

    existing = _find_saved_place(google_place_id or place_id)
    if existing:
        return {"ok": True, "place": existing, "duplicated": True}

    place = {
        "place_id": place_id,
        "google_place_id": google_place_id,
        "name": name,
        "address": data.get("address"),
        "lat": lat,
        "lng": lng,
        "phone": data.get("phone"),
        "website": data.get("website"),
        "google_rating": _safe_float(data.get("google_rating")),
        "price_level": _safe_int(data.get("price_level")),
        "open_now": data.get("open_now"),
        "opening_hours": data.get("opening_hours") or [],
        "photo_reference": data.get("photo_reference"),
        "photo_url": data.get("photo_url"),
        "place_types": data.get("place_types") or [],
        "source": data.get("source") or ("google" if google_place_id else "manual"),
        "reading_score": _safe_float(data.get("reading_score"), 0) or 0,
        "meeting_capacity": _safe_int(data.get("meeting_capacity")),
        "noise_level": data.get("noise_level") or "unknown",
        "outlet_score": _safe_int(data.get("outlet_score")),
        "wifi_score": _safe_int(data.get("wifi_score")),
        "reservation_url": data.get("reservation_url"),
        "memo": data.get("memo"),
        "created_by": user_id,
    }

    try:
        from app.db import execute_write, is_connected
        if is_connected():
            execute_write(
                """
                INSERT IGNORE INTO reading_places
                    (place_id, google_place_id, name, address, lat, lng, phone, website,
                     google_rating, price_level, open_now, opening_hours, photo_reference,
                     photo_url, place_types, source, reading_score, meeting_capacity,
                     noise_level, outlet_score, wifi_score, reservation_url, memo, created_by)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    place["place_id"], place["google_place_id"], place["name"], place["address"],
                    place["lat"], place["lng"], place["phone"], place["website"],
                    place["google_rating"], place["price_level"], place["open_now"],
                    _json_text(place["opening_hours"]), place["photo_reference"], place["photo_url"],
                    _json_text(place["place_types"]), place["source"], place["reading_score"],
                    place["meeting_capacity"], place["noise_level"], place["outlet_score"],
                    place["wifi_score"], place["reservation_url"], place["memo"], place["created_by"],
                ),
            )
            saved = _find_saved_place(place["place_id"])
            return {"ok": True, "place": saved or place}
    except Exception as e:
        print(f"[WARN] reading_places save failed -> mock fallback: {e}")

    place["saved"] = True
    _saved_places_mem[place_id] = place
    return {"ok": True, "place": place}


def update_reading_place(place_id, user_id, data) -> dict:
    allowed = {
        "reading_score", "meeting_capacity", "noise_level", "outlet_score",
        "wifi_score", "reservation_url", "memo", "photo_url",
    }
    existing = _find_saved_place(place_id)
    if not existing:
        return {"ok": False, "error": "장소를 찾을 수 없습니다."}
    updates = {k: data.get(k) for k in allowed if k in data}
    if not updates:
        return {"ok": True, "place": existing}

    try:
        from app.db import get_db, is_connected
        if is_connected():
            assignments = []
            params = []
            for key, value in updates.items():
                assignments.append(key + "=%s")
                params.append(value)
            params.extend([place_id, user_id or "user_demo"])
            with get_db() as cur:
                cur.execute(
                    "UPDATE reading_places SET " + ", ".join(assignments) + " WHERE place_id=%s AND created_by=%s",
                    tuple(params),
                )
            updated = _find_saved_place(place_id)
            return {"ok": True, "place": updated or existing}
    except Exception as e:
        print(f"[WARN] reading_places update failed -> mock fallback: {e}")

    existing.update(updates)
    _saved_places_mem[existing["place_id"]] = existing
    return {"ok": True, "place": existing}


def delete_reading_place(place_id, user_id) -> dict:
    # Policy: deleting a saved place also deletes its LUMA reviews. Google reviews are never stored here.
    existing = _find_saved_place(place_id)
    if not existing:
        return {"ok": False, "error": "장소를 찾을 수 없습니다."}
    try:
        from app.db import get_db, is_connected
        if is_connected():
            with get_db() as cur:
                cur.execute("DELETE FROM reading_place_reviews WHERE place_id=%s", (place_id,))
                cur.execute("DELETE FROM reading_places WHERE place_id=%s AND created_by=%s", (place_id, user_id or "user_demo"))
            return {"ok": True, "deleted": True, "review_policy": "deleted_with_place"}
    except Exception as e:
        print(f"[WARN] reading_places delete failed -> mock fallback: {e}")

    _saved_places_mem.pop(place_id, None)
    _place_reviews_mem.pop(place_id, None)
    return {"ok": True, "deleted": True, "review_policy": "deleted_with_place"}


def list_saved_reading_places(user_id, limit=50) -> list[dict]:
    limit = max(1, min(_safe_int(limit, 50) or 50, 100))
    try:
        from app.db import execute_all, is_connected
        if is_connected():
            rows = execute_all(
                "SELECT * FROM reading_places WHERE created_by=%s ORDER BY updated_at DESC LIMIT %s",
                (user_id or "user_demo", limit),
            )
            return [_row_to_place(row) for row in rows]
    except Exception as e:
        print(f"[WARN] reading_places list failed -> mock fallback: {e}")
    return [
        p for p in sorted(
            _saved_places_mem.values(),
            key=lambda x: x.get("updated_at") or x.get("created_at") or "",
            reverse=True,
        )
        if p.get("created_by") == (user_id or "user_demo")
    ][:limit]


def add_place_review(place_id, user_id, data) -> dict:
    content = (data.get("content") or data.get("text") or "").strip()
    if not content:
        return {"ok": False, "error": "후기 내용을 입력해주세요."}
    review = {
        "review_id": data.get("review_id") or f"rv_{uuid.uuid4().hex[:12]}",
        "place_id": place_id,
        "user_id": user_id or data.get("user_id") or "user_demo",
        "display_name": data.get("display_name") or data.get("user") or "독서가",
        "emoji": data.get("emoji") or "⭐",
        "rating": _safe_int(data.get("rating", data.get("score"))),
        "noise_level": data.get("noise_level") or "unknown",
        "group_size": _safe_int(data.get("group_size")),
        "visit_purpose": data.get("visit_purpose"),
        "content": content,
        "created_at": datetime.now().isoformat(),
    }

    try:
        from app.db import execute_write, is_connected
        if is_connected() and _find_saved_place(place_id):
            execute_write(
                """
                INSERT INTO reading_place_reviews
                    (review_id, place_id, user_id, display_name, emoji, rating,
                     noise_level, group_size, visit_purpose, content)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    review["review_id"], review["place_id"], review["user_id"],
                    review["display_name"], review["emoji"], review["rating"],
                    review["noise_level"], review["group_size"],
                    review["visit_purpose"], review["content"],
                ),
            )
            return {"ok": True, "review": review}
    except Exception as e:
        print(f"[WARN] reading_place_reviews insert failed -> mock fallback: {e}")

    if place_id in _saved_places_mem:
        _place_reviews_mem.setdefault(place_id, []).insert(0, review)
        return {"ok": True, "review": review}
    legacy = add_review(place_id, {
        "user": review["display_name"],
        "emoji": review["emoji"],
        "text": review["content"],
        "score": review["rating"] or 8,
    })
    if legacy.get("ok"):
        legacy["review"] = review
    return legacy


def list_place_reviews(place_id, limit=20) -> list[dict]:
    limit = max(1, min(_safe_int(limit, 20) or 20, 100))
    try:
        from app.db import execute_all, is_connected
        if is_connected():
            rows = execute_all(
                "SELECT * FROM reading_place_reviews WHERE place_id=%s ORDER BY created_at DESC LIMIT %s",
                (place_id, limit),
            )
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"[WARN] reading_place_reviews list failed -> mock fallback: {e}")
    if place_id in _place_reviews_mem:
        return _place_reviews_mem[place_id][:limit]
    spot = get_spot(place_id)
    if not spot:
        return []
    reviews = []
    for idx, r in enumerate(spot.get("reviews", [])[:limit]):
        reviews.append({
            "review_id": f"legacy_{idx}",
            "place_id": place_id,
            "user_id": "legacy",
            "display_name": r.get("user"),
            "emoji": r.get("emoji", "⭐"),
            "rating": r.get("score"),
            "noise_level": "unknown",
            "group_size": None,
            "visit_purpose": None,
            "content": r.get("text", ""),
        })
    return reviews


def summarize_place_for_reading(place, reviews) -> dict:
    review_text = "\n".join(f"- {r.get('content') or r.get('text')}" for r in (reviews or [])[:5])
    try:
        from app.services.gemini_service import _call_gemini, _parse_json_safe
        prompt = f"""
다음 장소가 오프라인 독서모임에 적합한지 짧게 요약해주세요.

장소명: {place.get('name')}
주소: {place.get('address')}
평점: {place.get('google_rating') or place.get('rating')}
독서 점수: {place.get('reading_score')}
후기:
{review_text}

JSON만 반환:
{{"summary":"한두 문장 요약","best_for":"어울리는 모임 유형","caution":"주의할 점"}}
"""
        raw = _call_gemini(prompt, expect_json=True)
        parsed = _parse_json_safe(raw) if raw else None
        if isinstance(parsed, dict) and parsed.get("summary"):
            parsed["source"] = "gemini"
            return parsed
    except Exception as e:
        print(f"[WARN] place summary Gemini failed -> rule fallback: {e}")

    name = place.get("name") or "이 장소"
    score = place.get("reading_score") or place.get("google_rating") or place.get("rating") or 0
    return {
        "summary": f"{name}은 독서모임 장소로 검토할 만한 곳입니다. 조용함, 좌석, 접근성을 후기로 확인해보세요.",
        "best_for": "소규모 독서모임",
        "caution": "방문 전 운영시간과 예약 가능 여부를 확인하세요.",
        "reading_score": score,
        "source": "rule",
    }
