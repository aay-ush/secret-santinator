from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from passlib.context import CryptContext


pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


def hash_client_key(client_hash: str) -> str:
    """Store an argon2 hash of the client-provided SHA-256(passphrase)."""
    return pwd_context.hash(client_hash)


def verify_client_key(client_hash: str, stored_hash: str) -> bool:
    return pwd_context.verify(client_hash, stored_hash)


# ---------------------------------------------------------------------------
# Assignment encryption-at-rest
#
# Goal: assignments should not be readable via the DB (or admin UI) in plaintext.
# The server encrypts the receiver_id before persisting it.
#
# NOTE: If someone has access to the server environment variables / SECRET_KEY,
# they could still decrypt. This is aimed at preventing "admin user" access and
# casual DB inspection.
# ---------------------------------------------------------------------------


def _assignment_fernet() -> Fernet:
    """Returns a Fernet instance keyed by ASSIGNMENT_ENC_KEY or derived from SECRET_KEY."""
    explicit = (os.environ.get("ASSIGNMENT_ENC_KEY") or "").strip()
    if explicit:
        # Expect a urlsafe base64-encoded 32-byte key.
        key = explicit.encode("utf-8")
        return Fernet(key)

    # Derive a stable key from Flask SECRET_KEY so decrypt works across restarts.
    # Fernet requires a urlsafe base64-encoded 32-byte key.
    secret = (current_app.config.get("SECRET_KEY") or "").encode("utf-8")
    digest = hashlib.sha256(b"secretsanta-assignments|" + secret).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_assignment_recipient(receiver_id: int) -> str:
    """Encrypt receiver_id -> ciphertext token (string)."""
    f = _assignment_fernet()
    token = f.encrypt(str(int(receiver_id)).encode("utf-8"))
    return token.decode("utf-8")


def decrypt_assignment_recipient(token: str) -> int:
    """Decrypt ciphertext token -> receiver_id (int). Raises ValueError on failure."""
    try:
        f = _assignment_fernet()
        raw = f.decrypt(token.encode("utf-8"))
        return int(raw.decode("utf-8"))
    except (InvalidToken, ValueError, TypeError) as e:
        raise ValueError("Invalid assignment token") from e

