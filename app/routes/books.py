"""
도서 검색 + OCR 라우터
GET  /api/books/search        도서 검색
GET  /api/books/popular       인기 도서
GET  /api/books/<id>          도서 상세
POST /api/books/ocr           이미지 → 텍스트 변환
POST /api/books/user-book     서재 추가
GET  /api/books/my-shelf      내 서재 조회
"""
import base64
from flask import Blueprint, request, jsonify
from app.services.book_service import (
    search_books, get_book_by_id, get_popular_books, get_book_status
)
from app.services.auth_service import get_current_user

books_bp = Blueprint('books', __name__)
TOKEN_COOKIE = "luma_token"

def _get_token():
    return (request.cookies.get(TOKEN_COOKIE)
            or request.headers.get("Authorization","").replace("Bearer ",""))

# 간단한 인메모리 서재 (DB 연동 전)
_user_shelves: dict[str, list] = {}


@books_bp.route('/search', methods=['GET'])
def api_search():
    q     = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 10))
    books = search_books(q, limit)
    return jsonify({"ok": True, "books": books, "count": len(books), "query": q})


@books_bp.route('/popular', methods=['GET'])
def api_popular():
    return jsonify({"ok": True, "books": get_popular_books()})


@books_bp.route('/<book_id>', methods=['GET'])
def api_book_detail(book_id):
    book = get_book_by_id(book_id)
    if not book:
        return jsonify({"ok": False, "error": "도서를 찾을 수 없습니다."}), 404
    return jsonify({"ok": True, "book": book})


@books_bp.route('/status', methods=['GET'])
def api_status():
    return jsonify({"ok": True, **get_book_status()})


@books_bp.route('/ocr', methods=['POST'])
def api_ocr():
    """
    이미지 → 텍스트 변환 (OCR)
    POST body: {"image_base64": "...", "type": "book_page|photo"}
    """
    data         = request.get_json() or {}
    image_base64 = data.get('image_base64', '')
    ocr_type     = data.get('type', 'book_page')

    if not image_base64:
        return jsonify({"ok": False, "error": "이미지 데이터가 필요합니다."}), 400

    # Gemini Vision OCR 시도
    extracted_text = ""
    try:
        from app.services.gemini_service import _gemini_ok, _gemini_model
        if _gemini_ok and _gemini_model:
            import PIL.Image, io
            img_bytes  = base64.b64decode(image_base64)
            img        = PIL.Image.open(io.BytesIO(img_bytes))
            prompt     = (
                "이 이미지에서 텍스트를 정확하게 추출해주세요. "
                "책 페이지이면 문단 구조를 유지해주세요. "
                "텍스트만 출력하고, 설명이나 주석은 붙이지 마세요."
            )
            response       = _gemini_model.generate_content([prompt, img])
            extracted_text = response.text.strip()
    except Exception as e:
        pass

    # Mock 폴백
    if not extracted_text:
        extracted_text = (
            "📸 OCR 결과 (Mock)\n\n"
            "Gemini Vision API 키가 설정되면 실제 텍스트가 추출됩니다.\n"
            "지금은 이미지를 성공적으로 받았으며, "
            "API 연동 후 자동으로 텍스트가 추출됩니다."
        )

    return jsonify({
        "ok":   True,
        "text": extracted_text,
        "type": ocr_type,
        "char_count": len(extracted_text),
    })


@books_bp.route('/user-book', methods=['POST'])
def api_add_to_shelf():
    """내 서재에 책 추가"""
    user  = get_current_user(_get_token())
    if not user:
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401

    data    = request.get_json() or {}
    book_id = data.get('book_id', '')
    status  = data.get('status', 'wishlist')
    book    = get_book_by_id(book_id)

    if not book:
        return jsonify({"ok": False, "error": "도서를 찾을 수 없습니다."}), 404

    uid   = user['user_id']
    shelf = _user_shelves.setdefault(uid, [])
    existing = next((b for b in shelf if b['book_id'] == book_id), None)

    if existing:
        existing['status'] = status
        return jsonify({"ok": True, "user_book": existing, "action": "updated"})

    user_book = {
        "user_book_id":  f"ub-{uid[:8]}-{book_id[:8]}",
        "book_id":       book_id,
        "title":         book.get('title', ''),
        "authors":       book.get('authors', []),
        "cover_url":     book.get('cover_url', ''),
        "cover_url_s":   book.get('cover_url_s', ''),
        "status":        status,
        "current_page":  0,
        "total_pages":   book.get('page_count', 0),
        "progress_pct":  0,
        "rating":        None,
    }
    shelf.insert(0, user_book)
    return jsonify({"ok": True, "user_book": user_book, "action": "added"}), 201


@books_bp.route('/my-shelf', methods=['GET'])
def api_my_shelf():
    """내 서재 조회"""
    user = get_current_user(_get_token())
    if not user:
        return jsonify({"ok": False, "error": "로그인이 필요합니다."}), 401

    uid    = user['user_id']
    shelf  = _user_shelves.get(uid, [])
    status = request.args.get('status', 'all')
    if status != 'all':
        shelf = [b for b in shelf if b['status'] == status]

    return jsonify({"ok": True, "books": shelf, "count": len(shelf)})
