"""
마음 서재 서비스
────────────────────────────────────────
기능:
  - 독서 감정 타임라인 기록 (날짜별 감정 태그)
  - 지식 별자리 그래프 데이터 생성
  - 월간 독서 리포트 자동 생성
  - AI 독서 성향 분석
"""
import uuid
from datetime import datetime, date
from typing import Optional
from collections import defaultdict

# ── 인메모리 저장소 ──────────────────────────────────────
_books: list[dict] = [
    {
        "book_id": "book_001", "user_id": "user_demo",
        "title": "사피엔스", "author": "유발 하라리",
        "cover_emoji": "📕", "genre": "역사/인류학",
        "status": "done", "progress": 100,
        "started_at": "2025-03-01", "finished_at": "2025-03-20",
        "total_pages": 636, "rating": 5,
    },
    {
        "book_id": "book_002", "user_id": "user_demo",
        "title": "어린왕자", "author": "생텍쥐페리",
        "cover_emoji": "📗", "genre": "문학",
        "status": "done", "progress": 100,
        "started_at": "2025-03-21", "finished_at": "2025-03-22",
        "total_pages": 120, "rating": 5,
    },
    {
        "book_id": "book_003", "user_id": "user_demo",
        "title": "코스모스", "author": "칼 세이건",
        "cover_emoji": "📘", "genre": "과학",
        "status": "reading", "progress": 62,
        "started_at": "2025-04-01", "finished_at": None,
        "total_pages": 758, "rating": None,
    },
]

_emotions: list[dict] = [
    # 감정 타입: inspired(영감) | curious(호기심) | sad(감동/슬픔) | surprised(놀람) | peaceful(평온)
    {"emotion_id": "em_001", "book_id": "book_001", "user_id": "user_demo",
     "date": "2025-03-05", "emotion": "curious", "intensity": 4,
     "note": "허구를 믿는 능력이 인류를 협력하게 했다는 개념이 충격적"},
    {"emotion_id": "em_002", "book_id": "book_001", "user_id": "user_demo",
     "date": "2025-03-12", "emotion": "inspired", "intensity": 5,
     "note": "역사를 이렇게 큰 그림으로 볼 수 있다는 것이 감동"},
    {"emotion_id": "em_003", "book_id": "book_001", "user_id": "user_demo",
     "date": "2025-03-20", "emotion": "surprised", "intensity": 4,
     "note": "현대 행복이 오히려 줄었다는 결론에 충격"},
    {"emotion_id": "em_004", "book_id": "book_002", "user_id": "user_demo",
     "date": "2025-03-21", "emotion": "sad", "intensity": 5,
     "note": "가장 중요한 것은 눈에 보이지 않아 — 읽는 내내 눈물"},
    {"emotion_id": "em_005", "book_id": "book_003", "user_id": "user_demo",
     "date": "2025-04-03", "emotion": "peaceful", "intensity": 4,
     "note": "우주의 광대함 앞에서 일상의 고민이 작아지는 느낌"},
]

_connections: list[dict] = [
    # 책들 사이의 지식 연결 (별자리 엣지)
    {"from": "book_001", "to": "book_002", "strength": 0.7,
     "theme": "허구와 상상력이 현실을 만든다",
     "note": "사피엔스의 '허구 믿기' ↔ 어린왕자의 '마음으로 보기'"},
    {"from": "book_001", "to": "book_003", "strength": 0.6,
     "theme": "인간이 우주에서 차지하는 위치",
     "note": "역사적 관점 ↔ 우주적 관점"},
    {"from": "book_002", "to": "book_003", "strength": 0.5,
     "theme": "별과 연결된 외로움",
     "note": "어린왕자의 별 ↔ 칼 세이건의 별"},
]


# ── 서재 (책 관리) ────────────────────────────────────────

def get_shelf(user_id: str) -> dict:
    """사용자 서재 전체 조회"""
    books = [b for b in _books if b["user_id"] == user_id]
    done    = [b for b in books if b["status"] == "done"]
    reading = [b for b in books if b["status"] == "reading"]
    want    = [b for b in books if b["status"] == "want"]
    return {
        "books": books,
        "stats": {
            "total": len(books),
            "done": len(done),
            "reading": len(reading),
            "want": len(want),
            "this_month": sum(1 for b in done if (b.get("finished_at") or "")[:7] == date.today().strftime("%Y-%m")),
        }
    }


def add_book(user_id: str, data: dict) -> dict:
    book = {
        "book_id":    f"book_{uuid.uuid4().hex[:6]}",
        "user_id":    user_id,
        "title":      data.get("title", "제목 없음"),
        "author":     data.get("author", ""),
        "cover_emoji":data.get("cover_emoji", "📚"),
        "genre":      data.get("genre", ""),
        "status":     data.get("status", "want"),
        "progress":   data.get("progress", 0),
        "started_at": data.get("started_at"),
        "finished_at":data.get("finished_at"),
        "total_pages":data.get("total_pages", 0),
        "rating":     data.get("rating"),
    }
    _books.append(book)
    return book


