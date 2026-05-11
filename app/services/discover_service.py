"""
LUMA Discover Daily Magazine service.

Builds a deterministic daily book curation for the Discover/Lounge page.
External providers are allowed to fail silently; the API must always return
usable magazine data for the frontend.
"""
from __future__ import annotations

import random
from datetime import date
from typing import Iterable


DAILY_THEMES = [
    {
        "id": "growth",
        "title": "삶의 방향을 다시 묻는 책",
        "subtitle": "선택과 성장에 관한 이야기",
        "keywords": ["성장 소설", "자기 발견", "데미안", "인생 책"],
        "question": "나는 내가 선택한 삶을 살고 있을까?",
    },
    {
        "id": "comfort",
        "title": "마음이 조용히 쉬는 책",
        "subtitle": "위로와 회복이 필요한 날",
        "keywords": ["위로 에세이", "힐링 소설", "따뜻한 문장"],
        "question": "지금 나에게 필요한 다정함은 무엇일까?",
    },
    {
        "id": "outside_taste",
        "title": "내 취향 바깥의 한 권",
        "subtitle": "독서의 폭을 한 걸음 넓히기",
        "keywords": ["과학 에세이", "역사 교양", "철학 입문"],
        "question": "나는 어떤 세계를 아직 읽어보지 않았을까?",
    },
    {
        "id": "family_memory",
        "title": "가족과 기억을 따라가는 책",
        "subtitle": "세대, 관계, 상처에 관한 이야기",
        "keywords": ["가족 소설", "기억", "세대", "한국 소설"],
        "question": "내가 물려받은 이야기들은 무엇일까?",
    },
    {
        "id": "thinking",
        "title": "생각을 깊게 만드는 책",
        "subtitle": "질문이 오래 남는 인문/철학",
        "keywords": ["철학 입문", "인문 고전", "사유", "질문"],
        "question": "나는 어떤 질문을 오래 붙잡고 싶은가?",
    },
    {
        "id": "short_start",
        "title": "짧게 시작하기 좋은 책",
        "subtitle": "부담 없이 첫 장을 넘길 수 있는 책",
        "keywords": ["짧은 소설", "가벼운 에세이", "단편집"],
        "question": "오늘 20분만 읽는다면 어떤 책이 좋을까?",
    },
]

FALLBACK_BOOKS = [
    {
        "book_id": "fallback_demian",
        "title": "데미안",
        "author": "헤르만 헤세",
        "cover_emoji": "🌱",
        "description": "한 소년이 자기 안의 목소리를 따라 성장해가는 고전 소설입니다.",
        "publisher": "민음사",
        "published_date": "",
        "isbn": "",
        "source": "fallback",
    },
    {
        "book_id": "fallback_lab_girl",
        "title": "랩 걸",
        "author": "호프 자런",
        "cover_emoji": "🌿",
        "description": "식물학자의 삶과 연구를 통해 과학과 성장의 감각을 함께 전하는 에세이입니다.",
        "publisher": "",
        "published_date": "",
        "isbn": "",
        "source": "fallback",
    },
    {
        "book_id": "fallback_sapiens",
        "title": "사피엔스",
        "author": "유발 하라리",
        "cover_emoji": "🌳",
        "description": "인류의 역사를 거대한 시야에서 다시 바라보게 하는 인문 교양서입니다.",
        "publisher": "",
        "published_date": "",
        "isbn": "",
        "source": "fallback",
    },
    {
        "book_id": "fallback_little_prince",
        "title": "어린왕자",
        "author": "생텍쥐페리",
        "cover_emoji": "🌼",
        "description": "마음으로 보는 법과 관계의 의미를 다시 생각하게 하는 짧은 문학입니다.",
        "publisher": "",
        "published_date": "",
        "isbn": "",
        "source": "fallback",
    },
    {
        "book_id": "fallback_fish",
        "title": "물고기는 존재하지 않는다",
        "author": "룰루 밀러",
        "cover_emoji": "🍃",
        "description": "분류와 믿음이 무너지는 자리에서 삶을 다시 바라보게 하는 논픽션입니다.",
        "publisher": "",
        "published_date": "",
        "isbn": "",
        "source": "fallback",
    },
    {
        "book_id": "fallback_cosmos",
        "title": "코스모스",
        "author": "칼 세이건",
        "cover_emoji": "🌲",
        "description": "우주와 인간의 자리를 사려 깊은 언어로 연결하는 과학 고전입니다.",
        "publisher": "",
        "published_date": "",
        "isbn": "",
        "source": "fallback",
    },
]

_DISCOVER_CACHE: dict[str, dict] = {}


def _today() -> str:
    return date.today().isoformat()


def _rng(user_id: str, today: str) -> random.Random:
    return random.Random(f"{today}:{user_id}")


def _book_key(book: dict) -> str:
    isbn = str(book.get("isbn") or "").replace(" ", "").replace("-", "").lower()
    if isbn:
        return f"isbn:{isbn}"
    title = str(book.get("title") or "").strip().lower()
    author = str(book.get("author") or "").strip().lower()
    return f"text:{title}|{author}"


