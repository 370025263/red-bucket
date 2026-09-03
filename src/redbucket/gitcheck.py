"""启动时确认系统 git 可用。"""
from __future__ import annotations

import subprocess

from redbucket.utils.proc import windowless_subprocess_kwargs


def require_git() -> str:
    result = subprocess.run(
        ["git", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        **windowless_subprocess_kwargs(),
    )
    if result.returncode != 0:
        raise RuntimeError("git executable is required")
    return result.stdout.decode("utf-8", errors="replace").strip()
