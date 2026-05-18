"""
LUMA — MySQL 기반 통합 API 라우터 v2
──────────────────────────────────────────────────────
모든 엔드포인트가 MySQL ↔ Mock 자동 전환
"""
from datetime import date, datetime

from flask import Blueprint, request, jsonify, g

mysql_bp = Blueprint("mysql_api", __name__)


@mysql_bp.before_request
def _reject_bad_bearer_token():
    """Bearer 토큰이 명시된 요청은 만료/오염 여부를 먼저 검증한다."""
    open_paths = (
        "/auth/login",
        "/auth/register",
        "/auth/refresh",
        "/system/status",
        "/system/init-db",
    )
    if request.path.endswith(open_paths):
        return None

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None

    from app.services.user_service import token_status
    status, payload = token_status(auth[7:].strip())
    if status == "expired":
        return jsonify({"ok": False, "error": "토큰이 만료되었습니다."}), 401
    if status != "ok" or not payload:
        return jsonify({"ok": False, "error": "유효하지 않은 토큰입니다."}), 401

    g.user_id = payload.get("user_id", "user_demo")
    g.token_payload = payload
    return None


# ── 인증 헬퍼 ────────────────────────────────────────────
def _get_uid() -> str:
    """Authorization 헤더 또는 query param에서 user_id 추출"""
    if getattr(g, "user_id", None):
        return g.user_id
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.services.user_service import verify_token
            payload = verify_token(auth[7:])
            if payload:
                return payload.get("user_id", "user_demo")
        except Exception:
            pass
    return request.args.get("user_id") or (request.get_json(silent=True) or {}).get("user_id", "user_demo")


def _json(data: dict, status: int = 200):
    return jsonify(data), status


# ══════════════════════════════════════════════════════
#  인증 API  /api/v2/auth/*
# ══════════════════════════════════════════════════════

