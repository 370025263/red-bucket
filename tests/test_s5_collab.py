"""S5 协作。"""
from __future__ import annotations

from tests.support import (
    SKILL_TEXT,
    assert_error,
    assert_location,
    auth_header,
    commit_count,
    create_bucket,
    set_storage_limit,
    signup,
    snapshot_tree,
    text_file,
    upload_asset,
)


def _users(client):
    owner = signup(client, "alice")
    author = signup(client, "bobby")
    third = signup(client, "carol")
    created = create_bucket(
        client,
        owner,
        "alice",
        "tools",
        visibility="public",
    )
    assert created.status_code == 201
    return owner, author, third


def test_s5_1_non_owner_issue(client) -> None:
    owner, author, _third = _users(client)
    del owner
    first = client.post(
        "/api/v1/users/alice/buckets/tools/issues",
        json={"title": "broken skill", "body": "markdown"},
        headers=auth_header(author),
    )
    assert first.status_code == 201
    assert first.json()["number"] == 1
    assert_location(
        first,
        "/api/v1/users/alice/buckets/tools/issues/1",
    )
    second = client.post(
        "/api/v1/users/alice/buckets/tools/issues",
        json={"title": "second", "body": ""},
        headers=auth_header(author),
    )
    assert second.json()["number"] == 2
    listed = client.get("/api/v1/users/alice/buckets/tools/issues")
    assert listed.status_code == 200
    assert listed.json()["total"] == 2


def test_s5_2_private_issue_rules(client) -> None:
    owner = signup(client, "alice")
    create_bucket(client, owner, "alice", "hid", visibility="private")
    stranger = signup(client, "bobby")
    denied = client.post(
        "/api/v1/users/alice/buckets/hid/issues",
        json={"title": "nope", "body": ""},
        headers=auth_header(stranger),
    )
    assert_error(denied, 404, "not_found")
    mine = client.post(
        "/api/v1/users/alice/buckets/hid/issues",
        json={"title": "owner note", "body": ""},
        headers=auth_header(owner),
    )
    assert mine.status_code == 201


def test_s5_3_close_and_comment_roles(client) -> None:
    owner, author, third = _users(client)
    opened = client.post(
        "/api/v1/users/alice/buckets/tools/issues",
        json={"title": "bug", "body": "x"},
        headers=auth_header(author),
    )
    number = opened.json()["number"]
    forbidden = client.patch(
        f"/api/v1/users/alice/buckets/tools/issues/{number}",
        json={"state": "closed"},
        headers=auth_header(third),
    )
    assert_error(forbidden, 403, "forbidden")
    still = client.get(
        f"/api/v1/users/alice/buckets/tools/issues/{number}"
    )
    assert still.json()["state"] == "open"
    closed = client.patch(
        f"/api/v1/users/alice/buckets/tools/issues/{number}",
        json={"state": "closed"},
        headers=auth_header(author),
    )
    assert closed.status_code == 200
    assert closed.json()["state"] == "closed"
    other = client.post(
        "/api/v1/users/alice/buckets/tools/issues",
        json={"title": "owner closes", "body": ""},
        headers=auth_header(author),
    )
    by_owner = client.patch(
        f"/api/v1/users/alice/buckets/tools/issues/{other.json()['number']}",
        json={"state": "closed"},
        headers=auth_header(owner),
    )
    assert by_owner.json()["state"] == "closed"
    comment = client.post(
        f"/api/v1/users/alice/buckets/tools/issues/{number}/comments",
        json={"body": "thanks"},
        headers=auth_header(author),
    )
    assert comment.status_code == 201
    assert_location(
        comment,
        "/api/v1/users/alice/buckets/tools/issues/"
        f"{number}/comments/{comment.json()['id']}",
    )
    listed = client.get(
        f"/api/v1/users/alice/buckets/tools/issues/{number}/comments"
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    denied = client.post(
        f"/api/v1/users/alice/buckets/tools/issues/{number}/comments",
        json={"body": "me too"},
        headers=auth_header(third),
    )
    assert_error(denied, 403, "forbidden")
    after = client.get(
        f"/api/v1/users/alice/buckets/tools/issues/{number}/comments"
    )
    assert after.json()["total"] == 1


def test_s5_4_pr_merge_path_replace(client) -> None:
    owner, author, _third = _users(client)
    upload_asset(
        client,
        owner,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_TEXT), text_file("keep.txt", "stay")],
    )
    new_skill = SKILL_TEXT.replace("demo thing", "merged")
    opened = client.post(
        "/api/v1/users/alice/buckets/tools/pulls",
        json={
            "title": "fix skill",
            "body": "please",
            "files": [
                {"path": "skills/demo/SKILL.md", "content_text": new_skill}
            ],
        },
        headers=auth_header(author),
    )
    assert opened.status_code == 201
    assert opened.json()["number"] == 1
    assert_location(
        opened,
        "/api/v1/users/alice/buckets/tools/pulls/1",
    )
    merged = client.post(
        "/api/v1/users/alice/buckets/tools/pulls/1/merge",
        json={},
        headers=auth_header(owner),
    )
    assert merged.status_code == 200, merged.text
    assert merged.json()["state"] == "merged"
    tree = snapshot_tree(client, "alice", "tools")
    assert tree["skills/demo/SKILL.md"] == new_skill.encode("utf-8")
    assert tree["skills/demo/keep.txt"] == b"stay"
    history = client.get("/api/v1/users/alice/buckets/tools/commits")
    head = history.json()["items"][0]
    assert head["author"]["username"] == "bobby"
    assert head["sha"] == merged.json()["merged_commit_sha"]