def update_book(book_id: str, data: dict) -> Optional[dict]:
    book = next((b for b in _books if b["book_id"] == book_id), None)
    if not book:
        return None
    for k, v in data.items():
        if k in book:
            book[k] = v
    if data.get("status") == "done" and not book.get("finished_at"):
        book["finished_at"] = date.today().isoformat()
        book["progress"] = 100
    return book


def delete_book(book_id: str) -> bool:
    global _books
    before = len(_books)
    _books = [b for b in _books if b["book_id"] != book_id]
    return len(_books) < before


# ── 감정 타임라인 ─────────────────────────────────────────

EMOTION_META = {
    "inspired":  {"label": "영감",   "emoji": "✨", "color": "#F2C94C"},
    "curious":   {"label": "호기심", "emoji": "🔍", "color": "#56CCF2"},
    "sad":       {"label": "감동",   "emoji": "💙", "color": "#2D9CDB"},
    "surprised": {"label": "놀람",   "emoji": "⚡", "color": "#BB6BD9"},
    "peaceful":  {"label": "평온",   "emoji": "🌿", "color": "#6FCF97"},
    "excited":   {"label": "흥분",   "emoji": "🔥", "color": "#EB5757"},
}

def add_emotion(user_id: str, data: dict) -> dict:
    em = {
        "emotion_id": f"em_{uuid.uuid4().hex[:6]}",
        "book_id":    data.get("book_id", ""),
        "user_id":    user_id,
        "date":       data.get("date", date.today().isoformat()),
        "emotion":    data.get("emotion", "inspired"),
        "intensity":  data.get("intensity", 3),   # 1~5
        "note":       data.get("note", ""),
    }
    _emotions.append(em)
    _auto_connect_books(data.get("book_id", ""), user_id)
    return em


def get_emotion_timeline(user_id: str, book_id: str = None) -> list[dict]:
    ems = [e for e in _emotions if e["user_id"] == user_id]
    if book_id:
        ems = [e for e in ems if e["book_id"] == book_id]
    # 책 정보 붙이기
    book_map = {b["book_id"]: b for b in _books}
    result = []
    for e in sorted(ems, key=lambda x: x["date"]):
        book = book_map.get(e["book_id"], {})
        meta = EMOTION_META.get(e["emotion"], {})
        result.append({
            **e,
            "book_title":  book.get("title", ""),
            "book_emoji":  book.get("cover_emoji", "📚"),
            "emotion_label": meta.get("label", e["emotion"]),
            "emotion_emoji": meta.get("emoji", ""),
            "emotion_color": meta.get("color", "#ccc"),
        })
    return result


def get_emotion_stats(user_id: str) -> dict:
    ems = [e for e in _emotions if e["user_id"] == user_id]
    counter = defaultdict(int)
    for e in ems:
        counter[e["emotion"]] += 1
    return {
        "total": len(ems),
        "by_emotion": [
            {**EMOTION_META.get(k, {"label": k, "emoji": "", "color": "#ccc"}),
             "type": k, "count": v}
            for k, v in sorted(counter.items(), key=lambda x: -x[1])
        ],
        "dominant": max(counter, key=counter.get) if counter else None,
    }


# ── 별자리 지식 그래프 ────────────────────────────────────

def get_constellation(user_id: str) -> dict:
    """D3.js용 노드·링크 데이터 반환"""
    books = [b for b in _books if b["user_id"] == user_id]
    book_ids = {b["book_id"] for b in books}

    # 감정 평균으로 노드 크기 결정
    book_emotion_map = defaultdict(list)
    for e in _emotions:
        if e["user_id"] == user_id:
            book_emotion_map[e["book_id"]].append(e["intensity"])

    nodes = []
    for b in books:
        intensities = book_emotion_map.get(b["book_id"], [3])
        avg_intensity = sum(intensities) / len(intensities)
        dominant_em = None
        counter = defaultdict(int)
        for e in _emotions:
            if e["book_id"] == b["book_id"] and e["user_id"] == user_id:
                counter[e["emotion"]] += 1
        if counter:
            dominant_em = max(counter, key=counter.get)
        meta = EMOTION_META.get(dominant_em, {"color": "#C17F3B", "emoji": "📚"})
        nodes.append({
            "id":      b["book_id"],
            "label":   b["title"],
            "author":  b["author"],
            "emoji":   b["cover_emoji"],
            "genre":   b["genre"],
            "status":  b["status"],
            "size":    8 + avg_intensity * 3,   # 감정 강도 → 노드 크기
            "color":   meta["color"],
            "emotion": dominant_em,
        })

    links = [
        {
            "source":   c["from"],
            "target":   c["to"],
            "strength": c["strength"],
            "theme":    c["theme"],
            "note":     c["note"],
        }
        for c in _connections
        if c["from"] in book_ids and c["to"] in book_ids
    ]

    return {"nodes": nodes, "links": links, "total_books": len(nodes), "total_links": len(links)}


