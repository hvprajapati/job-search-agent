"""Argon2id password hashing."""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def hash_password(password: str) -> str:
    """Hash a password with Argon2id."""
    return _hasher.hash(password)


def verify_password(hash_: str, password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return _hasher.verify(hash_, password)
    except VerifyMismatchError:
        return False
