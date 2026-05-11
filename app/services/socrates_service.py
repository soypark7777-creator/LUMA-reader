from typing import Optional
"""
AI 마음 정리사 서비스 — 소크라테스식 대화로 생각 정제
────────────────────────────────────────
- 책 구절 입력 → 5단계 심화 질문
- 강제 연결 인사이트 생성
- 나만의 지식 사전 구축
- 실천 액션 플랜 생성
"""
import uuid
from datetime import datetime

# ── 소크라테스 대화 세션 저장소 ──────────────────────────
_sessions: dict[str, dict] = {}
_action_plans: list[dict] = []
_my_dictionary: list[dict] = []


# ── 1. 소크라테스 대화 시작 ──────────────────────────────

SOCRATES_STAGES = [
    "이 문장이 처음 눈에 들어온 순간 어떤 감정이 느껴졌나요?",
    "이 생각과 연결되는 당신의 경험이 있다면 무엇인가요?",
    "만약 이 생각이 틀렸다면, 어떤 반론이 가능할까요?",
    "이 통찰을 오늘 당장 삶에 적용한다면 어떻게 하겠어요?",
    "이 문장을 한 줄로 '나만의 언어'로 다시 써보면 어떻게 될까요?",
]

def start_session(data: dict) -> dict:
    """소크라테스 대화 세션 시작"""
    session_id = f"sess_{uuid.uuid4().hex[:6]}"
    session = {
        "session_id":  session_id,
        "user_id":     data.get("user_id", "user_demo"),
        "book_title":  data.get("book_title", ""),
        "passage":     data.get("passage", ""),      # 원문 구절
        "stage":       0,                              # 현재 단계 (0~4)
        "exchanges":   [],                             # [{q, a}]
        "created_at":  datetime.now().isoformat(),
        "completed":   False,
        "final_insight": None,
    }
    _sessions[session_id] = session

    # 첫 번째 질문 생성
    first_q = _generate_question(session, stage=0)
    session["exchanges"].append({"q": first_q, "a": None, "stage": 0})

    return {"session_id": session_id, "question": first_q, "stage": 0, "total_stages": 5}


def answer_session(session_id: str, answer: str) -> dict:
    """사용자 답변 → 다음 질문 생성"""
    session = _sessions.get(session_id)
    if not session:
        return {"ok": False, "error": "세션 없음"}

    # 현재 교환에 답변 저장
    current = session["exchanges"][-1]
    current["a"] = answer

    next_stage = session["stage"] + 1

    if next_stage >= 5:
        # 5단계 완료 → 최종 인사이트 생성
        session["completed"] = True
        insight = _generate_final_insight(session)
        session["final_insight"] = insight
        return {
            "ok":        True,
            "completed": True,
            "insight":   insight,
            "stage":     next_stage,
        }

    session["stage"] = next_stage
    next_q = _generate_question(session, stage=next_stage)
    session["exchanges"].append({"q": next_q, "a": None, "stage": next_stage})

    return {
        "ok":       True,
        "completed":False,
        "question": next_q,
        "stage":    next_stage,
        "total_stages": 5,
        "progress": f"{next_stage}/5",
    }


def get_session(session_id: str) -> Optional[dict]:
    return _sessions.get(session_id)


# ── 2. 강제 연결 인사이트 ────────────────────────────────

