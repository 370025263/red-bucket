"""S2 Bucket 生命周期。"""
from __future__ import annotations

from tests.support import (
    assert_error,
    assert_field,
    assert_location,
    auth_header,
    commit_count,
    create_bucket,
    set_bucket_quota,
    signup,
    snapshot_tree,
    user_id_of,
)


def test_s2_1_create_lists_metadata(client) -> None:
    token = signup(client, "alice")
    resp = create_bucket(
        client,
        token,
        "alice",
        "tools",
        visibility="public",
        description="",
    )
    assert resp.status_code == 201
    assert_location(resp, "/api/v1/users/alice/buckets/tools")
    body = resp.json()
    assert body["name"] == "tools"
    assert body["description"] == ""
    assert body["visibility"] == "public"
    assert body["usage_bytes"] == 0
    assert body["limit_bytes"] == 10485760
    assert body["harness_mix"] == {}
    listing = client.get(
        "/api/v1/users/alice/buckets",
        headers=auth_header(token),
    )
    names = [item["name"] for item in listing.json()["items"]]
    assert "tools" in names


def test_s2_1a_description_limit(client) -> None:
    token = signup(client, "alice")
    ok_text = "x" * 350
    created = create_bucket(
        client,
        token,
        "alice",
        "tools",
        visibility="public",
        description=ok_text,
    )
    assert created.status_code == 201
    assert created.json()["description"] == ok_text
    patched = client.patch(
        "/api/v1/users/alice/buckets/tools",
        json={"description": "about this bucket"},
        headers=auth_header(token),
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "about this bucket"
    page = client.get("/alice/tools")
    assert page.status_code == 200
    assert "about this bucket" in page.text
    too_long = client.patch(
        "/api/v1/users/alice/buckets/tools",
        json={"description": "y" * 351},
        headers=auth_header(token),
    )
    err = assert_error(too_long, 422, "validation_failed")
    assert_field(err, "description")


def test_s2_2_duplicate_name(client) -> None:
    token = signup(client, "alice")
    first = create_bucket(client, token, "alice", "tools")
    assert first.status_code == 201
    again = create_bucket(client, token, "alice", "tools")
    assert_error(again, 409, "bucket_name_taken")


def test_s2_3_illegal_names(client) -> None:
    token = signup(client, "alice")
    for name in ("has/slash", "has space", "Upper"):
        resp = create_bucket(client, token, "alice", name)
        err = assert_error(resp, 422, "validation_failed")
        assert_field(err, "name")


def test_s2_4_sixth_bucket_quota(client) -> None:
    token = signup(client, "alice")
    for index in range(5):
        resp = create_bucket(client, token, "alice", f"bkt-{index}")
        assert resp.status_code == 201, resp.text
    sixth = create_bucket(client, token, "alice", "bkt-5")
    err = assert_error(sixth, 403, "bucket_quota_exceeded")
    detail = err["details"][0]
    assert detail["limit"] == 5
    assert detail["current"] == 5
    deleted = client.delete(
        "/api/v1/users/alice/buckets/bkt-0",
        headers=auth_header(token),
    )
    assert deleted.status_code == 204
    again = create_bucket(client, token, "alice", "bkt-5")
    assert again.status_code == 201


def test_s2_5_quota_field_in_sqlite(client) -> None:
    token = signup(client, "alice")
    for index in range(5):
        assert create_bucket(
            client,
            token,
            "alice",
            f"bkt-{index}",
        ).status_code == 201
    blocked = create_bucket(client, token, "alice", "bkt-5")
    assert_error(blocked, 403, "bucket_quota_exceeded")
    set_bucket_quota(client, user_id_of(client, "alice"), 6)
    sixth = create_bucket(client, token, "alice", "bkt-5")
    assert sixth.status_code == 201, sixth.text


def test_s2_6_public_to_private(client) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "tools", visibility="public")
    assert client.get("/api/v1/users/alice/buckets/tools").status_code == 200
    patched = client.patch(
        "/api/v1/users/alice/buckets/tools",
        json={"visibility": "private"},
        headers=auth_header(token),
    )
    assert patched.status_code == 200
    assert_error(
        client.get("/api/v1/users/alice/buckets/tools"),
        404,
        "not_found",
    )
    mine = client.get(
        "/api/v1/users/alice/buckets/tools",
        headers=auth_header(token),
    )
    assert mine.status_code == 200


def test_s2_7_templates_match_catalog(client) -> None:
    catalog = client.get("/api/v1/templates", params={"per_page": 100})
    assert catalog.status_code == 200
    names = [item["name"] for item in catalog.json()["items"]]
    assert names == ["codex", "agents", "claude", "openclaw"]
    for item in catalog.json()["items"]:
        assert "files" in item
        assert item["files"]
    token = signup(client, "alice")
    for name in names:
        detail = client.get(f"/api/v1/templates/{name}")
        assert detail.status_code == 200
        created = create_bucket(
            client,
            token,
            "alice",
            name,
            visibility="public",
            template=name,
        )
        assert created.status_code == 201
        assert commit_count(client, "alice", name) == 1
        tree = snapshot_tree(client, "alice", name)
        expected = {
            entry["path"]: entry["content_text"].encode("utf-8")
            for entry in detail.json()["files"]
        }
        assert tree == expected


def test_s2_7a_no_template_empty_tree(client) -> None:
    token = signup(client, "alice")
    created = create_bucket(client, token, "alice", "empty")
    assert created.status_code == 201
    assert created.json()["template"] is None
    tree = client.get("/api/v1/users/alice/buckets/empty/tree")
    assert tree.status_code == 200
    body = tree.json()
    assert body["items"] == []
    assert body["commit_count"] == 0
    assert body["latest_commit"] is None


def test_s2_8_delete_then_recreate(client) -> None:
    token = signup(client, "alice")
    created = create_bucket(
        client,
        token,
        "alice",
        "tools",
        visibility="public",
        template="claude",
    )
    old_id = created.json()["id"]
    deleted = client.delete(
        "/api/v1/users/alice/buckets/tools",
        headers=auth_header(token),
    )
    assert deleted.status_code == 204
    paths = (
        "/api/v1/users/alice/buckets/tools",
        "/api/v1/users/alice/buckets/tools/assets",
        "/api/v1/users/alice/buckets/tools/issues",
        "/api/v1/users/alice/buckets/tools/copies",
        "/api/v1/users/alice/buckets/tools/tree",
        "/api/v1/users/alice/buckets/tools/pulls",
        "/api/v1/users/alice/buckets/tools/commits",
    )
    for path in paths:
        assert_error(client.get(path), 404, "not_found")
    again = create_bucket(
        client,
        token,
        "alice",
        "tools",
        visibility="public",
    )
    assert again.status_code == 201
    assert again.json()["id"] != old_id
