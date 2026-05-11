"""
pytest 공용 픽스처
모든 테스트가 공유하는 Flask 테스트 클라이언트
"""
import sys, os, json
import pytest

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def app():
    """Flask 앱 인스턴스 (세션 전체 공유)"""
    from app.factory import create_app
    application = create_app()
    application.config["TESTING"] = True
    application.config["DEBUG"]   = False
    yield application


@pytest.fixture(scope="session")
def client(app):
    """Flask 테스트 클라이언트"""
    return app.test_client()


@pytest.fixture
def json_post(client):
    """JSON POST 헬퍼"""
    def _post(url, data):
        return client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
        )
    return _post


@pytest.fixture
def json_get(client):
    """JSON GET 헬퍼"""
    def _get(url, params=None):
        query = "?" + "&".join(f"{k}={v}" for k, v in (params or {}).items())
        return client.get(url + (query if params else ""))
    return _get
