"""按类型的资产校验。上传、copy、merge 共用。"""
from __future__ import annotations

import json
import tomllib

from redbucket.catalog_const import (
    ASSET_TYPES,
    HARNESSES,
    INSTRUCTIONS_MAX,
)
from redbucket.errors import validation_failed
from redbucket.formatters.frontmatter import (
    FrontmatterError,
    parse_frontmatter,
)
from redbucket.formatters.textutil import (
    decode_utf8,
    find_named,
    first_markdown,
)


def _detail(rule: str, path: str, message: str) -> dict:
    return {
        "field": "files",
        "rule": rule,
        "path": path,
        "message": message,
        "issue": message,
    }


def validate_asset(
    asset_type: str,
    source_harness: str,
    files: dict[str, bytes],
) -> None:
    details: list[dict] = []
    if asset_type not in ASSET_TYPES:
        details.append(
            _detail("type_unknown", "", f"unknown type {asset_type}")
        )
    if source_harness not in HARNESSES:
        details.append(
            _detail(
                "harness_unknown",
                "",
                f"unknown source_harness {source_harness}",
            )
        )
    if not files:
        details.append(_detail("files_empty", "", "files must not be empty"))
    if details:
        raise validation_failed(details)
    if asset_type == "skill":
        details.extend(_check_skill(files))
    elif asset_type == "mcp":
        details.extend(_check_mcp(files))
    elif asset_type == "instructions":
        details.extend(_check_instructions(files))
    elif asset_type == "subagent":
        details.extend(_check_named_md(files, "subagent"))
    elif asset_type == "plugin":
        details.extend(_check_plugin(files))
    if details:
        raise validation_failed(details)


def _check_skill(files: dict[str, bytes]) -> list[dict]:
    found = find_named(files, ("SKILL.md", "skill.md"))
    if found is None:
        return [_detail("skill_main_missing", "SKILL.md", "SKILL.md missing")]
    path, payload = found
    return _frontmatter_name_desc(path, payload, "skill_frontmatter")


def _check_named_md(files: dict[str, bytes], kind: str) -> list[dict]:
    found = first_markdown(files)
    if found is None:
        return [_detail(f"{kind}_md_missing", "", "markdown file missing")]
    path, text = found
    return _frontmatter_name_desc(
        path,
        text.encode("utf-8"),
        f"{kind}_frontmatter",
    )


def _check_plugin(files: dict[str, bytes]) -> list[dict]:
    found_json = find_named(files, ("plugin.json",))
    if found_json is not None:
        path, payload = found_json
        try:
            data = json.loads(decode_utf8(payload))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return [_detail("plugin_json_invalid", path, str(exc))]
        if not isinstance(data, dict) or not data.get("name"):
            return [_detail("plugin_name_missing", path, "name required")]
        return []
    return _check_named_md(files, "plugin")


def _check_instructions(files: dict[str, bytes]) -> list[dict]:
    try:
        found = first_markdown(files)
    except UnicodeDecodeError:
        path = ""
        for item in sorted(files):
            if item.lower().endswith(".md"):
                path = item
                break
        return [_detail("instructions_not_utf8", path, "must be utf-8")]
    if found is None:
        return [_detail("instructions_md_missing", "", "markdown missing")]
    path, text = found
    payload = files[path]
    if len(payload) > INSTRUCTIONS_MAX:
        return [
            _detail(
                "instructions_too_large",
                path,
                "instructions exceed size limit",
            )
        ]
    try:
        decode_utf8(payload)
    except UnicodeDecodeError:
        return [_detail("instructions_not_utf8", path, "must be utf-8")]
    if not text.strip():
        return [_detail("instructions_empty", path, "markdown is empty")]
    return []


def _check_mcp(files: dict[str, bytes]) -> list[dict]:
    for path, payload in files.items():
        lower = path.lower()
        if lower.endswith(".json"):
            return _check_mcp_json(path, payload)
        if lower.endswith(".toml"):
            return _check_mcp_toml(path, payload)
    return [_detail("mcp_config_missing", "", "json or toml config missing")]


def _check_mcp_json(path: str, payload: bytes) -> list[dict]:
    try:
        data = json.loads(decode_utf8(payload))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [_detail("mcp_json_invalid", path, str(exc))]
    if not isinstance(data, dict):
        return [_detail("mcp_json_object", path, "json must be an object")]
    return _check_mcp_mapping(path, data)


def _check_mcp_toml(path: str, payload: bytes) -> list[dict]:
    try:
        data = tomllib.loads(decode_utf8(payload))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return [_detail("mcp_toml_invalid", path, str(exc))]
    if not isinstance(data, dict):
        return [_detail("mcp_toml_table", path, "toml must be a table")]
    return _check_mcp_mapping(path, data)


def _check_mcp_mapping(path: str, data: dict) -> list[dict]:
    if "mcpServers" in data:
        servers = data.get("mcpServers")
        if not isinstance(servers, dict) or not servers:
            return [_detail("mcp_name_missing", path, "server name missing")]
        name = sorted(servers)[0]
        inner = servers[name]
        if not isinstance(inner, dict):
            return [_detail("mcp_server_invalid", path, "server invalid")]
        return _check_mcp_mapping(path, {"name": name, **inner})
    if not data.get("name"):
        return [_detail("mcp_name_missing", path, "server name missing")]
    has_transport = bool(
        data.get("transport")
        or data.get("command")
        or data.get("url")
    )
    if not has_transport:
        return [
            _detail(
                "mcp_transport_missing",
                path,
                "transport, command, or url required",
            )
        ]
    return []


def _frontmatter_name_desc(
    path: str,
    payload: bytes,
    rule: str,
) -> list[dict]:
    try:
        text = decode_utf8(payload)
        fields, _body = parse_frontmatter(text)
    except (UnicodeDecodeError, FrontmatterError) as exc:
        return [_detail(rule, path, str(exc))]
    details: list[dict] = []
    if not fields.get("name"):
        details.append(_detail("name_missing", path, "name required"))
    if not fields.get("description"):
        details.append(
            _detail("description_missing", path, "description required")
        )
    return details
