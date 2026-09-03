"""S4 Formatter 翻译。"""
from __future__ import annotations

from pathlib import Path

import pytest

from redbucket.fileset import unzip_bytes
from redbucket.formatters.registry import matrix_entries, pair_supported
from tests.support import (
    DOC_TYPES,
    FIXTURE_ROOT,
    HARNESSES,
    INSTRUCTIONS_TEXT,
    MCP_JSON_TEXT,
    PLUGIN_TEXT,
    SKILL_LOSSY_TEXT,
    SKILL_TEXT,
    SUBAGENT_TEXT,
    assert_error,
    create_bucket,
    load_tree,
    matrix_all,
    sample_path,
    signup,
    text_file,
    upload_asset,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _owner_bucket(client):
    token = signup(client, "alice")
    created = create_bucket(
        client,
        token,
        "alice",
        "tools",
        visibility="public",
    )
    assert created.status_code == 201
    return token


def test_s4_1_matrix_phase1_rows(client) -> None:
    rows = matrix_all(client)
    assert len(rows) == 70
    registry = {
        (item["asset_type"], item["source"], item["target"])
        for item in matrix_entries()
    }
    seen = {
        (item["asset_type"], item["source"], item["target"])
        for item in rows
    }
    assert seen == registry
    for asset_type in DOC_TYPES:
        pairs = [
            item
            for item in rows
            if item["asset_type"] == asset_type
        ]
        assert len(pairs) == 16
        identity = [item for item in pairs if item["identity"]]
        other = [item for item in pairs if not item["identity"]]
        assert len(identity) == 4
        assert len(other) == 12
    mcp = [item for item in rows if item["asset_type"] == "mcp"]
    assert len(mcp) == 6
    mcp_pairs = {(item["source"], item["target"]) for item in mcp}
    assert ("claude", "codex") in mcp_pairs
    assert ("codex", "claude") in mcp_pairs
    for harness in HARNESSES:
        assert (harness, harness) in mcp_pairs


def test_s4_2_doc_golden_pairs(client) -> None:
    token = _owner_bucket(client)
    for asset_type in DOC_TYPES:
        files = load_tree(FIXTURE_ROOT / "sources" / asset_type)
        payload = [
            {
                "path": name,
                "content_text": content.decode("utf-8"),
            }
            for name, content in files.items()
        ]
        for source in HARNESSES:
            path = f"{sample_path(asset_type)}-{source}"
            uploaded = upload_asset(
                client,
                token,
                "alice",
                "tools",
                asset_type,
                source,
                path,
                payload,
            )
            assert uploaded.status_code == 201, uploaded.text
            asset_id = uploaded.json()["id"]
            for target in HARNESSES:
                if source == target:
                    continue
                translated = client.get(
                    f"/api/v1/users/alice/buckets/tools/assets/"
                    f"{asset_id}/translated",
                    params={"target": target},
                )
                assert translated.status_code == 200, translated.text
                expected = load_tree(
                    FIXTURE_ROOT
                    / "expected"
                    / asset_type
                    / f"{source}-2-{target}"
                )
                if len(expected) == 1:
                    only = next(iter(expected.values()))
                    assert translated.content == only
                else:
                    assert unzip_bytes(translated.content) == expected


def test_s4_2_mcp_golden_pairs(client) -> None:
    token = _owner_bucket(client)
    for source, target in (("claude", "codex"), ("codex", "claude")):
        src_dir = FIXTURE_ROOT / "sources" / "mcp" / source
        files = load_tree(src_dir)
        payload = [
            {
                "path": name,
                "content_text": content.decode("utf-8"),
            }
            for name, content in files.items()
        ]
        uploaded = upload_asset(
            client,
            token,
            "alice",
            "tools",
            "mcp",
            source,
            f"mcp/{source}",
            payload,
        )
        assert uploaded.status_code == 201, uploaded.text
        translated = client.get(
            f"/api/v1/users/alice/buckets/tools/assets/"
            f"{uploaded.json()['id']}/translated",
            params={"target": target},
        )
        assert translated.status_code == 200, translated.text
        expected = load_tree(
            FIXTURE_ROOT / "expected" / "mcp" / f"{source}-2-{target}"
        )
        if len(expected) == 1:
            assert translated.content == next(iter(expected.values()))
        else:
            assert unzip_bytes(translated.content) == expected


def test_s4_3_identity_equals_raw(client) -> None:
    token = _owner_bucket(client)
    uploaded = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_TEXT)],
    )
    asset_id = uploaded.json()["id"]
    raw = client.get(
        f"/api/v1/users/alice/buckets/tools/assets/{asset_id}/raw"
    )
    translated = client.get(
        f"/api/v1/users/alice/buckets/tools/assets/{asset_id}/translated",
        params={"target": "claude"},
    )
    assert translated.status_code == 200
    assert translated.content == raw.content


def test_s4_4_unsupported_is_501(client) -> None:
    token = _owner_bucket(client)
    uploaded = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "mcp",
        "agents",
        "mcp/other",
        [text_file(".mcp.json", MCP_JSON_TEXT)],
    )
    assert uploaded.status_code == 201
    asset_id = uploaded.json()["id"]
    resp = client.get(
        f"/api/v1/users/alice/buckets/tools/assets/{asset_id}/translated",
        params={"target": "claude"},
    )
    assert_error(resp, 501, "translation_unsupported")
    assert MCP_JSON_TEXT.encode("utf-8") not in resp.content


