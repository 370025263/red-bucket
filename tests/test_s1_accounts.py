"""S1 账号与权限。"""
from __future__ import annotations

from tests.support import (
    PASSWORD,
    assert_error,
    assert_field,
    assert_location,
    auth_header,
    create_bucket,
    login,
    register,
    signup,
    snapshot_tree,
    text_file,
    upload_asset,
    user_id_of,
)


def test_s1_1_register_success(client) -> None:
    resp = register(client, "alice", "alice@example.com")
    assert resp.status_code == 201
    body = resp.json()
    assert_location(resp, "/api/v1/users/alice")
    assert body["username"] == "alice"
    assert "id" in body
    assert "created_at" in body
    assert "email" not in body
    assert "password" not in body
    assert "password_hash" not in body
    assert "token" not in body


def test_s1_2_username_taken(client) -> None:
    assert register(client, "alice").status_code == 201
    again = register(client, "alice", "alice2@example.com")
    assert_error(again, 409, "username_taken")


def test_s1_2a_email_case_conflict(client) -> None:
    assert register(client, "alice", "alice@example.com").status_code == 201
    again = register(client, "bobby", "Alice@Example.com")
    assert_error(again, 409, "email_taken")


def test_s1_2b_short_password(client) -> None:
    resp = register(client, "alice", password="short")
    err = assert_error(resp, 422, "validation_failed")
    assert_field(err, "password")


def test_s1_3_invalid_usernames(client) -> None:
    cases = (
        "alice!",
        "-alice",
        "ab",
    )
    for username in cases:
        resp = register(client, username, f"{username}@ex.com")
        err = assert_error(resp, 422, "validation_failed")
        assert_field(err, "username")


def test_s1_4_unauth_writes_leave_state(client) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "tools")
    buckets = client.get("/api/v1/users/alice/buckets")
    assert buckets.status_code == 200
    assert buckets.json()["total"] == 1
    unauth_bucket = client.post(
        "/api/v1/users/alice/buckets",
        json={"name": "other", "visibility": "public"},
    )
    assert_error(unauth_bucket, 401, "unauthorized")
    after = client.get("/api/v1/users/alice/buckets")
    assert after.json()["total"] == 1
    unauth_asset = client.post(
        "/api/v1/users/alice/buckets/tools/assets",
        json={
            "type": "skill",
            "source_harness": "claude",
            "path": "skills/demo",
            "files": [text_file("SKILL.md", "x")],
        },
    )
    assert_error(unauth_asset, 401, "unauthorized")
    listing = client.get("/api/v1/users/alice/buckets/tools/assets")
    assert listing.json()["total"] == 0


def test_s1_5_login_token_and_opaque_401(client) -> None:
    signup(client, "alice", "alice@example.com")
    ok = login(client, "alice@example.com")
    assert ok.status_code == 200
    token = ok.json()["token"]
    assert ok.json()["token_type"] == "bearer"
    me = client.get("/api/v1/users/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"
    created = create_bucket(client, token, "alice", "tools")
    assert created.status_code == 201
    bad_pw = login(client, "alice@example.com", "wrongpass")
    missing = login(client, "nobody@example.com", PASSWORD)
    assert_error(bad_pw, 401, "unauthorized")
    assert_error(missing, 401, "unauthorized")
    assert bad_pw.json() == missing.json()


def test_s1_5a_logout_revokes_token(client) -> None:
    token = signup(client, "alice")
    out = client.post(
        "/api/v1/auth/logout",
        json={},
        headers=auth_header(token),
    )
    assert out.status_code == 204
    me = client.get("/api/v1/users/me", headers=auth_header(token))
    assert_error(me, 401, "unauthorized")


def test_s1_5b_rename_keeps_disk(client, data_dir) -> None:
    token = signup(client, "alice")
    created = create_bucket(client, token, "alice", "tools")
    assert created.status_code == 201
    uid = user_id_of(client, "alice")
    repo = data_dir / "git" / str(uid)
    assert repo.is_dir()
    before = list(repo.iterdir())
    taken = signup(client, "bobby")
    conflict = client.patch(
        "/api/v1/users/me",
        json={"username": "bobby"},
        headers=auth_header(token),
    )
    assert_error(conflict, 409, "username_taken")
    del taken
    renamed = client.patch(
        "/api/v1/users/me",
        json={"username": "alice2"},
        headers=auth_header(token),
    )
    assert renamed.status_code == 200
    assert renamed.json()["username"] == "alice2"
    found = client.get(
        "/api/v1/users/alice2/buckets/tools",
        headers=auth_header(token),
    )
    assert found.status_code == 200
    assert list(repo.iterdir()) == before
    assert not (data_dir / "git" / "alice2").exists()


def test_s1_6_anon_reads_public(client) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "tools", visibility="public")
    skill = (
        "---\nname: demo\ndescription: d\n---\nbody\n"
    )
    uploaded = upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", skill)],
    )
    assert uploaded.status_code == 201
    asset_id = uploaded.json()["id"]
    listing = client.get("/api/v1/users/alice/buckets/tools/assets")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    raw = client.get(
        f"/api/v1/users/alice/buckets/tools/assets/{asset_id}/raw"
    )
    assert raw.status_code == 200
    assert raw.content == skill.encode("utf-8")


