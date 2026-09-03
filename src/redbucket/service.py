"""业务编排。HTTP 层只做参数与信封。"""
from __future__ import annotations

import json
import mimetypes
from redbucket.bucket_templates import (
    get_template,
    list_templates,
    require_template_name,
    template_files,
)
from redbucket.catalog_const import (
    DEVICE_CODE_TTL,
    DEVICE_POLL_INTERVAL,
    HARNESSES,
    VISIBILITIES,
)
from redbucket.clock import is_past, utc_in, utc_now
from redbucket.errors import (
    AppError,
    bucket_quota_exceeded,
    bucket_storage_exceeded,
    conflict,
    forbidden,
    not_found,
    translation_unsupported,
    unauthorized,
    validation_failed,
)
from redbucket.fileset import apply_replacements, decode_entries, zip_bytes
from redbucket.installscript import node_script
from redbucket.mdrender import render_markdown
from redbucket.formatters.registry import (
    matrix_entries,
    pair_supported,
    target_layout_root,
    translate_files,
)
from redbucket.gitstore.store import GIT_AUTHOR_DOMAIN, GitStore
from redbucket.httpjson import page_envelope, slice_page
from redbucket.present import (
    asset_json,
    bucket_json,
    comment_json,
    commit_json,
    copy_json,
    issue_json,
    pull_json,
    user_private,
    user_public,
    user_ref,
)
from redbucket.security.passwords import hash_password, verify_password
from redbucket.security.tokens import (
    hash_token,
    issue_token,
    issue_user_code,
)
from redbucket.settings import Settings
from redbucket.store.metadata import MetadataStore
from redbucket.validators.assets import validate_asset
from redbucket.validators.names import (
    normalize_name,
    require_bucket_name,
    require_email,
    require_password,
    require_username,
)
from redbucket.validators.paths import sanitize_relpath


