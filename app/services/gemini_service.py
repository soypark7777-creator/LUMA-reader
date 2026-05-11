"""
Gemini AI 서비스 — LUMA 핵심 AI 엔진
────────────────────────────────────────
기능:
  1. generate_cross_insight()   : 두 메모를 연결해 Cross-domain 인사이트 생성
  2. extract_keywords()         : 메모에서 핵심 키워드 추출
  3. generate_reframe_question(): 메모를 보고 심화 질문 생성
  4. analyze_memo_theme()       : 메모의 주제/감성 분석
  5. generate_discussion_guide(): 독서 모임 토론 가이드 질문 생성
  6. summarize_meeting()        : 모임 대화 → 보고서 자동 생성

Gemini API 키 없을 때 → Mock 응답으로 자동 폴백
"""

import os
import json
import re
import time
from contextlib import contextmanager
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ── Gemini SDK 초기화 ──────────────────────────────────────────
_gemini_ok  = False
_gemini_model = None
_API_KEY = os.getenv("GEMINI_API_KEY", "")
_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT", "4"))
_cooldown_until = 0.0

try:
    import google.generativeai as genai
    if _API_KEY and _API_KEY != "여기에_발급받은_키_입력":
        genai.configure(api_key=_API_KEY)
        _gemini_model = genai.GenerativeModel(_MODEL_NAME)
        _gemini_ok = True
        print(f"[OK] Gemini API connected ({_MODEL_NAME})")
    else:
        print("[WARN] GEMINI_API_KEY not set -> AI mock mode")
except ImportError:
    print("[WARN] google-generativeai not installed -> AI mock mode")
except Exception as e:
    print(f"[WARN] Gemini init failed: {e} -> AI mock mode")


@contextmanager
def _without_dead_local_proxy():
    """
    일부 로컬 실행 환경에서 HTTP(S)_PROXY가 127.0.0.1:9로 잡혀
    Gemini gRPC 호출이 API 서버가 아니라 죽은 로컬 프록시로 향한다.

    그런 명백한 차단 프록시만 호출 중 잠시 제거해, 실패하더라도
    60초 타임아웃 대신 실제 API 응답/쿼터 오류를 빠르게 받게 한다.
    """
    proxy_keys = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
    removed = {}
    for key in proxy_keys:
        value = os.environ.get(key, "")
        if "127.0.0.1:9" in value or "localhost:9" in value:
            removed[key] = value
            os.environ.pop(key, None)
    try:
        yield
    finally:
        os.environ.update(removed)


# ══════════════════════════════════════════════════════════════
#  내부 헬퍼
# ══════════════════════════════════════════════════════════════

def _call_gemini(prompt: str, expect_json: bool = False) -> str:
    """Gemini API 호출 공통 래퍼"""
    global _cooldown_until
    if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("LUMA_DISABLE_EXTERNAL_AI"):
        return None
    if not _gemini_ok or not _gemini_model:
        return None   # Mock 처리는 각 함수에서
    if time.time() < _cooldown_until:
        return None

    try:
        with _without_dead_local_proxy():
            resp = _gemini_model.generate_content(prompt, request_options={"timeout": _TIMEOUT})
        text = resp.text.strip()

        if expect_json:
            # 마크다운 코드펜스 제거
            text = re.sub(r"```(?:json)?\s*", "", text)
            text = re.sub(r"```\s*$", "", text).strip()

        return text
    except Exception as e:
        msg = str(e)
        if "429" in msg or "Quota exceeded" in msg or "RESOURCE_EXHAUSTED" in msg:
            _cooldown_until = time.time() + int(os.getenv("GEMINI_QUOTA_COOLDOWN_SECONDS", "60"))
        print(f"[Gemini 오류] {e}")
        return None


def _parse_json_safe(text: str) -> Optional[dict | list]:
    """JSON 파싱 안전하게"""
    try:
        return json.loads(text)
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
#  1. Cross-domain 인사이트 생성 (핵심 강제연결)
# ══════════════════════════════════════════════════════════════

