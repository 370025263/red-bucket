"""S11 元数据 schema。"""
from __future__ import annotations

EXPECTED_TABLES = {
    "schema_migrations": ("version", "applied_at"),
    "users": (
        "id",
        "username",
        "username_normalized",
        "email",
        "email_normalized",
        "password_hash",
        "bucket_quota",
        "created_at",
        "updated_at",
    ),
    "tokens": (
        "id",
        "user_id",
        "token_hash",
        "created_at",
        "last_used_at",
        "revoked_at",
    ),
    "buckets": (
        "id",
        "user_id",
        "name",
        "name_normalized",
        "visibility",
        "description",
        "template",
        "storage_usage_bytes",
        "storage_limit_bytes",
        "created_at",
        "updated_at",
        "deleted_at",
    ),
    "assets": (
        "id",
        "bucket_id",
        "type",
        "source_harness",
        "path",
        "size_bytes",
        "uploader_id",
        "source_copy_id",
        "head_commit_sha",
        "created_at",
        "updated_at",
    ),
    "copies": (
        "id",
        "dest_bucket_id",
        "dest_asset_id",
        "dest_path",
        "dest_type",
        "source_bucket_id",
        "source_full_name",
        "source_path",
        "source_commit_sha",
        "dest_commit_sha",
        "actor_id",
        "created_at",
    ),
    "issues": (
        "id",
        "bucket_id",
        "number",
        "author_id",
        "title",
        "body",
        "state",
        "closed_by_id",
        "created_at",
        "updated_at",
        "closed_at",
    ),
    "issue_comments": (
        "id",
        "issue_id",
        "author_id",
        "body",
        "created_at",
        "updated_at",
    ),
    "pull_requests": (
        "id",
        "bucket_id",
        "number",
        "author_id",
        "title",
        "body",
        "state",
        "proposed_files_json",
        "merged_commit_sha",
        "created_at",
        "updated_at",
        "closed_at",
    ),
    "device_codes": (
        "id",
        "device_code_hash",
        "user_code",
        "client",
        "state",
        "user_id",
        "created_at",
        "expires_at",
    ),
}

JSON_TO_SOURCE = {
    "User": {
        "id": "users.id",
        "username": "users.username",
        "created_at": "users.created_at",
        "email": "users.email",
        "bucket_quota": "users.bucket_quota",
        "bucket_count": "computed",
    },
    "Bucket": {
        "id": "buckets.id",
        "full_name": "computed",
        "username": "users.username",
        "name": "buckets.name",
        "visibility": "buckets.visibility",
        "description": "buckets.description",
        "template": "buckets.template",
        "usage_bytes": "buckets.storage_usage_bytes",
        "limit_bytes": "buckets.storage_limit_bytes",
        "open_issues_count": "computed",
        "open_pulls_count": "computed",
        "harness_mix": "computed",
        "created_at": "buckets.created_at",
        "updated_at": "buckets.updated_at",
    },
    "Asset": {
        "id": "assets.id",
        "bucket_id": "assets.bucket_id",
        "full_name": "computed",
        "type": "assets.type",
        "source_harness": "assets.source_harness",
        "path": "assets.path",
        "size_bytes": "assets.size_bytes",
        "uploader": "computed",
        "head_commit_sha": "assets.head_commit_sha",
        "provenance": "computed",
        "created_at": "assets.created_at",
        "updated_at": "assets.updated_at",
    },
    "Issue": {
        "id": "issues.id",
        "number": "issues.number",
        "bucket_full_name": "computed",
        "title": "issues.title",
        "body": "issues.body",
        "state": "issues.state",
        "author": "computed",
        "closed_by": "computed",
        "created_at": "issues.created_at",
        "updated_at": "issues.updated_at",
        "closed_at": "issues.closed_at",
    },
    "IssueComment": {
        "id": "issue_comments.id",
        "issue_number": "computed",
        "bucket_full_name": "computed",
        "body": "issue_comments.body",
        "author": "computed",
        "created_at": "issue_comments.created_at",
        "updated_at": "issue_comments.updated_at",
    },
    "PullRequest": {
        "id": "pull_requests.id",
        "number": "pull_requests.number",
        "bucket_full_name": "computed",
        "title": "pull_requests.title",
        "body": "pull_requests.body",
        "state": "pull_requests.state",
        "author": "computed",
        "files": "pull_requests.proposed_files_json",
        "merged_commit_sha": "pull_requests.merged_commit_sha",
        "created_at": "pull_requests.created_at",
        "updated_at": "pull_requests.updated_at",
        "closed_at": "pull_requests.closed_at",
    },
    "InstallRecord": {
        "id": "copies.id",
        "dest_full_name": "computed",
        "dest_asset": "computed",
        "source_full_name": "copies.source_full_name",
        "source_bucket_id": "copies.source_bucket_id",
        "source_path": "copies.source_path",
        "source_commit_sha": "copies.source_commit_sha",
        "dest_commit_sha": "copies.dest_commit_sha",
        "actor": "computed",
        "created_at": "copies.created_at",
    },
}