class RedBucket:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = MetadataStore(settings.sqlite_path)
        self.git = GitStore(settings.storage_root)
        self.cache_root = settings.cache_root
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        self.store.close()

    def user_by_name(self, username: str):
        return self.store.fetchone(
            "SELECT * FROM users WHERE username_normalized = ?",
            (normalize_name(username),),
        )

    def user_by_id(self, user_id: int):
        return self.store.fetchone(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        )

    def user_by_email(self, email: str):
        return self.store.fetchone(
            "SELECT * FROM users WHERE email_normalized = ?",
            (normalize_name(email),),
        )

    def bucket_count(self, user_id: int) -> int:
        row = self.store.fetchone(
            "SELECT COUNT(*) AS total FROM buckets "
            "WHERE user_id = ? AND deleted_at IS NULL",
            (user_id,),
        )
        return int(row["total"]) if row else 0

    def auth_user(self, token: str | None):
        if not token:
            raise unauthorized()
        token_hash = hash_token(token)
        row = self.store.fetchone(
            "SELECT * FROM tokens "
            "WHERE token_hash = ? AND revoked_at IS NULL",
            (token_hash,),
        )
        if row is None:
            raise unauthorized()
        self.store.run_commit(
            "UPDATE tokens SET last_used_at = ? WHERE id = ?",
            (utc_now(), row["id"]),
        )
        user = self.user_by_id(row["user_id"])
        if user is None:
            raise unauthorized()
        return user

    def optional_user(self, token: str | None):
        if not token:
            return None
        return self.auth_user(token)

    def register(self, username: str, email: str, password: str) -> dict:
        require_username(username)
        require_email(email)
        require_password(password)
        if self.user_by_name(username) is not None:
            raise conflict("username_taken", "username taken")
        if self.user_by_email(email) is not None:
            raise conflict("email_taken", "email taken")
        stamp = utc_now()
        cursor = self.store.run_commit(
            "INSERT INTO users("
            "username, username_normalized, email, email_normalized, "
            "password_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                username,
                normalize_name(username),
                email,
                normalize_name(email),
                hash_password(password),
                stamp,
                stamp,
            ),
        )
        user = self.user_by_id(int(cursor.lastrowid))
        return user_public(user)

    def login(self, email: str, password: str) -> dict:
        if not email or not password:
            raise validation_failed(
                [{"field": "email", "issue": "email and password required"}]
            )
        user = self.user_by_email(email)
        hashed = user["password_hash"] if user else ""
        if user is None or not verify_password(hashed, password):
            raise unauthorized()
        token = issue_token()
        stamp = utc_now()
        self.store.run_commit(
            "INSERT INTO tokens("
            "user_id, token_hash, created_at, last_used_at) "
            "VALUES (?, ?, ?, ?)",
            (user["id"], hash_token(token), stamp, stamp),
        )
        return {
            "token": token,
            "token_type": "bearer",
            "user": user_private(user, self.bucket_count(user["id"])),
        }

    def start_device(self, client: str) -> dict:
        """An agent opens a login it cannot finish on its own."""
        device_code = issue_token()
        user_code = issue_user_code()
        origin = self.settings.public_origin
        self.store.run_commit(
            "INSERT INTO device_codes("
            "device_code_hash, user_code, client, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                hash_token(device_code),
                user_code,
                (client or "")[:60],
                utc_now(),
                utc_in(DEVICE_CODE_TTL),
            ),
        )
        return {
            "device_code": device_code,
            "user_code": user_code,
            "verification_url": f"{origin}/link",
            "verification_url_complete": f"{origin}/link/{user_code}",
            "expires_in": DEVICE_CODE_TTL,
            "interval": DEVICE_POLL_INTERVAL,
        }

    def device_row(self, user_code: str):
        return self.store.fetchone(
            "SELECT * FROM device_codes WHERE user_code = ?",
            ((user_code or "").strip().upper(),),
        )

    def device_pending(self, user_code: str) -> dict:
        """What the approval page shows before the human decides."""
        row = self.device_row(user_code)
        if row is None or is_past(row["expires_at"]):
            raise not_found()
        return {
            "user_code": row["user_code"],
            "client": row["client"],
            "state": row["state"],
            "created_at": row["created_at"],
        }

    def decide_device(self, user_code: str, viewer, approve: bool) -> dict:
        """The human, signed in on the site, says yes or no."""
        if viewer is None:
            raise unauthorized()
        row = self.device_row(user_code)
        if row is None or is_past(row["expires_at"]):
            raise not_found()
        if row["state"] != "pending":
            raise conflict("device_code_used", "already decided")
        state = "approved" if approve else "denied"
        self.store.run_commit(
            "UPDATE device_codes SET state = ?, user_id = ? "
            "WHERE id = ? AND state = 'pending'",
            (state, viewer["id"] if approve else None, row["id"]),
        )
        return {"user_code": row["user_code"], "state": state}

    def poll_device(self, device_code: str) -> dict:
        """The agent collects its token. One shot, then the code is dead."""
        row = self.store.fetchone(
            "SELECT * FROM device_codes WHERE device_code_hash = ?",
            (hash_token(device_code or ""),),
        )
        collected = row is not None and row["state"] == "collected"
        if row is None or collected or is_past(row["expires_at"]):
            raise not_found()
        if row["state"] == "pending":
            return {"status": "pending"}
        if row["state"] != "approved":
            return {"status": row["state"]}
        user = self.user_by_id(row["user_id"])
        if user is None:
            raise not_found()
        token = issue_token()
        stamp = utc_now()
        self.store.run_commit(
            "INSERT INTO tokens("
            "user_id, token_hash, created_at, last_used_at) "
            "VALUES (?, ?, ?, ?)",
            (user["id"], hash_token(token), stamp, stamp),
        )
        self.store.run_commit(
            "UPDATE device_codes SET state = 'collected' WHERE id = ?",
            (row["id"],),
        )
        return {
            "status": "approved",
            "token": token,
            "token_type": "bearer",
            "user": user_private(user, self.bucket_count(user["id"])),
        }

    def logout(self, token: str) -> None:
        self.auth_user(token)
        self.store.run_commit(
            "UPDATE tokens SET revoked_at = ? "
            "WHERE token_hash = ? AND revoked_at IS NULL",
            (utc_now(), hash_token(token)),
        )

    def me(self, token: str) -> dict:
        user = self.auth_user(token)
        return user_private(user, self.bucket_count(user["id"]))

    def patch_me(self, token: str, username: str) -> dict:
        user = self.auth_user(token)
        require_username(username)
        other = self.user_by_name(username)
        if other is not None and other["id"] != user["id"]:
            raise conflict("username_taken", "username taken")
        self.store.run_commit(
            "UPDATE users SET username = ?, username_normalized = ?, "
            "updated_at = ? WHERE id = ?",
            (username, normalize_name(username), utc_now(), user["id"]),
        )
        return self.me(token)

    def public_profile(self, username: str) -> dict:
        user = self.user_by_name(username)
        if user is None:
            raise not_found()
        return user_public(user)

    def _live_bucket(self, username: str, bucket: str):
        owner = self.user_by_name(username)
        if owner is None:
            raise not_found()
        row = self.store.fetchone(
            "SELECT * FROM buckets WHERE user_id = ? "
            "AND name_normalized = ? AND deleted_at IS NULL",
            (owner["id"], normalize_name(bucket)),
        )
        if row is None:
            raise not_found()
        return owner, row

    def _visible(self, owner, bucket_row, viewer) -> None:
        if bucket_row["visibility"] == "public":
            return
        if viewer is not None and viewer["id"] == owner["id"]:
            return
        raise not_found()

    def _require_owner(self, owner, viewer) -> None:
        if viewer is None:
            raise unauthorized()
        if viewer["id"] != owner["id"]:
            raise not_found()

    def _require_self(self, username: str, viewer) -> object:
        owner = self.user_by_name(username)
        if owner is None:
            raise not_found()
        if viewer is None:
            raise unauthorized()
        if viewer["id"] != owner["id"]:
            raise forbidden()
        return owner

    def _harness_mix(self, bucket_id: int) -> dict:
        rows = self.store.fetchall(
            "SELECT source_harness, COUNT(*) AS total FROM assets "
            "WHERE bucket_id = ? GROUP BY source_harness",
            (bucket_id,),
        )
        return {row["source_harness"]: row["total"] for row in rows}

    def _open_counts(self, bucket_id: int) -> tuple[int, int]:
        issues = self.store.fetchone(
            "SELECT COUNT(*) AS total FROM issues "
            "WHERE bucket_id = ? AND state = 'open'",
            (bucket_id,),
        )
        pulls = self.store.fetchone(
            "SELECT COUNT(*) AS total FROM pull_requests "
            "WHERE bucket_id = ? AND state = 'open'",
            (bucket_id,),
        )
        return int(issues["total"]), int(pulls["total"])

    def _bucket_out(self, owner, row) -> dict:
        open_issues, open_pulls = self._open_counts(row["id"])
        return bucket_json(
            row,
            owner["username"],
            self._harness_mix(row["id"]),
            open_issues,
            open_pulls,
        )

    def list_buckets(
        self,
        username: str,
        viewer,
        page: int,
        per_page: int,
    ) -> dict:
        owner = self.user_by_name(username)
        if owner is None:
            raise not_found()
        if viewer is not None and viewer["id"] == owner["id"]:
            where = "user_id = ? AND deleted_at IS NULL"
            params: tuple = (owner["id"],)
        else:
            where = (
                "user_id = ? AND deleted_at IS NULL AND visibility = 'public'"
            )
            params = (owner["id"],)
        total_row = self.store.fetchone(
            f"SELECT COUNT(*) AS total FROM buckets WHERE {where}",
            params,
        )
        total = int(total_row["total"])
        offset = (page - 1) * per_page
        rows = self.store.fetchall(
            f"SELECT * FROM buckets WHERE {where} "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            params + (per_page, offset),
        )
        items = [self._bucket_out(owner, row) for row in rows]
        return page_envelope(items, page, per_page, total)

    def create_bucket(
        self,
        username: str,
        viewer,
        name: str,
        visibility: str,
        description: str,
        template: str | None,
    ) -> dict:
        owner = self._require_self(username, viewer)
        require_bucket_name(name)
        if visibility not in VISIBILITIES:
            raise validation_failed(
                [{"field": "visibility", "issue": "invalid visibility"}]
            )
        if len(description) > 350:
            raise validation_failed(
                [{"field": "description", "issue": "max 350 characters"}]
            )
        require_template_name(template)
        existing = self.store.fetchone(
            "SELECT id FROM buckets WHERE user_id = ? "
            "AND name_normalized = ? AND deleted_at IS NULL",
            (owner["id"], normalize_name(name)),
        )
        if existing is not None:
            raise conflict("bucket_name_taken", "bucket name taken")
        stamp = utc_now()
        with self.store.immediate_tx() as connection:
            count_row = connection.execute(
                "SELECT COUNT(*) AS total FROM buckets "
                "WHERE user_id = ? AND deleted_at IS NULL",
                (owner["id"],),
            ).fetchone()
            current = int(count_row["total"])
            if current >= owner["bucket_quota"]:
                raise bucket_quota_exceeded(owner["bucket_quota"], current)
            cursor = connection.execute(
                "INSERT INTO buckets("
                "user_id, name, name_normalized, visibility, description, "
                "template, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    owner["id"],
                    name,
                    normalize_name(name),
                    visibility,
                    description,
                    template,
                    stamp,
                    stamp,
                ),
            )
            bucket_id = int(cursor.lastrowid)
        self.git.init_bare(owner["id"], bucket_id)
        if template is not None:
            with self.git.locked(owner["id"], bucket_id):
                self.git.commit_tree(
                    owner["id"],
                    bucket_id,
                    owner["username"],
                    owner["id"],
                    f"Initialize template {template}",
                    template_files(template),
                )
                usage = sum(
                    len(content)
                    for content in template_files(template).values()
                )
                self.store.run_commit(
                    "UPDATE buckets SET storage_usage_bytes = ?, "
                    "updated_at = ? WHERE id = ?",
                    (usage, utc_now(), bucket_id),
                )
        owner, row = self._live_bucket(owner["username"], name)
        return self._bucket_out(owner, row)

    def get_bucket(self, username: str, bucket: str, viewer) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        return self._bucket_out(owner, row)

    def patch_bucket(
        self,
        username: str,
        bucket: str,
        viewer,
        visibility: str | None,
        description: str | None,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._require_owner(owner, viewer)
        new_vis = row["visibility"]
        new_desc = row["description"]
        if visibility is not None:
            if visibility not in VISIBILITIES:
                raise validation_failed(
                    [{"field": "visibility", "issue": "invalid visibility"}]
                )
            new_vis = visibility
        if description is not None:
            if len(description) > 350:
                raise validation_failed(
                    [{"field": "description", "issue": "max 350 characters"}]
                )
            new_desc = description
        self.store.run_commit(
            "UPDATE buckets SET visibility = ?, description = ?, "
            "updated_at = ? WHERE id = ?",
            (new_vis, new_desc, utc_now(), row["id"]),
        )
        return self.get_bucket(username, bucket, viewer)

    def delete_bucket(self, username: str, bucket: str, viewer) -> None:
        owner, row = self._live_bucket(username, bucket)
        self._require_owner(owner, viewer)
        self.store.run_commit(
            "UPDATE buckets SET deleted_at = ?, updated_at = ? WHERE id = ?",
            (utc_now(), utc_now(), row["id"]),
        )

    def templates_page(self, page: int, per_page: int) -> dict:
        return slice_page(list_templates(), page, per_page)

    def template_one(self, name: str) -> dict:
        return get_template(name)

    def _uploader_ref(self, user_id: int) -> dict:
        user = self.user_by_id(user_id)
        if user is None:
            raise AppError(500, "internal_error", "uploader missing")
        return user_ref(user)

    def _provenance(self, copy_id: int | None) -> dict | None:
        if copy_id is None:
            return None
        row = self.store.fetchone(
            "SELECT * FROM copies WHERE id = ?",
            (copy_id,),
        )
        if row is None:
            return None
        return {
            "id": row["id"],
            "source_full_name": row["source_full_name"],
            "source_commit_sha": row["source_commit_sha"],
            "created_at": row["created_at"],
        }

    def _asset_out(self, owner, bucket_row, asset_row) -> dict:
        return asset_json(
            asset_row,
            owner["username"],
            bucket_row["name"],
            self._uploader_ref(asset_row["uploader_id"]),
            self._provenance(asset_row["source_copy_id"]),
        )

    def list_assets(
        self,
        username: str,
        bucket: str,
        viewer,
        page: int,
        per_page: int,
        asset_type: str | None,
        source_harness: str | None,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        clauses = ["bucket_id = ?"]
        params: list = [row["id"]]
        if asset_type:
            clauses.append("type = ?")
            params.append(asset_type)
        if source_harness:
            clauses.append("source_harness = ?")
            params.append(source_harness)
        where = " AND ".join(clauses)
        total = int(
            self.store.fetchone(
                f"SELECT COUNT(*) AS total FROM assets WHERE {where}",
                tuple(params),
            )["total"]
        )
        offset = (page - 1) * per_page
        rows = self.store.fetchall(
            f"SELECT * FROM assets WHERE {where} "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            tuple(params) + (per_page, offset),
        )
        items = [self._asset_out(owner, row, item) for item in rows]
        return page_envelope(items, page, per_page, total)

    def _prefixed_files(
        self,
        asset_path: str,
        files: list[dict],
    ) -> tuple[dict[str, bytes], dict[str, bytes]]:
        relative = decode_entries(files, relative_to="")
        prefixed: dict[str, bytes] = {}
        root = sanitize_relpath(asset_path)
        for rel, content in relative.items():
            prefixed[f"{root}/{rel}"] = content
        return prefixed, relative

    def _commit_tree_quota(
        self,
        owner,
        bucket_row,
        author,
        message: str,
        new_tree: dict[str, bytes],
        rebuild=None,
    ) -> str:
        user_id = owner["id"]
        bucket_id = bucket_row["id"]
        with self.git.locked(user_id, bucket_id):
            current = self.git.snapshot(user_id, bucket_id)
            if rebuild is not None:
                new_tree = rebuild(current)
            current_size = sum(len(item) for item in current.values())
            new_size = sum(len(item) for item in new_tree.values())
            limit = bucket_row["storage_limit_bytes"]
            if new_size > limit:
                raise bucket_storage_exceeded(current_size, limit)
            sha = self.git.commit_tree(
                user_id,
                bucket_id,
                author["username"],
                author["id"],
                message,
                new_tree,
            )
            self.store.run_commit(
                "UPDATE buckets SET storage_usage_bytes = ?, "
                "updated_at = ? WHERE id = ?",
                (new_size, utc_now(), bucket_id),
            )
            return sha

    def create_asset(
        self,
        username: str,
        bucket: str,
        viewer,
        asset_type: str,
        source_harness: str,
        path: str,
        files: list[dict],
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._require_owner(owner, viewer)
        if not asset_type or not source_harness:
            raise validation_failed(
                [{"field": "type", "issue": "type and harness required"}]
            )
        root = sanitize_relpath(path)
        prefixed, relative = self._prefixed_files(root, files)
        validate_asset(asset_type, source_harness, relative)

        def apply_upload(current: dict[str, bytes]) -> dict[str, bytes]:
            updated = dict(current)
            for key in list(updated):
                if key == root or key.startswith(root + "/"):
                    del updated[key]
            updated.update(prefixed)
            return updated

        sha = self._commit_tree_quota(
            owner,
            row,
            viewer,
            f"Upload {asset_type} {root}",
            {},
            apply_upload,
        )
        size_bytes = sum(len(item) for item in relative.values())
        stamp = utc_now()
        existing = self.store.fetchone(
            "SELECT * FROM assets WHERE bucket_id = ? AND path = ?",
            (row["id"], root),
        )
        if existing is None:
            cursor = self.store.run_commit(
                "INSERT INTO assets("
                "bucket_id, type, source_harness, path, size_bytes, "
                "uploader_id, head_commit_sha, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["id"],
                    asset_type,
                    source_harness,
                    root,
                    size_bytes,
                    viewer["id"],
                    sha,
                    stamp,
                    stamp,
                ),
            )
            asset_id = int(cursor.lastrowid)
        else:
            self.store.run_commit(
                "UPDATE assets SET type = ?, source_harness = ?, "
                "size_bytes = ?, uploader_id = ?, head_commit_sha = ?, "
                "updated_at = ? WHERE id = ?",
                (
                    asset_type,
                    source_harness,
                    size_bytes,
                    viewer["id"],
                    sha,
                    stamp,
                    existing["id"],
                ),
            )
            asset_id = existing["id"]
        asset_row = self.store.fetchone(
            "SELECT * FROM assets WHERE id = ?",
            (asset_id,),
        )
        owner, row = self._live_bucket(username, bucket)
        return self._asset_out(owner, row, asset_row)

    def get_asset(
        self,
        username: str,
        bucket: str,
        asset_id: int,
        viewer,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        asset_row = self.store.fetchone(
            "SELECT * FROM assets WHERE id = ? AND bucket_id = ?",
            (asset_id, row["id"]),
        )
        if asset_row is None:
            raise not_found()
        return self._asset_out(owner, row, asset_row)

    def delete_asset(
        self,
        username: str,
        bucket: str,
        asset_id: int,
        viewer,
    ) -> None:
        owner, row = self._live_bucket(username, bucket)
        self._require_owner(owner, viewer)
        asset_row = self.store.fetchone(
            "SELECT * FROM assets WHERE id = ? AND bucket_id = ?",
            (asset_id, row["id"]),
        )
        if asset_row is None:
            raise not_found()
        root = asset_row["path"]

        def apply_delete(current: dict[str, bytes]) -> dict[str, bytes]:
            return {
                key: value
                for key, value in current.items()
                if key != root and not key.startswith(root + "/")
            }

        self._commit_tree_quota(
            owner,
            row,
            viewer,
            f"Delete asset {root}",
            {},
            apply_delete,
        )
        self.store.run_commit(
            "DELETE FROM assets WHERE id = ?",
            (asset_id,),
        )

    def _files_under(
        self,
        tree: dict[str, bytes],
        root: str,
    ) -> dict[str, bytes]:
        out: dict[str, bytes] = {}
        for path, content in tree.items():
            if path == root:
                out[path.rsplit("/", 1)[-1]] = content
            elif path.startswith(root + "/"):
                out[path[len(root) + 1 :]] = content
        return out

    def raw_asset(
        self,
        username: str,
        bucket: str,
        asset_id: int,
        viewer,
        commit: str | None,
    ) -> tuple[bytes, str]:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        asset_row = self.store.fetchone(
            "SELECT * FROM assets WHERE id = ? AND bucket_id = ?",
            (asset_id, row["id"]),
        )
        if asset_row is None:
            raise not_found()
        if commit:
            self._require_commit(owner["id"], row["id"], commit)
        tree = self.git.snapshot(owner["id"], row["id"], commit)
        files = self._files_under(tree, asset_row["path"])
        if not files:
            raise validation_failed(
                [{"field": "commit", "issue": "path missing at commit"}]
            )
        if len(files) == 1:
            path, payload = next(iter(files.items()))
            guessed = mimetypes.guess_type(path)[0]
            media = guessed if guessed else "application/octet-stream"
            return payload, media
        return zip_bytes(files), "application/zip"

    def _require_commit(self, user_id: int, bucket_id: int, sha: str) -> None:
        try:
            self.git.commit_detail(user_id, bucket_id, sha)
        except AppError as exc:
            if exc.code == "not_found":
                raise validation_failed(
                    [{"field": "commit", "issue": "unknown commit"}]
                ) from exc
            raise

    def _author_from_email(self, email: str) -> dict:
        prefix = "user-"
        suffix = f"@{GIT_AUTHOR_DOMAIN}"
        if not email.startswith(prefix) or not email.endswith(suffix):
            raise AppError(
                500,
                "internal_error",
                "commit author email invalid",
            )
        raw = email[len(prefix) : -len(suffix)]
        user = self.user_by_id(int(raw))
        if user is None:
            raise AppError(500, "internal_error", "commit author missing")
        return user_ref(user)

    def _commit_out(self, user_id: int, bucket_id: int, sha: str) -> dict:
        detail = self.git.commit_detail(user_id, bucket_id, sha)
        author = self._author_from_email(detail["author_email"])
        return commit_json(detail, author)

    def _asset_rows(self, bucket_id: int):
        return self.store.fetchall(
            "SELECT * FROM assets WHERE bucket_id = ?",
            (bucket_id,),
        )

    def _match_asset(self, assets, path: str) -> dict | None:
        best = None
        best_len = -1
        for asset in assets:
            root = asset["path"]
            if path == root or path.startswith(root + "/"):
                if len(root) > best_len:
                    best = asset
                    best_len = len(root)
        if best is None:
            return None
        return {
            "id": best["id"],
            "type": best["type"],
            "source_harness": best["source_harness"],
        }

    def tree_page(
        self,
        username: str,
        bucket: str,
        viewer,
        page: int,
        per_page: int,
        rel_path: str,
        commit: str | None,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        prefix = ""
        if rel_path:
            prefix = sanitize_relpath(rel_path)
        if commit:
            self._require_commit(owner["id"], row["id"], commit)
        is_dir = self.git.is_tree(
            owner["id"],
            row["id"],
            prefix,
            commit,
        )
        if prefix and not is_dir:
            raise not_found()
        entries = self.git.tree_entries(owner["id"], row["id"], prefix, commit)
        assets = self._asset_rows(row["id"])
        items: list[dict] = []
        for entry in entries:
            name = entry["name"]
            full = f"{prefix}/{name}" if prefix else name
            last = self.git.last_commit_for_path(
                owner["id"],
                row["id"],
                full,
                commit,
            )
            items.append(
                {
                    "name": name,
                    "path": full,
                    "entry_type": entry["entry_type"],
                    "size_bytes": entry["size_bytes"],
                    "last_commit_sha": last["sha"] if last else None,
                    "last_commit_message": last["message"] if last else None,
                    "last_commit_at": last["committed_at"] if last else None,
                    "asset": self._match_asset(assets, full),
                }
            )

        def tree_sort_key(item: dict) -> tuple:
            kind = 0 if item["entry_type"] == "dir" else 1
            return (kind, item["name"].casefold())

        items.sort(key=tree_sort_key)
        total = len(items)
        start = (page - 1) * per_page
        page_items = items[start : start + per_page]
        head = self.git.head_sha(owner["id"], row["id"])
        latest = None
        if head:
            latest = self._commit_out(owner["id"], row["id"], head)
        extra = {
            "latest_commit": latest,
            "commit_count": self.git.commit_count(owner["id"], row["id"]),
        }
        return page_envelope(page_items, page, per_page, total, extra)

    def blob(
        self,
        username: str,
        bucket: str,
        viewer,
        rel_path: str,
        commit: str | None,
        encoding: str | None,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        path = sanitize_relpath(rel_path)
        if commit:
            self._require_commit(owner["id"], row["id"], commit)
        if self.git.is_tree(owner["id"], row["id"], path, commit):
            raise validation_failed(
                [{"field": "path", "issue": "path is a directory"}]
            )
        payload = self.git.blob(owner["id"], row["id"], path, commit)
        last = self.git.last_commit_for_path(
            owner["id"],
            row["id"],
            path,
            commit,
        )
        text = None
        b64 = None
        try:
            decoded = payload.decode("utf-8", errors="strict")
            use_text = encoding != "base64"
        except UnicodeDecodeError:
            decoded = None
            use_text = False
        if use_text:
            text = decoded
        else:
            import base64

            b64 = base64.b64encode(payload).decode("ascii", errors="strict")
        return {
            "path": path,
            "size_bytes": len(payload),
            "content_text": text,
            "content_base64": b64,
            "last_commit_sha": last["sha"] if last else None,
            "last_commit_message": last["message"] if last else None,
            "last_commit_at": last["committed_at"] if last else None,
        }

    def list_commits(
        self,
        username: str,
        bucket: str,
        viewer,
        page: int,
        per_page: int,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        rows, total = self.git.commits(owner["id"], row["id"], page, per_page)
        items = []
        for item in rows:
            items.append(self._commit_out(owner["id"], row["id"], item["sha"]))
        return page_envelope(items, page, per_page, total)

    def get_commit(self, username: str, bucket: str, sha: str, viewer) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        return self._commit_out(owner["id"], row["id"], sha)

    def matrix_page(
        self,
        page: int,
        per_page: int,
        asset_type: str | None,
        source: str | None,
        target: str | None,
    ) -> dict:
        rows = matrix_entries()
        if asset_type:
            rows = [item for item in rows if item["asset_type"] == asset_type]
        if source:
            rows = [item for item in rows if item["source"] == source]
        if target:
            rows = [item for item in rows if item["target"] == target]
        return slice_page(rows, page, per_page)

    def _require_target(self, target: str | None) -> str:
        if not target:
            raise validation_failed(
                [{"field": "target", "issue": "target is required"}]
            )
        if target not in HARNESSES:
            raise validation_failed(
                [{"field": "target", "issue": "invalid target"}]
            )
        return target

    def translated_asset(
        self,
        username: str,
        bucket: str,
        asset_id: int,
        viewer,
        target: str,
        commit: str | None,
        meta_only: bool,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        target = self._require_target(target)
        asset_row = self.store.fetchone(
            "SELECT * FROM assets WHERE id = ? AND bucket_id = ?",
            (asset_id, row["id"]),
        )
        if asset_row is None:
            raise not_found()
        if commit:
            self._require_commit(owner["id"], row["id"], commit)
        source = asset_row["source_harness"]
        tree = self.git.snapshot(owner["id"], row["id"], commit)
        files = self._files_under(tree, asset_row["path"])
        if source == target:
            if len(files) == 1:
                path, payload = next(iter(files.items()))
                filename = path
                media = (
                    mimetypes.guess_type(path)[0]
                    or "application/octet-stream"
                )
            else:
                payload = zip_bytes(files)
                filename = f"{asset_row['path'].rsplit('/', 1)[-1]}.zip"
                media = "application/zip"
            notes = ""
            lossy = False
        else:
            if not pair_supported(asset_row["type"], source, target):
                raise translation_unsupported()
            translated = translate_files(
                asset_row["type"],
                source,
                target,
                files,
            )
            if len(translated.files) == 1:
                path, payload = next(iter(translated.files.items()))
                filename = path
                media = (
                    mimetypes.guess_type(path)[0]
                    or "application/octet-stream"
                )
            else:
                payload = zip_bytes(translated.files)
                filename = translated.filename
                if not filename.endswith(".zip"):
                    filename = f"{filename}.zip"
                media = "application/zip"
            notes = translated.notes
            lossy = translated.lossy
        if meta_only:
            return {
                "kind": "meta",
                "body": {
                    "lossy": lossy,
                    "notes": notes,
                    "filename": filename,
                },
                "lossy": lossy,
            }
        return {
            "kind": "bytes",
            "payload": payload,
            "media": media,
            "lossy": lossy,
            "filename": filename,
        }

    def translated_bucket(
        self,
        username: str,
        bucket: str,
        viewer,
        target: str,
        commit: str | None,
        strict: bool,
        meta_only: bool,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        target = self._require_target(target)
        if commit:
            self._require_commit(owner["id"], row["id"], commit)
        else:
            commit = self.git.head_sha(owner["id"], row["id"])
        cache_dir = None
        if commit:
            cache_dir = self.cache_root / commit / target
            cache_zip = cache_dir / "archive.zip"
            cache_meta = cache_dir / "meta.json"
            if cache_zip.exists() and cache_meta.exists() and not meta_only:
                meta = json.loads(
                    cache_meta.read_bytes().decode("utf-8", errors="strict")
                )
                if strict and meta.get("skipped"):
                    raise translation_unsupported()
                return {
                    "kind": "bytes",
                    "payload": cache_zip.read_bytes(),
                    "media": "application/zip",
                    "lossy": bool(meta.get("lossy")),
                    "filename": "bucket.zip",
                }
        assets = self._asset_rows(row["id"])
        tree = self.git.snapshot(owner["id"], row["id"], commit)
        files_out: dict[str, bytes] = {}
        notes: list[str] = []
        skipped: list[str] = []
        lossy = False
        for asset in assets:
            source = asset["source_harness"]
            files = self._files_under(tree, asset["path"])
            if not pair_supported(asset["type"], source, target):
                skipped.append(asset["path"])
                continue
            if source == target:
                root = asset["path"]
                for path, content in tree.items():
                    if path == root or path.startswith(root + "/"):
                        files_out[path] = content
                continue
            translated = translate_files(asset["type"], source, target, files)
            if translated.lossy:
                lossy = True
                notes.append(f"{asset['path']}: {translated.notes}")
            name = asset["path"].rsplit("/", 1)[-1]
            root = target_layout_root(asset["type"], target, name)
            for path, content in translated.files.items():
                dest = f"{root}/{path}" if root else path
                files_out[dest] = content
        if skipped:
            lossy = True
            notes.append("skipped: " + ", ".join(skipped))
        if strict and skipped:
            raise translation_unsupported()
        notes_text = "\n".join(notes) + ("\n" if notes else "")
        files_out["_red_bucket/lossy-notes.md"] = notes_text.encode("utf-8")
        payload = zip_bytes(files_out)
        meta = {"lossy": lossy, "notes": notes_text, "skipped": skipped}
        if cache_dir is not None:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_zip.write_bytes(payload)
            cache_meta.write_text(
                json.dumps(meta, sort_keys=True),
                encoding="utf-8",
            )
        if meta_only:
            return {"kind": "meta", "body": meta, "lossy": lossy}
        return {
            "kind": "bytes",
            "payload": payload,
            "media": "application/zip",
            "lossy": lossy,
            "filename": "bucket.zip",
        }

    def install_script(
        self,
        username: str,
        bucket: str,
        viewer,
        target: str,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        target = self._require_target(target)
        rel = (
            f"/api/v1/users/{owner['username']}/buckets/{row['name']}"
            f"/translated?target={target}"
        )
        origin = self.settings.public_origin
        script = node_script(origin, rel)
        return {
            "target": target,
            "script": script,
            "translated_url": rel,
        }

    def list_copies(
        self,
        username: str,
        bucket: str,
        viewer,
        page: int,
        per_page: int,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        total = int(
            self.store.fetchone(
                "SELECT COUNT(*) AS total FROM copies "
                "WHERE dest_bucket_id = ?",
                (row["id"],),
            )["total"]
        )
        offset = (page - 1) * per_page
        rows = self.store.fetchall(
            "SELECT * FROM copies WHERE dest_bucket_id = ? "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (row["id"], per_page, offset),
        )
        dest_full = f"{owner['username']}/{row['name']}"
        items = []
        for item in rows:
            actor = self._uploader_ref(item["actor_id"])
            items.append(copy_json(item, actor, dest_full))
        return page_envelope(items, page, per_page, total)

    def get_copy(
        self,
        username: str,
        bucket: str,
        copy_id: int,
        viewer,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        item = self.store.fetchone(
            "SELECT * FROM copies WHERE id = ? AND dest_bucket_id = ?",
            (copy_id, row["id"]),
        )
        if item is None:
            raise not_found()
        dest_full = f"{owner['username']}/{row['name']}"
        return copy_json(item, self._uploader_ref(item["actor_id"]), dest_full)

    def create_copy(
        self,
        username: str,
        bucket: str,
        viewer,
        source_username: str,
        source_bucket: str,
        source_asset_id: int,
        dest_path: str | None,
    ) -> dict:
        dest_owner, dest_row = self._live_bucket(username, bucket)
        self._require_owner(dest_owner, viewer)
        src_owner, src_row = self._live_bucket(source_username, source_bucket)
        self._visible(src_owner, src_row, viewer)
        src_asset = self.store.fetchone(
            "SELECT * FROM assets WHERE id = ? AND bucket_id = ?",
            (source_asset_id, src_row["id"]),
        )
        if src_asset is None:
            raise not_found()
        target_path = dest_path or src_asset["path"]
        target_path = sanitize_relpath(target_path)
        src_tree = self.git.snapshot(src_owner["id"], src_row["id"])
        relative = self._files_under(src_tree, src_asset["path"])
        validate_asset(
            src_asset["type"],
            src_asset["source_harness"],
            relative,
        )
        prefixed = {
            f"{target_path}/{name}": content
            for name, content in relative.items()
        }
        src_full = f"{src_owner['username']}/{src_row['name']}"
        src_sha = src_asset["head_commit_sha"]

        def apply_copy(current: dict[str, bytes]) -> dict[str, bytes]:
            updated = dict(current)
            for key in list(updated):
                if key == target_path or key.startswith(target_path + "/"):
                    del updated[key]
            updated.update(prefixed)
            return updated

        sha = self._commit_tree_quota(
            dest_owner,
            dest_row,
            viewer,
            f"Copy {src_full}@{src_sha} to {target_path}",
            {},
            apply_copy,
        )
        stamp = utc_now()
        size_bytes = sum(len(item) for item in relative.values())
        existing = self.store.fetchone(
            "SELECT * FROM assets WHERE bucket_id = ? AND path = ?",
            (dest_row["id"], target_path),
        )
        if existing is None:
            cursor = self.store.run_commit(
                "INSERT INTO assets("
                "bucket_id, type, source_harness, path, size_bytes, "
                "uploader_id, head_commit_sha, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    dest_row["id"],
                    src_asset["type"],
                    src_asset["source_harness"],
                    target_path,
                    size_bytes,
                    viewer["id"],
                    sha,
                    stamp,
                    stamp,
                ),
            )
            asset_id = int(cursor.lastrowid)
        else:
            self.store.run_commit(
                "UPDATE assets SET type = ?, source_harness = ?, "
                "size_bytes = ?, uploader_id = ?, head_commit_sha = ?, "
                "updated_at = ? WHERE id = ?",
                (
                    src_asset["type"],
                    src_asset["source_harness"],
                    size_bytes,
                    viewer["id"],
                    sha,
                    stamp,
                    existing["id"],
                ),
            )
            asset_id = existing["id"]
        copy_cursor = self.store.run_commit(
            "INSERT INTO copies("
            "dest_bucket_id, dest_asset_id, dest_path, dest_type, "
            "source_bucket_id, source_full_name, source_path, "
            "source_commit_sha, dest_commit_sha, actor_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                dest_row["id"],
                asset_id,
                target_path,
                src_asset["type"],
                src_row["id"],
                src_full,
                src_asset["path"],
                src_sha,
                sha,
                viewer["id"],
                stamp,
            ),
        )
        copy_id = int(copy_cursor.lastrowid)
        self.store.run_commit(
            "UPDATE assets SET source_copy_id = ? WHERE id = ?",
            (copy_id, asset_id),
        )
        return self.get_copy(username, bucket, copy_id, viewer)

    def list_issues(
        self,
        username: str,
        bucket: str,
        viewer,
        page: int,
        per_page: int,
        state: str | None,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        clauses = ["bucket_id = ?"]
        params: list = [row["id"]]
        if state:
            if state not in ("open", "closed"):
                raise validation_failed(
                    [{"field": "state", "issue": "invalid state"}]
                )
            clauses.append("state = ?")
            params.append(state)
        where = " AND ".join(clauses)
        total = int(
            self.store.fetchone(
                f"SELECT COUNT(*) AS total FROM issues WHERE {where}",
                tuple(params),
            )["total"]
        )
        offset = (page - 1) * per_page
        rows = self.store.fetchall(
            f"SELECT * FROM issues WHERE {where} "
            "ORDER BY number DESC LIMIT ? OFFSET ?",
            tuple(params) + (per_page, offset),
        )
        items = [self._issue_out(owner, row, item) for item in rows]
        return page_envelope(items, page, per_page, total)

    def _issue_out(self, owner, bucket_row, issue_row) -> dict:
        author = self._uploader_ref(issue_row["author_id"])
        closed_by = None
        if issue_row["closed_by_id"] is not None:
            closed_by = self._uploader_ref(issue_row["closed_by_id"])
        return issue_json(
            issue_row,
            f"{owner['username']}/{bucket_row['name']}",
            author,
            closed_by,
        )

    def create_issue(
        self,
        username: str,
        bucket: str,
        viewer,
        title: str,
        body: str,
    ) -> dict:
        if viewer is None:
            raise unauthorized()
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        if not title:
            raise validation_failed(
                [{"field": "title", "issue": "title is required"}]
            )
        stamp = utc_now()
        with self.store.immediate_tx() as connection:
            max_row = connection.execute(
                "SELECT COALESCE(MAX(number), 0) AS total FROM issues "
                "WHERE bucket_id = ?",
                (row["id"],),
            ).fetchone()
            number = int(max_row["total"]) + 1
            cursor = connection.execute(
                "INSERT INTO issues("
                "bucket_id, number, author_id, title, body, created_at, "
                "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (row["id"], number, viewer["id"], title, body, stamp, stamp),
            )
            issue_id = int(cursor.lastrowid)
        issue_row = self.store.fetchone(
            "SELECT * FROM issues WHERE id = ?",
            (issue_id,),
        )
        return self._issue_out(owner, row, issue_row)

    def get_issue(
        self,
        username: str,
        bucket: str,
        number: int,
        viewer,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        issue_row = self.store.fetchone(
            "SELECT * FROM issues WHERE bucket_id = ? AND number = ?",
            (row["id"], number),
        )
        if issue_row is None:
            raise not_found()
        return self._issue_out(owner, row, issue_row)

    def close_issue(
        self,
        username: str,
        bucket: str,
        number: int,
        viewer,
        state: str,
    ) -> dict:
        if viewer is None:
            raise unauthorized()
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        issue_row = self.store.fetchone(
            "SELECT * FROM issues WHERE bucket_id = ? AND number = ?",
            (row["id"], number),
        )
        if issue_row is None:
            raise not_found()
        if state != "closed":
            raise validation_failed(
                [{"field": "state", "issue": "only closed is accepted"}]
            )
        is_author = viewer["id"] == issue_row["author_id"]
        is_owner = viewer["id"] == owner["id"]
        if not is_author and not is_owner:
            raise forbidden()
        stamp = utc_now()
        self.store.run_commit(
            "UPDATE issues SET state = 'closed', closed_by_id = ?, "
            "closed_at = ?, updated_at = ? WHERE id = ?",
            (viewer["id"], stamp, stamp, issue_row["id"]),
        )
        return self.get_issue(username, bucket, number, viewer)

    def list_comments(
        self,
        username: str,
        bucket: str,
        number: int,
        viewer,
        page: int,
        per_page: int,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        issue_row = self.store.fetchone(
            "SELECT * FROM issues WHERE bucket_id = ? AND number = ?",
            (row["id"], number),
        )
        if issue_row is None:
            raise not_found()
        total = int(
            self.store.fetchone(
                "SELECT COUNT(*) AS total FROM issue_comments "
                "WHERE issue_id = ?",
                (issue_row["id"],),
            )["total"]
        )
        offset = (page - 1) * per_page
        rows = self.store.fetchall(
            "SELECT * FROM issue_comments WHERE issue_id = ? "
            "ORDER BY id ASC LIMIT ? OFFSET ?",
            (issue_row["id"], per_page, offset),
        )
        dest_full = f"{owner['username']}/{row['name']}"
        items = [
            comment_json(
                item,
                number,
                dest_full,
                self._uploader_ref(item["author_id"]),
            )
            for item in rows
        ]
        return page_envelope(items, page, per_page, total)

    def create_comment(
        self,
        username: str,
        bucket: str,
        number: int,
        viewer,
        body: str,
    ) -> dict:
        if viewer is None:
            raise unauthorized()
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        issue_row = self.store.fetchone(
            "SELECT * FROM issues WHERE bucket_id = ? AND number = ?",
            (row["id"], number),
        )
        if issue_row is None:
            raise not_found()
        if not body:
            raise validation_failed(
                [{"field": "body", "issue": "body is required"}]
            )
        is_author = viewer["id"] == issue_row["author_id"]
        is_owner = viewer["id"] == owner["id"]
        if not is_author and not is_owner:
            raise forbidden()
        stamp = utc_now()
        cursor = self.store.run_commit(
            "INSERT INTO issue_comments("
            "issue_id, author_id, body, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (issue_row["id"], viewer["id"], body, stamp, stamp),
        )
        comment_id = int(cursor.lastrowid)
        return self.get_comment(username, bucket, number, comment_id, viewer)

    def get_comment(
        self,
        username: str,
        bucket: str,
        number: int,
        comment_id: int,
        viewer,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        issue_row = self.store.fetchone(
            "SELECT * FROM issues WHERE bucket_id = ? AND number = ?",
            (row["id"], number),
        )
        if issue_row is None:
            raise not_found()
        item = self.store.fetchone(
            "SELECT * FROM issue_comments WHERE id = ? AND issue_id = ?",
            (comment_id, issue_row["id"]),
        )
        if item is None:
            raise not_found()
        return comment_json(
            item,
            number,
            f"{owner['username']}/{row['name']}",
            self._uploader_ref(item["author_id"]),
        )

    def _pull_files(self, row) -> list:
        return json.loads(row["proposed_files_json"])

    def _pull_out(self, owner, bucket_row, pull_row, with_files: bool) -> dict:
        files = self._pull_files(pull_row) if with_files else None
        return pull_json(
            pull_row,
            f"{owner['username']}/{bucket_row['name']}",
            self._uploader_ref(pull_row["author_id"]),
            files,
        )

    def list_pulls(
        self,
        username: str,
        bucket: str,
        viewer,
        page: int,
        per_page: int,
        state: str | None,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        clauses = ["bucket_id = ?"]
        params: list = [row["id"]]
        if state:
            if state not in ("open", "merged", "rejected"):
                raise validation_failed(
                    [{"field": "state", "issue": "invalid state"}]
                )
            clauses.append("state = ?")
            params.append(state)
        where = " AND ".join(clauses)
        total = int(
            self.store.fetchone(
                f"SELECT COUNT(*) AS total FROM pull_requests WHERE {where}",
                tuple(params),
            )["total"]
        )
        offset = (page - 1) * per_page
        rows = self.store.fetchall(
            f"SELECT * FROM pull_requests WHERE {where} "
            "ORDER BY number DESC LIMIT ? OFFSET ?",
            tuple(params) + (per_page, offset),
        )
        items = [self._pull_out(owner, row, item, False) for item in rows]
        return page_envelope(items, page, per_page, total)

    def create_pull(
        self,
        username: str,
        bucket: str,
        viewer,
        title: str,
        body: str,
        files: list[dict],
    ) -> dict:
        if viewer is None:
            raise unauthorized()
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        if not title:
            raise validation_failed(
                [{"field": "title", "issue": "title is required"}]
            )
        if not files:
            raise validation_failed(
                [{"field": "files", "issue": "files is required"}]
            )
        apply_replacements({}, files)
        stamp = utc_now()
        payload = json.dumps(files)
        with self.store.immediate_tx() as connection:
            max_row = connection.execute(
                "SELECT COALESCE(MAX(number), 0) AS total "
                "FROM pull_requests WHERE bucket_id = ?",
                (row["id"],),
            ).fetchone()
            number = int(max_row["total"]) + 1
            cursor = connection.execute(
                "INSERT INTO pull_requests("
                "bucket_id, number, author_id, title, body, "
                "proposed_files_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["id"],
                    number,
                    viewer["id"],
                    title,
                    body,
                    payload,
                    stamp,
                    stamp,
                ),
            )
            pull_id = int(cursor.lastrowid)
        pull_row = self.store.fetchone(
            "SELECT * FROM pull_requests WHERE id = ?",
            (pull_id,),
        )
        return self._pull_out(owner, row, pull_row, True)

    def get_pull(
        self,
        username: str,
        bucket: str,
        number: int,
        viewer,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._visible(owner, row, viewer)
        pull_row = self.store.fetchone(
            "SELECT * FROM pull_requests WHERE bucket_id = ? AND number = ?",
            (row["id"], number),
        )
        if pull_row is None:
            raise not_found()
        return self._pull_out(owner, row, pull_row, True)

    def pull_files_page(
        self,
        username: str,
        bucket: str,
        number: int,
        viewer,
        page: int,
        per_page: int,
    ) -> dict:
        body = self.get_pull(username, bucket, number, viewer)
        files = sorted(body["files"], key=self._file_path_key)
        return slice_page(files, page, per_page)

    def _file_path_key(self, item: dict) -> str:
        return str(item.get("path") or "")

    def merge_pull(
        self,
        username: str,
        bucket: str,
        number: int,
        viewer,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._require_owner(owner, viewer)
        pull_row = self.store.fetchone(
            "SELECT * FROM pull_requests WHERE bucket_id = ? AND number = ?",
            (row["id"], number),
        )
        if pull_row is None:
            raise not_found()
        if pull_row["state"] != "open":
            raise conflict("conflict", "pull request is not open")
        files = self._pull_files(pull_row)
        changed: list[str] = []
        for item in files:
            changed.append(sanitize_relpath(item["path"]))
        assets = self._asset_rows(row["id"])
        author = self.user_by_id(pull_row["author_id"])
        if author is None:
            raise AppError(500, "internal_error", "pull author missing")

        def apply_merge(current: dict[str, bytes]) -> dict[str, bytes]:
            updated = apply_replacements(current, files)
            for asset in assets:
                touched = False
                for path in changed:
                    root = asset["path"]
                    if path == root or path.startswith(root + "/"):
                        touched = True
                        break
                if not touched:
                    continue
                relative = self._files_under(updated, asset["path"])
                validate_asset(
                    asset["type"],
                    asset["source_harness"],
                    relative,
                )
            return updated

        sha = self._commit_tree_quota(
            owner,
            row,
            author,
            f"Merge pull request #{number}",
            {},
            apply_merge,
        )
        stamp = utc_now()
        self.store.run_commit(
            "UPDATE pull_requests SET state = 'merged', "
            "merged_commit_sha = ?, closed_at = ?, updated_at = ? "
            "WHERE id = ?",
            (sha, stamp, stamp, pull_row["id"]),
        )
        merged = self.git.snapshot(owner["id"], row["id"])
        for asset in assets:
            relative = self._files_under(merged, asset["path"])
            size_bytes = sum(len(item) for item in relative.values())
            self.store.run_commit(
                "UPDATE assets SET size_bytes = ?, head_commit_sha = ?, "
                "updated_at = ? WHERE id = ?",
                (size_bytes, sha, stamp, asset["id"]),
            )
        return self.get_pull(username, bucket, number, viewer)

    def reject_pull(
        self,
        username: str,
        bucket: str,
        number: int,
        viewer,
    ) -> dict:
        owner, row = self._live_bucket(username, bucket)
        self._require_owner(owner, viewer)
        pull_row = self.store.fetchone(
            "SELECT * FROM pull_requests WHERE bucket_id = ? AND number = ?",
            (row["id"], number),
        )
        if pull_row is None:
            raise not_found()
        if pull_row["state"] != "open":
            raise conflict("conflict", "pull request is not open")
        stamp = utc_now()
        self.store.run_commit(
            "UPDATE pull_requests SET state = 'rejected', closed_at = ?, "
            "updated_at = ? WHERE id = ?",
            (stamp, stamp, pull_row["id"]),
        )
        return self.get_pull(username, bucket, number, viewer)

    def markdown_html(self, text: str) -> str:
        return render_markdown(text)
