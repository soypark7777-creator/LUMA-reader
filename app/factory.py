"""
LUMA — Flask 앱 팩토리
모든 Blueprint 등록 + MySQL 초기화 + 페이지 라우트
"""
import os
import json
from flask import Flask, render_template, jsonify, send_from_directory

try:
    from flask_cors import CORS
    _has_cors = True
except ImportError:
    _has_cors = False


def create_app() -> Flask:
    # MySQL 초기화
    try:
        from app.db import init_db
        from app.schema import create_database, create_all_tables, seed_data
        if init_db():
            create_database()
            if create_all_tables():
                seed_data()
    except Exception as e:
        print(f"[WARN] DB 초기화 건너뜀 (Mock 모드): {e}")

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"]       = os.getenv("SECRET_KEY", "luma-dev-secret-2025")
    app.config["JSON_AS_ASCII"]    = False
    app.config["JSONIFY_MIMETYPE"] = "application/json; charset=utf-8"
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    if _has_cors:
        CORS(app)

    @app.route("/asset/<path:filename>")
    def asset_file(filename):
        return send_from_directory(os.path.join(app.root_path, "asset"), filename)

    def _try_bp(module_path, attr, prefix=None):
        try:
            import importlib
            mod = importlib.import_module(module_path)
            bp  = getattr(mod, attr)
            if prefix:
                app.register_blueprint(bp, url_prefix=prefix)
            else:
                app.register_blueprint(bp)
        except Exception as e:
            print(f"[WARN] [{attr}] 로드 실패: {e}")

    # 기존 Mock API
    _try_bp("app.routes.main",        "main_bp")
    _try_bp("app.routes.api",         "api_bp",        "/api")
    _try_bp("app.routes.memos",       "memos_bp",      "/api/memos")
    _try_bp("app.routes.ai",          "ai_bp",         "/api/ai")
    _try_bp("app.routes.community",   "community_bp",  "/community")
    _try_bp("app.routes.places",      "places_bp",     "/api/places")
    _try_bp("app.routes.auth",        "auth_bp",       "/auth")
    _try_bp("app.routes.books",       "books_bp",      "/api/books")
    _try_bp("app.routes.ocr",         "ocr_bp",        "/api/ocr")
    # _try_bp("app.routes.live", "live_bp", "/live/api")  # new_features.py로 대체
    _try_bp("app.routes.new_features","new_features_bp","/api")

    # MySQL API (/api/v2/*)
    _try_bp("app.routes.mysql_api",   "mysql_bp",      "/api/v2")

    # 페이지 라우트
    @app.route("/landing")
    def landing():       return render_template("landing.html")

    @app.route("/")
    def dashboard():
        try:
            from app.services.reading_service import get_constellation
            constellation = get_constellation("user_demo")
            for node in constellation.get("nodes", []):
                node["title"] = node.get("title") or node.get("label", "")
                node["memos"] = node.get("memos", 0)
            for link in constellation.get("links", []):
                link["insight"] = link.get("insight") or link.get("theme", "")
            from app.services.shelf_service import get_shelf
            from app.services.user_service import get_user_stats
            shelf_stats = get_shelf("user_demo").get("stats", {})
            user_stats = get_user_stats("user_demo")
            stats = {
                "total_books": shelf_stats.get("total", constellation.get("total_books", 0)),
                "total_memos": user_stats.get("memos", constellation.get("total_emotions", 0)),
                "reading_streak": shelf_stats.get("reading_streak", 0),
                "total_pages": shelf_stats.get("total_pages", 0),
                "this_month": shelf_stats.get("this_month", constellation.get("this_month_reads", 0)),
                "connections": user_stats.get("connections", constellation.get("total_links", 0)),
            }
            insights = [
                {
                    "book1": link.get("source", ""),
                    "book2": link.get("target", ""),
                    "text": link.get("theme", "새로운 연결을 탐색 중입니다."),
                }
                for link in constellation.get("links", [])[:3]
            ]
            return render_template(
                "dashboard.html",
                constellation=json.dumps(constellation, ensure_ascii=False),
                stats=stats,
                insights=insights,
            )
        except Exception:
            return render_template("dashboard.html", constellation='{"nodes":[],"links":[]}', stats={}, insights=[])

    @app.route("/heart")
    def heart():         return render_template("heart.html")

    @app.route("/live")
    def live_page():
        try:
            from app.services.live_backend_service import list_rooms
            rooms = list_rooms("active")
        except Exception:
            rooms = []
        return render_template("live.html", rooms=rooms, room=None, mode="lobby")

    @app.route("/live/<room_id>")
    def live_room_page(room_id):
        try:
            from app.services.live_backend_service import get_room, list_rooms
            room = get_room(room_id)
            if room:
                return render_template("live.html", rooms=list_rooms("active"), room=room, mode="room")
        except Exception:
            pass
        return render_template("live.html", rooms=[], room=None, mode="lobby", error="방을 찾을 수 없습니다.")

    @app.route("/social")
    def social():        return render_template("social.html")

    @app.route("/socrates")
    def socrates():      return render_template("socrates.html")

    @app.route("/deepdive")
    def deepdive():
        try:
            from app.services.shelf_service import get_shelf
            streak = get_shelf("user_demo").get("stats", {}).get("reading_streak", 0)
        except Exception:
            streak = 12
        return render_template("deepdive.html", streak=streak)

    @app.route("/ocr")
    def ocr():           return render_template("ocr.html")

    @app.route("/lounge")
    def lounge():
        try:             return render_template("lounge.html")
        except:          return render_template("dashboard.html")

    @app.route("/discover")
    def discover():
        try:             return render_template("lounge.html")
        except:          return render_template("dashboard.html")

    @app.route("/profile")
    def profile():       return render_template("profile.html")

    @app.route("/health")
    def health():
        try:
            from app.db import is_connected
            db_status = "connected" if is_connected() else "mock"
        except:
            db_status = "unknown"
        return jsonify({
            "ok": True,
            "status": "healthy",
            "service": "LUMA",
            "mysql": db_status,
            "app": "LUMA v2.0",
        })

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"ok": False, "error": "404 Not Found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"ok": False, "error": "500 Server Error"}), 500

    return app
