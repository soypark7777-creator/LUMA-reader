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
    # The browser reloads dashboard data through /api/v2 with the logged-in
    # user's bearer token. Do not render user_demo data here, because it can
    # briefly expose another reader's books before the client fetch finishes.
    stats = {
        "total_books": 0,
        "total_memos": 0,
        "reading_streak": 0,
        "total_pages": 0,
        "this_month": 0,
        "connections": 0,
    }
    return render_template(
        'dashboard.html',
        constellation=json.dumps({"nodes": [], "links": []}, ensure_ascii=False),
        stats=stats,
        insights=[],
    )
