"""
LUMA — Flask 앱 팩토리
모든 Blueprint 등록 + MySQL 초기화 + 페이지 라우트
"""
import os
import json
from flask import Flask, render_template, jsonify, send_from_directory

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

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
    _try_bp("app.routes.lounge_books","lounge_books_bp","/api/v2/lounge")
    _try_bp("app.routes.community_api","community_api_bp","/api/v2/community")

    # MySQL API (/api/v2/*)
    _try_bp("app.routes.mysql_api",   "mysql_bp",      "/api/v2")

    # 페이지 라우트
    @app.route("/landing")
    def landing():       return render_template("landing.html")

    @app.route("/")
    def dashboard():
        # Client-side API calls hydrate this page with the authenticated user.
        # Keeping the server payload empty prevents user_demo data from flashing
        # for a different logged-in reader.
        stats = {
            "total_books": 0,
            "total_memos": 0,
            "reading_streak": 0,
            "total_pages": 0,
            "this_month": 0,
            "connections": 0,
        }
        return render_template(
            "dashboard.html",
            constellation=json.dumps({"nodes": [], "links": []}, ensure_ascii=False),
            stats=stats,
            insights=[],
        )

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

    @app.route("/ocr", methods=["GET"])
    def ocr():           return render_template("ocr.html")

    @app.route("/ocr", methods=["POST"])
    def ocr_upload_root():
        from app.routes.ocr import ocr_google_upload

        return ocr_google_upload()

    @app.route("/ocr/health")
    @app.route("/health/ocr")
    def ocr_health_root():
        from app.services.google_vision_ocr import get_google_vision_status

        return jsonify({"success": True, **get_google_vision_status()})

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
