import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def generate_temp_code(num_bytes: int = 9) -> str:
    # ~12 chars base64-ish; readable enough for in-person
    return secrets.token_urlsafe(num_bytes)

def set_reset_temp_code(participant, temp_code: str, ttl_minutes: int = 30) -> None:
    # store hash of client-side sha256(temp_code), not temp_code itself
    from app.views.auth_clienthash import sha256_hex_server  # if you already have helper; else see note below
    temp_sha = sha256_hex_server(temp_code)
    participant.reset_temp_hash = generate_password_hash(temp_sha)
    participant.reset_temp_expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
    participant.force_passphrase_change = True
    participant.reset_requested = False