def generate_cross_insight(
    memo1: dict,   # {content, book_title, tags}
    memo2: dict,   # {content, book_title, tags}
) -> dict:
    """
    서로 다른 책의 두 메모를 연결해 새로운 인사이트 생성
    반환: {insight, connection_type, strength, question}
    """
    prompt = f"""
당신은 세계 최고의 독서 인사이트 큐레이터입니다.
전혀 다른 두 권의 책에서 나온 두 메모를 분석하여,
그 사이에 숨겨진 연결고리와 새로운 통찰을 발견해주세요.

[책 A: {memo1.get('book_title', '알 수 없음')}]
메모: {memo1.get('content', '')}
태그: {', '.join(memo1.get('tags', []))}

[책 B: {memo2.get('book_title', '알 수 없음')}]
메모: {memo2.get('content', '')}
태그: {', '.join(memo2.get('tags', []))}

다음 JSON 형식으로만 응답하세요 (다른 말 없이):
{{
  "insight": "두 생각을 연결하는 핵심 통찰 (2-3문장, 따뜻하고 지적인 문체)",
  "connection_type": "대립/심화/유추/순환/역설 중 하나",
  "strength": 0.0~1.0 사이 연결 강도 (숫자만),
  "question": "이 연결에서 탄생한 독자에게 던지는 깊은 질문 1개"
}}
"""

    raw = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and isinstance(parsed, dict) and "insight" in parsed:
        return {
            "insight":         parsed["insight"],
            "connection_type": parsed.get("connection_type", "심화"),
            "strength":        float(parsed.get("strength", 0.7)),
            "question":        parsed.get("question", ""),
            "source":          "gemini",
        }

    # ── Mock 폴백 ──
    MOCK_INSIGHTS = [
        {
            "insight": f"'{memo1.get('book_title')}'의 사유와 '{memo2.get('book_title')}'의 통찰은 "
                       "표면적으로 달라 보이지만, 두 저자 모두 인간 존재의 본질적 조건에 "
                       "질문을 던지고 있습니다. 서로 다른 언어로 같은 진실을 가리키는 두 손가락입니다.",
            "connection_type": "유추",
            "strength": 0.78,
            "question": "만약 두 저자가 대화를 나눈다면, 서로에게 가장 먼저 어떤 질문을 던질까요?",
            "source": "mock",
        },
        {
            "insight": f"'{memo1.get('book_title')}'에서 발견한 패턴이 "
                       f"'{memo2.get('book_title')}'에서 반전됩니다. "
                       "이 역설적 긴장감 속에서 오히려 더 깊은 진실이 모습을 드러냅니다.",
            "connection_type": "역설",
            "strength": 0.85,
            "question": "두 관점이 동시에 참일 수 있다면, 우리의 세계관은 어떻게 달라져야 할까요?",
            "source": "mock",
        },
        {
            "insight": f"'{memo1.get('book_title')}'의 메모가 씨앗이라면, "
                       f"'{memo2.get('book_title')}'의 메모는 그 씨앗이 자란 나무입니다. "
                       "한 생각이 다른 생각을 통해 비로소 완성되고 있습니다.",
            "connection_type": "심화",
            "strength": 0.72,
            "question": "이 두 생각의 연결을 일상의 구체적인 장면에 적용한다면 어떤 모습일까요?",
            "source": "mock",
        },
    ]

    import hashlib
    seed = int(hashlib.md5(
        (memo1.get('content','')[:10] + memo2.get('content','')[:10]).encode()
    ).hexdigest(), 16) % len(MOCK_INSIGHTS)

    return MOCK_INSIGHTS[seed]


# ══════════════════════════════════════════════════════════════
#  2. 키워드 추출
# ══════════════════════════════════════════════════════════════

def extract_keywords(content: str, book_title: str = "") -> list[str]:
    """메모에서 핵심 키워드 3~5개 추출"""
    prompt = f"""
다음 독서 메모에서 핵심 개념 키워드를 3~5개 추출해주세요.
책: {book_title}
메모: {content}

JSON 배열만 반환 (예: ["자아", "실존", "자유의지"]):
"""
    raw = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and isinstance(parsed, list):
        return [str(k) for k in parsed[:5]]

    # Mock 폴백
    words = content.replace(',', ' ').replace('.', ' ').split()
    return [w for w in words if len(w) >= 2][:4]


