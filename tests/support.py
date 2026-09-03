"""Shared HTTP helpers and sample payloads for S1-S11."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

HARNESSES = ("codex", "agents", "claude", "openclaw")
DOC_TYPES = ("skill", "instructions", "plugin", "subagent")
ASSET_TYPES = ("skill", "mcp", "instructions", "subagent", "plugin")
PASSWORD = "secret123"
STORAGE_LIMIT = 10485760
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "translate"

SKILL_TEXT = (
    "---\n"
    "name: demo-skill\n"
    "description: a demo skill\n"
    "---\n"
    "Do the demo thing.\n"
)
SKILL_LOSSY_TEXT = (
    "---\n"
    "name: demo-skill\n"
    "description: a demo skill\n"
    "license: MIT\n"
    "---\n"
    "Do the demo thing.\n"
)
INSTRUCTIONS_TEXT = (
    "# Project instructions\n"
    "\n"
    "Follow these rules when the user asks.\n"
)
PLUGIN_TEXT = (
    "---\n"
    "name: pretty\n"
    "description: formats output\n"
    "---\n"
    "Format the answer.\n"
)
SUBAGENT_TEXT = (
    "---\n"
    "name: reviewer\n"
    "description: reviews code\n"
    "---\n"
    "Review the diff carefully.\n"
)
MCP_JSON_TEXT = (
    "{\n"
    '  "mcpServers": {\n'
    '    "demo-mcp": {\n'
    '      "command": "uvx",\n'
    '      "transport": "stdio",\n'
    '      "args": ["demo-mcp"]\n'
    "    }\n"
    "  }\n"
    "}\n"
)
MCP_TOML_TEXT = (
    'name = "demo-mcp"\n'
    'transport = "stdio"\n'
    'command = "uvx"\n'
    'args = ["demo-mcp"]\n'
)


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(
    client: TestClient,
    username: str,
    email: str | None = None,
    password: str = PASSWORD,
) -> Any:
    if email is None:
        email = f"{username}@example.com"
    return client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )


def login(
    client: TestClient,
    email: str,
    password: str = PASSWORD,
) -> Any:
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


def signup(
    client: TestClient,
    username: str,
    email: str | None = None,
    password: str = PASSWORD,
) -> str:
    if email is None:
        email = f"{username}@example.com"
    created = register(client, username, email, password)
    assert created.status_code == 201, created.text
    session = login(client, email, password)
    assert session.status_code == 200, session.text
    return session.json()["token"]


def create_bucket(
    client: TestClient,
    token: str,
    username: str,
    name: str,
    visibility: str = "public",
    description: str = "",
    template: str | None = None,
) -> Any:
    body: dict[str, Any] = {
        "name": name,
        "visibility": visibility,
        "description": description,
    }
    if template is not None:
        body["template"] = template
    return client.post(
        f"/api/v1/users/{username}/buckets",
        json=body,
        headers=auth_header(token),
    )


def upload_asset(
    client: TestClient,
    token: str,
    username: str,
    bucket: str,
    asset_type: str,
    source_harness: str,
    path: str,
    files: list[dict],
) -> Any:
    return client.post(
        f"/api/v1/users/{username}/buckets/{bucket}/assets",
        json={
            "type": asset_type,
            "source_harness": source_harness,
            "path": path,
            "files": files,
        },
        headers=auth_header(token),
    )


def text_file(path: str, text: str) -> dict:
    return {"path": path, "content_text": text}


def b64_file(path: str, payload: bytes) -> dict:
    encoded = base64.b64encode(payload).decode("ascii")
    return {"path": path, "content_base64": encoded}


def sample_files(asset_type: str) -> list[dict]:
    if asset_type == "skill":
        return [text_file("SKILL.md", SKILL_TEXT)]
    if asset_type == "instructions":
        return [text_file("AGENTS.md", INSTRUCTIONS_TEXT)]
    if asset_type == "plugin":
        return [text_file("plugin.md", PLUGIN_TEXT)]
    if asset_type == "subagent":
        return [text_file("agent.md", SUBAGENT_TEXT)]
    if asset_type == "mcp":
        return [text_file(".mcp.json", MCP_JSON_TEXT)]
    raise ValueError(asset_type)


def sample_path(asset_type: str) -> str:
    return {
        "skill": "skills/demo",
        "instructions": "notes",
        "plugin": "plugins/pretty",
        "subagent": "agents/reviewer",
        "mcp": "mcp/demo-mcp",
    }[asset_type]


def error_of(response: Any) -> dict:
    body = response.json()
    assert "error" in body, body
    return body["error"]


def assert_error(response: Any, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    err = error_of(response)
    assert err["code"] == code
    assert isinstance(err["message"], str) and err["message"]
    assert isinstance(err["details"], list)
    return err


def assert_field(err: dict, field: str) -> None:
    fields = [item.get("field") for item in err["details"]]
    assert field in fields, err


def assert_location(response: Any, location: str) -> None:
    assert response.headers.get("location") == location


def page_keys(body: dict) -> None:
    for key in (
        "items",
        "page",
        "per_page",
        "total",
        "has_more",
        "next_cursor",
    ):
        assert key in body, key


def commit_count(
    client: TestClient,
    username: str,
    bucket: str,
    token: str | None = None,
) -> int:
    headers = auth_header(token) if token else {}
    resp = client.get(
        f"/api/v1/users/{username}/buckets/{bucket}/commits",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["total"]


def snapshot_tree(client: TestClient, username: str, bucket: str):
    core = client.app.state.core
    owner, row = core._live_bucket(username, bucket)
    return core.git.snapshot(owner["id"], row["id"])


def load_tree(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            files[rel] = path.read_bytes()
    return files


def write_tree(root: Path, files: dict[str, bytes]) -> None:
    for rel, content in files.items():
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)


def unzip_response(payload: bytes) -> dict[str, bytes]:
    from redbucket.fileset import unzip_bytes

    return unzip_bytes(payload)


def matrix_all(client: TestClient) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        resp = client.get(
            "/api/v1/translation-matrix",
            params={"page": page, "per_page": 100},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        rows.extend(body["items"])
        if not body["has_more"]:
            break
        page += 1
    return rows


def set_bucket_quota(client: TestClient, user_id: int, quota: int) -> None:
    client.app.state.core.store.run_commit(
        "UPDATE users SET bucket_quota = ? WHERE id = ?",
        (quota, user_id),
    )


def set_storage_limit(
    client: TestClient,
    bucket_id: int,
    limit_bytes: int,
) -> None:
    client.app.state.core.store.run_commit(
        "UPDATE buckets SET storage_limit_bytes = ? WHERE id = ?",
        (limit_bytes, bucket_id),
    )


def user_id_of(client: TestClient, username: str) -> int:
    row = client.app.state.core.user_by_name(username)
    assert row is not None
    return int(row["id"])


def dumps(data: Any) -> str:
    return json.dumps(data, sort_keys=True)
