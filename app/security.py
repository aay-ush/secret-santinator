from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)

def hash_client_key(client_hash: str) -> str:
    return pwd_context.hash(client_hash)

def verify_client_key(client_hash: str, stored_hash: str) -> bool:
    return pwd_context.verify(client_hash, stored_hash)