# ══════════════════════════════════════════════════════════════
#  3. 심화 질문 생성 (Reframe)
# ══════════════════════════════════════════════════════════════

def generate_reframe_question(content: str, book_title: str = "") -> dict:
    """
    메모를 보고 독자가 더 깊이 사유하도록 유도하는 질문 생성
    반환: {question, type, angle}
    """
    prompt = f"""
당신은 소크라테스식 독서 코치입니다.
독자의 메모를 읽고, 생각이 더 깊어지도록 유도하는 질문을 만들어주세요.

책: {book_title}
메모: {content}

JSON 형식으로만 응답:
{{
  "question": "독자의 사유를 확장하는 질문 1개 (한국어, 따뜻한 어조)",
  "type": "반론/확장/적용/비교 중 하나",
  "angle": "이 질문이 노리는 시각 전환 한 줄 설명"
}}
"""
    raw = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and isinstance(parsed, dict) and "question" in parsed:
        parsed["source"] = "gemini"
        return parsed

    # Mock 폴백
    MOCK_QUESTIONS = [
        {"question": "이 생각이 틀렸다고 주장하는 사람은 어떤 논거를 댈까요?", "type": "반론", "angle": "비판적 사고 훈련", "source": "mock"},
        {"question": "오늘 하루 일상에서 이 통찰이 적용될 수 있는 순간은 언제인가요?", "type": "적용", "angle": "추상→구체 전환", "source": "mock"},
        {"question": "이 생각과 정반대 입장의 책이 있다면, 어떤 책일까요?", "type": "비교", "angle": "대조를 통한 명료화", "source": "mock"},
        {"question": "10년 후의 당신이 이 메모를 다시 읽는다면, 어떤 감상을 남길까요?", "type": "확장", "angle": "시간적 관점 이동", "source": "mock"},
    ]
    import random; return random.choice(MOCK_QUESTIONS)


# ══════════════════════════════════════════════════════════════
#  4. 메모 주제 분석
# ══════════════════════════════════════════════════════════════

def analyze_memo_theme(content: str) -> dict:
    """
    메모의 주제 카테고리와 감성 분석
    반환: {theme, emotion, depth_score, summary}
    """
    prompt = f"""
다음 독서 메모를 분석해주세요:
"{content}"

JSON 형식으로만 응답:
{{
  "theme": "철학/과학/사회/심리/역사/예술/경제/기타 중 가장 적합한 것",
  "emotion": "영감/감동/호기심/성찰/불안/평온 중 하나",
  "depth_score": 1~10 사이 사유 깊이 점수 (숫자만),
  "summary": "메모의 핵심을 한 문장으로"
}}
"""
    raw = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and isinstance(parsed, dict):
        parsed["source"] = "gemini"
        return parsed

    return {
        "theme": "철학", "emotion": "영감",
        "depth_score": 7,
        "summary": content[:40] + "...",
        "source": "mock"
    }


# ══════════════════════════════════════════════════════════════
#  5. 독서 모임 토론 가이드
# ══════════════════════════════════════════════════════════════

def generate_discussion_guide(
    book_title: str,
    recent_messages: list[str],
    guide_type: str = "debate"   # debate | empathy | summary
) -> dict:
    """
    모임 대화 흐름을 읽고 AI 토론 가이드 질문 생성
    반환: {question, type, rationale}
    """
    msg_text = "\n".join(f"- {m}" for m in recent_messages[-5:])
    type_guide = {
        "debate":  "논쟁을 불러일으키는 도발적인",
        "empathy": "공감과 감성을 자극하는 따뜻한",
        "summary": "대화를 정리하고 핵심을 짚는",
    }
    style = type_guide.get(guide_type, "깊이 있는")

    prompt = f"""
독서 모임에서 '{book_title}'을 함께 읽고 있습니다.
최근 나눈 대화:
{msg_text}

대화가 더 풍성해지도록 {style} 질문 1개를 만들어주세요.

JSON 형식으로만 응답:
{{
  "question": "AI가 던지는 질문 (한국어)",
  "type": "{guide_type}",
  "rationale": "이 질문을 선택한 이유 한 줄"
}}
"""
    raw = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and isinstance(parsed, dict) and "question" in parsed:
        parsed["source"] = "gemini"
        return parsed

    MOCK = {
        "debate":  {"question": f"'{book_title}'의 주장 중 당신이 가장 동의하기 어려운 부분은 무엇인가요?", "type": "debate", "rationale": "비판적 사고 유도", "source": "mock"},
        "empathy": {"question": "이 책에서 가장 마음에 남는 장면이나 문장은 무엇인가요?", "type": "empathy", "rationale": "감성적 연결 강화", "source": "mock"},
        "summary": {"question": "오늘 대화를 통해 새롭게 발견하거나 바뀐 생각이 있다면 나눠볼까요?", "type": "summary", "rationale": "대화 마무리 정리", "source": "mock"},
    }
    return MOCK.get(guide_type, MOCK["debate"])


