from flask import Blueprint, jsonify, request

api_bp = Blueprint('api', __name__)

@api_bp.route('/insight/reframe', methods=['POST'])
def reframe_insight():
    """메모를 받아 AI 분석 후 별자리 연결 데이터 리턴"""
    data = request.get_json()
    memo = data.get('memo', '')
    # TODO: Gemini API 연동
    return jsonify({
        "status": "ok",
        "insight": f"'{memo[:20]}...' 와 연결된 새로운 관점이 발견되었습니다.",
        "connected_nodes": [1, 3]
    })

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    return jsonify({
        "total_books": 23,
        "total_memos": 147,
        "reading_streak": 12,
    })


@api_bp.route('/system/status', methods=['GET'])
def system_status():
    """구버전 테스트/클라이언트용 시스템 상태."""
    try:
        from app.core.config import settings
        gemini = "connected" if settings.gemini_ready else "mock"
        maps = "connected" if getattr(settings, "maps_ready", False) else "mock"
    except Exception:
        gemini = "mock"
        maps = "mock"
    try:
        from app.services.firebase_service import is_firebase_ready
        firebase = "connected" if is_firebase_ready() else "mock"
    except Exception:
        firebase = "mock"
    return jsonify({
        "ok": True,
        "apis": {
            "gemini": gemini,
            "firebase": firebase,
            "maps": maps,
        },
    })
