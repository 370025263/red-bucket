"""裸仓 + 每次变更的临时 worktree。配额 flock 由调用方包在同一把锁里。"""
from __future__ import annotations

import fcntl
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from redbucket.errors import AppError
from redbucket.gitstore.paths import lock_path, repo_path
from redbucket.utils.proc import windowless_subprocess_kwargs

GIT_AUTHOR_DOMAIN = "users.red-bucket.invalid"


class GitStore:
    def __init__(self, storage_root: Path) -> None:
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def init_bare(self, user_id: int, bucket_id: int) -> Path:
        target = repo_path(self.storage_root, user_id, bucket_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        if (target / "HEAD").exists():
            return target
        self._run(
            [
                "git",
                "init",
                "--bare",
                "--initial-branch=main",
                str(target),
            ]
        )
        return target

    @contextmanager
    def locked(self, user_id: int, bucket_id: int) -> Iterator[None]:
        path = lock_path(self.storage_root, user_id, bucket_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
            os.close(handle)

    def commit_tree(
        self,
        user_id: int,
        bucket_id: int,
        author_name: str,
        author_user_id: int,
        message: str,
        files: dict[str, bytes],
    ) -> str:
        """用 files 精确替换工作树并提交。"""
        repo = self.init_bare(user_id, bucket_id)
        work = repo.parent / f"{bucket_id}.work"
        self._rmtree(work)
        work.mkdir(parents=True)
        for path, content in files.items():
            dest = work / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        env = os.environ.copy()
        email = f"user-{author_user_id}@{GIT_AUTHOR_DOMAIN}"
        env["GIT_AUTHOR_NAME"] = author_name
        env["GIT_AUTHOR_EMAIL"] = email
        env["GIT_COMMITTER_NAME"] = author_name
        env["GIT_COMMITTER_EMAIL"] = email
        self._run(
            [
                "git",
                "--git-dir",
                str(repo),
                "symbolic-ref",
                "HEAD",
                "refs/heads/main",
            ]
        )
        self._run(
            [
                "git",
                "--git-dir",
                str(repo),
                "--work-tree",
                str(work),
                "add",
                "-A",
            ],
            env=env,
        )
        self._run(
            [
                "git",
                "-c",
                f"user.name={author_name}",
                "-c",
                f"user.email={email}",
                "--git-dir",
                str(repo),
                "--work-tree",
                str(work),
                "commit",
                "--allow-empty",
                "-m",
                message,
            ],
            env=env,
        )
        sha = self._run_text(
            ["git", "--git-dir", str(repo), "rev-parse", "HEAD"],
        ).strip()
        self._rmtree(work)
        return sha

    def snapshot(
        self,
        user_id: int,
        bucket_id: int,
        commit_sha: str | None = None,
    ) -> dict[str, bytes]:
        out: dict[str, bytes] = {}
        for path in self.list_all_files(user_id, bucket_id, commit_sha):
            out[path] = self.blob(user_id, bucket_id, path, commit_sha)
        return out

    def head_sha(self, user_id: int, bucket_id: int) -> str | None:
        repo = repo_path(self.storage_root, user_id, bucket_id)
        if not (repo / "HEAD").exists():
            return None
        code, text = self._try_text(
            ["git", "--git-dir", str(repo), "rev-parse", "--verify", "HEAD"],
        )
        if code != 0:
            return None
        return text.strip()

    def tree_entries(
        self,
        user_id: int,
        bucket_id: int,
        prefix: str = "",
        commit_sha: str | None = None,
    ) -> list[dict]:
        repo = repo_path(self.storage_root, user_id, bucket_id)
        spec = commit_sha if commit_sha else "HEAD"
        if not self._has_commit(repo, spec):
            if prefix:
                raise AppError(404, "not_found", "path not found")
            return []
        target = f"{spec}:{prefix}" if prefix else spec
        code, raw = self._try_text(
            ["git", "--git-dir", str(repo), "ls-tree", "-l", target],
        )
        if code != 0:
            if prefix:
                raise AppError(404, "not_found", "path not found")
            return []
        entries: list[dict] = []
        for line in raw.splitlines():
            if not line:
                continue
            meta, name = line.split("\t", 1)
            parts = meta.split()
            kind = parts[1]
            sha = parts[2]
            size_raw = parts[3]
            size_bytes = 0 if size_raw == "-" else int(size_raw)
            entries.append(
                {
                    "name": name,
                    "path": name,
                    "entry_type": "dir" if kind == "tree" else "file",
                    "size_bytes": size_bytes,
                    "sha": sha,
                }
            )
        return entries

    def blob(
        self,
        user_id: int,
        bucket_id: int,
        path: str,
        commit_sha: str | None = None,
    ) -> bytes:
        repo = repo_path(self.storage_root, user_id, bucket_id)
        spec = commit_sha if commit_sha else "HEAD"
        code, payload = self._try_bytes(
            [
                "git",
                "--git-dir",
                str(repo),
                "show",
                f"{spec}:{path}",
            ],
        )
        if code != 0:
            raise AppError(404, "not_found", "path not found")
        return payload

    def is_tree(
        self,
        user_id: int,
        bucket_id: int,
        path: str,
        commit_sha: str | None = None,
    ) -> bool:
        repo = repo_path(self.storage_root, user_id, bucket_id)
        spec = commit_sha if commit_sha else "HEAD"
        code, raw = self._try_text(
            [
                "git",
                "--git-dir",
                str(repo),
                "ls-tree",
                "-d",
                spec,
                "--",
                path,
            ],
        )
        return code == 0 and bool(raw.strip())

    def commits(
        self,
        user_id: int,
        bucket_id: int,
        page: int,
        per_page: int,
    ) -> tuple[list[dict], int]:
        repo = repo_path(self.storage_root, user_id, bucket_id)
        if self.head_sha(user_id, bucket_id) is None:
            return [], 0
        code, raw = self._try_text(
            [
                "git",
                "--git-dir",
                str(repo),
                "log",
                "--format=%H%x1f%an%x1f%ae%x1f%aI%x1f%s",
            ],
        )
        if code != 0:
            return [], 0
        rows: list[dict] = []
        for line in raw.splitlines():
            if not line:
                continue
            sha, name, email, stamp, subject = line.split("\x1f", 4)
            rows.append(
                {
                    "sha": sha,
                    "author_name": name,
                    "author_email": email,
                    "committed_at": stamp,
                    "message": subject,
                }
            )
        total = len(rows)
        start = (page - 1) * per_page
        return rows[start : start + per_page], total

    def commit_count(self, user_id: int, bucket_id: int) -> int:
        repo = repo_path(self.storage_root, user_id, bucket_id)
        if self.head_sha(user_id, bucket_id) is None:
            return 0
        code, raw = self._try_text(
            ["git", "--git-dir", str(repo), "rev-list", "--count", "HEAD"],
        )
        if code != 0:
            return 0
        return int(raw.strip())

    def commit_detail(
        self,
        user_id: int,
        bucket_id: int,
        sha: str,
    ) -> dict:
        repo = repo_path(self.storage_root, user_id, bucket_id)
        code, raw = self._try_text(
            [
                "git",
                "--git-dir",
                str(repo),
                "show",
                "-s",
                "--format=%H%x1f%an%x1f%ae%x1f%aI%x1f%s",
                sha,
            ],
        )
        if code != 0 or not raw.strip():
            raise AppError(404, "not_found", "commit not found")
        line = raw.splitlines()[0]
        full, name, email, stamp, subject = line.split("\x1f", 4)
        files_code, files_raw = self._try_text(
            [
                "git",
                "--git-dir",
                str(repo),
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "--root",
                "-r",
                sha,
            ],
        )
        paths = []
        if files_code == 0:
            paths = [item for item in files_raw.splitlines() if item]
        return {
            "sha": full,
            "author_name": name,
            "author_email": email,
            "committed_at": stamp,
            "message": subject,
            "paths": paths,
        }

    def last_commit_for_path(
        self,
        user_id: int,
        bucket_id: int,
        path: str,
        commit_sha: str | None = None,
    ) -> dict | None:
        repo = repo_path(self.storage_root, user_id, bucket_id)
        spec = commit_sha if commit_sha else "HEAD"
        if not self._has_commit(repo, spec):
            return None
        code, raw = self._try_text(
            [
                "git",
                "--git-dir",
                str(repo),
                "log",
                "-1",
                "--format=%H%x1f%s%x1f%aI",
                spec,
                "--",
                path,
            ],
        )
        if code != 0 or not raw.strip():
            return None
        sha, subject, stamp = raw.splitlines()[0].split("\x1f", 2)
        return {
            "sha": sha,
            "message": subject,
            "committed_at": stamp,
        }

    def working_tree_bytes(self, user_id: int, bucket_id: int) -> int:
        files = self.snapshot(user_id, bucket_id)
        return sum(len(content) for content in files.values())

    def list_all_files(
        self,
        user_id: int,
        bucket_id: int,
        commit_sha: str | None = None,
    ) -> list[str]:
        repo = repo_path(self.storage_root, user_id, bucket_id)
        spec = commit_sha if commit_sha else "HEAD"
        if not self._has_commit(repo, spec):
            return []
        code, raw = self._try_text(
            [
                "git",
                "--git-dir",
                str(repo),
                "ls-tree",
                "-r",
                "--name-only",
                spec,
            ],
        )
        if code != 0:
            return []
        return [line for line in raw.splitlines() if line]

    def _has_commit(self, repo: Path, spec: str) -> bool:
        if not (repo / "HEAD").exists():
            return False
        code, _text = self._try_text(
            ["git", "--git-dir", str(repo), "rev-parse", "--verify", spec],
        )
        return code == 0

    def _run(
        self,
        argv: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        code, payload = self._try_bytes(argv, cwd=cwd, env=env)
        if code != 0:
            err = payload.decode("utf-8", errors="replace")
            raise AppError(
                500,
                "internal_error",
                f"git failed: {err.strip()}",
            )

    def _run_text(
        self,
        argv: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> str:
        return self._run_bytes(argv, cwd=cwd, env=env).decode(
            "utf-8",
            errors="replace",
        )

    def _run_bytes(
        self,
        argv: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> bytes:
        code, payload = self._try_bytes(argv, cwd=cwd, env=env)
        if code != 0:
            err = payload.decode("utf-8", errors="replace")
            raise AppError(
                500,
                "internal_error",
                f"git failed: {err.strip()}",
            )
        return payload

    def _try_text(
        self,
        argv: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        code, payload = self._try_bytes(argv, cwd=cwd, env=env)
        return code, payload.decode("utf-8", errors="replace")

    def _try_bytes(
        self,
        argv: list[str],
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[int, bytes]:
        result = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            **windowless_subprocess_kwargs(),
        )
        return result.returncode, result.stdout

    def _rmtree(self, path: Path) -> None:
        if not path.exists():
            return
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()
