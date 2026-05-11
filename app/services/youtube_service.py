"""
YouTube 관련 영상 검색 서비스
OCR로 추출한 텍스트나 책 키워드로 관련 영상을 찾는다.
YouTube Data API v3 없으면 Mock 데이터로 폴백
"""
import os
import re
import hashlib

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
_yt_ok = bool(YOUTUBE_API_KEY and YOUTUBE_API_KEY not in ("여기에_YouTube_키_입력", ""))


def _youtube_api_key() -> str:
    return os.getenv("YOUTUBE_API_KEY", "").strip()


def classify_video_category(title: str) -> str:
    text = (title or "").lower()
    if "요약" in text or "summary" in text:
        return "summary"
    if "리뷰" in text or "review" in text:
        return "review"
    if any(word in text for word in ("해설", "강의", "강연", "lecture")):
        return "lecture"
    if "낭독" in text:
        return "reading"
    if "토론" in text or "debate" in text:
        return "discussion"
    return "general"


def deepdive_search_queries(query: str) -> list[str]:
    q = (query or "").strip()
    if not q:
        return []
    return [
        f"{q} 책 요약",
        f"{q} 책 리뷰",
        f"{q} 해설",
        f"{q} 독서모임 질문",
        f"{q} 낭독",
        f"{q} 책 추천",
        f"{q} 인문학 강연",
        f"{q} 철학 책",
        f"{q} 독서모임",
    ]


def search_youtube_videos(query: str, limit: int = 8) -> dict:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "q가 필요합니다.", "videos": []}
    limit = max(1, min(int(limit or 8), 20))
    videos: list[dict] = []
    seen: set[str] = set()

    for source_query in deepdive_search_queries(q):
        remaining = limit - len(videos)
        if remaining <= 0:
            break
        found = _youtube_api_search(source_query, remaining)
        if _youtube_api_key() and not found:
            break
        for video in found:
            video_id = video.get("video_id")
            if not video_id or video_id in seen:
                continue
            seen.add(video_id)
            video["source_query"] = source_query
            video["category"] = classify_video_category(video.get("title", ""))
            videos.append(video)
            if len(videos) >= limit:
                break

    if not videos:
        videos = _mock_deepdive_videos(q, limit)
    return {"ok": True, "videos": videos[:limit], "source": "youtube" if _youtube_api_key() else "mock"}


def _youtube_api_search(source_query: str, limit: int) -> list[dict]:
    key = _youtube_api_key()
    if not key:
        return []
    try:
        import requests
        params = {
            "part": "snippet",
            "q": source_query,
            "type": "video",
            "maxResults": max(1, min(limit, 10)),
            "key": key,
            "relevanceLanguage": "ko",
            "safeSearch": "moderate",
        }
        resp = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=5)
        if resp.status_code != 200:
            return []
        videos = []
        for item in resp.json().get("items", []):
            video_id = (item.get("id") or {}).get("videoId")
            snippet = item.get("snippet") or {}
            if not video_id:
                continue
            thumb = ((snippet.get("thumbnails") or {}).get("medium") or {}).get("url") or ""
            videos.append({
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "thumbnail": thumb,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "category": classify_video_category(snippet.get("title", "")),
                "source_query": source_query,
                "description": snippet.get("description", ""),
            })
        return videos
    except Exception:
        return []


def _mock_deepdive_videos(query: str, limit: int = 8) -> list[dict]:
    query_list = deepdive_search_queries(query) or [query]
    base = [
        ("summary", f"{query} 책 요약: 읽기 전 핵심 맥락 정리", "LUMA Book Lab"),
        ("review", f"{query} 리뷰와 독서 포인트", "책읽는 밤"),
        ("lecture", f"{query} 해설 강의: 배경지식과 질문", "인문학 강연실"),
        ("discussion", f"{query} 독서모임 질문 만들기", "토론하는 독자들"),
        ("reading", f"{query} 낭독으로 다시 읽기", "문장 낭독실"),
        ("lecture", f"{query}와 연결되는 철학 강연", "철학의 방"),
        ("general", f"{query}를 더 깊게 이해하는 방법", "Deep Reading"),
        ("review", f"{query}를 읽은 사람들이 남긴 생각", "독서 지도"),
    ]
    videos = []
    for idx, (category, title, channel) in enumerate(base[:limit], start=1):
        seed = hashlib.md5(f"{query}-{idx}".encode()).hexdigest()[:11]
        videos.append({
            "video_id": seed,
            "title": title,
            "channel": channel,
            "thumbnail": f"https://img.youtube.com/vi/{seed}/mqdefault.jpg",
            "url": f"https://www.youtube.com/watch?v={seed}",
            "category": category,
            "source_query": query_list[(idx - 1) % len(query_list)],
            "description": "YouTube API를 사용할 수 없을 때 제공되는 Deep Dive mock 큐레이션입니다.",
            "mock": True,
        })
    return videos


