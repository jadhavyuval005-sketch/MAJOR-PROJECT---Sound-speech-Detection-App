import os
from datetime import timedelta


class Config:
    """All settings come from environment variables (see .env.example)."""

    # MySQL on Amazon RDS in production, e.g.
    # mysql+pymysql://user:pass@my-db.xxxx.ap-south-1.rds.amazonaws.com:3306/ssd
    # Falls back to a local SQLite file for development.
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///ssd_dev.db")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_HOURS", "8")))

    MAX_CONTENT_LENGTH = 6 * 1024 * 1024  # one short word recording is far below this
    MAX_AUDIO_SECONDS = 10

    # Audio storage: S3 if S3_BUCKET is set, otherwise a local folder.
    S3_BUCKET = os.getenv("S3_BUCKET")
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    LOCAL_AUDIO_DIR = os.getenv("LOCAL_AUDIO_DIR", os.path.abspath("audio_store"))

    # CloudWatch Logs if set.
    CLOUDWATCH_LOG_GROUP = os.getenv("CLOUDWATCH_LOG_GROUP")

    # "quality" (signal checks only) or "wav2vec2" (automatic phoneme scoring).
    ANALYZER = os.getenv("ANALYZER", "quality")
    WAV2VEC2_MODEL = os.getenv("WAV2VEC2_MODEL", "facebook/wav2vec2-lv-60-espeak-cv-ft")

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    LOGIN_PAGE_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "login-page"))
    # Built React app, served by Flask in production.
    FRONTEND_DIST = os.getenv(
        "FRONTEND_DIST",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")),
    )


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    JWT_SECRET_KEY = "test-secret-key-that-is-long-enough-for-hmac"
    S3_BUCKET = None
    CLOUDWATCH_LOG_GROUP = None
    ANALYZER = "quality"
    LOCAL_AUDIO_DIR = os.path.abspath("test_audio_store")
