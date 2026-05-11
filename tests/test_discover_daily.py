from datetime import date


def _fake_book(title="가짜 책", isbn="9791190000001"):
    return {
        "book_id": isbn,
        "title": title,
        "author": "테스트 작가",
        "cover_url": "https://example.com/cover.jpg",
        "cover_emoji": "🌱",
        "description": "이 책은 테스트를 위해 준비된 설명입니다. 충분히 긴 설명으로 줄거리 카드에 표시될 수 있습니다.",
        "publisher": "테스트 출판사",
        "published_date": "20260509",
        "isbn": isbn,
        "external_url": "https://example.com/book",
        "source": "naver",
    }


def test_discover_today_route_returns_magazine(client):
    response = client.get("/api/v2/discover/today?user_id=user_demo")
    data = response.get_json()

    assert response.status_code == 200
    assert data["ok"] is True
    assert data["date"] == date.today().isoformat()
    assert "hero" in data
    assert "sections" in data
    assert len(data["sections"]) >= 3
    assert all(isinstance(section.get("books"), list) for section in data["sections"])


def test_discover_today_is_deterministic_for_same_user(client):
    first = client.get("/api/v2/discover/today?user_id=same_user").get_json()
    second = client.get("/api/v2/discover/today?user_id=same_user").get_json()

    assert first["hero"]["title"] == second["hero"]["title"]
    assert [s["id"] for s in first["sections"]] == [s["id"] for s in second["sections"]]


def test_discover_uses_naver_provider_when_available(client, monkeypatch):
    from app.services import discover_service

    discover_service._DISCOVER_CACHE.clear()
    monkeypatch.setattr(
        "app.services.shelf_service.search_books_naver",
        lambda query, limit=10: [_fake_book(f"네이버 {query}", "9791190000001")],
    )
    monkeypatch.setattr("app.services.shelf_service.search_books_google", lambda query, limit=10: [])
    monkeypatch.setattr("app.services.shelf_service.search_books", lambda query, limit=10: [])

    data = client.get("/api/v2/discover/today?user_id=naver_user").get_json()

    assert data["ok"] is True
    assert data["hero"]["source"] == "naver"
    assert data["hero"]["cover_url"] == "https://example.com/cover.jpg"
    assert data["hero"]["publisher"] == "테스트 출판사"
    assert data["hero"]["title"].startswith("네이버 ")


def test_discover_provider_failure_returns_fallback(client, monkeypatch):
    from app.services import discover_service

    discover_service._DISCOVER_CACHE.clear()

    def fail(*args, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr("app.services.shelf_service.search_books_naver", fail)
    monkeypatch.setattr("app.services.shelf_service.search_books_google", fail)
    monkeypatch.setattr("app.services.shelf_service.search_books", fail)

    data = client.get("/api/v2/discover/today?user_id=fallback_user").get_json()

    assert data["ok"] is True
    assert data["source"] == "fallback"
    assert data["hero"]["title"]
    assert len(data["sections"]) >= 3
