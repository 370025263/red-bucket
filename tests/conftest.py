"""App client fixture: unique data dir + lifespan TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from redbucket.main import create_app


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("RED_BUCKET_DATA", str(tmp_path))
    monkeypatch.delenv("RED_BUCKET_SQLITE", raising=False)
    monkeypatch.delenv("RED_BUCKET_STORAGE", raising=False)
    monkeypatch.delenv("RED_BUCKET_CACHE", raising=False)
    monkeypatch.delenv("RED_BUCKET_URL", raising=False)
    return tmp_path


@pytest.fixture
def client(data_dir):
    del data_dir
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
