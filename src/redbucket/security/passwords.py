"""Argon2id 密码哈希。"""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_HASHER = PasswordHasher()


def hash_password(plain: str) -> str:
    return _HASHER.hash(plain)


def verify_password(password_hash: str, plain: str) -> bool:
    try:
        return _HASHER.verify(password_hash, plain)
    except VerifyMismatchError:
        return False
