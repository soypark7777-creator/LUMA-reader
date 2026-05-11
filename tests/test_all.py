import io
"""
STEP 9 — 핵심 페이지 & 시스템 테스트
"""
import json


class TestHealthAndSystem:
    """헬스체크 & 시스템 상태"""

    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        d = r.get_json()
        assert d["status"] == "healthy"
        assert d["service"] == "LUMA"

    def test_system_status(self, client):
        r = client.get("/api/system/status")
        assert r.status_code == 200
        d = r.get_json()
        assert "apis"    in d
        assert "gemini"  in d["apis"]
        assert "firebase" in d["apis"]
        assert "maps"    in d["apis"]

    def test_404_api_returns_json(self, client):
        r = client.get("/api/does-not-exist-xyz")
        assert r.status_code == 404
        d = r.get_json()
        assert d["ok"] is False

    def test_root_dashboard(self, client):
        r = client.get("/")
        assert r.status_code == 200
        html = r.data.decode()
        assert "LUMA" in html
        assert "constellation" in html   # 별자리 데이터

    def test_community_main(self, client):
        r = client.get("/community/")
        assert r.status_code == 200
        html = r.data.decode()
        assert "공독의 장" in html or "view-map" in html

    def test_community_club_detail(self, client):
        r = client.get("/community/club_001")
        assert r.status_code == 200
        html = r.data.decode()
        assert "사피엔스" in html or "lcard" in html


class TestMemoAPI:
    """메모 CRUD API"""

    def test_save_memo(self, client):
        r = client.post("/api/memos/save",
            data=json.dumps({
                "book_title": "데미안",
                "content":    "새는 알을 깨고 나온다.",
                "tags":       ["성장", "자아"],
                "mood":       "inspired",
            }),
            content_type="application/json",
        )
        assert r.status_code == 201
        d = r.get_json()
        assert d["ok"] is True
        assert "memo_id" in d["memo"]

    def test_save_memo_empty_content(self, client):
        r = client.post("/api/memos/save",
            data=json.dumps({"book_title": "테스트", "content": ""}),
            content_type="application/json",
        )
        assert r.status_code == 400
        assert r.get_json()["ok"] is False

    def test_list_memos(self, client):
        r = client.get("/api/memos/list?user_id=user_demo")
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert isinstance(d["memos"], list)
        assert d["count"] >= 0

    def test_memo_stats(self, client):
        r = client.get("/api/memos/stats?user_id=user_demo")
        assert r.status_code == 200
        d = r.get_json()
        assert "total_memos" in d["stats"]

    def test_delete_nonexistent_memo(self, client):
        r = client.delete("/api/memos/memo_nonexistent_xyz")
        assert r.status_code == 404


