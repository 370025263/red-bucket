"""S10 API 契约一致性。"""
from __future__ import annotations

from fastapi.routing import APIRoute

from redbucket.main import create_app
from tests.support import (
    SKILL_TEXT,
    assert_error,
    assert_field,
    assert_location,
    auth_header,
    create_bucket,
    page_keys,
    signup,
    text_file,
    upload_asset,
)

STABLE_CODES = {
    "unauthorized",
    "not_found",
    "forbidden",
    "bucket_quota_exceeded",
    "conflict",
    "username_taken",
    "email_taken",
    "bucket_name_taken",
    "bucket_storage_exceeded",
    "validation_failed",
    "translation_unsupported",
    "internal_error",
}

CATALOG_PATHS = {
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/auth/device"),
    ("POST", "/api/v1/auth/device/token"),
    ("GET", "/api/v1/auth/device/{user_code}"),
    ("POST", "/api/v1/auth/device/{user_code}/decision"),
    ("GET", "/api/v1/users/me"),
    ("PATCH", "/api/v1/users/me"),
    ("GET", "/api/v1/users/{username}"),
    ("GET", "/api/v1/users/{username}/buckets"),
    ("POST", "/api/v1/users/{username}/buckets"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}"),
    ("PATCH", "/api/v1/users/{username}/buckets/{bucket}"),
    ("DELETE", "/api/v1/users/{username}/buckets/{bucket}"),
    ("GET", "/api/v1/templates"),
    ("GET", "/api/v1/templates/{name}"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/assets"),
    ("POST", "/api/v1/users/{username}/buckets/{bucket}/assets"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/assets/{asset_id}"),
    ("DELETE", "/api/v1/users/{username}/buckets/{bucket}/assets/{asset_id}"),
    (
        "GET",
        "/api/v1/users/{username}/buckets/{bucket}/assets/{asset_id}/raw",
    ),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/tree"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/tree/{path}"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/blob/{path}"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/commits"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/commits/{sha}"),
    ("GET", "/api/v1/translation-matrix"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/translated"),
    (
        "GET",
        "/api/v1/users/{username}/buckets/{bucket}/assets/{asset_id}/translated",
    ),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/install-script"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/copies"),
    ("POST", "/api/v1/users/{username}/buckets/{bucket}/copies"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/copies/{copy_id}"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/issues"),
    ("POST", "/api/v1/users/{username}/buckets/{bucket}/issues"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/issues/{number}"),
    ("PATCH", "/api/v1/users/{username}/buckets/{bucket}/issues/{number}"),
    (
        "GET",
        "/api/v1/users/{username}/buckets/{bucket}/issues/{number}/comments",
    ),
    (
        "POST",
        "/api/v1/users/{username}/buckets/{bucket}/issues/{number}/comments",
    ),
    (
        "GET",
        "/api/v1/users/{username}/buckets/{bucket}/issues/{number}/comments/{comment_id}",
    ),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/pulls"),
    ("POST", "/api/v1/users/{username}/buckets/{bucket}/pulls"),
    ("GET", "/api/v1/users/{username}/buckets/{bucket}/pulls/{number}"),
    (
        "GET",
        "/api/v1/users/{username}/buckets/{bucket}/pulls/{number}/files",
    ),
    (
        "POST",
        "/api/v1/users/{username}/buckets/{bucket}/pulls/{number}/merge",
    ),
    (
        "POST",
        "/api/v1/users/{username}/buckets/{bucket}/pulls/{number}/reject",
    ),
}


def _norm_path(path: str) -> str:
    return path.replace("{path:path}", "{path}")


def _api_pairs(app) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    stack = list(app.routes)
    while stack:
        route = stack.pop()
        nested = getattr(route, "original_router", None)
        if nested is not None:
            stack.extend(nested.routes)
            continue
        if not isinstance(route, APIRoute):
            continue
        path = _norm_path(route.path)
        if not path.startswith("/api/v1"):
            continue
        for method in route.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            found.add((method, path))
    return found


def test_s10_1_lifecycle(client) -> None:
    created = client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert created.status_code == 201
    assert_location(created, "/api/v1/users/alice")
    session = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "secret123"},
    )
    assert session.status_code == 200
    token = session.json()["token"]
    bucket = create_bucket(
        client,
        token,
        "alice",
        "tools",
        visibility="public",
        template="claude",
    )
    assert bucket.status_code == 201
    assert_location(bucket, "/api/v1/users/alice/buckets/tools")
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
    assert uploaded.status_code == 201
    patched = client.patch(
        "/api/v1/users/alice/buckets/tools",
        json={"visibility": "private"},
        headers=auth_header(token),
    )
    assert patched.status_code == 200
    translated = client.get(
        "/api/v1/users/alice/buckets/tools/translated",
        params={"target": "codex"},
        headers=auth_header(token),
    )
    assert translated.status_code == 200
    client.post(
        "/api/v1/auth/logout",
        json={},
        headers=auth_header(token),
    )
    failed = client.patch(
        "/api/v1/users/alice/buckets/tools",
        json={"description": "x"},
        headers=auth_header(token),
    )
    assert_error(failed, 401, "unauthorized")
    again = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "secret123"},
    )
    fresh = again.json()["token"]
    deleted = client.delete(
        "/api/v1/users/alice/buckets/tools",
        headers=auth_header(fresh),
    )
    assert deleted.status_code == 204