@mysql_bp.route("/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json() or {}
    from app.services.user_service import register
    result = register(data)
    return _json(result, 201 if result.get("ok") else 400)


@mysql_bp.route("/auth/login", methods=["POST"])
def auth_login():
    data     = request.get_json() or {}
    email    = data.get("email","")
    password = data.get("password","")
    from app.services.user_service import login
    result = login(email, password)
    return _json(result, 200 if result.get("ok") else 401)


@mysql_bp.route("/auth/refresh", methods=["POST"])
def auth_refresh():
    data = request.get_json() or {}
    token = data.get("token", "")
    if not token:
        auth = request.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.startswith("Bearer ") else ""
    from app.services.user_service import refresh_token
    result = refresh_token(token)
    return _json(result, 200 if result.get("ok") else 401)


@mysql_bp.route("/auth/me", methods=["GET"])
def auth_me():
    uid = _get_uid()
    from app.services.user_service import get_me
    user = get_me(uid)
    if not user:
        return _json({"ok": False, "error": "사용자 없음"}, 404)
    return _json({"ok": True, "user": user})


@mysql_bp.route("/auth/profile", methods=["PUT"])
def auth_update_profile():
    uid  = _get_uid()
    data = request.get_json() or {}
    from app.services.user_service import update_profile
    return _json(update_profile(uid, data))


@mysql_bp.route("/auth/stats", methods=["GET"])
def auth_stats():
    uid = _get_uid()
    from app.services.user_service import get_user_stats
    return _json({"ok": True, **get_user_stats(uid)})


# Profile universe API /api/v2/profile/*
@mysql_bp.route("/profile/summary", methods=["GET"])
def profile_summary():
    from app.services.profile_service import get_summary
    return _json(get_summary(_get_uid()))


@mysql_bp.route("/profile/current-reading", methods=["GET"])
def profile_current_reading():
    from app.services.profile_service import get_current_reading
    return _json(get_current_reading(_get_uid()))


@mysql_bp.route("/profile/constellation", methods=["GET"])
def profile_constellation():
    from app.services.profile_service import get_constellation
    return _json(get_constellation(_get_uid()))


@mysql_bp.route("/profile/sentences", methods=["GET"])
def profile_sentences():
    from app.services.profile_service import get_sentences
    return _json(get_sentences(_get_uid()))


@mysql_bp.route("/profile/timeline", methods=["GET"])
def profile_timeline():
    from app.services.profile_service import get_timeline
    return _json(get_timeline(_get_uid()))


@mysql_bp.route("/profile/questions", methods=["GET"])
def profile_questions():
    from app.services.profile_service import get_questions
    return _json(get_questions(_get_uid()))


@mysql_bp.route("/profile/persona", methods=["GET"])
def profile_persona():
    from app.services.profile_service import get_persona
    return _json(get_persona(_get_uid()))


@mysql_bp.route("/profile/lounges", methods=["GET"])
def profile_lounges():
    from app.services.profile_service import get_lounges
    return _json(get_lounges(_get_uid()))


@mysql_bp.route("/profile/similar-readers", methods=["GET"])
def profile_similar_readers():
    from app.services.profile_service import get_similar_readers
    return _json(get_similar_readers(_get_uid()))


# ══════════════════════════════════════════════════════
#  책 탐색  /api/v2/books/*
# ══════════════════════════════════════════════════════

def _discover_book_shape(book: dict, reason: str = "") -> dict:
    return {
        "book_id": book.get("book_id") or book.get("isbn") or book.get("title", ""),
        "title": book.get("title", ""),
        "author": book.get("author", ""),
        "cover_url": book.get("cover_url", ""),
        "cover_emoji": book.get("cover_emoji", "📚"),
        "category": book.get("genre", book.get("category", "")),
        "genre": book.get("genre", book.get("category", "")),
        "rating": book.get("rating", 4.5),
        "review_count": book.get("review_count", book.get("ratingsCount", book.get("saved_count", 0))),
        "source": book.get("source", "local"),
        "reason": book.get("reason", reason),
        "saved": bool(book.get("saved", False)),
        "reading_status": book.get("status", "want"),
        "total_pages": book.get("total_pages", 0),
        "description": book.get("description", ""),
        "isbn": book.get("isbn", ""),
        "publisher": book.get("publisher", ""),
        "published_date": book.get("published_date", book.get("publishedDate", "")),
        "external_url": book.get("external_url", book.get("link", "")),
    }


def _parse_book_date(value) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    formats = ("%Y%m%d", "%Y-%m-%d", "%Y-%m", "%Y")
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _sort_discover_books(books: list[dict], sort: str) -> list[dict]:
    sort = (sort or "").strip().lower()
    today = datetime.combine(date.today(), datetime.min.time())

    def recent_key(book: dict):
        parsed = _parse_book_date(book.get("published_date"))
        if not parsed:
            return (1, 999999)
        return (0, abs((today - parsed).days))

    if sort in {"rating", "score"}:
        return sorted(books, key=lambda b: (float(b.get("rating") or 0), int(b.get("review_count") or 0), bool(b.get("cover_url"))), reverse=True)
    if sort in {"reviews", "review_count"}:
        return sorted(books, key=lambda b: (int(b.get("review_count") or 0), float(b.get("rating") or 0), bool(b.get("cover_url"))), reverse=True)
    if sort == "cover":
        return sorted(books, key=lambda b: (bool(b.get("cover_url")), float(b.get("rating") or 0)), reverse=True)
    if sort in {"recent", "new", "published"}:
        return sorted(books, key=recent_key)
    return books


def _fallback_discover_books(query: str) -> list[dict]:
    """외부 도서 API가 비어 있을 때 /lounge가 빈 화면이 되지 않도록 쓰는 기본 큐레이션."""
    q = (query or "").lower()
    base = [
        {
            "book_id": "9780345539434",
            "title": "Cosmos",
            "author": "Carl Sagan",
            "cover_url": "https://covers.openlibrary.org/b/isbn/9780345539434-L.jpg",
            "cover_emoji": "🔭",
            "rating": 4.8,
            "review_count": 1840,
            "published_date": "20131210",
            "publisher": "Ballantine Books",
            "source": "fallback",
            "reason": "넓은 세계를 새롭게 열어주는 지식의 별입니다.",
        },
        {
            "book_id": "9780062316097",
            "title": "Sapiens",
            "author": "Yuval Noah Harari",
            "cover_url": "https://covers.openlibrary.org/b/isbn/9780062316097-L.jpg",
            "cover_emoji": "🧠",
            "rating": 4.7,
            "review_count": 2510,
            "published_date": "20150210",
            "publisher": "Harper",
            "source": "fallback",
            "reason": "많은 독자가 함께 이야기해온 인문 베스트셀러입니다.",
        },
        {
            "book_id": "9780451524935",
            "title": "1984",
            "author": "George Orwell",
            "cover_url": "https://covers.openlibrary.org/b/isbn/9780451524935-L.jpg",
            "cover_emoji": "👁",
            "rating": 4.7,
            "review_count": 2260,
            "published_date": "19500601",
            "publisher": "Signet Classic",
            "source": "fallback",
            "reason": "권력과 자유를 오래 생각하게 만드는 강한 이야기입니다.",
        },
        {
            "book_id": "9780143106784",
            "title": "Demian",
            "author": "Hermann Hesse",
            "cover_url": "https://covers.openlibrary.org/b/isbn/9780143106784-L.jpg",
            "cover_emoji": "🦋",
            "rating": 4.5,
            "review_count": 1180,
            "published_date": "20130129",
            "publisher": "Penguin Classics",
            "source": "fallback",
            "reason": "자기 발견과 성장의 감각을 깨우는 고전입니다.",
        },
        {
            "book_id": "9780316769488",
            "title": "The Catcher in the Rye",
            "author": "J. D. Salinger",
            "cover_url": "https://covers.openlibrary.org/b/isbn/9780316769488-L.jpg",
            "cover_emoji": "🌙",
            "rating": 4.4,
            "review_count": 1320,
            "published_date": "19910501",
            "publisher": "Little, Brown",
            "source": "fallback",
            "reason": "예민한 마음과 성장의 통과의례를 따라가는 소설입니다.",
        },
        {
            "book_id": "9780156012195",
            "title": "The Little Prince",
            "author": "Antoine de Saint-Exupery",
            "cover_url": "https://covers.openlibrary.org/b/isbn/9780156012195-L.jpg",
            "cover_emoji": "⭐",
            "rating": 4.8,
            "review_count": 2100,
            "published_date": "20000629",
            "publisher": "Mariner Books",
            "source": "fallback",
            "reason": "짧지만 오래 남는 질문을 남기는 책입니다.",
        },
    ]
    if any(word in q for word in ("베스트", "인기", "많이")):
        return sorted(base, key=lambda b: b["review_count"], reverse=True)
    if any(word in q for word in ("신간", "새", "최근")):
        return sorted(base, key=lambda b: b["published_date"], reverse=True)
    return base


def _book_dedupe_key(book: dict) -> str:
    isbn = str(book.get("isbn", "") or "").replace("-", "").replace(" ", "").strip().lower()
    if isbn:
        return f"isbn:{isbn}"
    title = str(book.get("title", "") or "").strip().lower()
    author = str(book.get("author", "") or "").strip().lower()
    return f"text:{title}|{author}"


def _dedupe_books(books: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for book in books:
        key = _book_dedupe_key(book)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(book)
    return unique


@mysql_bp.route("/books/search", methods=["GET"])
def books_search():
    query = request.args.get("q", "").strip()
    source = request.args.get("source", "all").strip().lower() or "all"
    sort = request.args.get("sort", "").strip().lower()
    limit = max(1, min(int(request.args.get("limit", "12")), 30))
    if not query:
        return _json({"ok": True, "books": [], "source": source})

    from app.services.shelf_service import search_books, search_books_google, search_books_naver

    if source == "google":
        books = search_books_google(query, limit)
    elif source == "naver":
        books = search_books_naver(query, limit) or search_books_google(query, limit) or search_books(query, limit)
    elif source == "local":
        books = search_books(query, limit)
    else:
        books = (
            search_books(query, limit)
            + search_books_naver(query, limit)
            + search_books_google(query, limit)
        )
    shaped = [_discover_book_shape(b) for b in _dedupe_books(books)]
    shaped = _sort_discover_books(shaped, sort)[:limit]
    if not shaped and source != "local":
        shaped = [_discover_book_shape(b) for b in search_books(query, limit)]
        shaped = _sort_discover_books(shaped, sort)[:limit]
    if not shaped and source != "local":
        shaped = _sort_discover_books([_discover_book_shape(b) for b in _fallback_discover_books(query)], sort)[:limit]
    return _json({"ok": True, "books": shaped, "source": source, "sort": sort})


@mysql_bp.route("/books/recommendations", methods=["GET"])
def books_recommendations():
    uid = _get_uid()
    sort = request.args.get("sort", "").strip().lower()
    from app.services.reading_service import auto_suggest_books
    result = auto_suggest_books(uid)
    books = [_discover_book_shape(b, "당신의 독서 패턴에서 자라난 추천입니다.") for b in result.get("books", [])]
    books = _sort_discover_books(books, sort)
    return _json({"ok": True, "books": books, "source": result.get("source", "mock")})


@mysql_bp.route("/books/popular", methods=["GET"])
def books_popular():
    limit = int(request.args.get("limit", "12"))
    if limit < 1:
        limit = 12
    try:
        from app.db import is_connected, execute_all
        if is_connected():
            rows = execute_all(
                """SELECT b.book_id,b.title,b.author,b.publisher,b.isbn,b.cover_emoji,
                          b.cover_url,b.genre,b.total_pages,b.description,
                          COUNT(sb.shelf_id) AS saved_count
                   FROM books b
                   LEFT JOIN shelf_books sb ON sb.book_id=b.book_id
                   GROUP BY b.book_id,b.title,b.author,b.publisher,b.isbn,b.cover_emoji,
                            b.cover_url,b.genre,b.total_pages,b.description
                   ORDER BY saved_count DESC, b.created_at DESC
                   LIMIT %s""",
                (limit,),
            )
            books = [dict(r) for r in rows]
        else:
            from app.services.shelf_service import _books_mem
            books = list(_books_mem)[:limit]
    except Exception:
        books = []
    return _json({"ok": True, "books": [_discover_book_shape(b, "많은 독자가 심고 있는 씨앗입니다.") for b in books]})


@mysql_bp.route("/books/recommend-by-emotion", methods=["GET"])
def books_recommend_by_emotion():
    uid = _get_uid()
    emotion = request.args.get("emotion", "").strip()
    from app.services.reading_service import auto_suggest_books
    result = auto_suggest_books(uid)
    reason = "지금의 감정에 맞춰 천천히 자라날 책입니다."
    if emotion:
        reason = f"{emotion}의 마음에 어울리는 생각의 씨앗입니다."
    return _json({
        "ok": True,
        "books": [_discover_book_shape(b, reason) for b in result.get("books", [])],
        "source": result.get("source", "mock"),
    })


@mysql_bp.route("/books/<book_id>", methods=["GET"])
def books_detail(book_id):
    try:
        from app.db import is_connected, execute_one
        if is_connected():
            row = execute_one(
                """SELECT book_id,title,author,publisher,isbn,cover_emoji,cover_url,
                          genre,total_pages,description
                   FROM books WHERE book_id=%s""",
                (book_id,),
            )
            if row:
                return _json({"ok": True, "book": _discover_book_shape(dict(row))})
        else:
            from app.services.shelf_service import _books_mem
            book = next((b for b in _books_mem if b.get("book_id") == book_id), None)
            if book:
                return _json({"ok": True, "book": _discover_book_shape(book)})
    except Exception:
        pass
    return _json({"ok": False, "error": "책을 찾을 수 없습니다."}, 404)


@mysql_bp.route("/discover/today", methods=["GET"])
def discover_today():
    uid = _get_uid()
    from app.services.discover_service import get_daily_discover
    return _json(get_daily_discover(uid))


# Deep Dive curation /api/v2/youtube, /api/v2/deepdive
@mysql_bp.route("/youtube/search", methods=["GET"])
def youtube_search():
    query = request.args.get("q", "").strip()
    try:
        limit = int(request.args.get("limit", "8") or 8)
    except ValueError:
        limit = 8
    from app.services.youtube_service import search_youtube_videos
    result = search_youtube_videos(query, limit)
    return _json(result, 200 if result.get("ok") else 400)


@mysql_bp.route("/deepdive/search", methods=["GET"])
def deepdive_search():
    query = request.args.get("q", "").strip()
    try:
        limit = int(request.args.get("limit", "8") or 8)
    except ValueError:
        limit = 8
    from app.services.deepdive_service import search_deepdive
    result = search_deepdive(query, _get_uid(), limit)
    return _json(result, 200 if result.get("ok") else 400)


@mysql_bp.route("/deepdive/save", methods=["POST"])
def deepdive_save():
    data = request.get_json() or {}
    from app.services.deepdive_service import save_deepdive_item
    result = save_deepdive_item(_get_uid(), data)
    return _json(result, 201 if result.get("ok") else 400)


# ══════════════════════════════════════════════════════
#  서재 API  /api/v2/shelf/*
# ══════════════════════════════════════════════════════

@mysql_bp.route("/shelf", methods=["GET"])
def shelf_list():
    uid = _get_uid()
    from app.services.shelf_service import get_shelf
    result = get_shelf(uid)
    if 'ok' not in result:
        result['ok'] = True
    return _json(result)


@mysql_bp.route("/shelf/books", methods=["POST"])
def shelf_add():
    uid  = _get_uid()
    data = request.get_json() or {}
    if not data.get("title","").strip():
        return _json({"ok": False, "error": "책 제목을 입력하세요."}, 400)
    from app.services.shelf_service import add_book
    result = add_book(uid, data)
    return _json(result, 201 if result.get("ok") else 400)


@mysql_bp.route("/shelf/books/<book_id>", methods=["PUT"])
def shelf_update(book_id):
    uid  = _get_uid()
    data = request.get_json() or {}
    from app.services.shelf_service import update_shelf_book
    return _json(update_shelf_book(book_id, uid, data))


@mysql_bp.route("/shelf/books/<book_id>", methods=["DELETE"])
def shelf_delete(book_id):
    uid = _get_uid()
    from app.services.shelf_service import delete_shelf_book
    return _json(delete_shelf_book(book_id, uid))


@mysql_bp.route("/shelf/search", methods=["GET"])
def shelf_search():
    query = request.args.get("q","").strip()
    limit = int(request.args.get("limit","10"))
    from app.services.shelf_service import search_books
    return _json({"ok": True, "books": search_books(query, limit)})


@mysql_bp.route("/shelf/books/search", methods=["GET"])
def shelf_books_search():
    query = request.args.get("q","").strip()
    source = request.args.get("source","local")
    limit = int(request.args.get("limit","5"))
    from app.services.shelf_service import search_books, search_books_google
    if source == "google":
        books = search_books_google(query, limit)
    elif source == "all":
        books = search_books(query, limit) + search_books_google(query, limit)
    else:
        books = search_books(query, limit)
    return _json({"ok": True, "books": books})


@mysql_bp.route("/shelf/books/<book_id>/progress", methods=["POST"])
def shelf_progress(book_id):
    uid = _get_uid()
    data = request.get_json() or {}
    from app.services.shelf_service import update_reading_progress
    return _json(update_reading_progress(book_id, uid, data.get("pages_read", 0)))


# ══════════════════════════════════════════════════════
#  감정 타임라인  /api/v2/emotions/*
# ══════════════════════════════════════════════════════

@mysql_bp.route("/emotions", methods=["POST"])
def emotion_add():
    uid  = _get_uid()
    data = request.get_json() or {}
    if not data.get("book_id"):
        return _json({"ok": False, "error": "book_id가 필요합니다."}, 400)
    from app.services.reading_service import add_emotion
    result = add_emotion(uid, data)
    return _json(result, 201 if result.get("ok") else 400)


@mysql_bp.route("/emotions", methods=["GET"])
def emotion_list():
    uid     = _get_uid()
    book_id = request.args.get("book_id")
    from app.services.reading_service import get_emotion_timeline
    return _json(get_emotion_timeline(uid, book_id))


@mysql_bp.route("/emotions/<emotion_id>", methods=["PUT"])
def emotion_update(emotion_id):
    uid = _get_uid()
    data = request.get_json() or {}
    from app.services.reading_service import update_emotion
    result = update_emotion(uid, emotion_id, data)
    return _json(result, 200 if result.get("ok") else 404)


@mysql_bp.route("/emotions/<emotion_id>", methods=["DELETE"])
def emotion_delete(emotion_id):
    uid = _get_uid()
    from app.services.reading_service import delete_emotion
    result = delete_emotion(uid, emotion_id)
    return _json(result, 200 if result.get("ok") else 404)


# ══════════════════════════════════════════════════════
#  별자리  /api/v2/constellation/*
# ══════════════════════════════════════════════════════

@mysql_bp.route("/constellation", methods=["GET"])
def constellation_get():
    uid = _get_uid()
    from app.services.reading_service import get_constellation
    return _json(get_constellation(uid))


@mysql_bp.route("/constellation/connect", methods=["POST"])
def constellation_connect():
    uid  = _get_uid()
    data = request.get_json() or {}
    if not (data.get("from_book_id") and data.get("to_book_id")):
        return _json({"ok": False, "error": "from_book_id, to_book_id 필요"}, 400)
    from app.services.reading_service import add_connection
    return _json(add_connection(uid, data))


@mysql_bp.route("/constellation/suggestions", methods=["GET"])
def constellation_suggestions():
    uid = _get_uid()
    from app.services.reading_service import auto_suggest_books
    return _json(auto_suggest_books(uid))


# ══════════════════════════════════════════════════════
#  메모  /api/v2/memos/*
# ══════════════════════════════════════════════════════

@mysql_bp.route("/memos", methods=["POST"])
def memo_save():
    uid  = _get_uid()
    data = request.get_json() or {}
    if not data.get("content","").strip():
        return _json({"ok": False, "error": "메모 내용이 없습니다."}, 400)
    from app.services.reading_service import save_memo
    result = save_memo(uid, data)
    return _json(result, 201 if result.get("ok") else 400)


@mysql_bp.route("/memos", methods=["GET"])
def memo_list():
    uid     = _get_uid()
    book_id = request.args.get("book_id")
    limit   = int(request.args.get("limit","20"))
    from app.services.reading_service import list_memos
    return _json(list_memos(uid, book_id, limit))


@mysql_bp.route("/memos/<memo_id>", methods=["PUT"])
def memo_update(memo_id):
    uid = _get_uid()
    data = request.get_json() or {}
    from app.services.reading_service import update_memo
    result = update_memo(uid, memo_id, data)
    return _json(result, 200 if result.get("ok") else 404)


@mysql_bp.route("/memos/<memo_id>", methods=["DELETE"])
def memo_delete(memo_id):
    uid = _get_uid()
    from app.services.reading_service import delete_memo
    result = delete_memo(uid, memo_id)
    return _json(result, 200 if result.get("ok") else 404)


@mysql_bp.route("/memos/stats", methods=["GET"])
def memo_stats():
    uid = _get_uid()
    from app.services.reading_service import get_memo_stats
    return _json(get_memo_stats(uid))


# ══════════════════════════════════════════════════════
#  리포트 & 성향  /api/v2/report/*
# ══════════════════════════════════════════════════════

@mysql_bp.route("/report/monthly", methods=["GET"])
def report_monthly():
    uid   = _get_uid()
    month = request.args.get("month")
    from app.services.reading_service import get_monthly_report
    return _json(get_monthly_report(uid, month))


@mysql_bp.route("/report/persona", methods=["GET"])
def report_persona():
    uid = _get_uid()
    from app.services.heart_library_service import get_reading_persona
    return _json({"ok": True, "persona": get_reading_persona(uid)})


# ══════════════════════════════════════════════════════
#  라이브 독서방  /api/v2/live/*
# ══════════════════════════════════════════════════════

@mysql_bp.route("/live/rooms", methods=["GET"])
def live_list():
    status = request.args.get("status","active")
    from app.services.live_backend_service import list_rooms
    return _json({"ok": True, "rooms": list_rooms(status)})


@mysql_bp.route("/live/rooms", methods=["POST"])
def live_create():
    data = request.get_json() or {}
    if not data.get("title","").strip():
        return _json({"ok": False, "error": "방 이름을 입력하세요."}, 400)
    from app.services.live_backend_service import create_room
    result = create_room(data, _get_uid())
    return _json(result, 201 if result.get("ok") else 400)


@mysql_bp.route("/live/rooms/<room_id>", methods=["GET"])
def live_get(room_id):
    from app.services.live_backend_service import get_room
    room = get_room(room_id)
    if not room:
        return _json({"ok": False, "error": "방 없음"}, 404)
    return _json({"ok": True, "room": room})


@mysql_bp.route("/live/rooms/<room_id>/join", methods=["POST"])
def live_join(room_id):
    data = request.get_json() or {}
    from app.services.live_backend_service import join_room
    result = join_room(room_id, data, _get_uid())
    return _json(result, 200 if result.get("ok") else 400)


@mysql_bp.route("/live/rooms/<room_id>/message", methods=["POST"])
def live_message(room_id):
    data = request.get_json() or {}
    if not (data.get("text") or data.get("content") or "").strip():
        return _json({"ok": False, "error": "메시지 내용 필요"}, 400)
    from app.services.live_backend_service import send_message
    result = send_message(room_id, data, _get_uid())
    return _json(result, 200 if result.get("ok") else 400)


@mysql_bp.route("/live/rooms/<room_id>/poll", methods=["GET"])
def live_poll(room_id):
    since = request.args.get("since", "0")
    from app.services.live_backend_service import get_room_updates
    result = get_room_updates(room_id, since, _get_uid())
    return _json(result, 200 if result.get("ok") else 404)


@mysql_bp.route("/live/rooms/<room_id>/leave", methods=["POST"])
def live_leave(room_id):
    data = request.get_json() or {}
    peer_id = data.get("peer_id", "")
    if False and not peer_id:
        return _json({"ok": False, "error": "peer_id 필요"}, 400)
    from app.services.live_backend_service import leave_room
    result = leave_room(room_id, data, _get_uid())
    return _json(result, 200 if result.get("ok") else 400)


@mysql_bp.route("/live/rooms/<room_id>/end", methods=["POST"])
def live_end(room_id):
    from app.services.live_backend_service import end_room
    result = end_room(room_id, _get_uid())
    return _json(result, 200 if result.get("ok") else 403)


@mysql_bp.route("/live/rooms/<room_id>/transcript", methods=["POST"])
def live_transcript(room_id):
    data = request.get_json() or {}
    from app.services.live_backend_service import add_transcript
    result = add_transcript(room_id, data, _get_uid())
    return _json(result, 200 if result.get("ok") else 400)


@mysql_bp.route("/live/rooms/<room_id>/report", methods=["GET"])
def live_report(room_id):
    from app.services.live_backend_service import get_report
    report = get_report(room_id)
    if not report:
        return _json({"ok": False, "error": "아직 생성된 리포트가 없습니다."}, 404)
    return _json({"ok": True, "report": report})


# ══════════════════════════════════════════════════════
#  소크라테스  /api/v2/socrates/*
# ══════════════════════════════════════════════════════

@mysql_bp.route("/socrates/start", methods=["POST"])
def socrates_start():
    data = request.get_json() or {}
    uid  = _get_uid()
    data["user_id"] = uid
    from app.services.socrates_discussion_service import normalize_discussion_mode
    data["discussion_mode"] = normalize_discussion_mode(data.get("discussion_mode"))
    if not data.get("passage","").strip():
        return _json({"ok": False, "error": "구절이 필요합니다."}, 400)
    from app.services.live_socrates_service import start_session
    return _json(start_session(data), 201)


@mysql_bp.route("/socrates/book-brief", methods=["POST"])
def socrates_book_brief():
    data = request.get_json() or {}
    passage = (data.get("passage") or "").strip()
    if not passage:
        return _json({"ok": False, "error": "구절(passage)이 필요합니다."}, 400)
    from app.services.socrates_discussion_service import generate_book_brief
    return _json({"ok": True, "brief": generate_book_brief(
        passage=passage,
        book_title=data.get("book_title", ""),
        user_id=_get_uid(),
    )})


@mysql_bp.route("/socrates/discussion-questions", methods=["POST"])
def socrates_discussion_questions():
    data = request.get_json() or {}
    from app.services.socrates_discussion_service import (
        generate_discussion_questions,
        normalize_discussion_mode,
    )
    return _json({"ok": True, "questions": generate_discussion_questions(
        session_id=data.get("session_id", ""),
        passage=data.get("passage", ""),
        book_title=data.get("book_title", ""),
        insight=data.get("insight", ""),
        discussion_mode=normalize_discussion_mode(data.get("discussion_mode")),
        user_id=_get_uid(),
    )})


@mysql_bp.route("/socrates/debate-topic", methods=["POST"])
def socrates_debate_topic():
    data = request.get_json() or {}
    from app.services.socrates_discussion_service import generate_debate_topic
    return _json({"ok": True, "debate": generate_debate_topic(
        passage=data.get("passage", ""),
        book_title=data.get("book_title", ""),
        insight=data.get("insight", ""),
        user_id=_get_uid(),
    )})


@mysql_bp.route("/socrates/lounge-card", methods=["POST"])
def socrates_lounge_card():
    data = request.get_json() or {}
    from app.services.socrates_discussion_service import build_lounge_card
    return _json({"ok": True, "card": build_lounge_card(
        passage=data.get("passage", ""),
        book_title=data.get("book_title", ""),
        insight=data.get("insight", ""),
        discussion_questions=data.get("discussion_questions") or data.get("questions") or [],
        debate=data.get("debate") or {},
        user_id=_get_uid(),
    )})


@mysql_bp.route("/socrates/answer", methods=["POST"])
def socrates_answer():
    data       = request.get_json() or {}
    session_id = data.get("session_id","")
    answer     = data.get("answer","").strip()
    if not session_id or not answer:
        return _json({"ok": False, "error": "session_id와 answer 필요"}, 400)
    from app.services.live_socrates_service import answer_session
    return _json(answer_session(session_id, answer))


@mysql_bp.route("/socrates/connect", methods=["POST"])
def socrates_connect():
    data = request.get_json() or {}
    if not (data.get("text_a") and data.get("text_b")):
        return _json({"ok": False, "error": "text_a, text_b 필요"}, 400)
    from app.services.live_socrates_service import force_connect
    return _json(force_connect(data))


@mysql_bp.route("/socrates/sessions", methods=["GET"])
def socrates_sessions():
    uid = _get_uid()
    limit = int(request.args.get("limit","10"))
    from app.services.live_socrates_service import list_sessions
    return _json(list_sessions(uid, limit))


@mysql_bp.route("/socrates/sessions/<session_id>/resume", methods=["GET"])
def socrates_resume(session_id):
    from app.services.live_socrates_service import resume_session
    result = resume_session(session_id)
    return _json(result, 200 if result.get("ok") else 404)


@mysql_bp.route("/socrates/dictionary", methods=["GET"])
def socrates_get_dict():
    uid = _get_uid()
    from app.services.live_socrates_service import get_dict_entries
    return _json(get_dict_entries(uid))


@mysql_bp.route("/socrates/dictionary", methods=["POST"])
def socrates_add_dict():
    uid  = _get_uid()
    data = request.get_json() or {}
    if not data.get("concept","").strip():
        return _json({"ok": False, "error": "concept 필요"}, 400)
    data["user_id"] = uid
    from app.services.live_socrates_service import add_dict_entry
    result = add_dict_entry(uid, data)
    return _json(result, 201 if result.get("ok") else 400)


@mysql_bp.route("/socrates/action", methods=["POST"])
def socrates_action():
    uid  = _get_uid()
    data = request.get_json() or {}
    if not data.get("insight","").strip():
        return _json({"ok": False, "error": "insight 필요"}, 400)
    from app.services.live_socrates_service import create_action_plan
    result = create_action_plan(uid, data)
    return _json(result, 201 if result.get("ok") else 400)


@mysql_bp.route("/socrates/actions", methods=["GET"])
def socrates_actions():
    uid = _get_uid()
    from app.services.live_socrates_service import get_action_plans
    return _json(get_action_plans(uid))


@mysql_bp.route("/socrates/action/<plan_id>/checkin", methods=["POST"])
def socrates_checkin(plan_id):
    data = request.get_json() or {}
    from app.services.live_socrates_service import checkin_plan
    return _json(checkin_plan(plan_id, data.get("note","")))


# ══════════════════════════════════════════════════════
#  소셜 피드  /api/v2/social/*
# ══════════════════════════════════════════════════════

@mysql_bp.route("/community/feed", methods=["GET"])
def v2_community_feed():
    from app.services.community_feed_service import get_feed
    return _json(get_feed(
        user_id=_get_uid(),
        page=int(request.args.get("page", 1)),
        limit=int(request.args.get("limit", 12)),
        tag=request.args.get("tag", ""),
        q=request.args.get("q", ""),
        emotion=request.args.get("emotion", ""),
    ))


@mysql_bp.route("/community/trending-books", methods=["GET"])
def v2_community_trending_books():
    from app.services.community_feed_service import get_trending_books
    return _json(get_trending_books(_get_uid(), int(request.args.get("limit", 12))))


@mysql_bp.route("/community/questions", methods=["GET"])
def v2_community_questions():
    from app.services.community_feed_service import get_questions
    return _json(get_questions(_get_uid(), int(request.args.get("limit", 12))))


@mysql_bp.route("/community/quotes", methods=["GET"])
def v2_community_quotes():
    from app.services.community_feed_service import get_quotes
    return _json(get_quotes(_get_uid(), int(request.args.get("limit", 12))))


@mysql_bp.route("/community/same-book-readers", methods=["GET"])
def v2_community_same_book_readers():
    from app.services.community_feed_service import get_same_book_readers
    return _json(get_same_book_readers(
        book_id=request.args.get("book_id", ""),
        title=request.args.get("title", ""),
        limit=int(request.args.get("limit", 12)),
    ))


@mysql_bp.route("/community/lounge-recruit", methods=["GET"])
def v2_community_lounge_recruit():
    from app.services.community_feed_service import get_lounge_recruit
    return _json(get_lounge_recruit(_get_uid(), int(request.args.get("limit", 8))))


@mysql_bp.route("/community/posts", methods=["POST"])
def v2_community_create_post():
    from app.services.community_feed_service import create_post
    data = request.get_json(silent=True) or {}
    result = create_post(_get_uid(), data)
    return _json(result, 201 if result.get("ok") else 400)


@mysql_bp.route("/community/posts/<post_id>/like", methods=["POST"])
def v2_community_like(post_id):
    from app.services.community_feed_service import toggle_like
    return _json(toggle_like(post_id, _get_uid()))


@mysql_bp.route("/community/posts/<post_id>/comments", methods=["GET"])
def v2_community_comments(post_id):
    from app.services.community_feed_service import get_comments
    return _json({"ok": True, "comments": get_comments(post_id, int(request.args.get("limit", 50)))})


@mysql_bp.route("/community/posts/<post_id>/comments", methods=["POST"])
def v2_community_add_comment(post_id):
    from app.services.community_feed_service import add_comment
    data = request.get_json(silent=True) or {}
    result = add_comment(post_id, data, _get_uid())
    return _json(result, 201 if result.get("ok") else 400)


@mysql_bp.route("/community/posts/<post_id>/save", methods=["POST"])
def v2_community_save(post_id):
    from app.services.community_feed_service import toggle_save
    return _json(toggle_save(post_id, _get_uid()))


@mysql_bp.route("/social/feed", methods=["GET"])
def v2_social_feed():
    return v2_community_feed()


@mysql_bp.route("/social/cards", methods=["POST"])
def v2_social_create_card():
    from app.services.community_feed_service import create_post, check_and_create_bookclub
    data = request.get_json(silent=True) or {}
    content = (data.get("passage") or data.get("content") or data.get("text") or "").strip()
    if not content:
        return _json({"ok": False, "error": "구절(passage)이 필요합니다."}, 400)
    data["passage"] = content
    result = create_post(_get_uid(), data)
    club = check_and_create_bookclub(data.get("book_title", ""))
    if not result.get("ok"):
        return _json(result, 400)
    return _json({"ok": True, "card": result.get("post"), "post": result.get("post"), "new_club": club}, 201)


@mysql_bp.route("/social/cards/<card_id>/like", methods=["POST"])
def v2_social_like(card_id):
    return v2_community_like(card_id)


@mysql_bp.route("/social/cards/<card_id>/comments", methods=["GET"])
def v2_social_comments(card_id):
    return v2_community_comments(card_id)


@mysql_bp.route("/social/cards/<card_id>/comments", methods=["POST"])
def v2_social_add_comment(card_id):
    from app.services.social_feed_service import add_comment
    data = request.get_json(silent=True) or {}
    content = (data.get("text") or data.get("content") or "").strip()
    if not content:
        return _json({"ok": False, "error": "댓글 내용 필요"}, 400)
    data["text"] = content
    return _json(add_comment(card_id, data))


@mysql_bp.route("/social/match", methods=["GET"])
def v2_social_match():
    from app.services.social_feed_service import find_reading_buddies
    uid = _get_uid()
    genres = request.args.get("genres", "철학,역사,과학").split(",")
    books = request.args.get("books", "사피엔스,어린왕자").split(",")
    return _json({"ok": True, "matches": find_reading_buddies(uid, genres, books)})


@mysql_bp.route("/social/clubs", methods=["GET"])
def v2_social_clubs():
    from app.services.social_feed_service import get_bookclubs
    clubs = get_bookclubs()
    if not clubs:
        clubs = [
            {"club_id": "pod_pachinko", "name": "파친코 독서 파드", "member_count": 12, "current_book": "파친코"},
            {"club_id": "pod_cosmos", "name": "코스모스 사유 파드", "member_count": 9, "current_book": "코스모스"},
            {"club_id": "pod_lit", "name": "한국문학 문장 파드", "member_count": 15, "current_book": "채식주의자"},
        ]
    return _json({"ok": True, "clubs": clubs})


@mysql_bp.route("/social/challenge", methods=["GET"])
def v2_social_challenge():
    from app.services.social_feed_service import get_challenge_status
    uid = _get_uid()
    books_read = int(request.args.get("books_read", 3))
    memos = int(request.args.get("memos", 5))
    return _json({"ok": True, **get_challenge_status(uid, books_read, memos)})


@mysql_bp.route("/social/badges", methods=["GET"])
def v2_social_badges():
    from app.services.social_feed_service import get_user_badges
    return _json({"ok": True, "badges": get_user_badges(_get_uid())})


# ══════════════════════════════════════════════════════
#  시스템  /api/v2/system/*
# ══════════════════════════════════════════════════════

@mysql_bp.route("/system/status", methods=["GET"])
def system_status():
    from app.db import is_connected
    from app.core.config import settings
    return _json({
        "ok":      True,
        "mysql":   "✅ 연결됨" if is_connected() else "⚠️  Mock 모드",
        "gemini":  "✅ 연결됨" if settings.gemini_ready else "⚠️  Mock 모드",
        "version": "2.0 (MySQL)",
    })


@mysql_bp.route("/system/init-db", methods=["POST"])
def system_init_db():
    """개발용: 테이블 생성"""
    from app.schema import create_all_tables
    ok = create_all_tables()
    return _json({"ok": ok, "message": "테이블 생성 완료" if ok else "Mock 모드"})
