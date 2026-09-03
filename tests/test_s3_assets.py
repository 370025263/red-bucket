"""S3 资产上传与校验。"""
from __future__ import annotations

from tests.support import (
    ASSET_TYPES,
    SKILL_TEXT,
    STORAGE_LIMIT,
    assert_error,
    assert_field,
    assert_location,
    auth_header,
    b64_file,
    commit_count,
    create_bucket,
    sample_files,
    sample_path,
    signup,
    snapshot_tree,
    text_file,
    upload_asset,
)


def _public_bucket(client, username: str = "alice"):
    token = signup(client, username)
    created = create_bucket(
        client,
        token,
        username,
        "tools",
        visibility="public",
    )
    assert created.status_code == 201
    return token


def test_s3_1_five_types_upload(client) -> None:
    token = _public_bucket(client)
    for asset_type in ASSET_TYPES:
        harness = "claude" if asset_type != "mcp" else "claude"
        resp = upload_asset(
            client,
            token,
            "alice",
            "tools",
            asset_type,
            harness,
            sample_path(asset_type),
            sample_files(asset_type),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert_location(
            resp,
            f"/api/v1/users/alice/buckets/tools/assets/{body['id']}",
        )
        assert body["type"] == asset_type
        assert body["source_harness"] == harness
        assert body["path"] == sample_path(asset_type)
        assert body["size_bytes"] > 0
        assert body["updated_at"]
    listing = client.get("/api/v1/users/alice/buckets/tools/assets")
    items = listing.json()["items"]
    assert len(items) == 5
    for item in items:
        assert item["type"] in ASSET_TYPES
        assert item["source_harness"]
        assert item["path"]
        assert "size_bytes" in item
        assert item["updated_at"]


def test_s3_2_invalid_samples_do_not_write(client) -> None:
    token = _public_bucket(client)
    cases = (
        (
            "skill",
            "claude",
            "skills/bad-name",
            [text_file("SKILL.md", "---\ndescription: d\n---\n")],
        ),
        (
            "skill",
            "claude",
            "skills/bad-fm",
            [text_file("SKILL.md", "not frontmatter")],
        ),
        (
            "mcp",
            "claude",
            "mcp/bad-json",
            [text_file("server.json", "{not-json")],
        ),
        (
            "mcp",
            "claude",
            "mcp/no-transport",
            [text_file("server.json", '{"name": "x"}')],
        ),
        (
            "instructions",
            "agents",
            "notes/bin",
            [b64_file("AGENTS.md", b"\xff\xfe not utf8")],
        ),
        (
            "instructions",
            "agents",
            "notes/huge",
            [text_file("AGENTS.md", "a" * (1048576 + 1))],
        ),
        (
            "subagent",
            "claude",
            "agents/bad",
            [text_file("agent.md", "no frontmatter here")],
        ),
        (
            "plugin",
            "claude",
            "plugins/bad",
            [text_file("plugin.json", '{"ok": true}')],
        ),
    )
    for asset_type, harness, path, files in cases:
        before = snapshot_tree(client, "alice", "tools")
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
        err = assert_error(resp, 422, "validation_failed")
        assert err["details"]
        for item in err["details"]:
            assert item.get("rule")
            assert "path" in item
        assert snapshot_tree(client, "alice", "tools") == before


def test_s3_3_unknown_or_missing_type(client) -> None:
    token = _public_bucket(client)
    missing = client.post(
        "/api/v1/users/alice/buckets/tools/assets",
        json={
            "source_harness": "claude",
            "path": "skills/x",
            "files": sample_files("skill"),
        },
        headers=auth_header(token),
    )
    err = assert_error(missing, 422, "validation_failed")
    assert_field(err, "type")
    unknown = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "widget",
        "claude",
        "skills/x",
        sample_files("skill"),
    )
    assert_error(unknown, 422, "validation_failed")


def test_s3_4_two_versions_two_commits(client) -> None:
    token = _public_bucket(client)
    first = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_TEXT)],
    )
    assert first.status_code == 201
    second_text = SKILL_TEXT.replace("demo thing", "second cut")
    second = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", second_text)],
    )
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    history = client.get("/api/v1/users/alice/buckets/tools/commits")
    assert history.json()["total"] == 2
    items = history.json()["items"]
    assert items[0]["author"]["username"] == "alice"
    assert items[1]["author"]["username"] == "alice"
    assert items[0]["sha"] != items[1]["sha"]


