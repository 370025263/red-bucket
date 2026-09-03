"""翻译对注册表。GET /translation-matrix 的唯一数据源。"""
from __future__ import annotations

import json

from redbucket.catalog_const import ASSET_TYPES, HARNESSES
from redbucket.errors import translation_unsupported
from redbucket.formatters.doc_codec import (
    decode_doc,
    decode_instructions,
    encode_doc,
    encode_instructions,
)
from redbucket.formatters.mcp_codec import (
    decode_mcp,
    encode_mcp_json,
    encode_mcp_toml,
)
from redbucket.formatters.models import CanonicalDoc, TranslatedTree
from redbucket.formatters.textutil import decode_utf8, find_named

DOC_TYPES = ("skill", "instructions", "plugin", "subagent")


def pair_doc(source: str, target: str) -> str:
    return f"cross-transfer/{source}-2-{target}.md"


def is_identity(source: str, target: str) -> bool:
    return source == target


def mcp_supported(source: str, target: str) -> bool:
    if source == target:
        return True
    pair = {source, target}
    return pair == {"claude", "codex"}


def pair_supported(asset_type: str, source: str, target: str) -> bool:
    if source not in HARNESSES or target not in HARNESSES:
        return False
    if asset_type in DOC_TYPES:
        return True
    if asset_type == "mcp":
        return mcp_supported(source, target)
    return False


def matrix_entries() -> list[dict]:
    rows: list[dict] = []
    for asset_type in ASSET_TYPES:
        for source in HARNESSES:
            for target in HARNESSES:
                if not pair_supported(asset_type, source, target):
                    continue
                identity = is_identity(source, target)
                rows.append(
                    {
                        "asset_type": asset_type,
                        "source": source,
                        "target": target,
                        "supported": True,
                        "identity": identity,
                        "doc": None if identity else pair_doc(source, target),
                    }
                )
    return rows


def main_filename(asset_type: str, target: str) -> str:
    if asset_type == "skill":
        return "SKILL.md"
    if asset_type == "plugin":
        return "plugin.md"
    if asset_type == "subagent":
        return "agent.md"
    if asset_type == "instructions":
        if target == "claude":
            return "CLAUDE.md"
        return "AGENTS.md"
    raise translation_unsupported()


def translate_files(
    asset_type: str,
    source: str,
    target: str,
    files: dict[str, bytes],
) -> TranslatedTree:
    if not pair_supported(asset_type, source, target):
        raise translation_unsupported()
    if is_identity(source, target):
        raise translation_unsupported()
    if asset_type == "mcp":
        item = decode_mcp(files)
        if target == "claude":
            return encode_mcp_json(item)
        if target == "codex":
            return encode_mcp_toml(item)
        raise translation_unsupported()
    if asset_type == "instructions":
        doc = decode_instructions(files)
        return encode_instructions(doc, main_filename(asset_type, target))
    if asset_type == "plugin":
        found_json = find_named(files, ("plugin.json",))
        if found_json is not None:
            data = json.loads(decode_utf8(found_json[1]))
            doc = CanonicalDoc(
                name=str(data.get("name") or ""),
                description=str(data.get("description") or ""),
                body="",
            )
            return encode_doc(doc, main_filename(asset_type, target))
    mains = {
        "skill": ("SKILL.md", "skill.md"),
        "plugin": ("plugin.md", "PLUGIN.md"),
        "subagent": ("agent.md", "AGENT.md", "subagent.md"),
    }[asset_type]
    doc = decode_doc(files, mains)
    return encode_doc(doc, main_filename(asset_type, target))


def target_layout_root(asset_type: str, target: str, name: str) -> str:
    if asset_type == "instructions":
        return ""
    if asset_type == "mcp":
        if target == "claude":
            return ""
        if target == "codex":
            return ".codex/mcp-servers"
        if target == "agents":
            return "mcp"
        return ".openclaw/mcp"
    mapping = {
        ("skill", "claude"): f"skills/{name}",
        ("skill", "agents"): f"skills/{name}",
        ("skill", "codex"): f".codex/skills/{name}",
        ("skill", "openclaw"): f".openclaw/skills/{name}",
        ("plugin", "claude"): f"plugins/{name}",
        ("plugin", "agents"): f"plugins/{name}",
        ("plugin", "codex"): f".codex/plugins/{name}",
        ("plugin", "openclaw"): f".openclaw/plugins/{name}",
        ("subagent", "claude"): f".claude/agents/{name}",
        ("subagent", "agents"): f"agents/{name}",
        ("subagent", "codex"): f".codex/agents/{name}",
        ("subagent", "openclaw"): f".openclaw/agents/{name}",
    }
    return mapping[(asset_type, target)]
