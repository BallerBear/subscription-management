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

# Password-reset emails: the link points at the frontend, the mail goes to Mailpit locally.
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3000").rstrip("/")
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))
