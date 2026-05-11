"""
도서 검색 서비스
Google Books API 연동 + 표지 이미지 고화질 추출
API 키 없으면 → 풍성한 Mock 데이터로 자동 폴백
"""
import os
import re
import requests
from typing import Optional

BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")
BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"

# ══════════════════════════════════════════════════════════════
#  Mock 도서 데이터 (API 키 없을 때)
# ══════════════════════════════════════════════════════════════
_MOCK_BOOKS: list[dict] = [
    {"book_id":"book-001","title":"사피엔스","subtitle":"유인원에서 사이보그까지, 인간 역사의 대담하고 위대한 질문","authors":["유발 하라리"],"publisher":"김영사","published_date":"2015","description":"10만 년 전 지구상에서 가장 보잘것없는 동물 중 하나였던 호모 사피엔스는 어떻게 먹이사슬의 최정상에 올라 지구의 지배자가 되었을까?","page_count":636,"genres":["역사","인류학","사회과학"],"language":"ko","cover_url":"https://covers.openlibrary.org/b/isbn/9788934972464-L.jpg","cover_url_s":"https://covers.openlibrary.org/b/isbn/9788934972464-S.jpg","isbn":"9788934972464","avg_rating":4.6,"ratings_count":12847},
    {"book_id":"book-002","title":"코스모스","subtitle":"Carl Sagan's Cosmos","authors":["칼 세이건"],"publisher":"사이언스북스","published_date":"2006","description":"우주와 인간의 관계에 대한 심오하고 아름다운 탐구. 천문학적 발견과 인류 문명의 역사를 넘나드는 지적 여정.","page_count":472,"genres":["과학","천문학","철학"],"language":"ko","cover_url":"https://covers.openlibrary.org/b/isbn/9788983710871-L.jpg","cover_url_s":"https://covers.openlibrary.org/b/isbn/9788983710871-S.jpg","isbn":"9788983710871","avg_rating":4.8,"ratings_count":9234},
    {"book_id":"book-003","title":"어린왕자","subtitle":"Le Petit Prince","authors":["앙투안 드 생텍쥐페리"],"publisher":"문학동네","published_date":"2015","description":"어느 날 사막에 불시착한 비행사가 만난 어린왕자. 세상에서 가장 아름다운 이야기.","page_count":120,"genres":["소설","우화","고전"],"language":"ko","cover_url":"https://covers.openlibrary.org/b/isbn/9788954622936-L.jpg","cover_url_s":"https://covers.openlibrary.org/b/isbn/9788954622936-S.jpg","isbn":"9788954622936","avg_rating":4.9,"ratings_count":45231},
    {"book_id":"book-004","title":"데미안","subtitle":"Emil Sinclairs Jugend","authors":["헤르만 헤세"],"publisher":"민음사","published_date":"2009","description":"새는 알을 깨고 나온다. 알은 세계다. 태어나려는 자는 하나의 세계를 파괴해야 한다.","page_count":230,"genres":["소설","성장","철학"],"language":"ko","cover_url":"https://covers.openlibrary.org/b/isbn/9788937460449-L.jpg","cover_url_s":"https://covers.openlibrary.org/b/isbn/9788937460449-S.jpg","isbn":"9788937460449","avg_rating":4.7,"ratings_count":23451},
    {"book_id":"book-005","title":"총균쇠","subtitle":"무기·병균·금속은 인류의 운명을 어떻게 바꿨는가","authors":["재러드 다이아몬드"],"publisher":"문학사상사","published_date":"2005","description":"왜 어떤 민족은 다른 민족을 지배하는가? 인류 불평등의 기원을 지리적·생태적 관점에서 분석.","page_count":726,"genres":["역사","지리학","사회과학"],"language":"ko","cover_url":"https://covers.openlibrary.org/b/isbn/9788970123547-L.jpg","cover_url_s":"https://covers.openlibrary.org/b/isbn/9788970123547-S.jpg","isbn":"9788970123547","avg_rating":4.5,"ratings_count":8923},
    {"book_id":"book-006","title":"1984","subtitle":"Nineteen Eighty-Four","authors":["조지 오웰"],"publisher":"민음사","published_date":"2003","description":"전체주의 사회의 공포와 빅브라더의 감시 아래 인간 자유의 의미를 묻는 디스토피아 소설.","page_count":408,"genres":["소설","SF","디스토피아"],"language":"ko","cover_url":"https://covers.openlibrary.org/b/isbn/9788937460777-L.jpg","cover_url_s":"https://covers.openlibrary.org/b/isbn/9788937460777-S.jpg","isbn":"9788937460777","avg_rating":4.7,"ratings_count":31245},
    {"book_id":"book-007","title":"파친코","subtitle":"Pachinko","authors":["이민진"],"publisher":"문학사상","published_date":"2022","description":"일제강점기부터 1980년대까지 재일 한국인 가족 4대의 이야기. 정체성과 생존의 서사시.","page_count":672,"genres":["소설","역사소설","가족"],"language":"ko","cover_url":"https://covers.openlibrary.org/b/isbn/9788974746926-L.jpg","cover_url_s":"https://covers.openlibrary.org/b/isbn/9788974746926-S.jpg","isbn":"9788974746926","avg_rating":4.8,"ratings_count":19867},
    {"book_id":"book-008","title":"페스트","subtitle":"La Peste","authors":["알베르 카뮈"],"publisher":"민음사","published_date":"2011","description":"전염병이 창궐한 알제리 오랑 시. 인간의 실존과 연대, 그리고 부조리에 맞서는 인간의 투쟁.","page_count":388,"genres":["소설","실존주의","고전"],"language":"ko","cover_url":"https://covers.openlibrary.org/b/isbn/9788937460388-L.jpg","cover_url_s":"https://covers.openlibrary.org/b/isbn/9788937460388-S.jpg","isbn":"9788937460388","avg_rating":4.6,"ratings_count":14532},
    {"book_id":"book-009","title":"멋진 신세계","subtitle":"Brave New World","authors":["올더스 헉슬리"],"publisher":"소담출판사","published_date":"2015","description":"과학기술로 완성된 유토피아가 실은 인간성을 말살하는 디스토피아라는 섬뜩한 예언.","page_count":342,"genres":["소설","SF","디스토피아"],"language":"ko","cover_url":"https://covers.openlibrary.org/b/isbn/9788958963462-L.jpg","cover_url_s":"https://covers.openlibrary.org/b/isbn/9788958963462-S.jpg","isbn":"9788958963462","avg_rating":4.4,"ratings_count":9876},
    {"book_id":"book-010","title":"죽음의 수용소에서","subtitle":"Man's Search for Meaning","authors":["빅터 프랭클"],"publisher":"청아출판사","published_date":"2020","description":"아우슈비츠 수용소에서 살아남은 정신과 의사가 발견한 삶의 의미.","page_count":264,"genres":["자기계발","심리학","회고록"],"language":"ko","cover_url":"https://covers.openlibrary.org/b/isbn/9788936408848-L.jpg","cover_url_s":"https://covers.openlibrary.org/b/isbn/9788936408848-S.jpg","isbn":"9788936408848","avg_rating":4.9,"ratings_count":27654},
]


