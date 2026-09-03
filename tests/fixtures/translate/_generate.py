"""Write golden translation trees under tests/fixtures/translate."""
from __future__ import annotations

from pathlib import Path

from redbucket.formatters.registry import translate_files

from tests.support import (
    DOC_TYPES,
    FIXTURE_ROOT,
    HARNESSES,
    INSTRUCTIONS_TEXT,
    MCP_JSON_TEXT,
    MCP_TOML_TEXT,
    PLUGIN_TEXT,
    SKILL_TEXT,
    SUBAGENT_TEXT,
    write_tree,
)

SOURCES: dict[str, dict[str, bytes]] = {
    "skill": {"SKILL.md": SKILL_TEXT.encode("utf-8")},
    "instructions": {"AGENTS.md": INSTRUCTIONS_TEXT.encode("utf-8")},
    "plugin": {"plugin.md": PLUGIN_TEXT.encode("utf-8")},
    "subagent": {"agent.md": SUBAGENT_TEXT.encode("utf-8")},
}


def main() -> None:
    src_root = FIXTURE_ROOT / "sources"
    exp_root = FIXTURE_ROOT / "expected"
    for asset_type, files in SOURCES.items():
        write_tree(src_root / asset_type, files)
    write_tree(
        src_root / "mcp" / "claude",
        {".mcp.json": MCP_JSON_TEXT.encode("utf-8")},
    )
    write_tree(
        src_root / "mcp" / "codex",
        {"demo-mcp.toml": MCP_TOML_TEXT.encode("utf-8")},
    )
    for asset_type in DOC_TYPES:
        for source in HARNESSES:
            for target in HARNESSES:
                if source == target:
                    continue
                translated = translate_files(
                    asset_type,
                    source,
                    target,
                    SOURCES[asset_type],
                )
                dest = exp_root / asset_type / f"{source}-2-{target}"
                write_tree(dest, translated.files)
    claude_mcp = {".mcp.json": MCP_JSON_TEXT.encode("utf-8")}
    codex_mcp = {"demo-mcp.toml": MCP_TOML_TEXT.encode("utf-8")}
    write_tree(
        exp_root / "mcp" / "claude-2-codex",
        translate_files("mcp", "claude", "codex", claude_mcp).files,
    )
    write_tree(
        exp_root / "mcp" / "codex-2-claude",
        translate_files("mcp", "codex", "claude", codex_mcp).files,
    )


if __name__ == "__main__":
    main()
    print("wrote", Path(FIXTURE_ROOT))
