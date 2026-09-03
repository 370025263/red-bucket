"""S9 性能门禁：这里只做模块可导入的冒烟。

S9 full run is `locust -f scripts/locust/browse.py`.
Do not run the 5-minute load mix in pytest.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

BROWSE = (
    Path(__file__).resolve().parents[1] / "scripts" / "locust" / "browse.py"
)


def test_s9_locust_module_imports() -> None:
    pytest.importorskip("locust")
    spec = importlib.util.spec_from_file_location("rb_locust_browse", BROWSE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "BrowseUser")
