"""
Socrates discussion preparation helpers.

These functions extend the existing 5-step Socrates flow into a book
discussion preparation room while keeping API responses mock-safe.
"""
from __future__ import annotations

import re


DISCUSSION_MODES = {
    "appreciation": "감상형",
    "analysis": "분석형",
    "debate": "토론형",
    "life": "삶 연결형",
    "character": "인물 분석형",
}


def normalize_discussion_mode(mode: str | None) -> str:
    mode = (mode or "appreciation").strip()
    return mode if mode in DISCUSSION_MODES else "appreciation"


def get_mode_label(mode: str | None) -> str:
    return DISCUSSION_MODES[normalize_discussion_mode(mode)]


def _compact_text(text: str, limit: int = 80) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return text[:limit] + ("..." if len(text) > limit else "")


def _fallback_keywords(passage: str) -> list[str]:
    words = re.findall(r"[가-힣A-Za-z]{2,}", passage or "")
    stop = {"그리고", "하지만", "그래서", "이것은", "저것은", "나는", "우리는", "그들은"}
    result = []
    for word in words:
        word = re.sub(r"(은|는|이|가|을|를|과|와|로|으로|에게|에서|부터|까지)$", "", word)
        if word in stop or word in result:
            continue
        result.append(word)
        if len(result) >= 3:
            break
    return result or ["이해", "질문", "토론"]


def _json_from_gemini(prompt: str) -> dict | None:
    try:
        from app.services.gemini_service import _call_gemini, _parse_json_safe

        raw = _call_gemini(prompt, expect_json=True)
        parsed = _parse_json_safe(raw) if raw else None
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def generate_book_brief(passage: str, book_title: str = "", user_id: str = "user_demo") -> dict:
    prompt = f"""책 토론 전 이해 카드를 생성해주세요.
책: 《{book_title}》
구절: {passage}

JSON 형식으로만 응답:
{{
  "summary": ["핵심 요약 1", "핵심 요약 2", "핵심 요약 3"],
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "main_question": "이 구절이 독자에게 던지는 중심 질문",
  "discussion_hint": "독서모임에서 토론하면 좋은 관점"
}}"""
    parsed = _json_from_gemini(prompt)
    if parsed and isinstance(parsed.get("summary"), list) and parsed.get("main_question"):
        return {
            "summary": [str(item) for item in parsed.get("summary", [])[:3]],
            "keywords": [str(item) for item in parsed.get("keywords", [])[:5]],
            "main_question": str(parsed.get("main_question", "")),
            "discussion_hint": str(parsed.get("discussion_hint", "")),
            "source": "gemini",
        }

    preview = _compact_text(passage, 64)
    keywords = _fallback_keywords(passage)
    return {
        "summary": [
            f"《{book_title or '이 책'}》의 구절은 독자가 붙잡은 핵심 생각을 드러냅니다.",
            f"중심 문장은 '{preview}'로 요약할 수 있습니다.",
            "토론에서는 이 생각이 왜 마음에 남았는지부터 시작하면 좋습니다.",
        ],
        "keywords": keywords,
        "main_question": f"이 구절은 우리에게 어떤 {keywords[0]}의 의미를 묻고 있나요?",
        "discussion_hint": f"{', '.join(keywords[:3])}의 관계를 중심으로 이야기해볼 수 있습니다.",
        "source": "mock",
    }


def generate_discussion_questions(
    session_id: str = "",
    passage: str = "",
    book_title: str = "",
    insight: str | dict = "",
    discussion_mode: str = "appreciation",
    user_id: str = "user_demo",
) -> list[dict]:
    mode = normalize_discussion_mode(discussion_mode)
    if isinstance(insight, dict):
        insight_text = insight.get("refined_thought") or insight.get("my_sentence") or str(insight)
    else:
        insight_text = insight or ""

    prompt = f"""독서모임 질문 3~5개를 생성해주세요.
대화 모드: {get_mode_label(mode)}({mode})
책: 《{book_title}》
구절: {passage}
최종 인사이트: {insight_text}

JSON 형식으로만 응답:
{{
  "questions": [
    {{"type":"understanding","label":"이해 질문","question":"질문"}},
    {{"type":"emotion","label":"감정 질문","question":"질문"}},
    {{"type":"debate","label":"토론 질문","question":"질문"}}
  ]
}}"""
    parsed = _json_from_gemini(prompt)
    questions = parsed.get("questions") if parsed else None
    if isinstance(questions, list) and questions:
        return [
            {
                "type": str(q.get("type", "discussion")),
                "label": str(q.get("label", "토론 질문")),
                "question": str(q.get("question", "")),
            }
            for q in questions[:5]
            if isinstance(q, dict) and q.get("question")
        ]

    mode_question = {
        "appreciation": "이 구절에서 가장 오래 마음에 남는 표현은 무엇인가요?",
        "analysis": "이 구절의 핵심 주장과 근거를 나누면 어떻게 정리할 수 있나요?",
        "debate": "당신은 이 구절의 주장에 동의하나요, 반대하나요?",
        "life": "이 생각을 지금의 삶에 적용하면 무엇이 달라질까요?",
        "character": "이 구절 속 인물은 어떤 욕망이나 두려움으로 움직이고 있나요?",
    }
    return [
        {
            "type": "understanding",
            "label": "이해 질문",
            "question": "이 구절에서 가장 중요한 단어는 무엇인가요?",
        },
        {
            "type": "emotion",
            "label": "감정 질문",
            "question": "이 문장을 읽었을 때 어떤 감정이 먼저 들었나요?",
        },
        {
            "type": mode if mode in ("debate", "life", "analysis", "character") else "appreciation",
            "label": get_mode_label(mode),
            "question": mode_question[mode],
        },
    ]


