"""Lounge book recommendation pipeline and API response contract.

Query contract for GET /api/v2/lounge/books/recommend:
- emotion: calm | growth | lonely | curious | warm
- persona: MBTI-like code, e.g. INFJ
- field: literature | philosophy | science | history | humanities | psychology
- mode: classic | new | fresh
- sort: score | rating | reviews | recent | shuffle
- limit: handled by the route, clamped to 1..40

The response always contains at least {"ok": bool, "books": list}.
"""
from __future__ import annotations

import hashlib
from datetime import date
from functools import lru_cache

from app.services.book_deduplicator_service import dedupe_books
from app.services.book_normalizer_service import normalize_book
from app.services.book_scoring_service import score_book
from app.services.book_seed_service import get_seed_books
from app.services.book_tagger_service import normalize_field, tag_book


FILTER_CONTRACT = {
    "emotion": ["", "calm", "growth", "lonely", "curious", "warm"],
    "field": ["", "literature", "philosophy", "science", "history", "humanities", "psychology", "art", "business", "self", "sf", "mystery", "essay"],
    "mode": ["", "classic", "new", "fresh"],
    "sort": ["score", "rating", "reviews", "recent", "shuffle"],
    "limit": {"min": 1, "max": 40, "default": 20},
}

LOCAL_BOOK_IMAGES = [
    "/asset/images/책/BOOK.jpg",
    "/asset/images/책/BOOK (2).jpg",
    "/asset/images/책/BOOK (3).jpg",
    "/asset/images/책/BOOK (4).jpg",
    "/asset/images/책/BOOK (5).jpg",
    "/asset/images/책/BOOK STORE.jpg",
    "/asset/images/책/BOOK STORE (2).jpg",
    "/asset/images/책/MEETING.jpg",
]


def _local_book_cover(book: dict) -> str:
    key = f"{book.get('title', '')}|{book.get('author', '')}|{book.get('book_id', '')}"
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return LOCAL_BOOK_IMAGES[int(digest[:8], 16) % len(LOCAL_BOOK_IMAGES)]

FIELD_QUERY = {
    "문학": ["문학 고전", "한국 소설", "세계 문학"],
    "철학": ["철학 입문", "실존주의 문학", "사유 고전"],
    "과학": ["교양 과학", "우주 과학", "과학 에세이"],
    "역사": ["역사 교양", "문명 역사", "인류 역사"],
    "인문": ["인문 교양", "사회 인문", "생각하는 책"],
    "심리": ["심리학", "마음 치유", "상담 심리"],
    "자기계발": ["성장 에세이", "자기 발견", "습관"],
    "예술": ["예술 에세이", "미술 교양", "음악 이야기"],
    "경제경영": ["경제 경영", "비즈니스 전략", "투자 교양"],
    "SF": ["SF 과학소설", "미래 소설", "상상력 소설"],
    "미스터리": ["미스터리 소설", "추리 소설", "스릴러 소설"],
    "에세이": ["시집 추천", "에세이 추천", "감성 에세이"],
}

EMOTION_QUERY = {
    "calm": ["위로가 되는 책", "평온한 에세이", "사색 문학"],
    "growth": ["성장 소설", "자기 발견 책", "용기를 주는 책"],
    "lonely": ["고독과 관계", "외로움 위로 책", "상실 회복 책"],
    "curious": ["지적 호기심", "교양 인문", "질문하는 책"],
    "warm": ["따뜻한 소설", "가족 이야기", "관계 회복 책"],
}

FIELD_QUERY = {
    "문학": ["한국 소설 추천", "세계문학 추천", "문학 베스트셀러"],
    "철학": ["철학 입문 추천", "사유하는 책", "인문 철학 추천"],
    "과학": ["교양 과학 추천", "우주 과학 책", "과학 베스트셀러"],
    "역사": ["역사 교양 추천", "세계사 추천", "문명 역사 책"],
    "인문": ["인문 교양 추천", "생각하는 책", "사회 인문 추천"],
    "심리": ["심리학 책 추천", "마음 치유 책", "상담 심리 책"],
    "자기계발": ["성장 에세이", "자기계발 신간", "습관 책 추천"],
    "예술": ["예술 에세이", "미술 교양 책", "음악 이야기 책"],
    "경제경영": ["경제 경영 베스트셀러", "비즈니스 전략 책", "투자 교양 책"],
    "SF": ["SF 소설 추천", "미래 소설 추천", "과학소설 베스트셀러"],
    "미스터리": ["미스터리 소설 추천", "추리 소설 베스트셀러", "스릴러 소설"],
    "에세이": ["에세이 추천", "감성 에세이", "한국 에세이 신간"],
}

