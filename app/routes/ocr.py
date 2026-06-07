"""OCR API routes.

The frontend at /ocr uses this module as its single OCR contract:
scan image, improve text, draft a memo, save the memo, and run analysis.
"""
from __future__ import annotations

import base64
from typing import Any

from flask import Blueprint, jsonify, request

from app.services.google_vision_ocr import extract_text_google_vision, get_google_vision_status
from app.services.ocr_service import (
    analyze_page,
    detect_book_info,
    enhance_text,
    extract_text,
    generate_memo_from_text,
    get_ocr_status,
)
from app.services.youtube_service import get_all_resources

ocr_bp = Blueprint("ocr", __name__)

MAX_IMAGE_SIZE = 10 * 1024 * 1024


def _json_body() -> dict[str, Any]:
    return request.get_json(force=False, silent=True) or {}


def _uid(data: dict[str, Any] | None = None) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.services.user_service import verify_token

            payload = verify_token(auth[7:])
            if payload:
                return payload.get("user_id", "user_demo")
        except Exception:
            pass
    data = data or _json_body()
    return request.args.get("user_id") or data.get("user_id") or "user_demo"


def _get_image_bytes() -> tuple[bytes | None, str | None]:
    """Read an image from multipart form-data or JSON image_base64."""
    uploaded = request.files.get("image") or request.files.get("file")
    if uploaded:
        data = uploaded.read()
        if not data:
            return None, "비어 있는 이미지 파일입니다."
        if len(data) > MAX_IMAGE_SIZE:
            return None, "이미지 크기는 10MB 이하여야 합니다."
        return data, None

    b64_str = str(_json_body().get("image_base64") or "")
    if b64_str:
        try:
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            data = base64.b64decode(b64_str)
            if len(data) > MAX_IMAGE_SIZE:
                return None, "이미지 크기는 10MB 이하여야 합니다."
            return data, None
        except Exception:
            return None, "base64 이미지를 읽을 수 없습니다."

    return None, "image 파일 또는 image_base64 값이 필요합니다."


def _normalize_memo_result(result: dict[str, Any]) -> dict[str, Any]:
    memo_text = result.get("memo_draft") or result.get("quote") or ""
    tags = result.get("tags") or []
    keywords = result.get("keywords") or tags
    return {
        **result,
        "quote": memo_text,
        "memo_draft": memo_text,
        "tags": tags,
        "keywords": keywords,
    }


def _normalize_resources(resources: dict[str, Any]) -> dict[str, Any]:
    videos = resources.get("videos") or resources.get("youtube") or []
    papers = resources.get("scholar") or resources.get("papers") or []
    return {**resources, "youtube": videos, "papers": papers}


def _local_resources(text: str, book_title: str = "") -> dict[str, Any]:
    query = " ".join(part for part in [book_title, "독서 해석"] if part).strip() or "독서 문장 해석"
    return {
        "youtube": [
            {
                "title": f"{query} 관련 강의 검색",
                "channel": "YouTube 검색",
                "url": f"https://www.youtube.com/results?search_query={query}",
            }
        ],
        "papers": [
            {
                "title": f"{book_title or '이 구절'} 관련 비평/해설 자료 검색",
                "source": "Google Scholar",
                "year": "",
            }
        ],
    }