def test_s1_7_private_is_404(client) -> None:
    owner = signup(client, "alice")
    create_bucket(client, owner, "alice", "secret", visibility="private")
    stranger = signup(client, "bobby")
    anon = client.get("/api/v1/users/alice/buckets/secret")
    other = client.get(
        "/api/v1/users/alice/buckets/secret",
        headers=auth_header(stranger),
    )
    missing = client.get("/api/v1/users/alice/buckets/no-such")
    assert_error(anon, 404, "not_found")
    assert_error(other, 404, "not_found")
    assert_error(missing, 404, "not_found")
    assert anon.json() == other.json() == missing.json()
    mine = client.get(
        "/api/v1/users/alice/buckets/secret",
        headers=auth_header(owner),
    )
    assert mine.status_code == 200


def test_s1_8_list_visibility(client) -> None:
    owner = signup(client, "alice")
    create_bucket(client, owner, "alice", "pub", visibility="public")
    create_bucket(client, owner, "alice", "hid", visibility="private")
    mine = client.get(
        "/api/v1/users/alice/buckets",
        headers=auth_header(owner),
    )
    names = {item["name"] for item in mine.json()["items"]}
    assert names == {"pub", "hid"}
    stranger = signup(client, "bobby")
    seen = client.get(
        "/api/v1/users/alice/buckets",
        headers=auth_header(stranger),
    )
    assert {item["name"] for item in seen.json()["items"]} == {"pub"}
    anon = client.get("/api/v1/users/alice/buckets")
    assert {item["name"] for item in anon.json()["items"]} == {"pub"}


def test_s1_5b_tree_still_readable_after_rename(client) -> None:
    token = signup(client, "alice")
    create_bucket(
        client,
        token,
        "alice",
        "tools",
        visibility="public",
        template="claude",
    )
    before = snapshot_tree(client, "alice", "tools")
    client.patch(
        "/api/v1/users/me",
        json={"username": "carol"},
        headers=auth_header(token),
    )
    after = snapshot_tree(client, "carol", "tools")
    assert after == before

def test_s1_device_flow_end_to_end(client) -> None:
    token = signup(client, "alice")
    started = client.post(
        "/api/v1/auth/device",
        json={"client": "claude"},
    )
    assert started.status_code == 201
    body = started.json()
    device_code = body["device_code"]
    user_code = body["user_code"]
    assert body["expires_in"] == 600
    assert body["interval"] == 5
    assert user_code in body["verification_url_complete"]
    assert device_code not in body["verification_url_complete"]

    waiting = client.post(
        "/api/v1/auth/device/token",
        json={"device_code": device_code},
    )
    assert waiting.json() == {"status": "pending"}

    anon = client.post(
        f"/api/v1/auth/device/{user_code}/decision",
        json={"approve": True},
    )
    assert anon.status_code == 401

    said_yes = client.post(
        f"/api/v1/auth/device/{user_code}/decision",
        json={"approve": True},
        headers=auth_header(token),
    )
    assert said_yes.status_code == 200

    collected = client.post(
        "/api/v1/auth/device/token",
        json={"device_code": device_code},
    )
    assert collected.status_code == 200
    granted = collected.json()
    assert granted["status"] == "approved"
    assert granted["user"]["username"] == "alice"

    whoami = client.get(
        "/api/v1/users/me",
        headers=auth_header(granted["token"]),
    )
    assert whoami.status_code == 200
    assert whoami.json()["username"] == "alice"

    replay = client.post(
        "/api/v1/auth/device/token",
        json={"device_code": device_code},
    )
    assert replay.status_code == 404


def test_s1_device_denied_and_unknown(client) -> None:
    token = signup(client, "alice")
    body = client.post("/api/v1/auth/device", json={}).json()
    refused = client.post(
        f"/api/v1/auth/device/{body['user_code']}/decision",
        json={"approve": False},
        headers=auth_header(token),
    )
    assert refused.status_code == 200
    polled = client.post(
        "/api/v1/auth/device/token",
        json={"device_code": body["device_code"]},
    )
    assert polled.json() == {"status": "denied"}
    unknown = client.post(
        "/api/v1/auth/device/token",
        json={"device_code": "not-a-real-code"},
    )
    assert unknown.status_code == 404


def test_s1_link_pages(client) -> None:
    body = client.post("/api/v1/auth/device", json={}).json()
    entry = client.get("/link")
    assert entry.status_code == 200
    assert 'name="code"' in entry.text
    decide = client.get(f"/link/{body['user_code']}")
    assert decide.status_code == 200
    assert body["user_code"] in decide.text
    assert body["device_code"] not in decide.text
    missing = client.get("/link/ZZZZ-ZZZZ")
    assert missing.status_code == 404
