"""
LUMA 환경 설정 — 개발 / 프로덕션 자동 분리
.env 파일 또는 환경변수로 주입
"""
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # ── 앱 기본 ──────────────────────────────────────
    APP_NAME:    str  = "LUMA"
    SECRET_KEY:  str  = "dev-secret-change-in-production"
    DEBUG:       bool = True
    PORT:        int  = 5000
    HOST:        str  = "0.0.0.0"
    ENV:         str  = "development"   # development | production

    # ── AI / Gemini ───────────────────────────────────
    GEMINI_API_KEY:    str = ""
    GEMINI_MODEL:      str = "gemini-2.5-flash"

    # ── Firebase ─────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: str = "firebase-credentials.json"

    # ── Google APIs ───────────────────────────────────
    GOOGLE_MAPS_API_KEY:  str = ""
    GOOGLE_BOOKS_API_KEY: str = ""
    YOUTUBE_API_KEY:      str = ""

    # ── 기능 플래그 ────────────────────────────────────
    ENABLE_OCR:          bool = True
    ENABLE_AI:           bool = True
    ENABLE_MAPS:         bool = True

    # ── CORS ─────────────────────────────────────────
    CORS_ORIGINS: list = field(default_factory=lambda: ["*"])

    @classmethod
    def from_env(cls) -> "Config":
        """환경변수 / .env 파일에서 설정 로드"""
        _load_dotenv()
        return cls(
            APP_NAME   = os.getenv("APP_NAME", "LUMA"),
            SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production"),
            DEBUG      = os.getenv("FLASK_DEBUG", "true").lower() == "true",
            PORT       = int(os.getenv("PORT", "5000")),
            HOST       = os.getenv("HOST", "0.0.0.0"),
            ENV        = os.getenv("FLASK_ENV", "development"),

            GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", ""),
            GEMINI_MODEL     = os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),

            FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json"),

            GOOGLE_MAPS_API_KEY  = os.getenv("GOOGLE_MAPS_API_KEY", ""),
            GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", ""),
            YOUTUBE_API_KEY      = os.getenv("YOUTUBE_API_KEY", ""),

            ENABLE_OCR   = os.getenv("ENABLE_OCR",  "true").lower() == "true",
            ENABLE_AI    = os.getenv("ENABLE_AI",   "true").lower() == "true",
            ENABLE_MAPS  = os.getenv("ENABLE_MAPS", "true").lower() == "true",
        )

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def gemini_ready(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.ENABLE_AI)

    @property
    def maps_ready(self) -> bool:
        return bool(self.GOOGLE_MAPS_API_KEY and self.ENABLE_MAPS)

    def summary(self) -> dict:
        return {
            "env":           self.ENV,
            "debug":         self.DEBUG,
            "gemini":        "✅ 연결됨" if self.gemini_ready else "⚠️  Mock 모드",
            "firebase":      "✅ 연결됨" if os.path.exists(self.FIREBASE_CREDENTIALS_PATH) else "⚠️  Mock 모드",
            "google_maps":   "✅ 연결됨" if self.maps_ready else "⚠️  Mock 모드",
        }


def _load_dotenv():
    """python-dotenv 없어도 .env 수동 파싱"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return
    except ImportError:
        pass
    env_path = ".env"
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


# 싱글턴
settings = Config.from_env()