def test_s10_2_error_envelope(client) -> None:
    cases = []
    cases.append(
        (
            client.get("/api/v1/users/me"),
            401,
            "unauthorized",
        )
    )
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "tools", visibility="public")
    author = signup(client, "bobby")
    opened = client.post(
        "/api/v1/users/alice/buckets/tools/issues",
        json={"title": "x", "body": ""},
        headers=auth_header(author),
    )
    third = signup(client, "carol")
    cases.append(
        (
            client.patch(
                f"/api/v1/users/alice/buckets/tools/issues/{opened.json()['number']}",
                json={"state": "closed"},
                headers=auth_header(third),
            ),
            403,
            "forbidden",
        )
    )
    for index in range(4):
        create_bucket(client, token, "alice", f"bkt-{index}")
    cases.append(
        (
            create_bucket(client, token, "alice", "overflow"),
            403,
            "bucket_quota_exceeded",
        )
    )
    cases.append(
        (
            client.get("/api/v1/users/nope"),
            404,
            "not_found",
        )
    )
    cases.append(
        (
            client.post(
                "/api/v1/auth/register",
                json={
                    "username": "alice",
                    "email": "other@example.com",
                    "password": "secret123",
                },
            ),
            409,
            "username_taken",
        )
    )
    cases.append(
        (
            upload_asset(
                client,
                token,
                "alice",
                "tools",
                "skill",
                "claude",
                "skills/huge",
                [
                    text_file("SKILL.md", SKILL_TEXT),
                    {
                        "path": "blob.bin",
                        "content_text": "z" * (11 * 1024 * 1024),
                    },
                ],
            ),
            413,
            "bucket_storage_exceeded",
        )
    )
    cases.append(
        (
            client.post(
                "/api/v1/auth/register",
                json={
                    "username": "ab",
                    "email": "ab@example.com",
                    "password": "secret123",
                },
            ),
            422,
            "validation_failed",
        )
    )
    mcp = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "mcp",
        "agents",
        "mcp/x",
        [text_file(".mcp.json", '{"name":"x","command":"c"}')],
    )
    cases.append(
        (
            client.get(
                f"/api/v1/users/alice/buckets/tools/assets/{mcp.json()['id']}/translated",
                params={"target": "claude"},
            ),
            501,
            "translation_unsupported",
        )
    )
    seen = set()
    for resp, status, code in cases:
        err = assert_error(resp, status, code)
        assert set(err) == {"code", "message", "details"}
        assert err["code"] in STABLE_CODES
        seen.add(err["code"])
    assert "unauthorized" in seen
    assert "forbidden" in seen
    assert "not_found" in seen
    assert "validation_failed" in seen
    assert "translation_unsupported" in seen


def test_s10_3_pagination(client) -> None:
    listing = client.get(
        "/api/v1/templates",
        params={"page": 1, "per_page": 2},
    )
    assert listing.status_code == 200
    page_keys(listing.json())
    assert listing.json()["page"] == 1
    assert listing.json()["per_page"] == 2
    assert listing.json()["has_more"] is True
    assert listing.json()["next_cursor"] == "2"
    cursor = client.get("/api/v1/templates", params={"cursor": "abc"})
    err = assert_error(cursor, 422, "validation_failed")
    assert_field(err, "cursor")
    big = client.get("/api/v1/templates", params={"per_page": 101})
    err = assert_error(big, 422, "validation_failed")
    assert_field(err, "per_page")


def test_s10_canonical_public_origin(client) -> None:
    from redbucket.settings import CANONICAL_PUBLIC_ORIGIN, Settings

    assert CANONICAL_PUBLIC_ORIGIN == "https://redbucket.store"
    assert Settings().public_origin == "https://redbucket.store"
    token = signup(client, "alice")
    created = create_bucket(client, token, "alice", "tools")
    assert created.status_code == 201
    body = client.get(
        "/api/v1/users/alice/buckets/tools/install-script",
        params={"target": "claude"},
    )
    assert body.status_code == 200
    script = body.json()["script"]
    assert (
        "process.env.RED_BUCKET_URL || 'https://redbucket.store'"
        in script
    )


def test_s10_4_endpoint_count() -> None:
    app = create_app()
    found = _api_pairs(app)
    extra = found - CATALOG_PATHS
    missing = CATALOG_PATHS - found
    assert extra == set()
    assert missing == set()
    assert len(found) == 47
    install = [
        item
        for item in found
        if item[0] == "POST" and item[1].endswith("/install")
    ]
    assert install == []
