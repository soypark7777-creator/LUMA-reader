from typing import Optional
from collections import defaultdict
"""
북 유니버스 소셜 피드 서비스
────────────────────────────────────────
- 독서 카드 피드 공유
- AI 독서 친구 매칭
- 자동 북클럽 생성
- 챌린지 & 뱃지
"""
import uuid
import hashlib
from datetime import datetime, date
from collections import defaultdict

# ── 저장소 ──────────────────────────────────────────────
_feed_cards: list[dict] = [
    {
        "card_id": "fc_001", "user_id": "user_soyeon",
        "display_name": "소연", "user_emoji": "🦋",
        "book_title": "사피엔스", "author": "유발 하라리",
        "passage": "인류가 지구를 지배할 수 있었던 이유는 단 하나—허구를 집단적으로 믿는 능력이다.",
        "thought": "화폐, 국가, 종교 모두 허구라는 사실이 오히려 더 신비롭다.",
        "emotion": "surprised", "tags": ["인류학", "철학", "역사"],
        "likes": 24, "comments": 3, "liked_by": [],
        "created_at": "2025-04-01T09:00:00",
        "card_style": "dark",
    },
    {
        "card_id": "fc_002", "user_id": "user_jimin",
        "display_name": "지민", "user_emoji": "🌸",
        "book_title": "어린왕자", "author": "생텍쥐페리",
        "passage": "가장 중요한 것은 눈에 보이지 않아.",
        "thought": "어른이 된 후에야 이 문장이 얼마나 깊은지 알았다.",
        "emotion": "sad", "tags": ["문학", "감성", "철학"],
        "likes": 41, "comments": 7, "liked_by": [],
        "created_at": "2025-04-02T14:30:00",
        "card_style": "warm",
    },
    {
        "card_id": "fc_003", "user_id": "user_hyunwoo",
        "display_name": "현우", "user_emoji": "🌊",
        "book_title": "코스모스", "author": "칼 세이건",
        "passage": "우리는 별의 재료로 만들어졌다.",
        "thought": "일상의 고민이 너무 작게 느껴지면서도, 오히려 소중하게 느껴졌다.",
        "emotion": "peaceful", "tags": ["과학", "우주", "철학"],
        "likes": 38, "comments": 5, "liked_by": [],
        "created_at": "2025-04-03T20:00:00",
        "card_style": "cosmic",
    },
]

_comments: list[dict] = [
    {"comment_id":"cmt_001","card_id":"fc_001","user_id":"user_jimin","display_name":"지민","emoji":"🌸","text":"정말 충격적이었어요! 법도 허구라고 생각하니까 사회가 다르게 보이더라고요.","created_at":"2025-04-01T10:00:00"},
    {"comment_id":"cmt_002","card_id":"fc_002","user_id":"user_soyeon","display_name":"소연","emoji":"🦋","text":"어른이 돼서 다시 읽으니 완전 다른 책이 됐어요. 추천!","created_at":"2025-04-02T15:00:00"},
]

_book_clubs: list[dict] = []
_challenges: list[dict] = []
_user_badges: dict[str, list] = defaultdict(list)

BADGES = {
    "first_card":   {"name": "첫 카드",     "emoji": "🃏", "desc": "첫 독서 카드 공유"},
    "book_5":       {"name": "5권 독서가",  "emoji": "📚", "desc": "5권 완독"},
    "book_10":      {"name": "10권 독서가", "emoji": "🏆", "desc": "10권 완독"},
    "early_bird":   {"name": "새벽 독서가", "emoji": "🌅", "desc": "오전 6시 이전 체크인"},
    "connector":    {"name": "연결자",      "emoji": "✦",  "desc": "강제 연결 10회"},
    "social_star":  {"name": "소셜 스타",   "emoji": "⭐", "desc": "좋아요 100개 받기"},
    "genre_explorer":{"name":"장르 탐험가", "emoji": "🗺", "desc": "5개 이상 장르 독서"},
    "night_owl":    {"name": "밤 독서가",   "emoji": "🦉", "desc": "자정 이후 체크인"},
}

CARD_STYLES = {
    "dark":   {"bg": "#1A2B20", "text": "#E8DCC8", "accent": "#C17F3B"},
    "warm":   {"bg": "#2B1A1A", "text": "#F0E6D0", "accent": "#E07B54"},
    "cosmic": {"bg": "#0B1026", "text": "#E8DCC8", "accent": "#7EB8F7"},
    "forest": {"bg": "#162B20", "text": "#E8DCC8", "accent": "#4CAF7D"},
    "pure":   {"bg": "#FAFAF8", "text": "#2D2D2D", "accent": "#2D4A3E"},
}