class TestAIAPI:
    """AI 분석 API"""

    def test_ai_status(self, client):
        r = client.get("/api/ai/status")
        assert r.status_code == 200
        d = r.get_json()
        assert "mode" in d
        assert d["mode"] in ("gemini-1.5-flash", "mock")

    def test_ai_analyze(self, client):
        r = client.post("/api/ai/analyze",
            data=json.dumps({
                "book_title": "사피엔스",
                "content":    "인류는 허구를 믿는 능력으로 협력했다.",
                "tags":       ["인류학", "역사"],
                "mood":       "inspired",
            }),
            content_type="application/json",
        )
        assert r.status_code == 201
        d = r.get_json()
        assert d["ok"] is True
        assert "memo"     in d
        assert "keywords" in d
        assert "theme"    in d
        assert "reframe"  in d

    def test_ai_reframe(self, client):
        r = client.post("/api/ai/reframe",
            data=json.dumps({"content": "허구가 현실을 움직인다", "book_title": "사피엔스"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert "question" in d["reframe"]

    def test_ai_cross_insight(self, client):
        r = client.post("/api/ai/cross-insight",
            data=json.dumps({
                "memo1": {"content": "허구가 인류를 협력하게 했다",  "book_title": "사피엔스", "tags": ["인류학"]},
                "memo2": {"content": "가장 중요한 것은 눈에 보이지 않아", "book_title": "어린왕자", "tags": ["철학"]},
            }),
            content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert "connection_type" in d["insight"]
        assert "strength"        in d["insight"]

    def test_ai_connections(self, client):
        r = client.get("/api/ai/connections?user_id=user_demo")
        assert r.status_code == 200
        d = r.get_json()
        assert isinstance(d["connections"], list)

    def test_ai_discussion_guide(self, client):
        r = client.post("/api/ai/discussion",
            data=json.dumps({
                "book_title": "사피엔스",
                "messages":   ["허구가 인류를 협력하게 했다", "화폐도 허구다"],
                "guide_type": "debate",
            }),
            content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert "question" in d["guide"]

    def test_ai_meeting_report(self, client):
        r = client.post("/api/ai/report",
            data=json.dumps({
                "book_title":   "사피엔스",
                "messages":     ["허구 이야기", "화폐 이야기", "국가 이야기"],
                "participants": ["지민", "현우"],
            }),
            content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert "summary"      in d["report"]
        assert "key_insights" in d["report"]


class TestCommunityAPI:
    """공독의 장 API"""

    def test_create_club(self, client):
        r = client.post("/community/api/create",
            data=json.dumps({"name": "테스트 모임", "book_title": "파친코", "emoji": "🌊"}),
            content_type="application/json",
        )
        assert r.status_code == 201
        d = r.get_json()
        assert d["ok"] is True
        assert "club_id" in d["club"]

    def test_create_club_no_name(self, client):
        r = client.post("/community/api/create",
            data=json.dumps({"name": ""}),
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_post_card(self, client):
        r = client.post("/community/api/club_001/cards",
            data=json.dumps({
                "user_name": "테스터", "user_emoji": "⭐",
                "type": "thought", "content": "허구가 세상을 움직인다.",
            }),
            content_type="application/json",
        )
        assert r.status_code == 201
        d = r.get_json()
        assert d["ok"] is True
        assert d["card"]["type"] == "thought"

    def test_post_card_empty(self, client):
        r = client.post("/community/api/club_001/cards",
            data=json.dumps({"content": ""}),
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_like_card(self, client):
        r = client.post("/community/api/cards/card_001/like",
            data=json.dumps({"user_id": "user_demo"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert "liked"      in d
        assert "like_count" in d

    def test_comment_card(self, client):
        r = client.post("/community/api/cards/card_001/comment",
            data=json.dumps({"user_name": "나", "user_emoji": "⭐", "content": "공감해요!"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert "comment_count" in d

    def test_ai_guide(self, client):
        r = client.post("/community/api/club_001/ai-guide",
            data=json.dumps({"messages": ["허구 이야기"], "guide_type": "debate"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["card"]["is_ai"] is True

    def test_generate_report(self, client):
        # 먼저 카드 2개 추가
        for i in range(2):
            client.post("/community/api/club_001/cards",
                data=json.dumps({"user_name": f"멤버{i}", "user_emoji": "⭐",
                                 "type": "thought", "content": f"생각 {i}번"}),
                content_type="application/json",
            )
        r = client.post("/community/api/club_001/report",
            data=json.dumps({}), content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert "summary"      in d["report"]
        assert "key_insights" in d["report"]
        assert "next_questions" in d["report"]


class TestPlacesAPI:
    """독서 장소 API"""

    def test_all_spots(self, client):
        r = client.get("/api/places/all")
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert d["count"] > 0
        # 독서 점수 확인
        for s in d["spots"]:
            assert "reading_score" in s
            assert 0 <= s["reading_score"] <= 10

    def test_nearby_spots(self, client):
        r = client.get("/api/places/nearby?lat=37.5665&lng=126.9780&radius=5000")
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert isinstance(d["spots"], list)

    def test_nearby_missing_params(self, client):
        # lat/lng 없어도 기본값으로 동작
        r = client.get("/api/places/nearby")
        assert r.status_code == 200

    def test_spot_detail(self, client):
        r = client.get("/api/places/place_kr_001")
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert d["spot"]["name"] == "어니언 성수"
        assert "ai_tags"       in d["spot"]
        assert "reading_score" in d["spot"]
        assert "reviews"       in d["spot"]

    def test_spot_not_found(self, client):
        r = client.get("/api/places/place_nonexistent_xyz")
        assert r.status_code == 404

    def test_checkin(self, client):
        r = client.post("/api/places/place_kr_001/checkin",
            data=json.dumps({"user_id": "user_demo"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert "total" in d

    def test_add_review(self, client):
        r = client.post("/api/places/place_kr_001/review",
            data=json.dumps({"user": "테스터", "emoji": "⭐", "text": "정말 좋아요!", "score": 9}),
            content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True

    def test_review_empty(self, client):
        r = client.post("/api/places/place_kr_001/review",
            data=json.dumps({"text": ""}),
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_cities(self, client):
        r = client.get("/api/places/cities")
        assert r.status_code == 200
        d = r.get_json()
        assert "서울" in d["cities"]
        assert "도쿄" in d["cities"]
        assert "파리" in d["cities"]

    def test_filter_by_type(self, client):
        r = client.get("/api/places/all?type=library")
        assert r.status_code == 200
        d = r.get_json()
        for s in d["spots"]:
            assert s["type"] == "library"

    def test_filter_by_city(self, client):
        r = client.get("/api/places/all?city=서울")
        assert r.status_code == 200
        d = r.get_json()
        for s in d["spots"]:
            assert s["city"] == "서울"

    def test_place_status(self, client):
        r = client.get("/api/places/status")
        assert r.status_code == 200
        d = r.get_json()
        assert "total_spots" in d
        assert d["total_spots"] > 0


class TestOCRAPI:
    """STEP 6 — OCR 스캔 API"""

    # 1x1 픽셀 JPEG (최소 유효 이미지)
    TINY_JPG = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
        b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
        b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\x1e\xc3'
        b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
        b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
        b'\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04'
        b'\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa'
        b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd2\x8a(\x03\xff\xd9'
    )

    def test_ocr_status(self, client):
        r = client.get("/api/ocr/status")
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert "mode" in d
        assert d["mode"] in ("gemini-vision", "mock")

    def test_ocr_scan_file_upload(self, client):
        r = client.post(
            "/api/ocr/scan",
            data={"image": (io.BytesIO(self.TINY_JPG), "test.png", "image/png"), "language": "ko"},
            content_type="multipart/form-data",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert "text"       in d
        assert "confidence" in d
        assert "source"     in d
        assert "word_count" in d
        assert len(d["text"]) > 0

    def test_ocr_scan_base64(self, client):
        import base64, json
        b64 = base64.b64encode(self.TINY_JPG).decode()
        r = client.post(
            "/api/ocr/scan",
            data=json.dumps({"image_base64": b64, "language": "ko"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

    def test_ocr_scan_no_image(self, client):
        r = client.post("/api/ocr/scan", content_type="application/json",
                        data="{}")
        assert r.status_code == 400

    def test_ocr_enhance(self, client):
        r = client.post(
            "/api/ocr/enhance",
            data=json.dumps({"text": "인류가 지구를 지배할수있었던이유"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert "corrected" in d
        assert "quality"   in d

    def test_ocr_enhance_no_text(self, client):
        r = client.post("/api/ocr/enhance",
                        data=json.dumps({"text": ""}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_ocr_book_cover(self, client):
        r = client.post(
            "/api/ocr/book-cover",
            data={"image": (io.BytesIO(self.TINY_JPG), "cover.png", "image/png")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert "title"  in d
        assert "author" in d

    def test_ocr_analyze_page(self, client):
        r = client.post(
            "/api/ocr/analyze-page",
            data={"image": (io.BytesIO(self.TINY_JPG), "page.png", "image/png")},
            content_type="multipart/form-data",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert "full_text"  in d
        assert "paragraphs" in d

    def test_ocr_generate_memo(self, client):
        r = client.post(
            "/api/ocr/generate-memo",
            data=json.dumps({
                "text":       "인류가 지구를 지배할 수 있었던 이유는 허구를 믿는 능력이다.",
                "book_title": "사피엔스",
            }),
            content_type="application/json",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"] is True
        assert "memo_draft" in d
        assert "tags"       in d
        assert "mood"       in d
        assert "insight"    in d

    def test_ocr_generate_memo_no_text(self, client):
        r = client.post("/api/ocr/generate-memo",
                        data=json.dumps({"text": ""}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_ocr_full_pipeline(self, client):
        r = client.post(
            "/api/ocr/full-pipeline",
            data={
                "image":      (io.BytesIO(self.TINY_JPG), "scan.png", "image/png"),
                "book_title": "사피엔스",
                "language":   "ko",
            },
            content_type="multipart/form-data",
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["ok"]       is True
        assert "ocr"         in d
        assert "memo"        in d
        assert "resources"   in d
        assert "videos"      in d["resources"]
        assert "scholar"     in d["resources"]
        assert "pipeline"    in d

    def test_ocr_page_renders(self, client):
        r = client.get("/ocr")
        assert r.status_code == 200
        html = r.data.decode()
        assert "OCR 스캔" in html
        assert "full-pipeline" in html
        assert "camera" in html.lower()


import json  # test 파일 상단에 없어서 추가