def generate_debate_topic(
    passage: str = "",
    book_title: str = "",
    insight: str | dict = "",
    user_id: str = "user_demo",
) -> dict:
    prompt = f"""책 구절에서 찬반 토론이 가능한 주제를 생성해주세요.
책: 《{book_title}》
구절: {passage}
인사이트: {insight}

JSON 형식으로만 응답:
{{
  "topic": "찬반으로 나눌 수 있는 토론 명제",
  "pros": ["찬성 근거 1", "찬성 근거 2"],
  "cons": ["반대 근거 1", "반대 근거 2"],
  "neutral_question": "중립적으로 생각을 여는 질문"
}}"""
    parsed = _json_from_gemini(prompt)
    if parsed and parsed.get("topic"):
        return {
            "topic": str(parsed.get("topic", "")),
            "pros": [str(item) for item in parsed.get("pros", [])[:4]],
            "cons": [str(item) for item in parsed.get("cons", [])[:4]],
            "neutral_question": str(parsed.get("neutral_question", "")),
            "source": "gemini",
        }

    keywords = _fallback_keywords(passage)
    topic_key = next((kw for kw in keywords if kw not in ("인간", "사람", "우리")), keywords[0])
    return {
        "topic": f"삶에서 '{topic_key}'을 추구하는 일은 우리를 더 나은 방향으로 이끄는가?",
        "pros": [
            f"'{topic_key}'은 자기 삶을 선택하고 해석하게 합니다.",
            "선택과 해석의 힘은 인간의 존엄과 연결됩니다.",
        ],
        "cons": [
            f"'{topic_key}'은 때로 책임과 불안을 함께 가져옵니다.",
            "가치가 커질수록 현실의 복잡함을 더 크게 마주할 수 있습니다.",
        ],
        "neutral_question": f"'{topic_key}'과 안정 중 지금 당신에게 더 중요한 것은 무엇인가요?",
        "source": "mock",
    }


def build_lounge_card(
    passage: str = "",
    book_title: str = "",
    insight: str | dict = "",
    discussion_questions: list | None = None,
    debate: dict | None = None,
    user_id: str = "user_demo",
) -> dict:
    if isinstance(insight, dict):
        insight_text = (
            insight.get("my_sentence")
            or insight.get("refined_thought")
            or insight.get("personal_meaning")
            or ""
        )
        tags = insight.get("tags") or []
    else:
        insight_text = insight or ""
        tags = []

    questions = []
    for item in discussion_questions or []:
        if isinstance(item, dict) and item.get("question"):
            questions.append(item["question"])
        elif isinstance(item, str):
            questions.append(item)

    if not questions:
        questions = [
            "이 문장에 동의하나요?",
            "이 생각과 연결되는 개인적 경험이 있나요?",
            "이 구절을 지금 삶에 적용하면 무엇이 달라질까요?",
        ]

    if not tags:
        tags = _fallback_keywords((passage or "") + " " + insight_text)

    main_question = (
        (debate or {}).get("neutral_question")
        or (questions[0] if questions else "")
        or f"《{book_title or '이 책'}》의 이 구절은 우리에게 무엇을 묻고 있나요?"
    )
    title_keyword = tags[0] if tags else "책의 질문"
    return {
        "title": f"{title_keyword}에 대한 질문",
        "book_title": book_title,
        "passage_preview": _compact_text(passage, 72),
        "main_question": main_question,
        "tags": tags[:5],
        "discussion_questions": questions[:5],
    }
