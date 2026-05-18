"""Compatibility wrapper for the legacy social feed service.

New code should use app.services.community_feed_service directly. This module
keeps /api/social/* and /api/v2/social/* callers working while the frontend is
being moved to /api/v2/community/*.
"""
from __future__ import annotations

from app.services import community_feed_service as community


def get_feed(page: int = 1, limit: int = 10, tag: str = None, user_id: str = "user_demo") -> dict:
    return community.get_feed(user_id=user_id, page=page, limit=limit, tag=tag or "")


def create_card(user_id: str, data: dict) -> dict:
    result = community.create_post(user_id, data)
    return result.get("post") or result.get("card") or result


def toggle_like(card_id: str, user_id: str) -> dict:
    return community.toggle_like(card_id, user_id)


def add_comment(card_id: str, data: dict) -> dict:
    return community.add_comment(card_id, data, data.get("user_id", "user_demo"))


def get_comments(card_id: str) -> list[dict]:
    return community.get_comments(card_id)


def find_reading_buddies(user_id: str, user_genres: list, user_books: list) -> list[dict]:
    readers = []
    seen = set()
    for book_title in user_books or []:
        result = community.get_same_book_readers(title=book_title, limit=8)
        for reader in result.get("readers", []):
            if reader.get("user_id") == user_id or reader.get("user_id") in seen:
                continue
            seen.add(reader.get("user_id"))
            readers.append({
                **reader,
                "match_score": 70,
                "shared_genres": user_genres[:3] if user_genres else [],
                "shared_books": [book_title],
                "reason": "같은 책을 읽고 있는 독자입니다.",
            })
    return readers[:5]


def check_and_create_bookclub(book_title: str):
    return community.check_and_create_bookclub(book_title)


def get_bookclubs() -> list[dict]:
    return community.get_lounge_recruit().get("clubs", [])


def get_challenge_status(user_id: str, books_read: int, memos: int) -> dict:
    goal_books = 5
    goal_memos = 5
    pct = int(((min(books_read, goal_books) / goal_books) + (min(memos, goal_memos) / goal_memos)) / 2 * 100)
    return {
        "challenge": {
            "challenge_id": "monthly_reading",
            "title": "이달의 독서 마라톤",
            "goal_books": goal_books,
            "goal_memos": goal_memos,
        },
        "progress_books": min(books_read, goal_books),
        "progress_memos": min(memos, goal_memos),
        "percentage": pct,
        "completed": pct >= 100,
    }


def get_user_badges(user_id: str) -> list[dict]:
    return []