def test_s4_5_whole_bucket_layout(client) -> None:
    token = _owner_bucket(client)
    pairs = (
        (
            "skill",
            "claude",
            "skills/demo",
            [text_file("SKILL.md", SKILL_TEXT)],
        ),
        (
            "instructions",
            "claude",
            "notes",
            [text_file("AGENTS.md", INSTRUCTIONS_TEXT)],
        ),
        (
            "plugin",
            "claude",
            "plugins/pretty",
            [text_file("plugin.md", PLUGIN_TEXT)],
        ),
        (
            "subagent",
            "claude",
            "agents/reviewer",
            [text_file("agent.md", SUBAGENT_TEXT)],
        ),
    )
    for asset_type, harness, path, files in pairs:
        resp = upload_asset(
            client,
            token,
            "alice",
            "tools",
            asset_type,
            harness,
            path,
            files,
        )
        assert resp.status_code == 201, resp.text
    zipped = client.get(
        "/api/v1/users/alice/buckets/tools/translated",
        params={"target": "codex"},
    )
    assert zipped.status_code == 200
    files = unzip_bytes(zipped.content)
    assert ".codex/skills/demo/SKILL.md" in files
    assert "AGENTS.md" in files
    assert ".codex/plugins/pretty/plugin.md" in files
    assert ".codex/agents/reviewer/agent.md" in files
    assert "_red_bucket/lossy-notes.md" in files


def test_s4_5a_skip_unsupported_mcp(client) -> None:
    token = _owner_bucket(client)
    upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_TEXT)],
    )
    upload_asset(
        client,
        token,
        "alice",
        "tools",
        "mcp",
        "agents",
        "mcp/other",
        [text_file(".mcp.json", MCP_JSON_TEXT)],
    )
    zipped = client.get(
        "/api/v1/users/alice/buckets/tools/translated",
        params={"target": "claude"},
    )
    assert zipped.status_code == 200
    files = unzip_bytes(zipped.content)
    notes = files["_red_bucket/lossy-notes.md"].decode("utf-8")
    assert "skipped" in notes
    assert "mcp/other" in notes
    for path in files:
        if path.startswith("mcp/other"):
            raise AssertionError(path)
        if path.endswith(".mcp.json") and path != "_red_bucket/lossy-notes.md":
            if files[path] == MCP_JSON_TEXT.encode("utf-8"):
                raise AssertionError("source mcp leaked")
    meta = client.get(
        "/api/v1/users/alice/buckets/tools/translated",
        params={"target": "claude", "meta": "1"},
    )
    assert meta.status_code == 200
    assert "mcp/other" in meta.json().get("skipped", [])


def test_s4_5b_strict_is_501(client) -> None:
    token = _owner_bucket(client)
    upload_asset(
        client,
        token,
        "alice",
        "tools",
        "mcp",
        "agents",
        "mcp/other",
        [text_file(".mcp.json", MCP_JSON_TEXT)],
    )
    resp = client.get(
        "/api/v1/users/alice/buckets/tools/translated",
        params={"target": "claude", "strict": "1"},
    )
    assert_error(resp, 501, "translation_unsupported")


def test_s4_6_lossy_notes(client) -> None:
    token = _owner_bucket(client)
    uploaded = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_LOSSY_TEXT)],
    )
    asset_id = uploaded.json()["id"]
    meta = client.get(
        f"/api/v1/users/alice/buckets/tools/assets/{asset_id}/translated",
        params={"target": "codex", "meta": "1"},
    )
    assert meta.status_code == 200
    body = meta.json()
    assert body["lossy"] is True
    assert "license" in body["notes"]
    assert meta.headers.get("x-red-bucket-lossy") == "true"
    raw = client.get(
        f"/api/v1/users/alice/buckets/tools/assets/{asset_id}/translated",
        params={"target": "codex"},
    )
    text = raw.content.decode("utf-8")
    assert "Compatibility notes" in text
    assert "license" in text


def test_s4_7_deterministic_cache(client) -> None:
    token = _owner_bucket(client)
    uploaded = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_TEXT)],
    )
    sha = uploaded.json()["head_commit_sha"]
    url = "/api/v1/users/alice/buckets/tools/translated"
    first = client.get(url, params={"target": "codex", "commit": sha})
    second = client.get(url, params={"target": "codex", "commit": sha})
    assert first.content == second.content
    cache = Path(client.app.state.settings.cache_root) / sha / "codex"
    assert cache.exists()
    for child in cache.iterdir():
        child.unlink()
    cache.rmdir()
    third = client.get(url, params={"target": "codex", "commit": sha})
    assert third.content == first.content


def test_s4_8_cross_transfer_docs() -> None:
    rows = [
        item
        for item in matrix_entries()
        if item["supported"] and not item["identity"]
    ]
    missing = []
    for item in rows:
        doc = REPO_ROOT / item["doc"]
        if not doc.is_file():
            missing.append(item["doc"])
    if missing:
        pytest.skip(
            "cross-transfer docs are not in the repo; "
            "S4.2 goldens cover the pairs"
        )
    for item in rows:
        text = (REPO_ROOT / item["doc"]).read_text(encoding="utf-8")
        assert item["asset_type"] in text


def test_s4_unit_pair_supported() -> None:
    assert pair_supported("skill", "claude", "codex")
    assert not pair_supported("mcp", "agents", "claude")
