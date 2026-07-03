from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, stored_hash: str, algorithm: str, salt: str | None = None) -> tuple[bool, bool]:
    if algorithm == "argon2":
        try:
            valid = PASSWORD_HASHER.verify(stored_hash, password)
            return valid, valid and PASSWORD_HASHER.check_needs_rehash(stored_hash)
        except (VerifyMismatchError, InvalidHashError):
            return False, False
    if algorithm == "pbkdf2_sha256" and salt:
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
        candidate = base64.urlsafe_b64encode(digest).decode("ascii")
        return hmac.compare_digest(candidate, stored_hash), True
    return False, False


def random_token(bytes_count: int = 32) -> str:
    return secrets.token_urlsafe(bytes_count)


def token_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def keyed_digest(value: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()
