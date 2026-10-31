import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://brightloop:brightloop_local@localhost:5432/brightloop",
)
JWT_SECRET = os.getenv("JWT_SECRET", "replace-this-for-local-development")
ADMIN_BOOTSTRAP_TOKEN = os.getenv("ADMIN_BOOTSTRAP_TOKEN", "")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
