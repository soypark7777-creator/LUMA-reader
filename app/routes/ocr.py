"""OCR API routes.

The frontend at /ocr uses this module as its single OCR contract:
scan image, improve text, draft a memo, save the memo, and run analysis.
"""
import base64
from typing import Any

from flask import Blueprint, jsonify, request

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
    if "image" in request.files:
        data = request.files["image"].read()
        if not data:
            return None, "빈 이미지 파일입니다."
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


def _analyze_text(content: str, book_title: str = "") -> dict[str, Any]:
    from app.services.gemini_service import (
        analyze_memo_theme,
        extract_keywords,
        generate_reframe_question,
    )

    theme_info = analyze_memo_theme(content)
    reframe = generate_reframe_question(content, book_title)
    question = reframe.get("question") if isinstance(reframe, dict) else reframe
    return {
        "keywords": extract_keywords(content, book_title),
        "theme": theme_info.get("theme", "") if isinstance(theme_info, dict) else theme_info,
        "theme_info": theme_info,
        "summary": theme_info.get("summary", "") if isinstance(theme_info, dict) else "",
        "emotion": theme_info.get("emotion", "") if isinstance(theme_info, dict) else "",
        "depth_score": theme_info.get("depth_score", 0) if isinstance(theme_info, dict) else 0,
        "question": question or "",
        "reframe": reframe,
    }


@ocr_bp.route("/status", methods=["GET"])
def ocr_status():
    return jsonify({"ok": True, **get_ocr_status()})


@ocr_bp.route("/scan", methods=["POST"])
def ocr_scan():
    image_bytes, err = _get_image_bytes()
    if err:
        return jsonify({"ok": False, "error": err}), 400

    body = _json_body()
    language = request.form.get("language") or body.get("language", "ko")
    result = extract_text(image_bytes, language=language)
    return jsonify({"ok": True, **result})


@ocr_bp.route("/enhance", methods=["POST"])
def ocr_enhance():
    data = _json_body()
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "text 값이 필요합니다."}), 400

    result = enhance_text(text)
    corrected = result.get("corrected") or result.get("enhanced") or text
    return jsonify({"ok": True, **result, "corrected": corrected, "enhanced": corrected})


@ocr_bp.route("/book-cover", methods=["POST"])
def ocr_book_cover():
    image_bytes, err = _get_image_bytes()
    if err:
        return jsonify({"ok": False, "error": err}), 400
    return jsonify({"ok": True, **detect_book_info(image_bytes)})


@ocr_bp.route("/analyze-page", methods=["POST"])
def ocr_analyze_page():
    image_bytes, err = _get_image_bytes()
    if err:
        return jsonify({"ok": False, "error": err}), 400
    return jsonify({"ok": True, **analyze_page(image_bytes)})


@ocr_bp.route("/generate-memo", methods=["POST"])
def ocr_generate_memo():
    data = _json_body()
    text = (data.get("text") or data.get("content") or "").strip()
    book_title = data.get("book_title", "")
    if not text:
        return jsonify({"ok": False, "error": "text 값이 필요합니다."}), 400

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
        return jsonify({"ok": False, "error": "저장할 메모 내용이 필요합니다."}), 400

    payload = {
        "content": content,
        "book_id": data.get("book_id", ""),
        "book_title": data.get("book_title", ""),
        "page_num": data.get("page_num", data.get("page_number")),
        "tags": data.get("tags", []),
        "mood": data.get("mood", "neutral"),
        "source": "ocr",
        "is_public": bool(data.get("is_public", False)),
    }

    from app.services.reading_service import save_memo

    saved = save_memo(_uid(data), payload)
    if not saved.get("ok"):
        return jsonify(saved), 400

    analysis = _analyze_text(content, payload["book_title"])
    return jsonify({"ok": True, **saved, "analysis": analysis})


@ocr_bp.route("/full-pipeline", methods=["POST"])
def ocr_full_pipeline():
    body = _json_body()
    book_title = request.form.get("book_title") or body.get("book_title", "")
    language = request.form.get("language") or body.get("language", "ko")
    text = (body.get("text") or body.get("content") or "").strip()
    ocr_result = None

    if not text:
        image_bytes, err = _get_image_bytes()
        if err:
            return jsonify({"ok": False, "error": "분석할 text 또는 image가 필요합니다."}), 400
        ocr_result = extract_text(image_bytes, language=language)
        text = ocr_result.get("text", "")

    memo_result = _normalize_memo_result(generate_memo_from_text(text, book_title))
    resources = _normalize_resources(get_all_resources(text, book_title))
    analysis = _analyze_text(memo_result["memo_draft"] or text, book_title)

    return jsonify({
        "ok": True,
        "ocr": ocr_result or {
            "text": text,
            "source": "provided_text",
            "language": language,
            "char_count": len(text),
            "word_count": len(text.split()),
        },
        "memo": memo_result,
        "resources": resources,
        "analysis": analysis,
        "youtube": resources["youtube"],
        "papers": resources["papers"],
        "pipeline": "text -> memo -> analysis -> resources",
    })