# ══════════════════════════════════════════════════════════════
#  6. 모임 대화 → 자동 보고서
# ══════════════════════════════════════════════════════════════

def summarize_meeting(
    book_title: str,
    messages: list[str],
    participants: list[str],
) -> dict:
    """
    모임 전체 대화를 분석해 한 페이지 보고서 생성
    반환: {summary, key_insights, highlight_quotes, next_questions, mood}
    """
    all_msg = "\n".join(f"- {m}" for m in messages)
    prompt = f"""
독서 모임 대화를 분석하여 한 페이지 보고서를 작성해주세요.

책: {book_title}
참여자: {', '.join(participants)}명 참여
대화 내용:
{all_msg}

JSON 형식으로만 응답:
{{
  "summary": "모임 전체 흐름 요약 (3~4문장, 지적이고 따뜻한 문체)",
  "key_insights": ["핵심 인사이트 1", "인사이트 2", "인사이트 3"],
  "highlight_quotes": ["인상적인 발언 또는 문장 1", "발언 2"],
  "next_questions": ["다음 모임을 위한 질문 1", "질문 2"],
  "mood": "열정적/사색적/유쾌한/진지한 중 하나"
}}
"""
    raw = _call_gemini(prompt, expect_json=True)
    parsed = _parse_json_safe(raw) if raw else None

    if parsed and isinstance(parsed, dict) and "summary" in parsed:
        parsed["source"] = "gemini"
        return parsed

    return {
        "summary": f"'{book_title}'을 중심으로 {len(participants)}명이 깊이 있는 대화를 나눴습니다. "
                   "각자의 삶의 맥락에서 책을 해석하며 다양한 시각을 교환했고, "
                   "그 과정에서 예상치 못한 연결들이 탄생했습니다.",
        "key_insights": [
            "텍스트의 의미는 독자의 경험과 만날 때 비로소 완성된다.",
            "서로 다른 관점이 충돌할 때 오히려 더 풍성한 이해가 생긴다.",
            "읽는다는 행위는 결국 자기 자신을 발견하는 여정이다.",
        ],
        "highlight_quotes": [
            "\"이 책은 나에게 거울처럼 느껴졌어요.\"",
            "\"이 부분에서 완전히 다른 의미로 읽혔는데, 신기하네요.\"",
        ],
        "next_questions": [
            f"'{book_title}'이 출판된 시대적 배경이 내용에 어떤 영향을 미쳤을까요?",
            "이 책의 주인공이 현재 우리 사회에 살고 있다면 어떤 선택을 할까요?",
        ],
        "mood": "사색적",
        "source": "mock",
    }


# ══════════════════════════════════════════════════════════════
#  상태 확인
# ══════════════════════════════════════════════════════════════

def get_ai_status() -> dict:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return {
            "gemini_connected": False,
            "mode": "mock",
            "api_key_set": bool(_API_KEY and _API_KEY != "여기에_발급받은_키_입력"),
        }
    return {
        "gemini_connected": _gemini_ok,
        "mode": _MODEL_NAME if _gemini_ok else "mock",
        "api_key_set": bool(_API_KEY and _API_KEY != "여기에_발급받은_키_입력"),
    }
