"""Password reset: single-use, expiring, and only a HASH of the token is stored.

Flow:  forgot-password -> create_reset_link() + send_reset_email()
       reset-password  -> consume_token_and_set_password()
"""

import hashlib
import logging
import secrets
import smtplib
from email.message import EmailMessage

from app.core.config import APP_BASE_URL, SMTP_HOST, SMTP_PORT
from app.core.db import transaction

log = logging.getLogger(__name__)
TOKEN_MINUTES = 30


def _hash(token: str) -> str:
    # SHA-256 is enough here (not bcrypt): the token is 256 random bits, so it
    # cannot be guessed or brute-forced the way a human password can.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_reset_link(email: str) -> str | None:
    """Store a fresh token for an active user. Returns the link, or None if no such user."""
    with transaction() as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE lower(email) = lower(%s) AND is_active",
            (email,),
        ).fetchone()
        if user is None:
            return None
        token = secrets.token_urlsafe(32)  # goes in the email; only its hash is saved
        conn.execute(
            """
            INSERT INTO password_resets (user_id, token_hash, expires_at)
            VALUES (%s, %s, now() + make_interval(mins => %s))
            """,
            (user["id"], _hash(token), TOKEN_MINUTES),
        )
    return f"{APP_BASE_URL}/reset-password?token={token}"


def send_reset_email(email: str, link: str) -> None:
    """Send through Mailpit/SMTP. If that fails, print the link so the demo never gets stuck."""
    msg = EmailMessage()
    msg["Subject"] = "Reset your Brightloop password"
    msg["From"] = "Brightloop <no-reply@brightloop.example.com>"
    msg["To"] = email
    msg.set_content(
        f"Someone asked to reset the password for this account.\n\n"
        f"Choose a new password (the link works once and expires in {TOKEN_MINUTES} minutes):\n{link}\n\n"
        f"If this was not you, ignore this email."
    )
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5) as smtp:
            smtp.send_message(msg)
    except OSError:  # connection refused, timeout, DNS: mail server unreachable
        log.warning("SMTP unavailable, printing reset link instead: %s", link)
        print(f"[password reset] {email}: {link}")


def consume_token_and_set_password(token: str, password_hash: str) -> bool:
    """Atomically burn the token and change the password. False if invalid, used or expired."""
    with transaction() as conn:
        # One UPDATE both checks and burns the token. If two requests race with the
        # same token, Postgres lets exactly one of them match `used_at IS NULL`.
        row = conn.execute(
            """
            UPDATE password_resets SET used_at = now()
             WHERE token_hash = %s AND used_at IS NULL AND expires_at > now()
            RETURNING user_id
            """,
            (_hash(token),),
        ).fetchone()
        if row is None:
            return False
        conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, row["user_id"]))
        # Any other outstanding links for this user die too.
        conn.execute(
            "UPDATE password_resets SET used_at = now() WHERE user_id = %s AND used_at IS NULL",
            (row["user_id"],),
        )
    return True
