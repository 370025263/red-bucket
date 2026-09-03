"""API JSON 组装。字段名只来自 api-catalog / schema 映射。"""
from __future__ import annotations


def user_public(row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "created_at": row["created_at"],
    }


def user_private(row, bucket_count: int) -> dict:
    body = user_public(row)
    body["email"] = row["email"]
    body["bucket_quota"] = row["bucket_quota"]
    body["bucket_count"] = bucket_count
    return body


def user_ref(row) -> dict:
    return {"id": row["id"], "username": row["username"]}


def bucket_json(
    row,
    username: str,
    harness_mix: dict,
    open_issues: int,
    open_pulls: int,
) -> dict:
    return {
        "id": row["id"],
        "full_name": f"{username}/{row['name']}",
        "username": username,
        "name": row["name"],
        "visibility": row["visibility"],
        "description": row["description"],
        "template": row["template"],
        "usage_bytes": row["storage_usage_bytes"],
        "limit_bytes": row["storage_limit_bytes"],
        "open_issues_count": open_issues,
        "open_pulls_count": open_pulls,
        "harness_mix": harness_mix,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def asset_json(
    row,
    username: str,
    bucket_name: str,
    uploader: dict,
    provenance: dict | None,
) -> dict:
    return {
        "id": row["id"],
        "bucket_id": row["bucket_id"],
        "full_name": f"{username}/{bucket_name}",
        "type": row["type"],
        "source_harness": row["source_harness"],
        "path": row["path"],
        "size_bytes": row["size_bytes"],
        "uploader": uploader,
        "head_commit_sha": row["head_commit_sha"],
        "provenance": provenance,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def issue_json(
    row,
    bucket_full: str,
    author: dict,
    closed_by: dict | None,
) -> dict:
    return {
        "id": row["id"],
        "number": row["number"],
        "bucket_full_name": bucket_full,
        "title": row["title"],
        "body": row["body"],
        "state": row["state"],
        "author": author,
        "closed_by": closed_by,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "closed_at": row["closed_at"],
    }


def comment_json(
    row,
    issue_number: int,
    bucket_full: str,
    author: dict,
) -> dict:
    return {
        "id": row["id"],
        "issue_number": issue_number,
        "bucket_full_name": bucket_full,
        "body": row["body"],
        "author": author,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def pull_json(
    row,
    bucket_full: str,
    author: dict,
    files: list | None,
) -> dict:
    body = {
        "id": row["id"],
        "number": row["number"],
        "bucket_full_name": bucket_full,
        "title": row["title"],
        "body": row["body"],
        "state": row["state"],
        "author": author,
        "merged_commit_sha": row["merged_commit_sha"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "closed_at": row["closed_at"],
    }
    if files is not None:
        body["files"] = files
    return body


def copy_json(row, actor: dict, dest_full_name: str) -> dict:
    dest_id = row["dest_asset_id"]
    return {
        "id": row["id"],
        "dest_full_name": dest_full_name,
        "dest_asset": {
            "id": dest_id,
            "path": row["dest_path"],
            "type": row["dest_type"],
        },
        "source_full_name": row["source_full_name"],
        "source_bucket_id": row["source_bucket_id"],
        "source_path": row["source_path"],
        "source_commit_sha": row["source_commit_sha"],
        "dest_commit_sha": row["dest_commit_sha"],
        "actor": actor,
        "created_at": row["created_at"],
    }


def commit_json(detail: dict, author: dict) -> dict:
    sha = detail["sha"]
    return {
        "sha": sha,
        "short_sha": sha[:7],
        "message": detail["message"],
        "author": author,
        "authored_at": detail["committed_at"],
        "paths": detail.get("paths", []),
    }