def force_connect(data: dict) -> dict:
    """두 개의 메모/구절을 강제로 연결해 새 인사이트 생성"""
    from app.services.gemini_service import _call_gemini, _parse_json_safe

    text_a     = data.get("text_a", "")
    book_a     = data.get("book_a", "")
    text_b     = data.get("text_b", "")
    book_b     = data.get("book_b", "")

    prompt = f"""서로 다른 두 책의 생각을 연결해서 새로운 인사이트를 만들어주세요.

책 A: 《{book_a}》
생각 A: {text_a}

책 B: 《{book_b}》
생각 B: {text_b}

이 두 생각이 어떻게 연결되는지 분석하고, 그 연결이 만들어내는 새로운 통찰을 알려주세요.

JSON 형식으로만 응답:
{{
  "connection_type": "연결 유형 (대립/보완/심화/유추)",
  "bridge":          "연결 고리 키워드",
  "insight":         "두 생각이 만나서 생기는 새 통찰 (2-3문장)",
  "metaphor":        "이 연결을 설명하는 비유 한 문장",
  "strength":        0.0~1.0,
  "quote":           "이 연결을 담은 나만의 한 줄"
}}"""

    raw    = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and "insight" in parsed:
        return {**parsed, "book_a": book_a, "book_b": book_b, "source": "gemini"}

    return {
        "connection_type": "보완",
        "bridge":          "인간의 이해 방식",
        "insight":         f"《{book_a}》의 생각과 《{book_b}》의 생각은 서로 다른 방향에서 같은 진실을 가리키고 있습니다. 하나는 이성으로, 다른 하나는 감성으로 접근하지만, 결국 같은 지점에서 만납니다.",
        "metaphor":        "두 개의 산 정상에서 서로 다른 길로 올라갔지만, 정상에서 같은 하늘을 봅니다.",
        "strength":        0.7,
        "quote":           "다른 언어로 쓰인 같은 이야기.",
        "book_a":          book_a,
        "book_b":          book_b,
        "source":          "mock",
    }


# ── 3. 나만의 지식 사전 ───────────────────────────────────

def build_my_definition(data: dict) -> dict:
    """여러 책에서 수집한 생각으로 나만의 개념 정의"""
    from app.services.gemini_service import _call_gemini, _parse_json_safe

    concept   = data.get("concept", "자유")
    sources   = data.get("sources", [])   # [{book, text}]
    user_thought = data.get("user_thought", "")

    prompt = f"""여러 책에서 수집한 생각들을 통합해서 '{concept}'에 대한 나만의 정의를 만들어주세요.

개념: {concept}

수집한 생각들:
{chr(10).join(f"- 《{s.get('book','')}》: {s.get('text','')}" for s in sources)}

사용자의 생각: {user_thought}

JSON 형식으로만 응답:
{{
  "concept":       "{concept}",
  "my_definition": "나만의 정의 (2-3문장)",
  "core_words":    ["핵심 단어1", "핵심 단어2", "핵심 단어3"],
  "opposite":      "반대 개념",
  "personal_note": "이 정의가 삶에서 의미하는 것",
  "quote_to_live_by": "이 개념을 담은 삶의 문장"
}}"""

    raw    = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if not parsed or "my_definition" not in parsed:
        parsed = {
            "concept":          concept,
            "my_definition":    f"{concept}란 단순히 외부에서 주어지는 것이 아니라, 여러 책을 읽으며 스스로 발견하고 정의해가는 것입니다. {len(sources)}권의 책이 각각 다른 시각으로 {concept}을 가리켰지만, 결국 공통적으로 말하는 것은 하나입니다.",
            "core_words":       [concept, "탐구", "발견"],
            "opposite":         f"고정된 {concept}",
            "personal_note":    f"이 정의는 나의 {len(sources)}권 독서 여정에서 탄생했습니다.",
            "quote_to_live_by": f"{concept}은 찾는 것이 아니라 만들어가는 것이다.",
            "source":           "mock",
        }

    entry = {
        "entry_id":  f"dict_{uuid.uuid4().hex[:6]}",
        "user_id":   data.get("user_id", "user_demo"),
        "sources":   sources,
        "created_at":datetime.now().isoformat(),
        **parsed,
    }
    _my_dictionary.append(entry)
    return entry


def get_my_dictionary(user_id: str) -> list[dict]:
    return [e for e in _my_dictionary if e.get("user_id") == user_id]


# ── 4. 실천 액션 플랜 ────────────────────────────────────

