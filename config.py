import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me-in-production")
    STORAGE_DIR = os.path.join(BASE_DIR, "storage")
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024   # 500 MB
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "json"}
    SESSION_TTL_HOURS = 24