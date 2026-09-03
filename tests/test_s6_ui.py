"""S6 UI 与安装脚本。"""
from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest

from tests.support import (
    SKILL_TEXT,
    auth_header,
    create_bucket,
    signup,
    text_file,
    upload_asset,
)

REPO = Path(__file__).resolve().parents[1]
MANAGE_JS = REPO / "src" / "redbucket" / "web" / "static" / "manage.js"
LOGO = REPO / "src" / "redbucket" / "web" / "static" / "logo.svg"
CSS = REPO / "src" / "redbucket" / "web" / "static" / "app.css"


def _public_repo(client, template: str | None = "claude"):
    token = signup(client, "alice")
    created = create_bucket(
        client,
        token,
        "alice",
        "tools",
        visibility="public",
        description="handy tools",
        template=template,
    )
    assert created.status_code == 201
    return token, created.json()


def test_s6_1_public_bucket_page(client) -> None:
    _public_repo(client)
    page = client.get("/alice/tools")
    assert page.status_code == 200
    html = page.text
    assert "/static/logo.svg" in html
    assert "brand-mark" in html
    assert "#C41E3A" in html
    assert "red-bucket" in html
    assert "alice" in html
    assert "tools" in html
    assert "public" in html
    assert ">Code<" in html
    assert "Issues" in html
    assert "Pull requests" in html
    assert 'class="files"' in html
    assert "About" in html
    assert "/alice/tools/guide.md" in html
    assert "#!/bin/sh" not in html
    assert "Star" not in html
    assert "Watch" not in html
    assert "Fork" not in html
    logo = client.get("/static/logo.svg")
    assert logo.status_code == 200
    assert b"<svg" in logo.content
    assert logo.content == LOGO.read_bytes()
    css = CSS.read_text(encoding="utf-8")
    assert "--rb-bucket: #C41E3A" in css
    assert ".install" in css
    assert "#2da44e" not in css
    assert "#238636" not in html


def test_s6_2_private_and_missing_match(client) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "hid", visibility="private")
    stranger = signup(client, "bobby")
    private = client.get("/alice/hid")
    missing = client.get("/alice/no-such")
    assert private.status_code == 404
    assert missing.status_code == 404
    assert "Not found" in private.text
    assert private.text == missing.text
    settings = client.get(
        "/alice/hid/settings",
        headers=auth_header(stranger),
    )
    assert settings.status_code == 404
    assert "Not found" in settings.text


def test_s6_3_html_without_js(client) -> None:
    _public_repo(client)
    page = client.get("/alice/tools")
    html = page.text
    assert "alice" in html and "tools" in html
    assert "Code" in html and "Issues" in html
    assert 'class="files"' in html
    assert "About" in html
    assert "handy tools" in html
    assert "/alice/tools/guide.md" in html


def test_s6_4_new_bucket_form_and_page(client) -> None:
    token = signup(client, "alice")
    form = client.get("/new")
    assert form.status_code == 200
    assert 'name="template"' in form.text
    assert 'value="agents"' in form.text
    assert 'value="public"' in form.text
    created = create_bucket(
        client,
        token,
        "alice",
        "lab",
        visibility="public",
        template="agents",
    )
    assert created.status_code == 201
    page = client.get(
        "/alice/lab",
        headers=auth_header(token),
    )
    assert page.status_code == 200
    assert "public" in page.text
    assert "alice" in page.text
    assert "lab" in page.text
    assert "AGENTS.md" in page.text
    assert "Code" in page.text


def test_s6_5_ui_only_hits_api_v1() -> None:
    import re

    script = MANAGE_JS.read_text(encoding="utf-8")
    assert "function api(path" in script
    literals = re.findall(r'"(/[^"]*)"', script)
    api_paths = [
        item for item in literals if item.startswith("/api")
    ]
    assert api_paths
    for path in api_paths:
        assert path.startswith("/api/v1/"), path
        assert not path.endswith("/install")
    assert "/copies" not in script


