"""
Reading-place API for the community map.

Keeps the legacy mock endpoints while adding Google Places search/detail and
saved reading-meeting place management.
"""
from flask import Blueprint, request, jsonify

from app.services.place_service import (
    search_nearby, get_all_spots, get_spot,
    checkin_spot, get_cities, get_map_status,
    search_google_places, get_google_place_detail, get_google_photo_url,
    save_reading_place, update_reading_place, delete_reading_place,
    list_saved_reading_places, add_place_review, list_place_reviews,
    summarize_place_for_reading,
)

places_bp = Blueprint("places", __name__)


def _float_arg(name, default=None):
    try:
        value = request.args.get(name, default)
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return default


def _int_arg(name, default):
    try:
        return int(request.args.get(name, default))
    except (TypeError, ValueError):
        return default


@places_bp.route("/search", methods=["GET"])
def api_search_places():
    q = (request.args.get("q") or "").strip()
    lat = _float_arg("lat")
    lng = _float_arg("lng")
    radius = _int_arg("radius", 3000)
    limit = _int_arg("limit", 12)
    result = search_google_places(q or "독서모임하기 좋은 카페 도서관 북카페", lat, lng, radius, limit)
    if request.args.get("strict_google") in ("1", "true", "yes") and result.get("source") == "mock":
        result = {"source": "google_unavailable", "places": []}
    return jsonify({
        "ok": True,
        "places": result["places"],
        "center": {"lat": lat, "lng": lng},
        "source": result["source"],
    })


@places_bp.route("/google/<google_place_id>", methods=["GET"])
def api_google_place_detail(google_place_id):
    detail = get_google_place_detail(google_place_id)
    place = detail.get("place") or {}
    reviews = list_place_reviews(place.get("place_id") or google_place_id)
    return jsonify({
        "ok": True,
        "place": place,
        "summary": summarize_place_for_reading(place, reviews),
        "source": detail.get("source", "mock"),
    })


@places_bp.route("/saved", methods=["GET"])
def api_saved_places():
    user_id = request.args.get("user_id", "user_demo")
    limit = _int_arg("limit", 50)
    places = list_saved_reading_places(user_id, limit)
    return jsonify({"ok": True, "places": places, "count": len(places)})


@places_bp.route("/save", methods=["POST"])
def api_save_place():
    data = request.get_json() or {}
    result = save_reading_place(data.get("user_id", "user_demo"), data)
    status = 201 if result.get("ok") and not result.get("duplicated") else 200
    return jsonify(result), status


@places_bp.route("/photo", methods=["GET"])
def api_place_photo():
    photo_reference = request.args.get("photo_reference", "")
    max_width = _int_arg("max_width", 640)
    url = get_google_photo_url(photo_reference, max_width)
    if not url:
        return jsonify({"ok": False, "error": "photo_reference 또는 Google Maps API 키가 필요합니다."}), 400
    return jsonify({"ok": True, "photo_url": url})


@places_bp.route("/all", methods=["GET"])
def api_all_spots():
    spot_type = request.args.get("type", "all")
    city = request.args.get("city", "all")
    limit = _int_arg("limit", 20)
    spots = get_all_spots(spot_type, city, limit)
    return jsonify({"ok": True, "spots": spots, "count": len(spots)})


@places_bp.route("/nearby", methods=["GET"])
def api_nearby():
    try:
        lat = float(request.args.get("lat", 37.5665))
        lng = float(request.args.get("lng", 126.9780))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "lat, lng 값이 필요합니다."}), 400

    radius = float(request.args.get("radius", 50))
    spot_type = request.args.get("type", "all")
    limit = _int_arg("limit", 10)
    spots = search_nearby(lat, lng, radius, spot_type, limit)
    return jsonify({
        "ok": True,
        "spots": spots,
        "count": len(spots),
        "center": {"lat": lat, "lng": lng},
    })


@places_bp.route("/<place_id>", methods=["GET"])
def api_get_spot(place_id):
    spot = get_spot(place_id)
    if not spot:
        detail = get_google_place_detail(place_id)
        place = detail.get("place")
        if place:
            return jsonify({"ok": True, "spot": place, "place": place, "source": detail.get("source", "mock")})
        return jsonify({"ok": False, "error": "장소를 찾을 수 없습니다."}), 404
    return jsonify({"ok": True, "spot": spot})


@places_bp.route("/<place_id>", methods=["PUT"])
def api_update_place(place_id):
    data = request.get_json() or {}
    result = update_reading_place(place_id, data.get("user_id", "user_demo"), data)
    return jsonify(result), (200 if result.get("ok") else 404)


@places_bp.route("/<place_id>", methods=["DELETE"])
def api_delete_place(place_id):
    result = delete_reading_place(place_id, request.args.get("user_id", "user_demo"))
    return jsonify(result), (200 if result.get("ok") else 404)


@places_bp.route("/<place_id>/checkin", methods=["POST"])
def api_checkin(place_id):
    data = request.get_json() or {}
    result = checkin_spot(place_id, data.get("user_id", "user_demo"), data.get("memo", ""))
    return jsonify(result)


@places_bp.route("/<place_id>/reviews", methods=["GET"])
def api_reviews(place_id):
    limit = _int_arg("limit", 20)
    reviews = list_place_reviews(place_id, limit)
    return jsonify({"ok": True, "reviews": reviews, "count": len(reviews)})


@places_bp.route("/<place_id>/review", methods=["POST"])
def api_review(place_id):
    data = request.get_json() or {}
    if not (data.get("content") or data.get("text") or "").strip():
        return jsonify({"ok": False, "error": "후기 내용을 입력해주세요."}), 400
    return jsonify(add_place_review(place_id, data.get("user_id", "user_demo"), data))


@places_bp.route("/cities", methods=["GET"])
def api_cities():
    return jsonify({"ok": True, "cities": get_cities()})


@places_bp.route("/status", methods=["GET"])
def api_status():
    return jsonify({"ok": True, **get_map_status()})
