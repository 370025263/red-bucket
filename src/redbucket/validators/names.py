"""用户名、bucket 名、邮箱。"""
from __future__ import annotations

import re

from redbucket.errors import validation_failed

USERNAME_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{1,37}[a-z0-9])$"
)
BUCKET_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9._-]{0,98}[a-z0-9])?$"
)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_name(value: str) -> str:
    return value.casefold()


def require_username(value: str) -> str:
    if len(value) < 3 or len(value) > 39:
        raise validation_failed(
            [{"field": "username", "issue": "invalid username"}]
        )
    if not USERNAME_RE.fullmatch(value):
        raise validation_failed(
            [{"field": "username", "issue": "invalid username"}]
        )
    return value


def require_bucket_name(value: str) -> str:
    if len(value) < 1 or len(value) > 100:
        raise validation_failed(
            [{"field": "name", "issue": "invalid bucket name"}]
        )
    if not BUCKET_RE.fullmatch(value):
        raise validation_failed(
            [{"field": "name", "issue": "invalid bucket name"}]
        )
    return value


def require_email(value: str) -> str:
    if not EMAIL_RE.fullmatch(value) or len(value) > 254:
        raise validation_failed(
            [{"field": "email", "issue": "invalid email"}]
        )
    return value


def require_password(value: str) -> str:
    if len(value) < 8:
        raise validation_failed(
            [{"field": "password", "issue": "must be at least 8 characters"}]
        )
    return value
