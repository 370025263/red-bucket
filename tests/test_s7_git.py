"""S7 存储安全与配额。"""
from __future__ import annotations

import os
import subprocess
import threading

from tests.support import (
    SKILL_TEXT,
    auth_header,
    b64_file,
    commit_count,
    create_bucket,
    set_storage_limit,
    signup,
    snapshot_tree,
    text_file,
    upload_asset,
    user_id_of,
)


def test_s7_1_commits_only_on_tree_writes(client) -> None:
    owner = signup(client, "alice")
    author = signup(client, "bobby")
    created = create_bucket(
        client,
        owner,
        "alice",
        "tools",
        visibility="public",
        template="claude",
    )
    assert created.status_code == 201
    assert commit_count(client, "alice", "tools") == 1
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
    assert commit_count(client, "alice", "tools") == 2
    listed = client.get("/api/v1/users/alice/buckets/tools/assets")
    asset_id = listed.json()["items"][0]["id"]
    client.delete(
        f"/api/v1/users/alice/buckets/tools/assets/{asset_id}",
        headers=auth_header(owner),
    )
    assert commit_count(client, "alice", "tools") == 3
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
    dest = signup(client, "carol")
    create_bucket(client, dest, "carol", "lab", visibility="public")
    src = client.get("/api/v1/users/alice/buckets/tools/assets")
    client.post(
        "/api/v1/users/carol/buckets/lab/copies",
        json={
            "source_username": "alice",
            "source_bucket": "tools",
            "source_asset_id": src.json()["items"][0]["id"],
        },
        headers=auth_header(dest),
    )
    assert commit_count(client, "carol", "lab") == 1
    before = commit_count(client, "alice", "tools")
    client.patch(
        "/api/v1/users/alice/buckets/tools",
        json={"visibility": "public"},
        headers=auth_header(owner),
    )
    client.post(
        "/api/v1/users/alice/buckets/tools/issues",
        json={"title": "q", "body": ""},
        headers=auth_header(author),
    )
    client.post(
        "/api/v1/users/alice/buckets/tools/pulls",
        json={
            "title": "p",
            "body": "",
            "files": [
                {"path": "skills/demo/SKILL.md", "content_text": SKILL_TEXT}
            ],
        },
        headers=auth_header(author),
    )
    client.post(
        "/api/v1/auth/logout",
        json={},
        headers=auth_header(author),
    )
    assert commit_count(client, "alice", "tools") == before
    client.post(
        "/api/v1/users/alice/buckets/tools/pulls/1/merge",
        json={},
        headers=auth_header(owner),
    )
    assert commit_count(client, "alice", "tools") == before + 1


def test_s7_2_rename_does_not_move_repo(client, data_dir) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "tools", template="claude")
    uid = user_id_of(client, "alice")
    repo = data_dir / "git" / str(uid)
    assert repo.is_dir()
    names = {path.name for path in repo.iterdir()}
    client.patch(
        "/api/v1/users/me",
        json={"username": "alice2"},
        headers=auth_header(token),
    )
    assert {path.name for path in repo.iterdir()} == names
    assert (data_dir / "git" / "alice2").exists() is False


def test_s7_3_path_traversal(client, data_dir) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "tools", visibility="public")
    sentinel = data_dir / "SENTINEL"
    sentinel.write_text("secret", encoding="utf-8")
    before = sentinel.read_text(encoding="utf-8")
    cases = ("../escape", "/abs/path", ".git/config")
    for path in cases:
        resp = upload_asset(
            client,
            token,
            "alice",
            "tools",
            "skill",
            "claude",
            path,
            [text_file("SKILL.md", SKILL_TEXT)],
        )
        assert resp.status_code == 422, path
    pull = client.post(
        "/api/v1/users/alice/buckets/tools/pulls",
        json={
            "title": "bad",
            "body": "",
            "files": [
                {"path": "../outside", "content_text": "x"}
            ],
        },
        headers=auth_header(token),
    )
    assert pull.status_code == 422
    assert sentinel.read_text(encoding="utf-8") == before
    assert snapshot_tree(client, "alice", "tools") == {}


