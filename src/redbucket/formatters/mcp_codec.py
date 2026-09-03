"""mcp：claude JSON 与 codex TOML。"""
from __future__ import annotations

import json
import tomllib

from redbucket.formatters.models import CanonicalMcp, TranslatedTree
from redbucket.formatters.textutil import decode_utf8, find_named


def _from_mapping(data: dict) -> CanonicalMcp:
    if "mcpServers" in data and isinstance(data["mcpServers"], dict):
        servers = data["mcpServers"]
        if not servers:
            raise ValueError("mcp server name missing")
        name = sorted(servers)[0]
        inner = servers[name]
        if not isinstance(inner, dict):
            raise ValueError("mcp server invalid")
        return _from_mapping({"name": name, **inner})
    name = str(data.get("name") or "")
    command = str(data.get("command") or "")
    url = str(data.get("url") or "")
    transport = str(data.get("transport") or "")
    if not transport:
        transport = "http" if url else "stdio"
    args_val = data.get("args")
    if isinstance(args_val, list):
        args_text = "\x1f".join(str(item) for item in args_val)
    else:
        args_text = str(args_val or "")
    extras = {}
    for key, value in data.items():
        skip = ("name", "command", "url", "transport", "args")
        if key in skip or key == "mcpServers":
            continue
        extras[str(key)] = json.dumps(value, sort_keys=True, ensure_ascii=True)
    return CanonicalMcp(
        name=name,
        transport=transport,
        command=command,
        args_text=args_text,
        url=url,
        extras=extras,
    )


def decode_mcp(files: dict[str, bytes]) -> CanonicalMcp:
    found_json = find_named(files, ("mcp.json", ".mcp.json", "server.json"))
    if found_json is None:
        for path, content in files.items():
            lower = path.lower()
            if lower.endswith(".json"):
                found_json = (path, content)
                break
    if found_json is not None:
        data = json.loads(decode_utf8(found_json[1]))
        if not isinstance(data, dict):
            raise ValueError("mcp json must be an object")
        item = _from_mapping(data)
        item.raw_kind = "json"
        return item
    found_toml = None
    for path, content in files.items():
        if path.lower().endswith(".toml"):
            found_toml = (path, content)
            break
    if found_toml is None:
        raise ValueError("mcp config missing")
    data = tomllib.loads(decode_utf8(found_toml[1]))
    if not isinstance(data, dict):
        raise ValueError("mcp toml must be a table")
    item = _from_mapping(data)
    item.raw_kind = "toml"
    return item


def encode_mcp_json(item: CanonicalMcp) -> TranslatedTree:
    server: dict = {
        "command": item.command,
        "transport": item.transport,
    }
    if item.url:
        server["url"] = item.url
    if item.args_text:
        server["args"] = item.args_text.split("\x1f")
    payload = {
        "mcpServers": {
            item.name: server,
        }
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    notes = ""
    lossy = bool(item.extras)
    if lossy:
        notes = "Unmapped mcp fields: " + ", ".join(sorted(item.extras))
    return TranslatedTree(
        files={".mcp.json": text.encode("utf-8")},
        lossy=lossy,
        notes=notes,
        filename=".mcp.json",
    )


def encode_mcp_toml(item: CanonicalMcp) -> TranslatedTree:
    lines = [
        f'name = "{item.name}"',
        f'transport = "{item.transport}"',
    ]
    if item.command:
        lines.append(f'command = "{item.command}"')
    if item.url:
        lines.append(f'url = "{item.url}"')
    if item.args_text:
        args_list = ", ".join(
            f'"{part}"' for part in item.args_text.split("\x1f")
        )
        lines.append(f"args = [{args_list}]")
    text = "\n".join(lines) + "\n"
    notes = ""
    lossy = bool(item.extras)
    if lossy:
        notes = "Unmapped mcp fields: " + ", ".join(sorted(item.extras))
    return TranslatedTree(
        files={f"{item.name}.toml": text.encode("utf-8")},
        lossy=lossy,
        notes=notes,
        filename=f"{item.name}.toml",
    )