# ── 피드 카드 CRUD ────────────────────────────────────────

def get_feed(page: int = 1, limit: int = 10, tag: str = None) -> dict:
    cards = list(_feed_cards)
    if tag:
        cards = [c for c in cards if tag in c.get("tags", [])]
    cards.sort(key=lambda x: x["created_at"], reverse=True)
    start = (page - 1) * limit
    return {
        "cards": [_normalize_card(c) for c in cards[start:start + limit]],
        "total": len(cards),
        "page":  page,
        "has_next": start + limit < len(cards),
    }


def create_card(user_id: str, data: dict) -> dict:
    content = data.get("passage") or data.get("content") or data.get("text") or ""
    thought = data.get("thought") or data.get("memo") or ""
    card = {
        "card_id":      f"fc_{uuid.uuid4().hex[:6]}",
        "user_id":      user_id,
        "display_name": data.get("display_name", "독서인"),
        "user_emoji":   data.get("user_emoji", "📚"),
        "book_title":   data.get("book_title", ""),
        "author":       data.get("author", ""),
        "passage":      content,
        "thought":      thought,
        "emotion":      data.get("emotion", "inspired"),
        "tags":         data.get("tags", []),
        "likes":        0,
        "comments":     0,
        "liked_by":     [],
        "created_at":   datetime.now().isoformat(),
        "card_style":   data.get("card_style") or data.get("style") or "dark",
    }
    _feed_cards.append(card)
    _check_badges(user_id)
    return _normalize_card(card)


def toggle_like(card_id: str, user_id: str) -> dict:
    card = _find_card(card_id)
    if not card:
        return {"ok": False}
    liked_by = card.setdefault("liked_by", [])
    if user_id in liked_by:
        liked_by.remove(user_id)
        card["likes"] = max(0, card["likes"] - 1)
        liked = False
    else:
        liked_by.append(user_id)
        card["likes"] += 1
        liked = True
    return {"ok": True, "liked": liked, "likes": card["likes"]}


def add_comment(card_id: str, data: dict) -> dict:
    card = _find_card(card_id)
    if not card:
        return {"ok": False}
    content = data.get("text") or data.get("content") or ""
    cmt = {
        "comment_id":   f"cmt_{uuid.uuid4().hex[:6]}",
        "card_id":      card_id,
        "user_id":      data.get("user_id", "user_demo"),
        "display_name": data.get("display_name", "독서인"),
        "emoji":        data.get("emoji", "⭐"),
        "text":         content,
        "created_at":   datetime.now().isoformat(),
    }
    _comments.append(cmt)
    card["comments"] = len([c for c in _comments if c["card_id"] == card_id])
    return {"ok": True, "comment": _normalize_comment(cmt), "total_comments": card["comments"]}


def get_comments(card_id: str) -> list[dict]:
    return [_normalize_comment(c) for c in _comments if c["card_id"] == card_id]


def _find_card(card_id: str) -> Optional[dict]:
    return next((c for c in _feed_cards if c.get("card_id") == card_id or c.get("id") == card_id), None)


def _normalize_card(card: dict) -> dict:
    """프론트와 기존 서비스 양쪽이 쓰는 필드명을 모두 보장한다."""
    content = card.get("passage") or card.get("content") or card.get("thought") or ""
    comment_count = card.get("comments_cnt", card.get("comments", 0))
    return {
        **card,
        "id": card.get("id") or card.get("card_id"),
        "content": content,
        "style": card.get("style") or card.get("card_style") or "dark",
        "author_name": card.get("author_name") or card.get("display_name") or card.get("user_name") or "독자",
        "author_emoji": card.get("author_emoji") or card.get("user_emoji") or card.get("emoji") or "📚",
        "author_color": card.get("author_color") or "#1e2f6e",
        "like_count": int(card.get("like_count", card.get("likes", 0)) or 0),
        "comment_count": int(comment_count or 0),
        "liked": bool(card.get("liked") or card.get("is_liked")),
    }


def _normalize_comment(comment: dict) -> dict:
    return {
        **comment,
        "id": comment.get("id") or comment.get("comment_id"),
        "content": comment.get("content") or comment.get("text") or "",
        "author_name": comment.get("author_name") or comment.get("display_name") or "독자",
        "author_emoji": comment.get("author_emoji") or comment.get("emoji") or "📚",
    }