def test_s6_6_install_script_runs(data_dir, monkeypatch) -> None:
    del monkeypatch
    if not _have_cmd("node"):
        pytest.skip("node required for S6.6")
    import httpx
    import uvicorn

    from redbucket.main import create_app

    app = create_app()
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="error",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_port(port)
    base = f"http://127.0.0.1:{port}"
    try:
        with httpx.Client(base_url=base, timeout=30) as http:
            created = http.post(
                "/api/v1/auth/register",
                json={
                    "username": "alice",
                    "email": "alice@example.com",
                    "password": "secret123",
                },
            )
            assert created.status_code == 201, created.text
            session = http.post(
                "/api/v1/auth/login",
                json={
                    "email": "alice@example.com",
                    "password": "secret123",
                },
            )
            token = session.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}
            bucket = http.post(
                "/api/v1/users/alice/buckets",
                json={"name": "tools", "visibility": "public"},
                headers=headers,
            )
            assert bucket.status_code == 201, bucket.text
            uploaded = http.post(
                "/api/v1/users/alice/buckets/tools/assets",
                json={
                    "type": "skill",
                    "source_harness": "claude",
                    "path": "skills/demo",
                    "files": [
                        {"path": "SKILL.md", "content_text": SKILL_TEXT}
                    ],
                },
                headers=headers,
            )
            assert uploaded.status_code == 201, uploaded.text
            body = http.get(
                "/api/v1/users/alice/buckets/tools/install-script",
                params={"target": "claude"},
            )
            assert body.status_code == 200
            script = body.json()["script"]
        dest = data_dir / "installed"
        dest.mkdir()
        script_path = data_dir / "install.mjs"
        script_path.write_text(script, encoding="utf-8")
        env = os.environ.copy()
        env["RED_BUCKET_URL"] = base
        env["RED_BUCKET_DEST"] = str(dest)
        ran = subprocess.run(
            ["node", str(script_path)],
            env=env,
            check=False,
            capture_output=True,
        )
        assert ran.returncode == 0, ran.stderr
        skill = dest / "skills" / "demo" / "SKILL.md"
        assert skill.is_file()
        assert "demo-skill" in skill.read_text(encoding="utf-8")
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_s6_7_tree_and_blob_pages(client) -> None:
    _public_repo(client)
    root = client.get("/alice/tools")
    assert "README.md" in root.text
    assert "/alice/tools/blob/README.md" in root.text
    tree = client.get("/alice/tools/tree/skills")
    assert tree.status_code == 200
    assert "skills" in tree.text
    blob = client.get("/alice/tools/blob/README.md")
    assert blob.status_code == 200
    assert "# bucket" in blob.text or "bucket" in blob.text


def test_s6_8_readme_and_about(client) -> None:
    token, meta = _public_repo(client)
    page = client.get("/alice/tools")
    assert "handy tools" in page.text
    assert "public" in page.text
    assert str(meta["usage_bytes"]) in page.text
    assert str(meta["limit_bytes"]) in page.text
    assert "10485760" in page.text
    assert "Harness mix" in page.text
    detail = client.get("/api/v1/users/alice/buckets/tools")
    body = detail.json()
    assert body["description"] == "handy tools"
    assert body["visibility"] == "public"
    assert body["limit_bytes"] == 10485760
    del token


def test_s6_9_empty_bucket_hints(client) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "empty", visibility="public")
    page = client.get("/alice/empty")
    assert page.status_code == 200
    assert "This directory is empty." in page.text
    assert "Add a README or upload an asset." in page.text


def test_s6_10_issues_tab(client) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "tools", visibility="public")
    opened = client.post(
        "/api/v1/users/alice/buckets/tools/issues",
        json={"title": "broken skill", "body": "see log"},
        headers=auth_header(token),
    )
    assert opened.status_code == 201
    page = client.get("/alice/tools/issues")
    assert page.status_code == 200
    assert "#1 broken skill" in page.text
    assert "open" in page.text
    assert "alice" in page.text
    assert "/alice/tools/issues/1" in page.text
    assert "Issues (1)" in page.text
    meta = client.get("/api/v1/users/alice/buckets/tools")
    assert meta.json()["open_issues_count"] == 1
    code = client.get("/alice/tools")
    assert "Issues (1)" in code.text


def test_s6_11_owner_settings(client) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "tools", visibility="public")
    page = client.get(
        "/alice/tools/settings",
        headers=auth_header(token),
    )
    assert page.status_code == 200
    assert "description" in page.text
    assert "visibility" in page.text
    code = client.get("/alice/tools")
    assert "Settings" in code.text
    anon_page = client.get("/alice/tools/settings")
    assert anon_page.status_code == 200
    assert "settings-owner-panel" in anon_page.text


