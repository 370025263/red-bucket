"""在资产文件树里找主文件。"""
from __future__ import annotations


def basename_of(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def find_named(
    files: dict[str, bytes],
    names: tuple[str, ...],
) -> tuple[str, bytes] | None:
    wanted = {item.lower() for item in names}
    for path, content in files.items():
        if basename_of(path).lower() in wanted:
            return path, content
    return None


def decode_utf8(payload: bytes) -> str:
    return payload.decode("utf-8", errors="strict")


def first_markdown(files: dict[str, bytes]) -> tuple[str, str] | None:
    for path in sorted(files):
        if path.lower().endswith(".md"):
            return path, decode_utf8(files[path])
    return None
