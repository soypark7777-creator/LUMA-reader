"""
Firebase Firestore 서비스
실제 Firebase 연동 + 없을 때는 인메모리 Mock으로 자동 폴백
→ API 키 없어도 개발/테스트 가능
"""
import os
import uuid
from datetime import datetime
from typing import Optional

# ── Firebase Admin SDK (없으면 Mock 모드) ──────────────────────
_firebase_ok = False
_db = None

try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
    if os.path.exists(cred_path) and not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        _db = firestore.client()
        _firebase_ok = True
        print("[OK] Firebase connected")
    else:
        print("[WARN] Firebase credentials not found -> mock mode")
except ImportError:
    print("[WARN] firebase-admin not installed -> mock mode")
except Exception as e:
    print(f"[WARN] Firebase init failed: {e} -> mock mode")

# ── 인메모리 Mock 저장소 ───────────────────────────────────────
_mock_store: dict[str, list] = {
    "memos": [],
    "books": []
}

# 샘플 데이터 (첫 실행 시 보여줄 기존 메모들)
_mock_store["memos"] = [
    {
        "memo_id": "memo_001",
        "user_id": "user_demo",
        "book_id": "book_001",
        "book_title": "사피엔스",
        "content": "인류가 지구를 지배할 수 있었던 이유는 단순히 지능이 아니라, '허구'를 집단적으로 믿는 능력 덕분이다.",
        "page_number": 42,
        "tags": ["인류학", "역사", "철학"],
        "mood": "inspired",
        "is_public": True,
        "created_at": "2025-03-28T09:15:00",
    },
    {
        "memo_id": "memo_002",
        "user_id": "user_demo",
        "book_id": "book_003",
        "book_title": "어린왕자",
        "content": "'가장 중요한 것은 눈에 보이지 않아.' 이 문장이 왜 이렇게 마음에 남는 걸까.",
        "page_number": 87,
        "tags": ["철학", "감성"],
        "mood": "emotional",
        "is_public": True,
        "created_at": "2025-03-30T21:40:00",
    },
    {
        "memo_id": "memo_003",
        "user_id": "user_demo",
        "book_id": "book_002",
        "book_title": "코스모스",
        "content": "우리는 별의 재료로 만들어졌다. 이 우주적 관점이 일상의 사소한 갈등을 얼마나 작게 만드는가.",
        "page_number": 156,
        "tags": ["과학", "우주", "철학"],
        "mood": "inspired",
        "is_public": False,
        "created_at": "2025-04-01T14:22:00",
    },
]

# ── 공개 API 함수들 ────────────────────────────────────────────

def save_memo(memo_data: dict) -> dict:
    """메모 저장 (Firebase 또는 Mock)"""
    memo_id = f"memo_{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    doc = {
        "memo_id":    memo_id,
        "user_id":    memo_data.get("user_id", "user_demo"),
        "book_id":    memo_data.get("book_id", "book_unknown"),
        "book_title": memo_data.get("book_title", ""),
        "content":    memo_data.get("content", ""),
        "page_number":memo_data.get("page_number"),
        "tags":       memo_data.get("tags", []),
        "mood":       memo_data.get("mood", "neutral"),
        "is_public":  memo_data.get("is_public", False),
        "created_at": now,
    }

    if _firebase_ok and _db:
        _db.collection("memos").document(memo_id).set(doc)
    else:
        _mock_store["memos"].insert(0, doc)   # 최신 순으로 앞에 삽입

    return doc


def get_memos(user_id: str = "user_demo", limit: int = 20) -> list:
    """메모 목록 조회"""
    if _firebase_ok and _db:
        docs = (
            _db.collection("memos")
            .where("user_id", "==", user_id)
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        return [d.to_dict() for d in docs]
    else:
        return _mock_store["memos"][:limit]


def get_memo_by_id(memo_id: str) -> Optional[dict]:
    """단일 메모 조회"""
    if _firebase_ok and _db:
        doc = _db.collection("memos").document(memo_id).get()
        return doc.to_dict() if doc.exists else None
    else:
        return next((m for m in _mock_store["memos"] if m["memo_id"] == memo_id), None)


def delete_memo(memo_id: str) -> bool:
    """메모 삭제"""
    if _firebase_ok and _db:
        _db.collection("memos").document(memo_id).delete()
        return True
    else:
        before = len(_mock_store["memos"])
        _mock_store["memos"] = [m for m in _mock_store["memos"] if m["memo_id"] != memo_id]
        return len(_mock_store["memos"]) < before


def get_stats(user_id: str = "user_demo") -> dict:
    """독서 통계 계산"""
    memos = get_memos(user_id, limit=1000)
    tags_flat = [t for m in memos for t in m.get("tags", [])]
    tag_count: dict[str, int] = {}
    for t in tags_flat:
        tag_count[t] = tag_count.get(t, 0) + 1

    return {
        "total_memos": len(memos),
        "top_tags": sorted(tag_count.items(), key=lambda x: -x[1])[:5],
        "mood_dist": {
            "inspired":  sum(1 for m in memos if m.get("mood") == "inspired"),
            "emotional": sum(1 for m in memos if m.get("mood") == "emotional"),
            "curious":   sum(1 for m in memos if m.get("mood") == "curious"),
            "neutral":   sum(1 for m in memos if m.get("mood") == "neutral"),
        },
        "mode": "firebase" if _firebase_ok else "mock",
    }
