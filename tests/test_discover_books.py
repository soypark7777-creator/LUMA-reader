import requests


class FakeNaverResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "items": [
                {
                    "title": "<b>데미안</b>",
                    "author": "헤르만 <b>헤세</b>",
                    "image": "https://example.com/demian.jpg",
                    "description": "자기 자신에게 이르는 <b>성장</b> 소설",
                    "publisher": "민음사",
                    "pubdate": "20200101",
                    "isbn": "1234567890 9791190000001",
                    "link": "https://book.naver.com/bookdb/book_detail.naver?bid=1",
                }
            ]
        }


def test_search_books_naver_maps_and_cleans_fields(monkeypatch):
    from app.services.shelf_service import search_books_naver

    monkeypatch.setenv("NAVER_CLIENT_ID", "client-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeNaverResponse())

    books = search_books_naver("데미안", 5)

    assert len(books) == 1
    assert books[0]["title"] == "데미안"
    assert books[0]["author"] == "헤르만 헤세"
    assert books[0]["cover_url"] == "https://example.com/demian.jpg"
    assert books[0]["isbn"] == "9791190000001"
    assert books[0]["source"] == "naver"
    assert books[0]["published_date"] == "20200101"
    assert "<b>" not in books[0]["description"]


def test_books_search_route_uses_naver_source(client, monkeypatch):
    monkeypatch.setenv("NAVER_CLIENT_ID", "client-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeNaverResponse())

    response = client.get("/api/v2/books/search?q=데미안&source=naver&limit=3")
    data = response.get_json()

    assert response.status_code == 200
    assert data["ok"] is True
    assert data["source"] == "naver"
    assert data["books"][0]["title"] == "데미안"
    assert data["books"][0]["source"] == "naver"
    assert data["books"][0]["publisher"] == "민음사"
    assert data["books"][0]["external_url"].startswith("https://book.naver.com/")


def test_books_search_empty_query_returns_empty_list(client):
    response = client.get("/api/v2/books/search?q=&source=naver")
    data = response.get_json()

    assert response.status_code == 200
    assert data["ok"] is True
    assert data["books"] == []
