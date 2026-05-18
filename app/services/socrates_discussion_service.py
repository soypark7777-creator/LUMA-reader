"""Socrates discussion preparation helpers.

These helpers power both /api/socrates/* and /api/v2/socrates/* without
changing the existing Socrates session flow.
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
    mode = (mode or "appreciation").strip().lower()
    return mode if mode in DISCUSSION_MODES else "appreciation"


def get_mode_label(mode: str | None) -> str:
    return DISCUSSION_MODES[normalize_discussion_mode(mode)]


def generate_book_brief(passage: str, book_title: str = "", user_id: str = "user_demo") -> dict:
    passage = _compact_text(passage, 900)
    book_title = (book_title or "").strip()
    prompt = f"""독서 토론을 위한 책/구절 브리프를 JSON으로 작성하세요.
책: {book_title}
구절: {passage}

응답 형식:
{{
  "summary": ["핵심 요약 1", "핵심 요약 2", "핵심 요약 3"],
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "main_question": "독자가 함께 이야기할 중심 질문",
  "discussion_hint": "독서모임에서 대화를 여는 짧은 힌트"
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

    keywords = _fallback_keywords(passage)
    preview = _compact_text(passage, 70)
    title = book_title or "이 책"
    return {
        "summary": [
            f"{title}의 이 구절은 독자가 붙잡을 만한 중심 생각을 드러냅니다.",
            f"핵심 문장은 '{preview}'로 요약할 수 있습니다.",
            "토론에서는 문장의 의미와 각자의 경험을 연결하는 방식으로 시작하기 좋습니다.",
        ],
        "keywords": keywords,
        "main_question": f"이 구절은 우리에게 어떤 {keywords[0]}의 의미를 묻고 있나요?",
        "discussion_hint": f"{', '.join(keywords[:3])}를 중심으로 서로 다른 해석을 나눠보세요.",
        "source": "fallback",
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
    insight_text = _insight_text(insight)
    prompt = f"""독서모임 질문 3~5개를 JSON으로 작성하세요.
토론 모드: {get_mode_label(mode)}({mode})
책: {book_title}
구절: {passage}
인사이트: {insight_text}

응답 형식:
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
        shaped = [
            {
                "type": str(item.get("type", "discussion")),
                "label": str(item.get("label", "토론 질문")),
                "question": str(item.get("question", "")),
            }
            for item in questions[:5]
            if isinstance(item, dict) and item.get("question")
        ]
        if shaped:
            return shaped

    mode_question = {
        "appreciation": "이 구절에서 가장 오래 마음에 남는 표현은 무엇인가요?",
        "analysis": "이 구절의 핵심 주장과 근거를 나누면 어떻게 정리할 수 있나요?",
        "debate": "당신은 이 구절의 주장에 동의하나요, 반대하나요?",
        "life": "이 생각을 지금의 삶에 적용한다면 무엇이 달라질까요?",
        "character": "이 구절 속 인물은 어떤 욕망이나 두려움으로 움직이고 있나요?",
    }
    return [
        {"type": "understanding", "label": "이해 질문", "question": "이 구절에서 가장 중요한 단어는 무엇인가요?"},
        {"type": "emotion", "label": "감정 질문", "question": "이 문장을 읽었을 때 어떤 감정이 먼저 들었나요?"},
        {"type": mode, "label": get_mode_label(mode), "question": mode_question[mode]},
    ]


def generate_debate_topic(
    passage: str = "",
    book_title: str = "",
    insight: str | dict = "",
    user_id: str = "user_demo",
) -> dict:
    insight_text = _insight_text(insight)
    prompt = f"""책 구절에서 찬반 토론이 가능한 주제를 JSON으로 작성하세요.
책: {book_title}
구절: {passage}
인사이트: {insight_text}

응답 형식:
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

    keywords = _fallback_keywords(passage + " " + insight_text)
    key = keywords[0]
    return {
        "topic": f"삶에서 '{key}'을 추구하는 일은 우리를 더 자유롭게 만드는가?",
        "pros": [
            f"'{key}'은 자기 삶을 선택하고 해석하게 합니다.",
            "가치 있는 선택은 불안보다 더 큰 의미를 만들 수 있습니다.",
        ],
        "cons": [
            f"'{key}'을 지나치게 추구하면 책임과 현실을 놓칠 수 있습니다.",
            "개인의 해석만으로는 공동체의 복잡한 문제를 충분히 다루기 어렵습니다.",
        ],
        "neutral_question": f"'{key}'과 안정 중 지금 우리에게 더 중요한 것은 무엇인가요?",
        "source": "fallback",
    }


def build_lounge_card(
    passage: str = "",
    book_title: str = "",
    insight: str | dict = "",
    discussion_questions: list | None = None,
    debate: dict | None = None,
    user_id: str = "user_demo",
) -> dict:
    insight_text = _insight_text(insight)
    tags = _insight_tags(insight) or _fallback_keywords((passage or "") + " " + insight_text)
    questions = _question_strings(discussion_questions)
    if not questions:
        questions = [
            "이 문장에 동의하나요?",
            "이 생각과 연결되는 개인적 경험이 있나요?",
            "이 구절을 지금 삶에 적용한다면 무엇이 달라질까요?",
        ]

    main_question = (
        (debate or {}).get("neutral_question")
        or questions[0]
        or f"{book_title or '이 책'}의 이 구절은 우리에게 무엇을 묻고 있나요?"
    )
    title_keyword = tags[0] if tags else "책의 질문"
    return {
        "title": f"{title_keyword}에 대한 질문",
        "book_title": book_title,
        "passage_preview": _compact_text(passage, 90),
        "insight": insight_text,
        "main_question": main_question,
        "tags": tags[:5],
        "discussion_questions": questions[:5],
        "debate": debate or {},
        "source": "socrates",
    }


def _json_from_gemini(prompt: str) -> dict | None:
    try:
        from app.services.gemini_service import _call_gemini, _parse_json_safe

        raw = _call_gemini(prompt, expect_json=True)
        parsed = _parse_json_safe(raw) if raw else None
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _compact_text(text: str, limit: int = 80) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _fallback_keywords(text: str) -> list[str]:
    words = re.findall(r"[가-힣A-Za-z]{2,}", text or "")
    stop = {"그리고", "하지만", "그래서", "나는", "우리는", "그들은", "것이다", "있는", "없는"}
    result = []
    for word in words:
        word = re.sub(r"(은|는|이|가|을|를|과|와|으로|에게|에서|처럼|까지|만큼)$", "", word)
        if len(word) < 2 or word in stop or word in result:
            continue
        result.append(word)
        if len(result) >= 5:
            break
    return result[:5] or ["이해", "질문", "토론"]


def _insight_text(insight: str | dict) -> str:
    if isinstance(insight, dict):
        return (
            insight.get("my_sentence")
            or insight.get("refined_thought")
            or insight.get("personal_meaning")
            or insight.get("summary")
            or ""
        )
    return str(insight or "")


def _insight_tags(insight: str | dict) -> list[str]:
    if not isinstance(insight, dict):
        return []
    tags = insight.get("tags") or insight.get("keywords") or []
    if isinstance(tags, str):
        tags = [item.strip().strip("#") for item in tags.split(",")]
    return [str(item).strip().strip("#") for item in tags if str(item).strip()][:5]


def _question_strings(items: list | None) -> list[str]:
    questions = []
    for item in items or []:
        if isinstance(item, dict) and item.get("question"):
            questions.append(str(item["question"]))
        elif isinstance(item, str) and item.strip():
            questions.append(item.strip())
    return questions