def create_action_plan(data: dict) -> dict:
    """독서 인사이트 → 실천 계획으로 변환"""
    from app.services.gemini_service import _call_gemini, _parse_json_safe

    insight    = data.get("insight", "")
    book_title = data.get("book_title", "")

    prompt = f"""독서에서 얻은 인사이트를 실천 계획으로 만들어주세요.

책: 《{book_title}》
인사이트: {insight}

JSON 형식으로만 응답:
{{
  "summary":     "실천의 핵심 한 줄",
  "today":       "오늘 당장 할 수 있는 것 (구체적)",
  "this_week":   "이번 주 안에 할 것 (구체적)",
  "this_month":  "이번 달 안에 할 것 (구체적)",
  "mindset":     "이 실천을 위해 필요한 마음가짐",
  "check_in_days": 7
}}"""

    raw    = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if not parsed or "today" not in parsed:
        parsed = {
            "summary":        "작은 실천이 큰 변화를 만든다",
            "today":          "이 인사이트를 일기에 적고, 오늘 하루 이 관점으로 세상을 바라보기",
            "this_week":      "관련 주제로 주변 사람과 대화 나눠보기",
            "this_month":     "이 인사이트를 실제로 적용한 사례를 3가지 만들어보기",
            "mindset":        "결과보다 과정을, 완벽보다 꾸준함을",
            "check_in_days":  7,
        }

    plan = {
        "plan_id":   f"plan_{uuid.uuid4().hex[:6]}",
        "user_id":   data.get("user_id", "user_demo"),
        "book_title":book_title,
        "insight":   insight,
        "status":    "active",
        "created_at":datetime.now().isoformat(),
        "checked_in":False,
        **parsed,
    }
    _action_plans.append(plan)
    return plan


def get_action_plans(user_id: str) -> list[dict]:
    return [p for p in _action_plans if p.get("user_id") == user_id]


def checkin_plan(plan_id: str, note: str = "") -> dict:
    plan = next((p for p in _action_plans if p["plan_id"] == plan_id), None)
    if not plan:
        return {"ok": False}
    plan["checked_in"] = True
    plan["checkin_note"] = note
    plan["checkin_at"] = datetime.now().isoformat()
    return {"ok": True, "plan": plan}


# ── 내부 헬퍼 ─────────────────────────────────────────────

def _generate_question(session: dict, stage: int) -> str:
    from app.services.gemini_service import _call_gemini

    passage = session["passage"]
    book    = session["book_title"]
    prev    = session["exchanges"]

    # 이전 답변 맥락
    context = ""
    if prev and prev[-1].get("a"):
        context = f"\n이전 답변: {prev[-1]['a']}"

    prompt = f"""독서 소크라테스 코치입니다. 아래 구절에 대해 심화 질문을 해주세요.

책: 《{book}》
구절: {passage}
현재 단계: {stage+1}/5{context}

단계별 목적:
1단계=감정 탐색, 2단계=경험 연결, 3단계=비판적 사고, 4단계=실천 적용, 5단계=자기 언어화

{stage+1}단계에 맞는 질문 하나만 출력하세요. (설명 없이 질문만)"""

    q = _call_gemini(prompt)
    if q and len(q) > 10:
        return q.strip()

    return SOCRATES_STAGES[stage]


def _generate_final_insight(session: dict) -> dict:
    from app.services.gemini_service import _call_gemini, _parse_json_safe

    exchanges_text = "\n".join(
        f"Q: {ex['q']}\nA: {ex.get('a','')}"
        for ex in session["exchanges"]
        if ex.get("a")
    )

    prompt = f"""소크라테스식 대화 5단계가 완료되었습니다. 대화를 분석해서 최종 인사이트를 생성해주세요.

책: 《{session['book_title']}》
원문: {session['passage']}

대화 내용:
{exchanges_text}

JSON 형식으로만 응답:
{{
  "refined_thought": "정제된 생각 (2-3문장)",
  "personal_meaning": "이 생각이 이 사람에게 갖는 개인적 의미",
  "my_sentence": "본인 언어로 재작성된 핵심 문장",
  "tags": ["태그1", "태그2", "태그3"],
  "next_action": "바로 할 수 있는 작은 실천"
}}"""

    raw    = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and "refined_thought" in parsed:
        return {**parsed, "source": "gemini"}

    return {
        "refined_thought":  "이 책의 구절과 나의 경험이 만나 새로운 이해를 만들어냈습니다. 5번의 질문을 통해 처음의 막연한 감동이 구체적인 생각으로 정제되었습니다.",
        "personal_meaning": "이 생각은 당신이 삶을 바라보는 고유한 시각을 반영합니다.",
        "my_sentence":      session["passage"][:50] + "... — 그것은 결국 나에 관한 이야기였다.",
        "tags":             ["독서", "성찰", "성장"],
        "next_action":      "이 생각을 노트에 적고 일주일 후 다시 읽어보세요.",
        "source":           "mock",
    }