def test_s7_4_symlink_does_not_read_outside(client, data_dir) -> None:
    token = signup(client, "alice")
    created = create_bucket(
        client,
        token,
        "alice",
        "tools",
        visibility="public",
        template="claude",
    )
    assert created.status_code == 201
    uid = user_id_of(client, "alice")
    bid = created.json()["id"]
    sentinel = data_dir / "outside.txt"
    sentinel.write_text("OUTSIDE-SECRET", encoding="utf-8")
    repo = data_dir / "git" / str(uid) / f"{bid}.git"
    work = data_dir / "git" / str(uid) / "link-work"
    work.mkdir()
    link = work / "leak"
    os.symlink(str(sentinel), str(link))
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "alice"
    env["GIT_AUTHOR_EMAIL"] = f"user-{uid}@users.red-bucket.invalid"
    env["GIT_COMMITTER_NAME"] = env["GIT_AUTHOR_NAME"]
    env["GIT_COMMITTER_EMAIL"] = env["GIT_AUTHOR_EMAIL"]
    subprocess.run(
        ["git", "--git-dir", str(repo), "--work-tree", str(work), "add", "-A"],
        check=True,
        env=env,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=alice",
            "-c",
            f"user.email={env['GIT_AUTHOR_EMAIL']}",
            "--git-dir",
            str(repo),
            "--work-tree",
            str(work),
            "commit",
            "-m",
            "plant symlink",
        ],
        check=True,
        env=env,
        capture_output=True,
    )
    blob = client.get("/api/v1/users/alice/buckets/tools/blob/leak")
    if blob.status_code == 200:
        text = blob.json().get("content_text") or ""
        assert "OUTSIDE-SECRET" not in text
    tree = snapshot_tree(client, "alice", "tools")
    for content in tree.values():
        assert b"OUTSIDE-SECRET" not in content


def test_s7_5_concurrent_quota(client) -> None:
    token = signup(client, "alice")
    created = create_bucket(
        client,
        token,
        "alice",
        "tools",
        visibility="public",
    )
    set_storage_limit(client, created.json()["id"], 20000)
    headers = auth_header(token)

    def one_payload(name: str, marker: bytes) -> dict:
        return {
            "type": "skill",
            "source_harness": "claude",
            "path": f"skills/{name}",
            "files": [
                text_file("SKILL.md", SKILL_TEXT),
                b64_file("blob.bin", marker * 12000),
            ],
        }

    for index in range(20):
        client.delete(
            "/api/v1/users/alice/buckets/tools",
            headers=headers,
        )
        create_bucket(
            client,
            token,
            "alice",
            "tools",
            visibility="public",
        )
        meta = client.get(
            "/api/v1/users/alice/buckets/tools",
            headers=headers,
        )
        set_storage_limit(client, meta.json()["id"], 20000)
        results: list[int] = []
        lock = threading.Lock()

        def worker(name: str, mark: bytes) -> None:
            resp = client.post(
                "/api/v1/users/alice/buckets/tools/assets",
                json=one_payload(name, mark),
                headers=headers,
            )
            with lock:
                results.append(resp.status_code)

        first = threading.Thread(target=worker, args=("a", b"a"))
        second = threading.Thread(target=worker, args=("b", b"b"))
        first.start()
        second.start()
        first.join()
        second.join()
        assert results.count(201) <= 1, (index, results)
        assert 413 in results or results.count(201) == 1
        usage = client.get(
            "/api/v1/users/alice/buckets/tools",
            headers=headers,
        ).json()["usage_bytes"]
        assert usage <= 20000
        assert usage <= 10485760


def test_s7_6_historical_raw_and_no_commits_table(client) -> None:
    token = signup(client, "alice")
    create_bucket(client, token, "alice", "tools", visibility="public")
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
    sha = first.json()["head_commit_sha"]
    later = SKILL_TEXT.replace("demo thing", "changed")
    upload_asset(
        client,
        token,
        "alice",
        "tools",
        "skill",
        "claude",
        "skills/demo",
        [text_file("SKILL.md", later)],
    )
    raw = client.get(
        f"/api/v1/users/alice/buckets/tools/assets/{first.json()['id']}/raw",
        params={"commit": sha},
    )
    assert raw.content == SKILL_TEXT.encode("utf-8")
    tables = client.app.state.core.store.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    names = {row["name"] for row in tables}
    assert "commits" not in names