# ══════════════════════════════════════════════════════════════
#  Mock 영상 데이터
# ══════════════════════════════════════════════════════════════
_MOCK_VIDEOS = [
    {
        "video_id":    "dQw4w9WgXcQ",
        "title":       "[TED] 유발 하라리 — 인류의 미래를 말하다",
        "channel":     "TED",
        "duration":    "18:03",
        "thumbnail":   "https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
        "url":         "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "description": "사피엔스 저자 유발 하라리의 TED 강연. 인류의 미래와 AI에 대해.",
        "tags":        ["역사", "인류학", "미래"],
        "view_count":  "2.3M",
    },
    {
        "video_id":    "abc123def45",
        "title":       "칼 세이건의 코스모스 — 우주의 경이로움",
        "channel":     "Science Channel",
        "duration":    "12:45",
        "thumbnail":   "https://img.youtube.com/vi/abc123def45/mqdefault.jpg",
        "url":         "https://youtube.com/watch?v=abc123def45",
        "description": "칼 세이건의 '코스모스'에서 가장 감동적인 장면 모음.",
        "tags":        ["과학", "우주", "철학"],
        "view_count":  "4.1M",
    },
    {
        "video_id":    "xyz789abc12",
        "title":       "[독서 리뷰] 어린왕자 — 어른이 잊어버린 것들",
        "channel":     "북튜버 책방",
        "duration":    "09:22",
        "thumbnail":   "https://img.youtube.com/vi/xyz789abc12/mqdefault.jpg",
        "url":         "https://youtube.com/watch?v=xyz789abc12",
        "description": "어린왕자를 어른의 시선으로 다시 읽는 리뷰.",
        "tags":        ["문학", "고전", "감성"],
        "view_count":  "892K",
    },
    {
        "video_id":    "pqr456stu78",
        "title":       "존재의 의미 — 빅터 프랭클의 삶과 철학",
        "channel":     "철학TV",
        "duration":    "22:17",
        "thumbnail":   "https://img.youtube.com/vi/pqr456stu78/mqdefault.jpg",
        "url":         "https://youtube.com/watch?v=pqr456stu78",
        "description": "홀로코스트 생존자이자 심리학자 빅터 프랭클의 의미 치료.",
        "tags":        ["심리학", "철학", "실존"],
        "view_count":  "1.7M",
    },
    {
        "video_id":    "mno321vwx65",
        "title":       "[북클럽] 1984 — 빅브라더는 지금도 살아있는가",
        "channel":     "독서클럽",
        "duration":    "35:48",
        "thumbnail":   "https://img.youtube.com/vi/mno321vwx65/mqdefault.jpg",
        "url":         "https://youtube.com/watch?v=mno321vwx65",
        "description": "조지 오웰의 1984와 현대 감시 사회를 비교하는 토론.",
        "tags":        ["SF", "디스토피아", "사회"],
        "view_count":  "3.2M",
    },
    {
        "video_id":    "ghi654jkl98",
        "title":       "헤르만 헤세의 데미안 — 자아를 찾는 여정",
        "channel":     "문학산책",
        "duration":    "14:33",
        "thumbnail":   "https://img.youtube.com/vi/ghi654jkl98/mqdefault.jpg",
        "url":         "https://youtube.com/watch?v=ghi654jkl98",
        "description": "데미안을 통해 자아 탐색의 의미를 이야기하는 문학 강의.",
        "tags":        ["문학", "성장", "자아"],
        "view_count":  "1.1M",
    },
]

_MOCK_SCHOLAR = [
    {
        "type":    "scholar",
        "title":   "집단 기억과 허구의 사회적 기능 — 유발 하라리 연구",
        "source":  "한국사회학회 논문",
        "url":     "https://scholar.google.com",
        "summary": "사피엔스에서 다루는 허구의 사회적 기능을 실증적으로 분석한 학술 논문.",
        "year":    "2022",
    },
    {
        "type":    "scholar",
        "title":   "실존주의와 의미 치료의 현대적 적용",
        "source":  "심리학 저널",
        "url":     "https://scholar.google.com",
        "summary": "프랭클의 의미 치료를 현대 심리 상담에 적용하는 방법론 연구.",
        "year":    "2023",
    },
    {
        "type":    "scholar",
        "title":   "디지털 시대의 빅브라더 — 1984 재해석",
        "source":  "미디어연구소 보고서",
        "url":     "https://scholar.google.com",
        "summary": "소셜미디어와 AI 감시 시스템을 오웰의 관점으로 분석.",
        "year":    "2024",
    },
]