def _analyze_text(content: str, book_title: str = "") -> dict[str, Any]:
    title = (book_title or "").strip()
    words = [
        token.strip(".,!?()[]{}'\"")
        for token in content.replace("\n", " ").split()
        if len(token.strip(".,!?()[]{}'\"")) >= 2
    ]
    keywords = []
    for token in words:
        if token not in keywords:
            keywords.append(token)
        if len(keywords) >= 5:
            break
    lower = content.lower()
    if any(word in content for word in ("사랑", "슬픔", "외로움", "그리움", "마음")):
        theme = "감정과 관계"
        emotion = "감성"
    elif any(word in content for word in ("생각", "질문", "의미", "진실", "이유")):
        theme = "사유와 질문"
        emotion = "사유"
    elif any(word in lower for word in ("time", "life", "truth", "love")):
        theme = "삶의 의미"
        emotion = "성찰"
    else:
        theme = "독서 메모"
        emotion = "사유"
    summary = f"{title + '의 ' if title else ''}구절에서 '{keywords[0] if keywords else '문장'}'을 중심으로 생각할 지점을 발견했습니다."
    question = f"{title + '에서 ' if title else ''}이 문장이 지금 나에게 묻는 것은 무엇일까요?"
    theme_info = {
        "theme": theme,
        "summary": summary,
        "emotion": emotion,
        "depth_score": min(100, max(30, len(content) // 8)),
    }
    reframe = {"question": question, "source": "local"}
    return {
        "keywords": keywords or ["독서", "문장", "생각"],
        "theme": theme,
        "theme_info": theme_info,
        "summary": summary,
        "emotion": emotion,
        "depth_score": theme_info.get("depth_score", 0) if isinstance(theme_info, dict) else 0,
        "question": question,
        "reframe": reframe,
        "book_title": title,
    }


def _ensure_book_for_ocr_memo(user_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """Ensure OCR memos with a typed/detected title are attached to the user's shelf."""
    if (data.get("book_id") or "").strip():
        return None
    title = (data.get("book_title") or "").strip()
    if not title:
        return None
    try:
        from app.services.shelf_service import add_book

        created = add_book(
            user_id,
            {
                "title": title,
                "author": (data.get("book_author") or "").strip(),
                "publisher": (data.get("publisher") or "").strip(),
                "status": "reading",
                "progress": 0,
                "cover_emoji": "\U0001f4da",
            },
        )
        if created.get("ok") and created.get("book", {}).get("book_id"):
            return created["book"]
    except Exception:
        return None
    return None


@ocr_bp.route("/status", methods=["GET"])
def ocr_status():
    return jsonify({"ok": True, **get_ocr_status()})


@ocr_bp.route("/health", methods=["GET"])
def ocr_health():
    return jsonify({"ok": True, "success": True, **get_google_vision_status()})


@ocr_bp.route("", methods=["POST"])
def ocr_google_upload():
    uploaded = request.files.get("file") or request.files.get("image")
    if not uploaded:
        return jsonify({
            "ok": False,
            "success": False,
            "engine": "google_vision",
            "source": "google_vision_upload",
            "error": "form-data file 필드가 필요합니다.",
        }), 400
    if not (uploaded.mimetype or "").startswith("image/"):
        return jsonify({
            "ok": False,
            "success": False,
            "engine": "google_vision",
            "source": "google_vision_upload",
            "error": "이미지 파일만 업로드할 수 있습니다.",
        }), 400

    try:
        return jsonify({"ok": True, **extract_text_google_vision(uploaded.read(), uploaded.filename or "upload")})
    except Exception as exc:
        return jsonify({
            "ok": False,
            "success": False,
            "engine": "google_vision",
            "source": "google_vision_upload",
            "error": str(exc),
        }), 500


@ocr_bp.route("/scan", methods=["POST"])
def ocr_scan():
    image_bytes, err = _get_image_bytes()
    if err:
        return jsonify({"ok": False, "error": err, "source": "ocr_scan"}), 400

    body = _json_body()
    language = request.form.get("language") or body.get("language", "ko")
    result = extract_text(image_bytes, language=language)
    return jsonify({"ok": True, **result})


@ocr_bp.route("/enhance", methods=["POST"])
def ocr_enhance():
    data = _json_body()
    text = (data.get("text") or "").strip()
    book_title = (data.get("book_title") or "").strip()
    book_author = (data.get("book_author") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "text 값이 필요합니다.", "source": "ocr_enhance"}), 400

    result = enhance_text(text, book_title=book_title, book_author=book_author)
    corrected = result.get("corrected") or result.get("enhanced") or text
    return jsonify({"ok": True, **result, "corrected": corrected, "enhanced": corrected})


@ocr_bp.route("/book-cover", methods=["POST"])
def ocr_book_cover():
    image_bytes, err = _get_image_bytes()
    if err:
        return jsonify({"ok": False, "error": err, "source": "ocr_book_cover"}), 400
    return jsonify({"ok": True, **detect_book_info(image_bytes)})


@ocr_bp.route("/analyze-page", methods=["POST"])
def ocr_analyze_page():
    image_bytes, err = _get_image_bytes()
    if err:
        return jsonify({"ok": False, "error": err, "source": "ocr_analyze_page"}), 400
    return jsonify({"ok": True, **analyze_page(image_bytes)})


@ocr_bp.route("/generate-memo", methods=["POST"])
def ocr_generate_memo():
    data = _json_body()
    text = (data.get("text") or data.get("content") or "").strip()
    book_title = data.get("book_title", "")
    if not text:
        return jsonify({"ok": False, "error": "text 값이 필요합니다.", "source": "ocr_generate_memo"}), 400

    result = _normalize_memo_result(generate_memo_from_text(text, book_title))
    analysis = _analyze_text(result["memo_draft"] or text, book_title)
    return jsonify({"ok": True, **result, "analysis": analysis})


@ocr_bp.route("/save-memo", methods=["POST"])
def ocr_save_memo():
    data = _json_body()
    content = (
        data.get("content")
        or data.get("memo_draft")
        or data.get("quote")
        or data.get("text")
        or ""
    ).strip()
    if not content:
        return jsonify({"ok": False, "error": "저장할 메모 내용이 필요합니다.", "source": "ocr_save_memo"}), 400

    user_id = _uid(data)
    linked_book = _ensure_book_for_ocr_memo(user_id, data)
    payload = {
        "content": content,
        "book_id": data.get("book_id", "") or ((linked_book or {}).get("book_id") or ""),
        "book_title": data.get("book_title", ""),
        "page_num": data.get("page_num", data.get("page_number")),
        "tags": data.get("tags", []),
        "mood": data.get("mood", "neutral"),
        "source": "ocr",
        "is_public": bool(data.get("is_public", False)),
    }

    from app.services.reading_service import save_memo

    saved = save_memo(user_id, payload)
    if not saved.get("ok"):
        return jsonify({**saved, "source": saved.get("source", "ocr_save_memo")}), 400

    analysis = _analyze_text(content, payload["book_title"])
    return jsonify({"ok": True, **saved, "book": linked_book, "analysis": analysis, "source": "ocr_save_memo"})


@ocr_bp.route("/full-pipeline", methods=["POST"])
def ocr_full_pipeline():
    body = _json_body()
    book_title = request.form.get("book_title") or body.get("book_title", "")
    book_author = request.form.get("book_author") or body.get("book_author", "")
    language = request.form.get("language") or body.get("language", "ko")
    text = (request.form.get("text") or body.get("text") or body.get("content") or "").strip()
    ocr_result = None
    book_info: dict[str, Any] = {}

    if not text:
        image_bytes, err = _get_image_bytes()
        if err:
            return jsonify({"ok": False, "error": "분석할 text 또는 image가 필요합니다.", "source": "ocr_full_pipeline"}), 400
        ocr_result = extract_text(image_bytes, language=language)
        text = ocr_result.get("text", "")
        try:
            book_info = detect_book_info(image_bytes)
            book_title = book_title or book_info.get("title", "")
            book_author = book_author or book_info.get("author", "")
        except Exception:
            book_info = {}
    elif book_title or book_author:
        book_info = {"title": book_title, "author": book_author, "source": "provided_text"}

    memo_result = _normalize_memo_result(generate_memo_from_text(text, book_title))
    resources = _local_resources(text, book_title)
    analysis = _analyze_text(memo_result["memo_draft"] or text, book_title)

    return jsonify({
        "ok": True,
        "ocr": ocr_result or {
            "ok": True,
            "text": text,
            "source": "provided_text",
            "engine": "provided_text",
            "language": language,
            "char_count": len(text),
            "word_count": len(text.split()),
        },
        "book_info": {**book_info, "title": book_title, "author": book_author},
        "memo": memo_result,
        "resources": resources,
        "analysis": analysis,
        "youtube": resources["youtube"],
        "papers": resources["papers"],
        "pipeline": "text -> book_info -> memo -> analysis -> resources",
        "source": "ocr_full_pipeline",
        "engine": (ocr_result or {}).get("engine") or (ocr_result or {}).get("source") or "provided_text",
    })