# ══════════════════════════════════════════════════════════════
#  Google Books API 호출
# ══════════════════════════════════════════════════════════════
def _fetch_google_books(query: str, max_results: int = 10) -> list[dict]:
    """Google Books API로 도서 검색"""
    params = {
        "q":          query,
        "maxResults": min(max_results, 40),
        "langRestrict": "ko",
        "printType":  "books",
    }
    if BOOKS_API_KEY:
        params["key"] = BOOKS_API_KEY

    try:
        resp = requests.get(BOOKS_API_URL, params=params, timeout=5)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [_parse_google_book(item) for item in data.get("items", [])]
    except Exception:
        return []


def _parse_google_book(item: dict) -> dict:
    """Google Books 응답 파싱 → 표준 형식"""
    info    = item.get("volumeInfo", {})
    images  = info.get("imageLinks", {})

    # 표지 이미지 고화질 변환 (zoom 파라미터 조작)
    cover_raw = (images.get("thumbnail") or images.get("smallThumbnail") or "")
    cover_l   = cover_raw.replace("zoom=1", "zoom=3").replace("&edge=curl", "") if cover_raw else ""
    cover_s   = cover_raw.replace("zoom=1", "zoom=1").replace("&edge=curl", "") if cover_raw else ""

    isbn_list = [id_["identifier"] for id_ in info.get("industryIdentifiers", [])
                 if id_.get("type") == "ISBN_13"]
    isbn = isbn_list[0] if isbn_list else ""

    return {
        "book_id":        item.get("id", ""),
        "google_books_id":item.get("id", ""),
        "title":          info.get("title", "제목 없음"),
        "subtitle":       info.get("subtitle", ""),
        "authors":        info.get("authors", ["알 수 없음"]),
        "publisher":      info.get("publisher", ""),
        "published_date": info.get("publishedDate", ""),
        "description":    (info.get("description") or "")[:500],
        "page_count":     info.get("pageCount", 0),
        "genres":         info.get("categories", []),
        "language":       info.get("language", "ko"),
        "cover_url":      cover_l,
        "cover_url_s":    cover_s,
        "isbn":           isbn,
        "avg_rating":     info.get("averageRating", 0),
        "ratings_count":  info.get("ratingsCount", 0),
    }