EMOTION_QUERY = {
    "calm": ["위로가 되는 책", "평온한 에세이", "사색 문학"],
    "growth": ["성장 소설", "자기 발견 책", "용기를 주는 책"],
    "lonely": ["고독과 관계 책", "외로움 위로 책", "상실 회복 책"],
    "curious": ["지적 호기심 책", "교양 인문 추천", "질문하는 책"],
    "warm": ["따뜻한 소설", "가족 이야기 책", "관계 회복 책"],
}

NEW_BOOK_QUERIES = [
    "2026 신간",
    "2026 신간 도서",
    "2026 에세이",
    "문학 신간",
    "에세이 신간",
]


def recommend_books(filters: dict | None = None, limit: int = 20) -> dict:
    filters = _normalize_filters(filters or {})
    limit = _clamp_limit(limit)

    try:
        provider_candidates = []
        provider_limit = max(5, min(8, limit))
        for query in _queries_for(filters):
            provider_candidates.extend(_provider_books(query, provider_limit))

        seed_candidates = _seed_books_with_enriched_covers()
        if filters.get("mode") in {"new", "fresh"}:
            candidates = provider_candidates
        elif filters.get("mode") == "classic":
            candidates = [*seed_candidates, *provider_candidates]
        else:
            candidates = [*provider_candidates, *seed_candidates]

        normalized = [normalize_book(book, book.get("source", "")) for book in candidates]
        unique = dedupe_books(normalized)
        tagged = [tag_book(book, filters) for book in unique]
        scored = [score_book(book, filters) for book in tagged]
        if filters.get("mode") in {"new", "fresh"}:
            recent_scored = [book for book in scored if _is_recent_book(book) and _is_lounge_bookish(book)]
            provider_scored = [book for book in scored if book.get("source") != "seed"]
            scored = recent_scored or provider_scored or scored
        scored = _sort_books(scored, filters)
        scored = _dedupe_display_books(scored)
        books = [shape_lounge_book(book) for book in scored[:limit]]
        return response_contract(
            ok=True,
            books=books,
            filters=filters,
            count=len(books),
            meta={
                "source": "lounge_pipeline",
                "pipeline": ["seed", "providers", "normalize", "dedupe", "tag", "score"],
                "contract_version": "2026-05-18",
                "fallback_ready": True,
            },
        )
    except Exception as exc:
        fallback_books = []
        try:
            fallback_books = [
                shape_lounge_book(score_book(tag_book(normalize_book(book, book.get("source", "seed")), filters), filters))
                for book in get_seed_books()
            ][:limit]
        except Exception:
            fallback_books = []
        return response_contract(
            ok=True,
            books=fallback_books,
            filters=filters,
            count=len(fallback_books),
            error=str(exc),
            meta={
                "source": "lounge_pipeline_fallback",
                "pipeline": ["seed", "providers", "normalize", "dedupe", "tag", "score"],
                "contract_version": "2026-05-18",
                "fallback_ready": True,
            },
        )


def response_contract(
    ok: bool,
    books: list[dict] | None = None,
    filters: dict | None = None,
    count: int | None = None,
    meta: dict | None = None,
    error: str = "",
) -> dict:
    payload = {
        "ok": bool(ok),
        "books": books or [],
    }
    payload["count"] = len(payload["books"]) if count is None else int(count)
    payload["filters"] = filters or _normalize_filters({})
    payload["meta"] = meta or {
        "source": "lounge_pipeline",
        "contract_version": "2026-05-18",
        "fallback_ready": True,
    }
    if error:
        payload["error"] = error
    return payload


def get_recommendation_detail(book_id: str) -> dict:
    result = recommend_books({}, 40)
    for book in result["books"]:
        if book.get("book_id") == book_id or book.get("isbn") == book_id:
            return {"ok": True, "book": book, "source": "lounge_pipeline"}
    return {"ok": False, "error": "책을 찾을 수 없습니다.", "source": "lounge_pipeline"}


