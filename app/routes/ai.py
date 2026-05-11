"""
AI 전용 API 라우터
────────────────────────────────────────
POST /api/ai/analyze        메모 저장 즉시 AI 분석 + 강제연결
POST /api/ai/reframe        메모 심화 질문 생성
POST /api/ai/cross-insight  두 메모 직접 지정해서 인사이트 생성
GET  /api/ai/connections    전체 메모 연결 맵 조회
GET  /api/ai/status         Gemini 연결 상태 확인
POST /api/ai/discussion     모임 토론 가이드 질문 생성
POST /api/ai/report         모임 자동 보고서 생성
"""

from flask import Blueprint, request, jsonify
from app.services.gemini_service import (
    generate_cross_insight,
    extract_keywords,
    generate_reframe_question,
    analyze_memo_theme,
    generate_discussion_guide,
    summarize_meeting,
    get_ai_status,
)
from app.services.embedding_service import (
    compute_similarity,
    find_best_cross_pair,
    rank_all_connections,
)
from app.services.firebase_service import save_memo, get_memos

ai_bp = Blueprint('ai', __name__)


def _uid(data: dict | None = None) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            from app.services.user_service import verify_token
            payload = verify_token(auth[7:])
            if payload:
                return payload.get("user_id", "user_demo")
        except Exception:
            pass
    data = data or {}
    return request.args.get("user_id") or data.get("user_id") or "user_demo"


def _get_user_memos(user_id: str, limit: int = 100) -> list[dict]:
    try:
        from app.services.reading_service import list_memos
        result = list_memos(user_id, limit=limit)
        memos = result.get("memos", [])
        if memos:
            return memos
    except Exception:
        pass
    return get_memos(user_id, limit=limit)


def _get_memo(user_id: str, memo_id: str) -> dict | None:
    if memo_id in (None, ""):
        return None
    memo_id = str(memo_id)
    memos = _get_user_memos(user_id)
    if memo_id.isdigit():
        idx = int(memo_id)
        if 0 <= idx < len(memos):
            return memos[idx]
    return next((m for m in memos if str(m.get("memo_id") or m.get("id")) == memo_id), None)


def _memo_payload(memo: dict) -> dict:
    return {
        "memo_id": memo.get("memo_id") or memo.get("id"),
        "content": memo.get("content") or memo.get("text") or "",
        "book_title": memo.get("book_title") or "미분류",
        "tags": memo.get("tags") or [],
    }


def _as_question_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, dict):
        question = value.get("question")
        return [question] if question else []
    if value:
        return [str(value)]
    return []


# ══════════════════════════════════════════════════════════════
#  1. 메모 저장 + 즉시 AI 분석 (핵심 통합 엔드포인트)
# ══════════════════════════════════════════════════════════════

@ai_bp.route('/analyze', methods=['POST'])
def analyze_and_save():
    """
    메모를 저장하고 즉시 AI 분석 수행:
    1. 메모 저장
    2. 키워드 추출
    3. 주제 분석
    4. 강제연결 대상 탐색
    5. Cross-domain Insight 생성
    6. 심화 질문 생성
    """
    data = request.get_json()

    user_id = _uid(data)
    memo = _get_memo(user_id, data.get("memo_id"))

    if memo:
        memo = _memo_payload(memo)
        content = memo["content"].strip()
        book_title = memo["book_title"]
        tags = memo["tags"]
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]

        keywords = extract_keywords(content, book_title)
        theme_info = analyze_memo_theme(content)
        reframe_q = generate_reframe_question(content, book_title)

        return jsonify({
            "ok": True,
            "memo": memo,
            "keywords": keywords,
            "theme": theme_info.get("theme", "") if isinstance(theme_info, dict) else theme_info,
            "theme_info": theme_info,
            "summary": theme_info.get("summary", "") if isinstance(theme_info, dict) else "",
            "emotion": theme_info.get("emotion", "") if isinstance(theme_info, dict) else "",
            "depth_score": theme_info.get("depth_score", 0) if isinstance(theme_info, dict) else 0,
            "questions": _as_question_list(reframe_q),
            "reframe": reframe_q,
        })

    content    = (data.get('content') or '').strip()
    book_title = data.get('book_title', '미분류')
    tags       = data.get('tags', [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',') if t.strip()]

    if not content:
        return jsonify({"ok": False, "error": "내용을 입력해주세요."}), 400

    # ── Step 1: 메모 저장 ──
    memo_data = {
        "user_id":    user_id,
        "book_id":    data.get('book_id', 'book_unknown'),
        "book_title": book_title,
        "content":    content,
        "page_number":data.get('page_number'),
        "tags":       tags,
        "mood":       data.get('mood', 'neutral'),
        "is_public":  data.get('is_public', False),
    }
    saved_memo = save_memo(memo_data)

    # ── Step 2: 키워드 추출 ──
    keywords = extract_keywords(content, book_title)

    # ── Step 3: 주제 분석 ──
    theme_info = analyze_memo_theme(content)

    # ── Step 4: 강제연결 대상 탐색 ──
    cross_target = find_best_cross_pair(saved_memo, user_id)

    # ── Step 5 & 6: 인사이트 + 질문 생성 ──
    cross_insight  = None
    reframe_q      = generate_reframe_question(content, book_title)

    if cross_target:
        cross_insight = generate_cross_insight(
            memo1={"content": content, "book_title": book_title, "tags": tags},
            memo2={"content": cross_target.get("content",""), "book_title": cross_target.get("book_title",""), "tags": cross_target.get("tags",[])},
        )
        cross_insight["linked_memo_id"]    = cross_target["memo_id"]
        cross_insight["linked_book_title"] = cross_target.get("book_title", "")
        cross_insight["similarity"]        = cross_target.get("_similarity", 0)

    return jsonify({
        "ok": True,
        "memo":          saved_memo,
        "keywords":      keywords,
        "theme":         theme_info,
        "cross_insight": cross_insight,
        "reframe":       reframe_q,
        "has_connection": cross_insight is not None,
    }), 201