# ══════════════════════════════════════════════════════════════
#  Mock 검색
# ══════════════════════════════════════════════════════════════
def _search_mock(query: str, limit: int = 10) -> list[dict]:
    """Mock 데이터에서 키워드 검색"""
    q = query.lower().strip()
    results = []
    for book in _MOCK_BOOKS:
        title   = book["title"].lower()
        authors = " ".join(book["authors"]).lower()
        genres  = " ".join(book["genres"]).lower()
        if q in title or q in authors or q in genres:
            results.append(book)
    if not results:
        # 완전 일치 없으면 전체 반환 (데모용)
        results = _MOCK_BOOKS[:limit]
    return results[:limit]


# ══════════════════════════════════════════════════════════════
#  공개 API
# ══════════════════════════════════════════════════════════════
def search_books(query: str, limit: int = 10) -> list[dict]:
    """
    도서 검색 메인 함수
    Google Books API → 실패 시 Mock 폴백
    """
    if not query.strip():
        return _MOCK_BOOKS[:limit]

    if BOOKS_API_KEY:
        results = _fetch_google_books(query, limit)
        if results:
            return results

    return _search_mock(query, limit)


def get_book_by_id(book_id: str) -> Optional[dict]:
    """단일 도서 상세 조회"""
    # Mock에서 먼저 확인
    mock = next((b for b in _MOCK_BOOKS if b["book_id"] == book_id), None)
    if mock:
        return mock

    # Google Books API
    if BOOKS_API_KEY or True:  # 공개 API라 키 없어도 됨
        try:
            resp = requests.get(f"{BOOKS_API_URL}/{book_id}", timeout=5)
            if resp.status_code == 200:
                return _parse_google_book(resp.json())
        except Exception:
            pass
    return None


def get_popular_books() -> list[dict]:
    """인기 도서 (홈화면용)"""
    return sorted(_MOCK_BOOKS, key=lambda b: -b["avg_rating"])[:6]


def get_book_status() -> dict:
    return {
        "google_books_api": bool(BOOKS_API_KEY),
        "mode": "google_books" if BOOKS_API_KEY else "mock",
        "mock_count": len(_MOCK_BOOKS),
    }