def test_s5_5_merge_keeps_open_on_fail(client) -> None:
    owner, author, _third = _users(client)
    upload_asset(
        client,
        owner,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_TEXT)],
    )
    before = snapshot_tree(client, "alice", "tools")
    bad = client.post(
        "/api/v1/users/alice/buckets/tools/pulls",
        json={
            "title": "break it",
            "body": "",
            "files": [
                {
                    "path": "skills/demo/SKILL.md",
                    "content_text": "not valid",
                }
            ],
        },
        headers=auth_header(author),
    )
    assert bad.status_code == 201
    failed = client.post(
        "/api/v1/users/alice/buckets/tools/pulls/1/merge",
        json={},
        headers=auth_header(owner),
    )
    assert_error(failed, 422, "validation_failed")
    still = client.get("/api/v1/users/alice/buckets/tools/pulls/1")
    assert still.json()["state"] == "open"
    assert snapshot_tree(client, "alice", "tools") == before
    huge = client.post(
        "/api/v1/users/alice/buckets/tools/pulls",
        json={
            "title": "too big",
            "body": "",
            "files": [
                {
                    "path": "skills/demo/blob.bin",
                    "content_text": "z" * 2000,
                }
            ],
        },
        headers=auth_header(author),
    )
    assert huge.status_code == 201
    meta = client.get("/api/v1/users/alice/buckets/tools")
    set_storage_limit(client, meta.json()["id"], 100)
    quota = client.post(
        "/api/v1/users/alice/buckets/tools/pulls/2/merge",
        json={},
        headers=auth_header(owner),
    )
    assert_error(quota, 413, "bucket_storage_exceeded")
    left = client.get("/api/v1/users/alice/buckets/tools/pulls/2")
    assert left.json()["state"] == "open"
    assert snapshot_tree(client, "alice", "tools") == before


def test_s5_6_reject_leaves_tree(client) -> None:
    owner, author, _third = _users(client)
    upload_asset(
        client,
        owner,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_TEXT)],
    )
    before = snapshot_tree(client, "alice", "tools")
    client.post(
        "/api/v1/users/alice/buckets/tools/pulls",
        json={
            "title": "nope",
            "body": "",
            "files": [
                {"path": "skills/demo/SKILL.md", "content_text": SKILL_TEXT}
            ],
        },
        headers=auth_header(author),
    )
    rejected = client.post(
        "/api/v1/users/alice/buckets/tools/pulls/1/reject",
        json={},
        headers=auth_header(owner),
    )
    assert rejected.status_code == 200
    assert rejected.json()["state"] == "rejected"
    assert snapshot_tree(client, "alice", "tools") == before


def test_s5_7_copy_writes_provenance(client) -> None:
    owner, author, _third = _users(client)
    uploaded = upload_asset(
        client,
        owner,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_TEXT)],
    )
    create_bucket(client, author, "bobby", "lab", visibility="public")
    before = commit_count(client, "bobby", "lab")
    copied = client.post(
        "/api/v1/users/bobby/buckets/lab/copies",
        json={
            "source_username": "alice",
            "source_bucket": "tools",
            "source_asset_id": uploaded.json()["id"],
            "dest_path": "skills/demo",
        },
        headers=auth_header(author),
    )
    assert copied.status_code == 201, copied.text
    body = copied.json()
    assert_location(
        copied,
        f"/api/v1/users/bobby/buckets/lab/copies/{body['id']}",
    )
    assert body["source_full_name"] == "alice/tools"
    assert body["source_commit_sha"] == uploaded.json()["head_commit_sha"]
    assert body["dest_asset"]["path"] == "skills/demo"
    assert body["dest_asset"]["type"] == "skill"
    dest = client.get(
        f"/api/v1/users/bobby/buckets/lab/assets/{body['dest_asset']['id']}"
    )
    assert dest.status_code == 200
    assert dest.json()["provenance"]["source_full_name"] == "alice/tools"
    assert commit_count(client, "bobby", "lab") == before + 1


def test_s5_8_copy_quota_and_private_source(client) -> None:
    owner = signup(client, "alice")
    create_bucket(client, owner, "alice", "hid", visibility="private")
    uploaded = upload_asset(
        client,
        owner,
        "alice",
        "hid",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_TEXT)],
    )
    stranger = signup(client, "bobby")
    create_bucket(client, stranger, "bobby", "lab", visibility="public")
    hidden = client.post(
        "/api/v1/users/bobby/buckets/lab/copies",
        json={
            "source_username": "alice",
            "source_bucket": "hid",
            "source_asset_id": uploaded.json()["id"],
        },
        headers=auth_header(stranger),
    )
    assert_error(hidden, 404, "not_found")
    create_bucket(client, owner, "alice", "pub", visibility="public")
    public = upload_asset(
        client,
        owner,
        "alice",
        "pub",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", SKILL_TEXT)],
    )
    dest = client.get("/api/v1/users/bobby/buckets/lab")
    set_storage_limit(client, dest.json()["id"], 10)
    before = snapshot_tree(client, "bobby", "lab")
    over = client.post(
        "/api/v1/users/bobby/buckets/lab/copies",
        json={
            "source_username": "alice",
            "source_bucket": "pub",
            "source_asset_id": public.json()["id"],
        },
        headers=auth_header(stranger),
    )
    assert_error(over, 413, "bucket_storage_exceeded")
    assert snapshot_tree(client, "bobby", "lab") == before


def test_s5_9_no_install_post(client) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "tools", visibility="public")
    resp = client.post("/api/v1/users/alice/buckets/tools/install")
    assert resp.status_code == 404
