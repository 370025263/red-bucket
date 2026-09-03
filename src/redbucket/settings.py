"""进程配置。只读环境变量，不兼容旧键名。"""
from __future__ import annotations

import os
from pathlib import Path

CANONICAL_PUBLIC_ORIGIN = "https://redbucket.store"


class Settings:
    def __init__(self) -> None:
        data_root = Path(
            os.environ.get("RED_BUCKET_DATA", "./data")
        ).resolve()
        self.sqlite_path = Path(
            os.environ.get(
                "RED_BUCKET_SQLITE",
                str(data_root / "red-bucket.sqlite"),
            )
        )
        self.storage_root = Path(
            os.environ.get(
                "RED_BUCKET_STORAGE",
                str(data_root / "git"),
            )
        )
        raw_origin = os.environ.get(
            "RED_BUCKET_URL",
            CANONICAL_PUBLIC_ORIGIN,
        )
        self.public_origin = raw_origin.rstrip("/")
        self.cache_root = Path(
            os.environ.get(
                "RED_BUCKET_CACHE",
                str(data_root / "translate-cache"),
            )
        )
