"""上传与 PR 的文件条目解码、zip 打包。"""
from __future__ import annotations

import base64
import io
import zipfile

from redbucket.errors import validation_failed
from redbucket.validators.paths import sanitize_relpath


def decode_entries(
    entries: list[dict],
    *,
    relative_to: str = "",
) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    seen: set[str] = set()
    for item in entries:
        raw_path = item.get("path")
        if not isinstance(raw_path, str):
            raise validation_failed(
                [{"field": "path", "issue": "path is required"}]
            )
        rel = sanitize_relpath(raw_path)
        if relative_to:
            full = f"{relative_to.rstrip('/')}/{rel}"
        else:
            full = rel
        if full in seen:
            raise validation_failed(
                [{"field": "path", "issue": "duplicate path", "path": full}]
            )
        seen.add(full)
        if item.get("delete"):
            if item.get("content_text") or item.get("content_base64"):
                raise validation_failed(
                    [
                        {
                            "field": "delete",
                            "issue": "delete cannot include content",
                            "path": full,
                        }
                    ]
                )
            out[full] = b""
            continue
        text = item.get("content_text")
        b64 = item.get("content_base64")
        if text is not None and b64 is not None:
            raise validation_failed(
                [
                    {
                        "field": "content_text",
                        "issue": "text and base64 are exclusive",
                        "path": full,
                    }
                ]
            )
        if text is not None:
            out[full] = text.encode("utf-8")
            continue
        if b64 is not None:
            try:
                out[full] = base64.b64decode(b64, validate=True)
            except (ValueError, TypeError) as exc:
                raise validation_failed(
                    [
                        {
                            "field": "content_base64",
                            "issue": "invalid base64",
                            "path": full,
                        }
                    ]
                ) from exc
            continue
        raise validation_failed(
            [
                {
                    "field": "files",
                    "issue": "content_text or content_base64 required",
                    "path": full,
                }
            ]
        )
    return out


def apply_replacements(
    tree: dict[str, bytes],
    entries: list[dict],
) -> dict[str, bytes]:
    updated = dict(tree)
    for item in entries:
        raw_path = item.get("path")
        if not isinstance(raw_path, str):
            raise validation_failed(
                [{"field": "path", "issue": "path is required"}]
            )
        full = sanitize_relpath(raw_path)
        if item.get("delete"):
            updated.pop(full, None)
            continue
        chunk = decode_entries([item], relative_to="")
        updated.update(chunk)
    return updated


def zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    archive = zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    )
    for path in sorted(files):
        info = zipfile.ZipInfo(
            filename=path,
            date_time=(1980, 1, 1, 0, 0, 0),
        )
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, files[path])
    archive.close()
    return buffer.getvalue()


def unzip_bytes(payload: bytes) -> dict[str, bytes]:
    buffer = io.BytesIO(payload)
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(buffer, "r") as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            out[name] = archive.read(name)
    return out