# ══════════════════════════════════════════════════════════════
#  핵심 함수
# ══════════════════════════════════════════════════════════════

def search_related_videos(text: str, book_title: str = "", limit: int = 3) -> list[dict]:
    """
    텍스트/책 키워드로 관련 YouTube 영상 검색
    """
    if _yt_ok:
        return _search_youtube_api(text, book_title, limit)
    return _mock_search(text, limit)


def search_scholar(text: str, limit: int = 2) -> list[dict]:
    """관련 학술 자료 검색 (Mock)"""
    seed  = int(hashlib.md5(text[:20].encode()).hexdigest(), 16)
    start = seed % len(_MOCK_SCHOLAR)
    results = []
    for i in range(min(limit, len(_MOCK_SCHOLAR))):
        results.append(_MOCK_SCHOLAR[(start + i) % len(_MOCK_SCHOLAR)])
    return results


def get_all_resources(text: str, book_title: str = "") -> dict:
    """
    OCR 텍스트에 대한 모든 관련 리소스를 한번에 반환
    videos + scholar + wikipedia_summary
    """
    videos  = search_related_videos(text, book_title, limit=3)
    scholar = search_scholar(text, limit=2)
    wiki    = _mock_wiki_summary(text, book_title)

    return {
        "videos":  videos,
        "scholar": scholar,
        "wiki":    wiki,
        "total":   len(videos) + len(scholar),
    }


# ══════════════════════════════════════════════════════════════
#  내부 구현
# ══════════════════════════════════════════════════════════════

def _search_youtube_api(text: str, book_title: str, limit: int) -> list[dict]:
    """실제 YouTube Data API v3 호출"""
    try:
        import requests
        query   = f"{book_title} {text[:30]}".strip()
        params  = {
            "part":       "snippet",
            "q":          query,
            "type":       "video",
            "maxResults": limit,
            "key":        YOUTUBE_API_KEY,
            "relevanceLanguage": "ko",
        }
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params, timeout=5
        )
        if resp.status_code != 200:
            return _mock_search(text, limit)

        items   = resp.json().get("items", [])
        results = []
        for item in items:
            vid_id  = item["id"]["videoId"]
            snippet = item["snippet"]
            results.append({
                "video_id":    vid_id,
                "title":       snippet["title"],
                "channel":     snippet["channelTitle"],
                "duration":    "—",
                "thumbnail":   snippet["thumbnails"]["medium"]["url"],
                "url":         f"https://youtube.com/watch?v={vid_id}",
                "description": snippet.get("description", "")[:100],
                "tags":        [],
                "view_count":  "—",
            })
        return results
    except Exception as e:
        print(f"[YouTube API 오류] {e}")
        return _mock_search(text, limit)


def _mock_search(text: str, limit: int) -> list[dict]:
    """일관된 Mock 영상 반환"""
    seed  = int(hashlib.md5(text[:20].encode()).hexdigest(), 16)
    start = seed % len(_MOCK_VIDEOS)
    results = []
    for i in range(min(limit, len(_MOCK_VIDEOS))):
        results.append(_MOCK_VIDEOS[(start + i) % len(_MOCK_VIDEOS)])
    return results


def _mock_wiki_summary(text: str, book_title: str) -> dict:
    """Mock 위키피디아 요약"""
    summaries = {
        "사피엔스": "유발 하라리의 2011년 저서. 인류 역사를 인지, 농업, 과학 혁명의 세 단계로 분석.",
        "어린왕자": "생텍쥐페리의 1943년 소설. 어른들이 잃어버린 순수함과 상상력을 이야기.",
        "코스모스": "칼 세이건의 1980년 저서. 천문학과 우주 역사를 대중적으로 서술.",
        "1984":    "조지 오웰의 1949년 디스토피아 소설. 전체주의와 감시 사회를 경고.",
        "데미안":  "헤르만 헤세의 1919년 성장소설. 자아 발견과 내면의 목소리를 따르는 여정.",
    }
    summary = summaries.get(book_title, "이 책에 대한 요약 정보를 가져오는 중입니다.")
    return {
        "title":   book_title or "관련 정보",
        "summary": summary,
        "url":     f"https://ko.wikipedia.org/wiki/{book_title}" if book_title else "https://ko.wikipedia.org",
        "source":  "mock",
    }
