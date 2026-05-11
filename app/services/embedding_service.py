"""
임베딩 & 유사도 서비스
────────────────────────────────────────
Gemini Embedding API가 있으면 사용,
없으면 TF-IDF 기반 경량 유사도 계산으로 폴백

메모 저장 시 → 기존 메모들과 유사도 계산
→ 가장 유사하면서도 다른 책의 메모 찾기
→ Cross-domain Insight 생성 대상 선정
"""

import math
import re
from typing import Optional
from app.services.firebase_service import get_memos


# ══════════════════════════════════════════════════════════════
#  TF-IDF 기반 경량 유사도 (Gemini Embedding 없을 때)
# ══════════════════════════════════════════════════════════════

def _tokenize(text: str) -> list[str]:
    """한국어 + 영어 간단 토크나이저"""
    text = text.lower()
    # 2글자 이상 한글/영문 추출
    tokens = re.findall(r'[가-힣]{2,}|[a-z]{3,}', text)
    return tokens


def _term_freq(tokens: list[str]) -> dict[str, float]:
    """단어 빈도 계산"""
    tf: dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    total = len(tokens) or 1
    return {k: v / total for k, v in tf.items()}


def _cosine_similarity(vec_a: dict, vec_b: dict) -> float:
    """코사인 유사도"""
    keys = set(vec_a) | set(vec_b)
    dot  = sum(vec_a.get(k, 0) * vec_b.get(k, 0) for k in keys)
    norm_a = math.sqrt(sum(v**2 for v in vec_a.values())) or 1
    norm_b = math.sqrt(sum(v**2 for v in vec_b.values())) or 1
    return dot / (norm_a * norm_b)


def _tag_overlap_score(tags_a: list, tags_b: list) -> float:
    """태그 겹침 점수 (0~1)"""
    if not tags_a or not tags_b:
        return 0.0
    set_a, set_b = set(tags_a), set(tags_b)
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def compute_similarity(memo_a: dict, memo_b: dict) -> float:
    """
    두 메모 간 종합 유사도 계산
    = 텍스트 코사인 유사도 70% + 태그 겹침 30%
    """
    tokens_a = _tokenize(memo_a.get("content", ""))
    tokens_b = _tokenize(memo_b.get("content", ""))

    tf_a = _term_freq(tokens_a)
    tf_b = _term_freq(tokens_b)

    text_sim = _cosine_similarity(tf_a, tf_b)
    tag_sim  = _tag_overlap_score(
        memo_a.get("tags", []),
        memo_b.get("tags", [])
    )

    return round(text_sim * 0.7 + tag_sim * 0.3, 4)


# ══════════════════════════════════════════════════════════════
#  핵심 함수: 강제연결 대상 메모 탐색
# ══════════════════════════════════════════════════════════════

def find_best_cross_pair(
    new_memo: dict,
    user_id: str = "user_demo",
    min_similarity: float = 0.08,   # 너무 낮으면 연결 의미 없음
    max_similarity: float = 0.85,   # 너무 높으면 같은 생각 → 재미없음
) -> Optional[dict]:
    """
    새 메모와 연결할 '다른 책'의 메모를 찾는다.
    
    조건:
    - 다른 책의 메모여야 함 (같은 책 제외)
    - 유사도 min~max 범위 (어느 정도 연결되지만 다른 관점)
    - 최고 점수 메모 반환
    
    반환: 연결 대상 메모 dict (없으면 None)
    """
    all_memos = get_memos(user_id, limit=100)

    new_book  = new_memo.get("book_title", "")
    new_id    = new_memo.get("memo_id", "")

    candidates = []

    for m in all_memos:
        # 자기 자신 제외
        if m.get("memo_id") == new_id:
            continue
        # 같은 책 제외 → Cross-domain이 핵심!
        if m.get("book_title") == new_book:
            continue

        score = compute_similarity(new_memo, m)

        # 범위 필터
        if min_similarity <= score <= max_similarity:
            candidates.append((score, m))

    if not candidates:
        # 범위 조건 완화해서 재시도
        for m in all_memos:
            if m.get("memo_id") == new_id:
                continue
            if m.get("book_title") == new_book:
                continue
            score = compute_similarity(new_memo, m)
            candidates.append((score, m))

    if not candidates:
        return None

    # 점수 기준 내림차순 → 최고 후보 반환
    candidates.sort(key=lambda x: -x[0])
    best_score, best_memo = candidates[0]

    return {
        **best_memo,
        "_similarity": best_score,
    }


def rank_all_connections(user_id: str = "user_demo") -> list[dict]:
    """
    전체 메모 쌍의 유사도를 계산해 상위 연결 관계 반환
    → 별자리 그래프 링크 데이터 생성에 활용
    """
    memos = get_memos(user_id, limit=50)
    pairs = []

    for i in range(len(memos)):
        for j in range(i + 1, len(memos)):
            m_a = memos[i]
            m_b = memos[j]

            # 같은 책 내 연결은 약하게 처리
            same_book = m_a.get("book_title") == m_b.get("book_title")
            score = compute_similarity(m_a, m_b)
            if same_book:
                score *= 0.5  # 같은 책은 패널티

            if score > 0.05:
                pairs.append({
                    "memo_a_id":    m_a["memo_id"],
                    "memo_b_id":    m_b["memo_id"],
                    "book_a":       m_a.get("book_title", ""),
                    "book_b":       m_b.get("book_title", ""),
                    "similarity":   round(score, 3),
                    "cross_domain": not same_book,
                })

    pairs.sort(key=lambda x: -x["similarity"])
    return pairs[:20]  # 상위 20개 연결만