def add_connection(data: dict) -> dict:
    conn = {
        "from":     data["from_book_id"],
        "to":       data["to_book_id"],
        "strength": data.get("strength", 0.5),
        "theme":    data.get("theme", ""),
        "note":     data.get("note", ""),
    }
    _connections.append(conn)
    return conn


def _auto_connect_books(book_id: str, user_id: str):
    """같은 사용자의 다른 책들과 자동 약한 연결 생성"""
    existing_pairs = {(c["from"], c["to"]) for c in _connections}
    user_books = [b["book_id"] for b in _books if b["user_id"] == user_id and b["book_id"] != book_id]
    for other in user_books:
        pair = (min(book_id, other), max(book_id, other))
        if pair not in existing_pairs:
            _connections.append({"from": pair[0], "to": pair[1], "strength": 0.2, "theme": "연결 탐색 중", "note": ""})


# ── 월간 리포트 ──────────────────────────────────────────

def get_monthly_report(user_id: str, year_month: str = None) -> dict:
    """year_month: '2025-04' 형식"""
    if not year_month:
        year_month = date.today().strftime("%Y-%m")

    done_this_month = [
        b for b in _books
        if b["user_id"] == user_id
        and b["status"] == "done"
        and (b.get("finished_at") or "")[:7] == year_month
    ]

    ems_this_month = [
        e for e in _emotions
        if e["user_id"] == user_id
        and e["date"][:7] == year_month
    ]

    # 감정 통계
    em_counter = defaultdict(int)
    for e in ems_this_month:
        em_counter[e["emotion"]] += 1

    # 장르 통계
    genre_counter = defaultdict(int)
    for b in done_this_month:
        genre_counter[b.get("genre", "기타")] += 1

    top_emotion = max(em_counter, key=em_counter.get) if em_counter else "inspired"
    top_meta    = EMOTION_META.get(top_emotion, {"label": "영감", "emoji": "✨"})

    # 키워드 수집
    keywords = []
    for e in ems_this_month:
        words = e.get("note", "").split()
        keywords.extend([w for w in words if len(w) >= 2])

    from collections import Counter
    kw_counter = Counter(keywords)
    top_keywords = [w for w, _ in kw_counter.most_common(5)]

    return {
        "year_month":    year_month,
        "books_read":    len(done_this_month),
        "books":         done_this_month,
        "emotions":      ems_this_month,
        "top_emotion":   {**top_meta, "type": top_emotion, "count": em_counter.get(top_emotion, 0)},
        "genre_dist":    [{"genre": k, "count": v} for k, v in genre_counter.items()],
        "top_keywords":  top_keywords,
        "total_pages":   sum(b.get("total_pages", 0) for b in done_this_month),
        "memo_count":    len(ems_this_month),
    }


# ── AI 독서 성향 분석 ────────────────────────────────────

def get_reading_persona(user_id: str) -> dict:
    """독서 패턴 기반 성향 분석"""
    from app.services.gemini_service import _call_gemini, _parse_json_safe

    books  = [b for b in _books if b["user_id"] == user_id]
    ems    = [e for e in _emotions if e["user_id"] == user_id]
    genres = defaultdict(int)
    for b in books:
        genres[b.get("genre", "기타")] += 1
    top_genres = sorted(genres.items(), key=lambda x: -x[1])[:3]
    notes = [e["note"] for e in ems if e.get("note")][:5]

    prompt = f"""독서 데이터를 분석해서 독서 성향을 알려주세요.

읽은 책: {[b['title'] for b in books]}
주요 장르: {top_genres}
감정 메모 샘플: {notes}

JSON 형식으로만 응답:
{{
  "persona_name": "성향 이름 (예: 철학적 탐험가)",
  "persona_emoji": "이모지",
  "description": "2문장 성향 설명",
  "strengths": ["강점1", "강점2", "강점3"],
  "recommend_genres": ["추천 장르1", "추천 장르2"],
  "next_book_hint": "다음에 읽으면 좋을 책 힌트"
}}"""

    raw    = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and "persona_name" in parsed:
        return {**parsed, "source": "gemini", "books_analyzed": len(books)}

    return {
        "persona_name":     "사색적 지식 탐험가",
        "persona_emoji":    "🔭",
        "description":      "다양한 분야를 넘나들며 깊이 사색하는 독자입니다. 단순히 정보를 수집하는 것이 아니라 책에서 삶의 의미를 찾습니다.",
        "strengths":        ["깊은 사색", "장르 다양성", "감정 공감"],
        "recommend_genres": ["철학", "과학 에세이"],
        "next_book_hint":   "인류와 우주의 연결을 다룬 책을 좋아하실 것 같아요",
        "source":           "mock",
        "books_analyzed":   len(books),
    }
