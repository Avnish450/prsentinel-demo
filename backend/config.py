import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR}/prsentinel.db")

# Admin credentials & Security
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "prsentinel-admin")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "prsentinel-secret-token")
SECRET_KEY = os.environ.get("SECRET_KEY", "prsentinel-production-secret-key-32chars!")

# Encryption secret for sensitive tokens (Fernet key)
ENCRYPTION_SECRET = os.environ.get("ENCRYPTION_SECRET", "8v1Xp7F2rM3kL9jW4qZ0tY5uI6oP8aB1cE2dF3gH4jK=")

# Operational limits
MAX_CLONE_TIMEOUT_SEC = int(os.environ.get("MAX_CLONE_TIMEOUT_SEC", 120))
MAX_REPO_SIZE_MB = int(os.environ.get("MAX_REPO_SIZE_MB", 250))
MAX_CONCURRENT_JOBS = int(os.environ.get("MAX_CONCURRENT_JOBS", 2))
MAX_DIFF_SIZE_BYTES = int(os.environ.get("MAX_DIFF_SIZE_BYTES", 5 * 1024 * 1024))  # 5MB

# GitHub credentials
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# CORS settings
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