# ══════════════════════════════════════════════════════════════
#  2. 메모 심화 질문 (Reframe)
# ══════════════════════════════════════════════════════════════

@ai_bp.route('/reframe', methods=['POST'])
def reframe():
    """기존 메모에 대한 심화 질문 생성"""
    data       = request.get_json()
    user_id    = _uid(data)
    memo       = _get_memo(user_id, data.get("memo_id"))
    if memo:
        memo = _memo_payload(memo)
    content    = ((memo or {}).get("content") or data.get('content') or '').strip()
    book_title = (memo or {}).get("book_title") or data.get('book_title', '')

    if not content:
        return jsonify({"ok": False, "error": "메모 내용이 필요합니다."}), 400

    result = generate_reframe_question(content, book_title)
    question = result.get("question") if isinstance(result, dict) else result
    return jsonify({"ok": True, "reframe": result, "question": question})


# ══════════════════════════════════════════════════════════════
#  3. 두 메모 직접 지정 → Cross-domain Insight
# ══════════════════════════════════════════════════════════════

@ai_bp.route('/cross-insight', methods=['POST'])
def cross_insight():
    """프론트에서 두 메모 ID를 직접 지정해 인사이트 요청"""
    data = request.get_json()
    user_id = _uid(data)
    memo1 = data.get('memo1')   # {content, book_title, tags}
    memo2 = data.get('memo2')

    if not memo1 and data.get("memo_id_1"):
        memo1 = _get_memo(user_id, data.get("memo_id_1"))
    if not memo2 and data.get("memo_id_2"):
        memo2 = _get_memo(user_id, data.get("memo_id_2"))

    if not memo1 or not memo2:
        return jsonify({"ok": False, "error": "memo1, memo2 데이터가 필요합니다."}), 400

    memo1 = _memo_payload(memo1)
    memo2 = _memo_payload(memo2)
    result = generate_cross_insight(memo1, memo2)
    return jsonify({
        "ok": True,
        "insight": result,
        "insight_text": result.get("insight") if isinstance(result, dict) else result,
        "cross_insight": result,
        "memo1": memo1,
        "memo2": memo2,
    })


# ══════════════════════════════════════════════════════════════
#  4. 전체 메모 연결 맵 (별자리 그래프용)
# ══════════════════════════════════════════════════════════════

@ai_bp.route('/connections', methods=['GET'])
def get_connections():
    """
    전체 메모 간 유사도 기반 연결 관계 반환
    → 프론트 별자리 그래프 링크 데이터에 활용
    """
    user_id = _uid()
    memos = [_memo_payload(m) for m in _get_user_memos(user_id, limit=50)]
    nodes = [
        {
            "id": m["memo_id"],
            "label": m["book_title"],
            "title": m["book_title"],
            "snippet": m["content"][:80],
        }
        for m in memos
        if m.get("memo_id")
    ]
    node_ids = {n["id"] for n in nodes}
    links = []
    for i in range(len(memos)):
        for j in range(i + 1, len(memos)):
            a, b = memos[i], memos[j]
            if not a.get("memo_id") or not b.get("memo_id"):
                continue
            score = compute_similarity(a, b)
            if a.get("book_title") == b.get("book_title"):
                score *= 0.5
            if score > 0.05 and a["memo_id"] in node_ids and b["memo_id"] in node_ids:
                links.append({
                    "source": a["memo_id"],
                    "target": b["memo_id"],
                    "similarity": round(score, 3),
                    "cross_domain": a.get("book_title") != b.get("book_title"),
                })
    links.sort(key=lambda item: item["similarity"], reverse=True)
    connections = [
        {
            "memo_a_id": link["source"],
            "memo_b_id": link["target"],
            "similarity": link["similarity"],
            "cross_domain": link["cross_domain"],
        }
        for link in links[:20]
    ]
    if not nodes and not links:
        connections = rank_all_connections(user_id)
    return jsonify({
        "ok": True,
        "nodes": nodes,
        "links": links[:20],
        "connections": connections,
        "count": len(connections),
    })


# ══════════════════════════════════════════════════════════════
#  5. AI 상태 확인
# ══════════════════════════════════════════════════════════════

@ai_bp.route('/status', methods=['GET'])
def ai_status():
    status = get_ai_status()
    return jsonify({"ok": True, **status})


# ══════════════════════════════════════════════════════════════
#  6. 모임 토론 가이드 질문
# ══════════════════════════════════════════════════════════════

@ai_bp.route('/discussion', methods=['POST'])
def discussion_guide():
    data            = request.get_json()
    book_title      = data.get('book_title', '')
    recent_messages = data.get('messages', [])
    guide_type      = data.get('guide_type', 'debate')

    result = generate_discussion_guide(book_title, recent_messages, guide_type)
    questions = _as_question_list(result)
    return jsonify({"ok": True, "guide": result, "questions": questions})


# ══════════════════════════════════════════════════════════════
#  7. 모임 자동 보고서
# ══════════════════════════════════════════════════════════════

@ai_bp.route('/report', methods=['POST'])
def meeting_report():
    data         = request.get_json()
    book_title   = data.get('book_title', '알 수 없는 책')
    messages     = data.get('messages', [])
    participants = data.get('participants', ['참여자'])

    if len(messages) < 2:
        return jsonify({"ok": False, "error": "보고서를 생성하려면 대화 내용이 필요합니다."}), 400

    report = summarize_meeting(book_title, messages, participants)
    return jsonify({"ok": True, "report": report})
