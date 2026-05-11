from flask import Blueprint, render_template, jsonify
import json, random, math

main_bp = Blueprint('main', __name__)

@main_bp.route('/lounge')
def lounge():
    return render_template('lounge.html')

@main_bp.route('/discover')
def discover():
    return render_template('lounge.html')


def generate_mock_constellation():
    """별자리 노드 & 링크 데이터 생성 (실제로는 DB에서 조회)"""
    books = [
        {"id": 1, "title": "사피엔스", "author": "유발 하라리", "genre": "역사", "memos": 12},
        {"id": 2, "title": "코스모스", "author": "칼 세이건", "genre": "과학", "memos": 8},
        {"id": 3, "title": "어린왕자", "author": "생텍쥐페리", "genre": "문학", "memos": 15},
        {"id": 4, "title": "총균쇠", "author": "재러드 다이아몬드", "genre": "역사", "memos": 6},
        {"id": 5, "title": "멋진 신세계", "author": "올더스 헉슬리", "genre": "SF", "memos": 9},
        {"id": 6, "title": "1984", "author": "조지 오웰", "genre": "SF", "memos": 11},
        {"id": 7, "title": "데미안", "author": "헤르만 헤세", "genre": "문학", "memos": 7},
        {"id": 8, "title": "페스트", "author": "알베르 카뮈", "genre": "문학", "memos": 5},
    ]
    genre_colors = {
        "역사": "#C17F3B",
        "과학": "#4A9ECC",
        "문학": "#7EC87E",
        "SF": "#9B7EC8",
    }
    nodes = []
    for b in books:
        nodes.append({
            "id": b["id"],
            "title": b["title"],
            "author": b["author"],
            "genre": b["genre"],
            "memos": b["memos"],
            "color": genre_colors.get(b["genre"], "#E0E0E0"),
            "size": 8 + b["memos"] * 1.5,
        })
    links = [
        {"source": 1, "target": 4, "strength": 0.9, "insight": "문명의 불평등 기원을 바라보는 두 시각"},
        {"source": 2, "target": 5, "strength": 0.7, "insight": "우주와 인류의 미래에 대한 상상력"},
        {"source": 3, "target": 7, "strength": 0.85, "insight": "자아 탐색과 존재의 의미"},
        {"source": 5, "target": 6, "strength": 0.95, "insight": "전체주의와 개인 자유의 충돌"},
        {"source": 7, "target": 8, "strength": 0.6, "insight": "실존과 운명 앞에 선 인간"},
        {"source": 1, "target": 2, "strength": 0.5, "insight": "인류 역사와 우주적 시간 스케일"},
        {"source": 3, "target": 8, "strength": 0.4, "insight": "삶의 본질에 대한 순수한 질문"},
    ]
    return {"nodes": nodes, "links": links}

@main_bp.route('/')
def index():
    try:
        from app.services.reading_service import get_constellation
        constellation_data = get_constellation("user_demo")
        for node in constellation_data.get("nodes", []):
            node["title"] = node.get("title") or node.get("label", "")
            node["memos"] = node.get("memos", 0)
        for link in constellation_data.get("links", []):
            link["insight"] = link.get("insight") or link.get("theme", "")
    except Exception:
        constellation_data = generate_mock_constellation()
    try:
        from app.services.shelf_service import get_shelf
        from app.services.user_service import get_user_stats
        shelf = get_shelf("user_demo")
        shelf_stats = shelf.get("stats", {})
        user_stats = get_user_stats("user_demo")
        stats = {
            "total_books": shelf_stats.get("total", 23),
            "total_memos": user_stats.get("memos", 147),
            "reading_streak": shelf_stats.get("reading_streak", 0),
            "total_pages": shelf_stats.get("total_pages", 6840),
            "this_month": shelf_stats.get("this_month", 3),
            "connections": user_stats.get("connections", 18),
        }
    except Exception:
        stats = {
            "total_books": 23,
            "total_memos": 147,
            "reading_streak": 0,
            "total_pages": 6840,
            "this_month": 3,
            "connections": 18,
        }
    recent_insights = [
        {"book1": "사피엔스", "book2": "총균쇠", "text": "문명의 흥망성쇠는 지리적 조건과 집단 허구의 결합으로 설명된다."},
        {"book1": "코스모스", "book2": "멋진 신세계", "text": "과학의 발전은 자유를 열어주기도, 새로운 통제의 도구가 되기도 한다."},
        {"book1": "데미안", "book2": "어린왕자", "text": "진정한 성장은 타인의 시선이 아닌 내면의 목소리를 따를 때 시작된다."},
    ]
    return render_template('dashboard.html',
                           constellation=json.dumps(constellation_data, ensure_ascii=False),
                           stats=stats,
                           insights=recent_insights)