def test_s6_12_guide_markdown(client) -> None:
    _public_repo(client)
    guide = client.get("/alice/tools/guide.md")
    assert guide.status_code == 200
    assert "text/markdown" in guide.headers["content-type"]
    body = guide.text
    assert "alice/tools" in body
    for harness in ("claude", "codex", "agents", "openclaw"):
        assert f"install-script?target={harness}" in body
    assert "/translated?target=" in body
    assert "Authorization: Bearer" in body
    assert "npx skills add 370025263/red-bucket" in body
    assert "no red-bucket MCP server" in body
    assert "Ask before you run anything" in body


def test_s6_13_guide_hidden_for_private(client) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "hid", visibility="private")
    private = client.get("/alice/hid/guide.md")
    missing = client.get("/alice/no-such/guide.md")
    assert private.status_code == 404
    assert missing.status_code == 404
    assert private.text == missing.text
    owner = client.get(
        "/alice/hid/guide.md",
        headers=auth_header(token),
    )
    assert owner.status_code == 200
    assert "alice/hid" in owner.text


def test_s6_14_guide_lists_stored_assets(client) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "tools", visibility="public")
    uploaded = client.post(
        "/api/v1/users/alice/buckets/tools/assets",
        json={
            "type": "skill",
            "source_harness": "codex",
            "path": "skills/demo",
            "files": [{"path": "SKILL.md", "content_text": SKILL_TEXT}],
        },
        headers=auth_header(token),
    )
    assert uploaded.status_code == 201
    body = client.get("/alice/tools/guide.md").text
    assert "skills/demo" in body
    assert "codex" in body


def test_s6_lang_zh_hides_spec_talk(client) -> None:
    home = client.get("/?lang=zh")
    assert home.status_code == 200
    html = home.text
    assert 'lang="zh"' in html
    assert "翻译" in html
    assert "中文" in html
    assert "Three ways" not in html
    assert "lossless" not in html
    assert "provenance" not in html
    assert "translated fetch" not in html
    login = client.get("/login")
    assert login.status_code == 200
    assert "登录" in login.text


def _have_cmd(name: str) -> bool:
    from shutil import which

    return which(name) is not None


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _wait_port(port: int) -> None:
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("server did not start")


FOLDED_AGENT_TEXT = (
    "---\n"
    "name: acceptance\n"
    "description: >-\n"
    "  Acceptance specialist. Use <b>Playwright</b> to interact,\n"
    "  then judge the result against the written design.\n"
    "model: inherit\n"
    "---\n"
    "\n"
    "You are a skeptical acceptance agent.\n"
)


def test_s6_15_blob_frontmatter_is_a_table(client) -> None:
    token, _meta = _public_repo(client)
    uploaded = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "subagent",
        "claude",
        "agents/acceptance",
        [text_file("agent.md", FOLDED_AGENT_TEXT)],
    )
    assert uploaded.status_code == 201, uploaded.text
    page = client.get("/alice/tools/blob/agents/acceptance/agent.md")
    assert page.status_code == 200
    html = page.text.split('<div class="markdown"', 1)[1]
    assert '<table class="frontmatter">' in html
    assert '<th scope="row">name</th><td>acceptance</td>' in html
    assert '<th scope="row">model</th><td>inherit</td>' in html
    assert "Acceptance specialist. Use &lt;b&gt;Playwright&lt;/b&gt;" in html
    assert "<b>Playwright</b>" not in html
    assert "<h1>" not in html
    assert "description: &gt;-" not in html
    assert "<p>You are a skeptical acceptance agent.</p>" in html


def test_s6_16_odd_frontmatter_never_becomes_a_heading() -> None:
    from redbucket.mdrender import render_markdown

    odd = "---\njust text, no fields\n---\n\nBody line.\n"
    html = render_markdown(odd)
    assert "<h1>" not in html and "<h2>" not in html
    assert '<pre class="frontmatter-raw">' in html
    assert "just text, no fields" in html
    assert "<p>Body line.</p>" in html
    unclosed = "---\nname: x\n\nBody line.\n"
    assert "<h1>" not in render_markdown(unclosed)
    plain = "# Real heading\n\nBody.\n"
    assert "<h1>Real heading</h1>" in render_markdown(plain)
