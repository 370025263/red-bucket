"""仓库路径。磁盘按 user_id/bucket_id，与 username 无关。"""
from __future__ import annotations

from pathlib import Path


def repo_path(storage_root: Path, user_id: int, bucket_id: int) -> Path:
    return storage_root / str(user_id) / f"{bucket_id}.git"


def lock_path(storage_root: Path, user_id: int, bucket_id: int) -> Path:
    parent = storage_root / str(user_id)
    return parent / f"{bucket_id}.lock"
