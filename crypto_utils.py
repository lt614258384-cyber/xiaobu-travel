import base64
import os

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from cryptography.fernet import Fernet

_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

# ── API Key encryption (Fernet symmetric, key derived from SECRET_KEY) ──

def _get_fernet() -> Fernet:
    """Derive a Fernet key from SECRET_KEY. Cached per process."""
    from config import settings
    import hashlib
    raw = settings.SECRET_KEY.encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def mask_api_key(plaintext: str) -> str:
    """Encrypt an API Key before storing in the database."""
    if not plaintext:
        return ""
    f = _get_fernet()
    token = f.encrypt(plaintext.encode())
    return "$enc$" + token.decode()


def unmask_api_key(ciphertext: str) -> str:
    """Decrypt an API Key when reading from the database."""
    if not ciphertext or not ciphertext.startswith("$enc$"):
        return ciphertext  # plaintext or empty
    try:
        f = _get_fernet()
        return f.decrypt(ciphertext[5:].encode()).decode()
    except Exception:
        return ""  # decryption failed, return empty


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerificationError:
        return False