def _tables(client) -> set[str]:
    rows = client.app.state.core.store.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'"
    )
    return {row["name"] for row in rows}


def _columns(client, table: str) -> list[str]:
    rows = client.app.state.core.store.fetchall(
        f"PRAGMA table_info({table})"
    )
    return [row["name"] for row in rows]


def test_s11_1_expected_tables(client) -> None:
    names = _tables(client)
    assert names == set(EXPECTED_TABLES)
    for table, columns in EXPECTED_TABLES.items():
        assert tuple(_columns(client, table)) == columns


def test_s11_2_live_bucket_predicate(client) -> None:
    from tests.support import (
        SKILL_TEXT,
        assert_error,
        auth_header,
        create_bucket,
        signup,
        text_file,
        upload_asset,
    )

    token = signup(client, "alice")
    created = create_bucket(
        client,
        token,
        "alice",
        "tools",
        visibility="public",
    )
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
    opened = client.post(
        "/api/v1/users/alice/buckets/tools/issues",
        json={"title": "x", "body": ""},
        headers=auth_header(token),
    )
    asset_id = uploaded.json()["id"]
    issue_no = opened.json()["number"]
    me = client.get("/api/v1/users/me", headers=auth_header(token))
    assert me.json()["bucket_count"] == 1
    client.delete(
        "/api/v1/users/alice/buckets/tools",
        headers=auth_header(token),
    )
    assert_error(
        client.get("/api/v1/users/alice/buckets/tools"),
        404,
        "not_found",
    )
    assert_error(
        client.get(
            f"/api/v1/users/alice/buckets/tools/assets/{asset_id}"
        ),
        404,
        "not_found",
    )
    assert_error(
        client.get(
            f"/api/v1/users/alice/buckets/tools/issues/{issue_no}"
        ),
        404,
        "not_found",
    )
    me = client.get("/api/v1/users/me", headers=auth_header(token))
    assert me.json()["bucket_count"] == 0
    for index in range(5):
        resp = create_bucket(client, token, "alice", f"bkt-{index}")
        assert resp.status_code == 201
    extra = create_bucket(client, token, "alice", "tools")
    assert_error(extra, 403, "bucket_quota_exceeded")
    assert created.status_code == 201


def test_s11_3_json_keys_mapped() -> None:
    for _name, mapping in JSON_TO_SOURCE.items():
        for key, source in mapping.items():
            assert key
            assert source == "computed" or "." in source


def test_s11_4_wal_and_foreign_keys(client) -> None:
    store = client.app.state.core.store
    mode = store.fetchone("PRAGMA journal_mode")
    assert mode[0].upper() == "WAL"
    keys = store.fetchone("PRAGMA foreign_keys")
    assert int(keys[0]) == 1
