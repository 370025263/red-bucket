"""1000 个 mock 用户，带代表性 buckets/assets。"""
from __future__ import annotations

import os
from pathlib import Path

from redbucket.security.passwords import hash_password
from redbucket.service import RedBucket
from redbucket.settings import Settings

SKILL_TEXT = """---
name: demo
description: mock skill
---
Do the demo task.
"""


def main() -> None:
    os.environ.setdefault("RED_BUCKET_DATA", str(Path("./data").resolve()))
    core = RedBucket(Settings())
    password_hash = hash_password("password12")
    stamp = __import__("redbucket.clock", fromlist=["utc_now"]).utc_now()
    for index in range(1, 1001):
        username = f"user{index:04d}"
        email = f"{username}@example.com"
        existing = core.user_by_name(username)
        if existing is not None:
            continue
        core.store.run_commit(
            "INSERT INTO users("
            "username, username_normalized, email, email_normalized, "
            "password_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                username,
                username,
                email,
                email,
                password_hash,
                stamp,
                stamp,
            ),
        )
    alice = core.user_by_name("user0001")
    if alice is None:
        raise RuntimeError("seed user missing")
    token_user = {
        "id": alice["id"],
        "username": alice["username"],
    }
    try:
        core.create_bucket(
            alice["username"],
            token_user,
            "tools",
            "public",
            "seed bucket",
            "claude",
        )
        core.create_asset(
            alice["username"],
            "tools",
            token_user,
            "skill",
            "claude",
            "skills/demo",
            [{"path": "SKILL.md", "content_text": SKILL_TEXT}],
        )
    except Exception as exc:
        print(f"seed bucket skipped: {exc}")
    print("seeded 1000 users")
    core.close()


if __name__ == "__main__":
    main()
