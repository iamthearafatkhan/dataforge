import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me-in-production")
    STORAGE_DIR = os.path.join(BASE_DIR, "storage")

    # Effective upload cap. Override via MAX_UPLOAD_MB env var.
    _mb = int(os.environ.get("MAX_UPLOAD_MB", "500"))
    MAX_CONTENT_LENGTH = _mb * 1024 * 1024

    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "json"}

    # Session lifetime — how long a user's data stays reachable.
    SESSION_TTL_HOURS = 24
    PERMANENT_SESSION_LIFETIME = timedelta(hours=SESSION_TTL_HOURS)

    # Cookie security & behaviour
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set to True once you're on HTTPS with a custom domain
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    SESSION_REFRESH_EACH_REQUEST = True