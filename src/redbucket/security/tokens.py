"""不透明 Bearer token：明文只回一次，库内存 SHA-256。

device code 走同一套哈希：明文只回给发起的 agent 进程一次。
"""
from __future__ import annotations

import hashlib
import secrets


def issue_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    digest = hashlib.sha256()
    digest.update(token.encode("utf-8"))
    return digest.hexdigest()


# 去掉 I L O U 0 1，念出来和抄下来都不会认错。
USER_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"


def issue_user_code() -> str:
    """人要念出来或抄进浏览器的短码，形如 BQ7K-2M4X。"""
    picked = [
        secrets.choice(USER_CODE_ALPHABET) for _ in range(8)
    ]
    return "".join(picked[:4]) + "-" + "".join(picked[4:])
