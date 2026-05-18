"""Lounge recommendation API routes."""
from __future__ import annotations

from flask import Blueprint, jsonify, request


lounge_books_bp = Blueprint("lounge_books", __name__)


def _uid() -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.services.user_service import verify_token

            payload = verify_token(auth[7:])
            if payload:
                return payload.get("user_id", "user_demo")
        except Exception:
            pass
    body = request.get_json(silent=True) or {}
    return request.args.get("user_id") or body.get("user_id") or "user_demo"


@lounge_books_bp.route("/books/recommend", methods=["GET"])
def recommend_books():
    from app.services.lounge_recommendation_service import recommend_books as recommend

    try:
        limit = int(request.args.get("limit", "20") or 20)
    except ValueError:
        limit = 20
    result = recommend(
        {
            "emotion": request.args.get("emotion", ""),
            "persona": request.args.get("persona", ""),
            "field": request.args.get("field", ""),
            "mode": request.args.get("mode", ""),
            "sort": request.args.get("sort", ""),
        },
        limit,
    )
    return jsonify(result), 200 if result.get("ok", True) else 500


@lounge_books_bp.route("/books/recommend/contract", methods=["GET"])
def recommend_contract():
    from app.services.lounge_recommendation_service import FILTER_CONTRACT

    return jsonify(
        {
            "ok": True,
            "endpoint": "/api/v2/lounge/books/recommend",
            "method": "GET",
            "query": {
                "emotion": "calm",
                "persona": "INFJ",
                "field": "philosophy",
                "mode": "classic",
                "sort": "score",
                "limit": 20,
            },
            "accepted": FILTER_CONTRACT,
            "response_shape": {
                "ok": True,
                "books": [],
                "count": 0,
                "filters": {
                    "emotion": "",
                    "persona": "",
                    "field": "",
                    "mode": "",
                    "sort": "score",
                },
                "meta": {
                    "source": "lounge_pipeline",
                    "pipeline": ["seed", "providers", "normalize", "dedupe", "tag", "score"],
                    "contract_version": "2026-05-18",
                    "fallback_ready": True,
                },
            },
            "book_shape": {
                "book_id": "",
                "isbn10": "",
                "isbn13": "",
                "isbn": "",
                "title": "",
                "author": "",
                "publisher": "",
                "published_date": "",
                "rating": 0,
                "review_count": 0,
                "description": "",
                "summary": "",
                "category": "",
                "genre": "",
                "tags": [],
                "scores": {},
                "luma_score": 0,
                "recommend_reason": "",
                "reason": "",
                "cover_url": "",
                "thumbnail": "",
                "thumbnail_url": "",
                "cover_url_candidates": [],
                "fallback_cover": {
                    "title": "",
                    "initial": "책",
                    "theme": "classic",
                    "label": "",
                    "background": "#173127",
                    "accent": "#C17F3B",
                    "source_url": "",
                },
                "initial": "책",
                "theme": "classic",
                "source": "local",
                "source_url": "",
                "external_url": "",
                "total_pages": 0,
            },
        }
    )


@lounge_books_bp.route("/books/detail/<path:book_id>", methods=["GET"])
def book_detail(book_id):
    from app.services.lounge_recommendation_service import get_recommendation_detail

    result = get_recommendation_detail(book_id)
    return jsonify(result), 200 if result.get("ok") else 404


@lounge_books_bp.route("/books/save", methods=["POST"])
def save_book():
    data = request.get_json(silent=True) or {}
    if not (data.get("title") or "").strip():
        return jsonify({"ok": False, "error": "책 제목을 입력하세요.", "source": "lounge_books_save"}), 400

    from app.services.book_normalizer_service import normalize_book
    from app.services.shelf_service import add_book

    book = normalize_book(data, data.get("source") or "lounge")
    payload = {
        "title": book.get("title", ""),
        "author": book.get("author", ""),
        "cover_url": book.get("cover_url", ""),
        "thumbnail": book.get("thumbnail", ""),
        "isbn": book.get("isbn", ""),
        "publisher": book.get("publisher", ""),
        "description": book.get("description") or book.get("summary") or "",
        "published_date": book.get("published_date", ""),
        "genre": book.get("genre") or book.get("category") or "",
        "total_pages": book.get("total_pages", 0),
        "status": data.get("status", "want"),
    }
    result = add_book(_uid(), payload)
    if result.get("ok"):
        result["book"] = {**book, **(result.get("book") or {})}
    result.setdefault("source", "lounge_books_save")
    return jsonify(result), 201 if result.get("ok") else 400


@lounge_books_bp.route("/create-from-book", methods=["POST"])
def create_from_book():
    data = request.get_json(silent=True) or {}

    from app.services.book_normalizer_service import normalize_book

    book = normalize_book(data, data.get("source") or "lounge")
    title = (book.get("title") or data.get("book_title") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "책 제목이 필요합니다.", "source": "lounge_create_from_book"}), 400

    lounge = {
        "lounge_id": f"lounge_{abs(hash((title, _uid()))) % 1000000:06d}",
        "title": f"{title} 독서 라운지",
        "book": {
            "book_id": book.get("book_id", ""),
            "title": title,
            "author": book.get("author") or data.get("book_author") or "",
            "cover_url": book.get("cover_url", ""),
            "thumbnail": book.get("thumbnail", ""),
            "thumbnail_url": book.get("thumbnail_url", ""),
            "fallback_cover": book.get("fallback_cover", {}),
            "initial": book.get("initial", ""),
            "theme": book.get("theme", ""),
            "source_url": book.get("source_url", ""),
        },
        "status": "draft",
        "recommended_questions": [
            f"{title}은 지금 우리에게 어떤 질문을 던지나요?",
            "가장 오래 붙잡고 싶은 문장은 무엇인가요?",
            "이 책을 함께 읽을 때 찬반으로 나눌 수 있는 주제는 무엇인가요?",
        ],
    }
    return jsonify({"ok": True, "lounge": lounge, "source": "lounge_create_from_book"}), 201
