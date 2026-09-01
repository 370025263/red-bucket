"""windowless_subprocess_kwargs 的平台行为。"""
from __future__ import annotations

import sys

from redbucket.utils.proc import windowless_subprocess_kwargs


def test_windowless_kwargs_empty_off_windows() -> None:
    result = windowless_subprocess_kwargs()
    if sys.platform == "win32":
        assert "creationflags" in result
        return
    assert result == {}