def shape_lounge_book(book: dict) -> dict:
    fallback = book.get("fallback_cover") or {}
    if not fallback:
        fallback = normalize_book(book, book.get("source", "")).get("fallback_cover", {})
    cover_url = book.get("cover_url", "") or _local_book_cover(book)
    cover_candidates = _cover_candidates_for_response(book, cover_url)
    return {
        "book_id": book.get("book_id", ""),
        "isbn10": book.get("isbn10", ""),
        "isbn13": book.get("isbn13", ""),
        "isbn": book.get("isbn", ""),
        "title": book.get("title", "제목 없음"),
        "author": book.get("author", "저자 미상"),
        "publisher": book.get("publisher", ""),
        "published_date": book.get("published_date", ""),
        "cover_url": cover_url,
        "thumbnail": book.get("thumbnail") or cover_url,
        "thumbnail_url": book.get("thumbnail_url") or cover_url,
        "cover_url_candidates": cover_candidates,
        "fallback_cover": {
            "title": fallback.get("title") or book.get("title", "책"),
            "initial": fallback.get("initial") or "책",
            "theme": fallback.get("theme") or "classic",
            "label": fallback.get("label") or book.get("category", ""),
            "background": fallback.get("background") or "#173127",
            "accent": fallback.get("accent") or "#C17F3B",
            "source_url": fallback.get("source_url") or book.get("source_url", ""),
        },
        "initial": book.get("initial") or fallback.get("initial", "책"),
        "theme": book.get("theme") or fallback.get("theme", "classic"),
        "description": book.get("description", ""),
        "summary": book.get("summary") or book.get("description", ""),
        "category": book.get("category", ""),
        "genre": book.get("genre", book.get("category", "")),
        "sub_category": book.get("sub_category", ""),
        "rating": book.get("rating", 0),
        "review_count": book.get("review_count", 0),
        "tags": book.get("tags", []),
        "scores": book.get("scores", {}),
        "luma_score": book.get("luma_score", 0),
        "recommend_reason": book.get("recommend_reason", ""),
        "reason": book.get("recommend_reason", ""),
        "source": book.get("source", "local"),
        "source_url": book.get("source_url", ""),
        "external_url": book.get("external_url", ""),
        "total_pages": book.get("total_pages", 0),
    }


def _cover_candidates_for_response(book: dict, cover_url: str) -> list[str]:
    candidates = book.get("cover_url_candidates") or []
    if not isinstance(candidates, list):
        candidates = []
    values = [cover_url, book.get("thumbnail_url"), book.get("thumbnail"), *candidates]
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        url = str(value or "").strip()
        if url and url not in seen:
            seen.add(url)
            result.append(url)
    return result


def _seed_books_with_enriched_covers() -> list[dict]:
    books = get_seed_books()
    for book in books:
        cover_url = str(book.get("cover_url") or "")
        if cover_url and not _is_low_confidence_cover(cover_url):
            continue
        enriched = _lookup_provider_cover(book.get("isbn13") or book.get("isbn") or book.get("title") or "")
        if not enriched and book.get("title"):
            enriched = _lookup_provider_cover(book.get("title", ""))
        if enriched:
            book["cover_url"] = enriched
            book["thumbnail"] = enriched
            book["thumbnail_url"] = enriched
    return books


def _is_low_confidence_cover(url: str) -> bool:
    text = str(url or "").lower()
    return "covers.openlibrary.org" in text


@lru_cache(maxsize=128)
def _lookup_provider_cover(query: str) -> str:
    query = str(query or "").strip()
    if not query:
        return ""
    try:
        from app.services.shelf_service import search_books_google, search_books_naver

        for provider in (search_books_naver, search_books_google):
            for book in provider(query, 3):
                url = (
                    book.get("cover_url")
                    or book.get("thumbnail_url")
                    or book.get("thumbnail")
                    or book.get("image")
                    or ""
                )
                if url and not _is_low_confidence_cover(url):
                    return str(url)
    except Exception:
        return ""
    return ""


def _normalize_filters(filters: dict) -> dict:
    emotion = str(filters.get("emotion") or "").strip().lower()
    mode = str(filters.get("mode") or "").strip().lower()
    sort = str(filters.get("sort") or "score").strip().lower()
    return {
        "emotion": emotion if emotion in FILTER_CONTRACT["emotion"] else "",
        "persona": str(filters.get("persona") or "").strip().upper(),
        "field": normalize_field(str(filters.get("field") or "").strip()),
        "mode": mode if mode in FILTER_CONTRACT["mode"] else "",
        "sort": sort if sort in FILTER_CONTRACT["sort"] else "score",
    }


def _clamp_limit(limit: int | str | None) -> int:
    try:
        value = int(limit or FILTER_CONTRACT["limit"]["default"])
    except (TypeError, ValueError):
        value = FILTER_CONTRACT["limit"]["default"]
    return max(FILTER_CONTRACT["limit"]["min"], min(value, FILTER_CONTRACT["limit"]["max"]))