# ── AI 독서 친구 매칭 ────────────────────────────────────

def find_reading_buddies(user_id: str, user_genres: list, user_books: list) -> list[dict]:
    """독서 취향 기반 친구 추천"""
    # Mock: 다른 사용자들의 카드에서 장르 분석
    other_users: dict[str, dict] = {}
    for card in _feed_cards:
        uid = card["user_id"]
        if uid == user_id:
            continue
        if uid not in other_users:
            other_users[uid] = {
                "user_id":      uid,
                "display_name": card["display_name"],
                "emoji":        card["user_emoji"],
                "genres":       [],
                "books":        [],
                "card_count":   0,
            }
        other_users[uid]["genres"].extend(card.get("tags", []))
        other_users[uid]["books"].append(card["book_title"])
        other_users[uid]["card_count"] += 1

    results = []
    for uid, info in other_users.items():
        # 장르 겹침 계산
        shared_genres = set(user_genres) & set(info["genres"])
        shared_books  = set(user_books) & set(info["books"])
        score = (len(shared_genres) * 20 + len(shared_books) * 30 + info["card_count"] * 5)
        score = min(99, score)
        if score > 30:
            results.append({
                **info,
                "match_score":   score,
                "shared_genres": list(shared_genres)[:3],
                "shared_books":  list(shared_books)[:2],
                "reason":        f"같은 장르 {len(shared_genres)}개, 같은 책 {len(shared_books)}권 읽음",
            })

    results.sort(key=lambda x: -x["match_score"])
    return results[:5]


# ── 자동 북클럽 생성 ─────────────────────────────────────

def check_and_create_bookclub(book_title: str) -> Optional[dict]:
    """같은 책 읽는 사람 3명+ → 자동 북클럽 생성"""
    # 이미 있는 클럽
    existing = next((c for c in _book_clubs if c["book_title"] == book_title), None)
    if existing:
        return existing

    readers = list({c["user_id"] for c in _feed_cards if c["book_title"] == book_title})
    if len(readers) >= 2:   # 데모용: 2명부터 생성
        club = {
            "club_id":    f"bc_{uuid.uuid4().hex[:6]}",
            "book_title": book_title,
            "members":    readers,
            "status":     "active",
            "created_at": datetime.now().isoformat(),
            "auto":       True,
        }
        _book_clubs.append(club)
        return club
    return None


def get_bookclubs() -> list[dict]:
    return _book_clubs


# ── 챌린지 & 뱃지 ────────────────────────────────────────

MONTHLY_CHALLENGE = {
    "challenge_id": "ch_2025_04",
    "title":        "4월 독서 마라톤",
    "description":  "이번 달 5권을 완독하고 각 책마다 감정 메모를 남기세요",
    "goal_books":   5,
    "goal_memos":   5,
    "reward_badge": "book_5",
    "ends_at":      "2025-04-30",
}


def get_challenge_status(user_id: str, books_read: int, memos: int) -> dict:
    ch = MONTHLY_CHALLENGE
    progress_books = min(books_read, ch["goal_books"])
    progress_memos = min(memos, ch["goal_memos"])
    pct = int((progress_books / ch["goal_books"] + progress_memos / ch["goal_memos"]) / 2 * 100)
    completed = pct >= 100
    if completed:
        _award_badge(user_id, ch["reward_badge"])
    return {
        "challenge":      ch,
        "progress_books": progress_books,
        "progress_memos": progress_memos,
        "percentage":     pct,
        "completed":      completed,
    }


def get_user_badges(user_id: str) -> list[dict]:
    return [
        {**BADGES[b], "badge_id": b, "earned_at": datetime.now().isoformat()}
        for b in _user_badges.get(user_id, [])
        if b in BADGES
    ]


def _award_badge(user_id: str, badge_id: str):
    if badge_id not in _user_badges[user_id]:
        _user_badges[user_id].append(badge_id)


def _check_badges(user_id: str):
    cards_by_user = [c for c in _feed_cards if c["user_id"] == user_id]
    if len(cards_by_user) == 1:
        _award_badge(user_id, "first_card")
    total_likes = sum(c.get("likes", 0) for c in cards_by_user)
    if total_likes >= 100:
        _award_badge(user_id, "social_star")
    h = datetime.now().hour
    if h < 6:
        _award_badge(user_id, "early_bird")
    if h >= 0 and h < 3:
        _award_badge(user_id, "night_owl")