def test_s3_5_storage_quota_keeps_bytes(client) -> None:
    token = _public_bucket(client)
    base = 9 * 1024 * 1024 + 512 * 1024
    first = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/big",
        [
            text_file("SKILL.md", SKILL_TEXT),
            b64_file("blob.bin", b"x" * (base - len(SKILL_TEXT))),
        ],
    )
    assert first.status_code == 201, first.text
    before = snapshot_tree(client, "alice", "tools")
    extra = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/more",
        [
            text_file("SKILL.md", SKILL_TEXT),
            b64_file("more.bin", b"y" * (1024 * 1024)),
        ],
    )
    err = assert_error(extra, 413, "bucket_storage_exceeded")
    detail = err["details"][0]
    assert "usage_bytes" in detail
    assert detail["limit_bytes"] == STORAGE_LIMIT
    assert snapshot_tree(client, "alice", "tools") == before


def test_s3_6_usage_within_one_percent(client) -> None:
    token = _public_bucket(client)
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
    meta = client.get("/api/v1/users/alice/buckets/tools")
    body = meta.json()
    assert body["limit_bytes"] == STORAGE_LIMIT
    tree = snapshot_tree(client, "alice", "tools")
    actual = sum(len(item) for item in tree.values())
    usage = body["usage_bytes"]
    if actual == 0:
        assert usage == 0
        return
    drift = abs(usage - actual) / actual
    assert drift < 0.01


def test_s3_7_raw_matches_bytes(client) -> None:
    token = _public_bucket(client)
    single = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/one",
        [text_file("SKILL.md", SKILL_TEXT)],
    )
    assert single.status_code == 201
    raw = client.get(
        f"/api/v1/users/alice/buckets/tools/assets/{single.json()['id']}/raw"
    )
    assert raw.content == SKILL_TEXT.encode("utf-8")
    extra = b"helper-bytes"
    multi = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/two",
        [
            text_file("SKILL.md", SKILL_TEXT),
            b64_file("notes.txt", extra),
        ],
    )
    assert multi.status_code == 201
    zipped = client.get(
        f"/api/v1/users/alice/buckets/tools/assets/{multi.json()['id']}/raw"
    )
    assert zipped.headers["content-type"].startswith("application/zip")
    from redbucket.fileset import unzip_bytes

    files = unzip_bytes(zipped.content)
    assert files["SKILL.md"] == SKILL_TEXT.encode("utf-8")
    assert files["notes.txt"] == extra


def test_s3_8_delete_asset_keeps_copy_snapshot(client) -> None:
    owner = signup(client, "alice")
    create_bucket(client, owner, "alice", "src", visibility="public")
    create_bucket(client, owner, "alice", "dst", visibility="public")
    uploaded = upload_asset(
        client,
        owner,
        "alice",
        "src",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_TEXT)],
    )
    asset_id = uploaded.json()["id"]
    copied = client.post(
        "/api/v1/users/alice/buckets/dst/copies",
        json={
            "source_username": "alice",
            "source_bucket": "src",
            "source_asset_id": asset_id,
            "dest_path": "skills/demo",
        },
        headers=auth_header(owner),
    )
    assert copied.status_code == 201, copied.text
    dest_id = copied.json()["dest_asset"]["id"]
    before = commit_count(client, "alice", "dst")
    deleted = client.delete(
        f"/api/v1/users/alice/buckets/dst/assets/{dest_id}",
        headers=auth_header(owner),
    )
    assert deleted.status_code == 204
    assert (
        client.get(
            f"/api/v1/users/alice/buckets/dst/assets/{dest_id}"
        ).status_code
        == 404
    )
    listing = client.get("/api/v1/users/alice/buckets/dst/assets")
    assert listing.json()["items"] == []
    assert commit_count(client, "alice", "dst") == before + 1
    copies = client.get("/api/v1/users/alice/buckets/dst/copies")
    assert copies.json()["total"] == 1
    record = copies.json()["items"][0]
    assert record["dest_asset"]["id"] is None
    assert record["dest_asset"]["path"] == "skills/demo"
    assert record["dest_asset"]["type"] == "skill"
