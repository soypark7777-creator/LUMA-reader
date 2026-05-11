import uuid


def test_places_search_returns_places(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    r = client.get("/api/places/search?q=서울 카페&lat=37.5665&lng=126.9780&radius=50000")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["source"] in ("google", "mock")
    assert isinstance(data["places"], list)


def test_places_search_falls_back_to_mock_without_key(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    r = client.get("/api/places/search?q=독서모임")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["source"] == "mock"
    assert len(data["places"]) > 0


def test_saved_place_crud_and_reviews(client):
    suffix = uuid.uuid4().hex[:8]
    place_payload = {
        "user_id": "user_demo",
        "place_id": "rp_test_" + suffix,
        "google_place_id": "google_test_" + suffix,
        "name": "LUMA 테스트 독서 카페",
        "address": "서울시 테스트구 테스트로 1",
        "lat": 37.5665,
        "lng": 126.9780,
        "reading_score": 8.4,
        "meeting_capacity": 6,
        "noise_level": "quiet",
        "outlet_score": 4,
        "wifi_score": 5,
        "memo": "테스트 저장 장소",
        "place_types": ["cafe", "book_store"],
    }

    created = client.post("/api/places/save", json=place_payload)
    assert created.status_code in (200, 201)
    created_data = created.get_json()
    assert created_data["ok"] is True
    place_id = created_data["place"]["place_id"]

    listed = client.get("/api/places/saved?user_id=user_demo")
    assert listed.status_code == 200
    listed_data = listed.get_json()
    assert listed_data["ok"] is True
    assert any(p["place_id"] == place_id for p in listed_data["places"])

    updated = client.put(
        "/api/places/" + place_id,
        json={
            "user_id": "user_demo",
            "reading_score": 9.1,
            "meeting_capacity": 8,
            "memo": "수정된 테스트 메모",
        },
    )
    assert updated.status_code == 200
    updated_data = updated.get_json()
    assert updated_data["ok"] is True
    assert float(updated_data["place"]["reading_score"]) == 9.1

    review = client.post(
        "/api/places/" + place_id + "/review",
        json={
            "user_id": "user_demo",
            "display_name": "테스터",
            "rating": 5,
            "noise_level": "quiet",
            "group_size": 4,
            "visit_purpose": "offline_reading",
            "content": "조용하고 모임하기 좋았습니다.",
        },
    )
    assert review.status_code == 200
    assert review.get_json()["ok"] is True

    reviews = client.get("/api/places/" + place_id + "/reviews")
    assert reviews.status_code == 200
    reviews_data = reviews.get_json()
    assert reviews_data["ok"] is True
    assert any(r["content"] == "조용하고 모임하기 좋았습니다." for r in reviews_data["reviews"])

    deleted = client.delete("/api/places/" + place_id + "?user_id=user_demo")
    assert deleted.status_code == 200
    assert deleted.get_json()["ok"] is True