def _sort_books(books: list[dict], filters: dict) -> list[dict]:
    sort = filters.get("sort") or "score"
    if sort == "rating":
        return sorted(
            books,
            key=lambda book: (
                _source_priority(book),
                float(book.get("rating") or 0),
                book.get("scores", {}).get("final", 0),
                int(book.get("review_count") or 0),
            ),
            reverse=True,
        )
    if sort == "reviews":
        return sorted(
            books,
            key=lambda book: (
                _source_priority(book),
                int(book.get("review_count") or 0),
                float(book.get("rating") or 0),
                book.get("scores", {}).get("final", 0),
            ),
            reverse=True,
        )
    if sort == "recent":
        return sorted(
            books,
            key=lambda book: (
                _published_year(book.get("published_date")),
                _source_priority(book),
                book.get("scores", {}).get("final", 0),
            ),
            reverse=True,
        )
    if sort == "shuffle":
        seed = "|".join(
            [
                filters.get("emotion", ""),
                filters.get("persona", ""),
                filters.get("field", ""),
                filters.get("mode", ""),
            ]
        )
        return sorted(books, key=lambda book: hash(f"{seed}|{book.get('book_id') or book.get('title')}"))
    return sorted(
        books,
        key=lambda book: (
            _source_priority(book),
            book.get("scores", {}).get("final", 0),
            int(book.get("review_count") or 0),
        ),
        reverse=True,
    )


def _source_priority(book: dict) -> int:
    source = str(book.get("source") or "").lower()
    if source in {"naver", "google"}:
        return 2
    if source == "local":
        return 1
    return 0


def _is_recent_book(book: dict) -> bool:
    year = _published_year(book.get("published_date"))
    if not year:
        return book.get("source") != "seed"
    return year >= date.today().year - 2


def _is_lounge_bookish(book: dict) -> bool:
    title = str(book.get("title") or "").lower()
    blocked = (
        "검정고시",
        "ncs",
        "한국어능력시험",
        "코레일",
        "기출",
        "모의고사",
        "공식기출",
        "단기기본서",
        "자격증",
        "수험서",
        "문항",
    )
    return not any(word.lower() in title for word in blocked)


def _dedupe_display_books(books: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for book in books:
        title = "".join(str(book.get("title") or "").lower().split())
        author = "".join(str(book.get("author") or "").lower().split())
        key = title if not author else f"{title}|{author}"
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(book)
    return result


def _published_year(value) -> int:
    text = str(value or "")
    digits = "".join(ch if ch.isdigit() else " " for ch in text).split()
    if not digits:
        return 0
    year = digits[0][:4]
    return int(year) if year.isdigit() else 0


def _queries_for(filters: dict) -> list[str]:
    queries: list[str] = []
    if filters.get("persona"):
        queries.extend(_persona_queries(filters["persona"]))
    if filters.get("field"):
        queries.extend(FIELD_QUERY.get(filters["field"], [filters["field"]]))
    if filters.get("emotion"):
        queries.extend(EMOTION_QUERY.get(filters["emotion"], [filters["emotion"]]))
    if filters.get("mode") == "classic":
        queries.extend(["고전 문학", "인문 고전"])
    elif filters.get("mode") in {"new", "fresh"}:
        queries.extend(["신간 에세이", "최근 출간 도서"])
    if not queries:
        queries = ["독서모임 추천", "문학 고전", "교양 인문"]
    return queries[:3]


def _persona_queries(persona: str) -> list[str]:
    persona = str(persona or "").upper()
    queries = [f"{persona} 추천 책"]
    if persona.startswith("IN"):
        queries.extend(["사색하는 사람을 위한 책", "인문 에세이 추천"])
    elif persona.startswith("EN"):
        queries.extend(["토론하기 좋은 책", "사회 인문 추천"])
    elif persona.startswith("IS"):
        queries.extend(["조용히 읽기 좋은 책", "깊이 읽는 소설"])
    else:
        queries.extend(["요즘 읽기 좋은 책", "독서모임 추천 도서"])
    return queries


def _queries_for(filters: dict) -> list[str]:
    queries: list[str] = []
    if filters.get("field"):
        queries.extend(FIELD_QUERY.get(filters["field"], [filters["field"]]))
    if filters.get("emotion"):
        queries.extend(EMOTION_QUERY.get(filters["emotion"], [filters["emotion"]]))
    if filters.get("mode") == "classic":
        queries.extend(["고전 문학", "인문 고전", "철학 고전"])
    elif filters.get("mode") in {"new", "fresh"}:
        queries.extend(NEW_BOOK_QUERIES)
    if not queries:
        queries = ["독서모임 추천 도서", "요즘 읽는 책", "베스트셀러 추천", "인문 교양 추천", "에세이 추천"]
    return queries[:3]


def _provider_books(query: str, limit: int) -> list[dict]:
    books: list[dict] = []
    try:
        from app.services.shelf_service import search_books_google, search_books_naver, search_books

        books.extend(search_books_naver(query, limit))
        books.extend(search_books_google(query, limit))
        books.extend(search_books(query, limit))
    except Exception:
        return []
    return books
