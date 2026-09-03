# Cross-Transfer Specification: codex to claude

This document defines the translation rules, schema mappings, layout transformations, and behavioral expectations when converting `red-bucket` assets authored for the **Codex** harness into the **Claude Code** harness format.

Experiment validation record: [cross-transfer/experiments/codex-2-claude.md](experiments/codex-2-claude.md)

---

## Asset Formats on Both Sides

| Asset Type | Source Format (`codex`) | Target Format (`claude`) | Supported in Phase 1 |
| --- | --- | --- | --- |
| `skill` | Markdown with YAML-like frontmatter (`SKILL.md` or `skill.md`) | Markdown with YAML-like frontmatter (`SKILL.md`) | Yes |
| `instructions` | Markdown file (`AGENTS.md`) | Markdown file (`CLAUDE.md`) | Yes |
| `plugin` | Markdown frontmatter (`plugin.md`) or `plugin.json` | Markdown with YAML-like frontmatter (`plugin.md`) | Yes |
| `subagent` | Markdown frontmatter (`agent.md`, `AGENT.md`, or `subagent.md`) | Markdown with YAML-like frontmatter (`agent.md`) | Yes |
| `mcp` | TOML configuration (`{name}.toml`) | JSON configuration (`.mcp.json`) | Yes |

---

## Field Mapping Tables

### 1. Document Assets (`skill`, `plugin`, `subagent`)

| Source Field (`codex`) | Target Field (`claude`) | Behavior & Fallback |
| --- | --- | --- |
| `name` (frontmatter) | `name` (frontmatter) | Direct copy. Extracted verbatim. |
| `description` (frontmatter) | `description` (frontmatter) | Direct copy. Extracted verbatim. |
| Unrecognized frontmatter keys | `## Compatibility notes` (markdown body) | Appended under notes heading in body. Sets `lossy: true`. |
| Main markdown body | Main markdown body | Preserved verbatim above compatibility notes. |
| Auxiliary files (`scripts/`, references) | Auxiliary files | Preserved verbatim and copied into target package. |

### 2. Instructions (`instructions`)

| Source Field (`codex`) | Target Field (`claude`) | Behavior & Fallback |
| --- | --- | --- |
| File path: `AGENTS.md` | File path: `CLAUDE.md` | Renamed to standard Claude Code instruction file. |
| Full markdown content | Full markdown content | Transferred verbatim with guaranteed trailing newline. |

### 3. MCP Servers (`mcp`)

| Source Field (`codex` TOML) | Target Field (`claude` JSON) | Behavior & Fallback |
| --- | --- | --- |
| `name = "..."` | `mcpServers.<name>` | Top-level server entry key in JSON. |
| `command = "..."` | `mcpServers.<name>.command` | Command binary or executable path. |
| `transport = "..."` | `mcpServers.<name>.transport` | Transport protocol string (`stdio` or `http`). Defaults to `http` if `url` is set, otherwise `stdio`. |
| `args = [...]` | `mcpServers.<name>.args` | Array of command-line argument strings. |
| `url = "..."` | `mcpServers.<name>.url` | Remote endpoint URL string (if present). |
| Extra table keys | Response notes / unmapped | Serialized into warning notes. Sets `lossy: true`. |

---

## Whole-Bucket Layout Mapping

When unpacking an entire bucket translated for `claude`, directories are mapped as follows:

| Asset Type | Source Layout (`codex`) | Target Layout (`claude`) |
| --- | --- | --- |
| `skill` | `.codex/skills/{name}/` | `skills/{name}/` |
| `plugin` | `.codex/plugins/{name}/` | `plugins/{name}/` |
| `subagent` | `.codex/agents/{name}/` | `.claude/agents/{name}/` |
| `instructions` | `AGENTS.md` | `CLAUDE.md` |
| `mcp` | `.codex/mcp-servers/{name}.toml` | `.mcp.json` (root level) |

---

## User-Facing Migration Notes

- **Fetching via CLI:** Use `curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=claude" -H "Accept: text/plain" | sh` to install translated assets into a Claude Code project (self-hosted instances use `$RED_BUCKET_URL`).
- **Instruction Renaming:** Project instructions authored as `AGENTS.md` are automatically materialized as `CLAUDE.md` at root.
- **MCP Conversion:** Standalone `{name}.toml` server definitions in Codex are consolidated into Claude's `.mcp.json` format.
- **Subagent Relocation:** Subagents are placed inside `.claude/agents/{name}/agent.md` so Claude Code subagent routing recognizes them.

---

## Behavioral Changes & Runtime Expectations

1. **Instruction Loading:** Claude Code reads system prompt instructions from `CLAUDE.md` instead of `AGENTS.md`.
2. **MCP Tool Invocation:** Server transport and command invocations defined in `.mcp.json` run via Claude Code's native MCP client.
3. **Subagent Scoping:** Subagents under `.claude/agents/` are picked up by Claude Code subagent delegators.

---

## Equivalence Checklist

- [x] Primary frontmatter fields `name` and `description` are preserved in `SKILL.md`, `plugin.md`, and `agent.md`.
- [x] Instructions file is renamed to `CLAUDE.md` with complete markdown content intact.
- [x] MCP configurations correctly translate from TOML tables to `.mcp.json` structure.
- [x] Subagents are placed in `.claude/agents/{name}/`.
- [x] Unmapped fields are collected under `## Compatibility notes` and flagged as lossy.
- [x] Output is deterministic and cacheable by `(commit, target)`.
