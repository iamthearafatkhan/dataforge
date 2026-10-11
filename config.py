import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me-in-production")
    STORAGE_DIR = os.path.join(BASE_DIR, "storage")

    # Effective upload cap. Override via MAX_UPLOAD_MB env var.
    # Local dev: 500 MB. Koyeb free tier: 50 MB (recommended).
    _mb = int(os.environ.get("MAX_UPLOAD_MB", "500"))
    MAX_CONTENT_LENGTH = _mb * 1024 * 1024

    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "json"}
    SESSION_TTL_HOURS = 24