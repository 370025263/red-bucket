"""拒绝 .. 与绝对路径。"""
from __future__ import annotations

from redbucket.errors import validation_failed


def sanitize_relpath(path: str) -> str:
    if not path or path.startswith("/") or path.startswith("\\"):
        raise validation_failed(
            [{"field": "path", "issue": "absolute path is not allowed"}]
        )
    parts = path.replace("\\", "/").split("/")
    cleaned: list[str] = []
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise validation_failed(
                [{"field": "path", "issue": "parent traversal is not allowed"}]
            )
        if part == ".git":
            raise validation_failed(
                [{"field": "path", "issue": ".git is not allowed"}]
            )
        cleaned.append(part)
    if not cleaned:
        raise validation_failed(
            [{"field": "path", "issue": "empty path is not allowed"}]
        )
    joined = "/".join(cleaned)
    if "/.git/" in f"/{joined}/":
        raise validation_failed(
            [{"field": "path", "issue": ".git is not allowed"}]
        )
    return joined
