"""四种 bucket 模板，内容与 api-catalog Template 一节一致。"""
from __future__ import annotations

from redbucket.errors import not_found, validation_failed

TEMPLATES: dict[str, dict] = {
    "codex": {
        "name": "codex",
        "description": "Codex 风格目录骨架",
        "files": [
            {"path": "README.md", "content_text": "# bucket\n"},
            {
                "path": "AGENTS.md",
                "content_text": (
                    "# AGENTS.md\n\n"
                    "Project instructions for Codex-style agents.\n"
                ),
            },
            {
                "path": ".codex/config.toml",
                "content_text": "# codex bucket config\n",
            },
            {"path": ".codex/skills/.gitkeep", "content_text": ""},
            {"path": ".codex/agents/.gitkeep", "content_text": ""},
            {"path": ".codex/plugins/.gitkeep", "content_text": ""},
            {"path": ".codex/mcp-servers/.gitkeep", "content_text": ""},
        ],
    },
    "agents": {
        "name": "agents",
        "description": "Generic agents 风格目录骨架",
        "files": [
            {"path": "README.md", "content_text": "# bucket\n"},
            {
                "path": "AGENTS.md",
                "content_text": (
                    "# AGENTS.md\n\nGeneric agents-style instructions.\n"
                ),
            },
            {"path": "skills/.gitkeep", "content_text": ""},
            {"path": "agents/.gitkeep", "content_text": ""},
            {"path": "plugins/.gitkeep", "content_text": ""},
            {"path": "mcp/.gitkeep", "content_text": ""},
        ],
    },
    "claude": {
        "name": "claude",
        "description": "Claude Code 风格目录骨架",
        "files": [
            {"path": "README.md", "content_text": "# bucket\n"},
            {
                "path": "CLAUDE.md",
                "content_text": (
                    "# CLAUDE.md\n\nProject instructions go here.\n"
                ),
            },
            {"path": "skills/.gitkeep", "content_text": ""},
            {"path": ".claude/settings.json", "content_text": "{}\n"},
            {"path": ".claude/skills/.gitkeep", "content_text": ""},
            {"path": ".claude/agents/.gitkeep", "content_text": ""},
            {
                "path": ".mcp.json",
                "content_text": '{\n  "mcpServers": {}\n}\n',
            },
        ],
    },
    "openclaw": {
        "name": "openclaw",
        "description": "OpenClaw 风格目录骨架",
        "files": [
            {"path": "README.md", "content_text": "# bucket\n"},
            {
                "path": "AGENTS.md",
                "content_text": (
                    "# AGENTS.md\n\n"
                    "OpenClaw-style workspace instructions.\n"
                ),
            },
            {"path": ".openclaw/openclaw.json", "content_text": "{}\n"},
            {"path": ".openclaw/skills/.gitkeep", "content_text": ""},
            {"path": ".openclaw/agents/.gitkeep", "content_text": ""},
            {"path": ".openclaw/plugins/.gitkeep", "content_text": ""},
            {"path": ".openclaw/mcp/.gitkeep", "content_text": ""},
        ],
    },
}


def list_templates() -> list[dict]:
    names = ("codex", "agents", "claude", "openclaw")
    return [TEMPLATES[name] for name in names]


def get_template(name: str) -> dict:
    if name not in TEMPLATES:
        raise not_found()
    return TEMPLATES[name]


def require_template_name(name: str | None) -> str | None:
    if name is None:
        return None
    if name not in TEMPLATES:
        raise validation_failed(
            [{"field": "template", "issue": "unknown template"}]
        )
    return name


def template_files(name: str) -> dict[str, bytes]:
    item = get_template(name)
    out: dict[str, bytes] = {}
    for entry in item["files"]:
        out[entry["path"]] = entry["content_text"].encode("utf-8")
    return out