def _dedupe_books(books: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    result = []
    for book in books:
        key = _book_key(book)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(book)
    return result


def _trim_summary(text: str, limit: int = 170) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[:limit].rstrip() + "..."


def _theme_reason(theme: dict) -> str:
    by_id = {
        "growth": "오늘의 테마인 성장과 자기 발견에 연결해 읽기 좋은 책입니다.",
        "comfort": "조용한 위로가 필요한 날, 마음의 결을 부드럽게 만져주는 책입니다.",
        "outside_taste": "평소의 취향에서 한 걸음 벗어나 독서의 폭을 넓혀줄 책입니다.",
        "family_memory": "가족과 기억이라는 오래된 숲을 따라 읽기 좋은 책입니다.",
        "thinking": "질문을 오래 붙잡고 생각을 깊게 만드는 데 어울리는 책입니다.",
        "short_start": "오늘 짧게 시작해도 충분히 한 문장을 남길 수 있는 책입니다.",
    }
    return by_id.get(theme.get("id"), f"오늘의 테마인 '{theme.get('title', '독서')}'와 연결해 읽기 좋은 책입니다.")


def normalize_discover_book(book: dict, theme: dict) -> dict:
    description = book.get("description") or ""
    summary = _trim_summary(description) or f"이 책은 {theme.get('title', '오늘의 주제')}라는 오늘의 주제와 어울리는 책입니다."
    reason = book.get("reason") or _theme_reason(theme)
    return {
        "book_id": book.get("book_id") or book.get("isbn") or book.get("title", ""),
        "title": book.get("title", ""),
        "author": book.get("author", ""),
        "cover_url": book.get("cover_url", ""),
        "cover_emoji": book.get("cover_emoji", "🌱"),
        "summary": summary,
        "description": description,
        "reason": reason,
        "publisher": book.get("publisher", ""),
        "published_date": book.get("published_date", book.get("publishedDate", "")),
        "isbn": book.get("isbn", ""),
        "external_url": book.get("external_url", book.get("link", "")),
        "source": book.get("source", "local"),
        "question": theme.get("question", ""),
    }


def pick_daily_themes(user_id: str, today: str) -> list[dict]:
    rng = _rng(user_id, today)
    count = rng.randint(4, min(6, len(DAILY_THEMES)))
    return rng.sample(DAILY_THEMES, count)


def _search_theme_books(theme: dict, rng: random.Random) -> list[dict]:
    keyword = rng.choice(theme.get("keywords") or [theme.get("title", "책")])
    books: list[dict] = []
    try:
        from app.services.shelf_service import search_books_naver
        books.extend(search_books_naver(keyword, 10))
    except Exception:
        pass
    if len(books) < 4:
        try:
            from app.services.shelf_service import search_books_google
            books.extend(search_books_google(keyword, 10))
        except Exception:
            pass
    if len(books) < 4:
        try:
            from app.services.shelf_service import search_books
            books.extend(search_books(keyword, 10))
        except Exception:
            pass
    if not books:
        books = FALLBACK_BOOKS
    normalized = [normalize_discover_book(book, theme) for book in _dedupe_books(books)]
    return normalized[:10]


def build_hero_book(sections: list[dict]) -> dict:
    for section in sections:
        books = section.get("books") or []
        if books:
            hero = dict(books[0])
            hero["question"] = section.get("question", hero.get("question", ""))
            return hero
    return normalize_discover_book(FALLBACK_BOOKS[0], DAILY_THEMES[0])


def fallback_daily_discover(user_id: str) -> dict:
    today = _today()
    themes = pick_daily_themes(user_id, today)
    sections = []
    for idx, theme in enumerate(themes[:4]):
        books = [
            normalize_discover_book(FALLBACK_BOOKS[(idx + offset) % len(FALLBACK_BOOKS)], theme)
            for offset in range(4)
        ]
        sections.append({
            "id": theme["id"],
            "title": theme["title"],
            "subtitle": theme["subtitle"],
            "question": theme["question"],
            "books": books,
        })
    return {
        "ok": True,
        "date": today,
        "theme": "오늘 당신 안에 심어질 새로운 문장",
        "hero": build_hero_book(sections),
        "sections": sections,
        "source": "fallback",
    }


def get_daily_discover(user_id: str) -> dict:
    user_id = user_id or "user_demo"
    today = _today()
    cache_key = f"{today}:{user_id}"
    if cache_key in _DISCOVER_CACHE:
        return _DISCOVER_CACHE[cache_key]

    try:
        rng = _rng(user_id, today)
        sections = []
        for theme in pick_daily_themes(user_id, today):
            books = _search_theme_books(theme, rng)
            sections.append({
                "id": theme["id"],
                "title": theme["title"],
                "subtitle": theme["subtitle"],
                "question": theme["question"],
                "books": books,
            })

        used_only_fallback = all(
            all(book.get("source") == "fallback" for book in section.get("books", []))
            for section in sections
        )
        if not sections or not any(section.get("books") for section in sections) or used_only_fallback:
            result = fallback_daily_discover(user_id)
        else:
            result = {
                "ok": True,
                "date": today,
                "theme": "오늘 당신 안에 심어질 새로운 문장",
                "hero": build_hero_book(sections),
                "sections": sections,
                "source": "daily",
            }
    except Exception:
        result = fallback_daily_discover(user_id)

    _DISCOVER_CACHE[cache_key] = result
    return result
