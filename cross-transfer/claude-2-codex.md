# Cross-Transfer Specification: claude to codex

This document defines the translation rules, schema mappings, layout transformations, and behavioral expectations when converting `red-bucket` assets authored for the **Claude Code** harness into the **Codex** harness format.

Experiment validation record: [cross-transfer/experiments/claude-2-codex.md](experiments/claude-2-codex.md)

---

## Asset Formats on Both Sides

| Asset Type | Source Format (`claude`) | Target Format (`codex`) | Supported in Phase 1 |
| --- | --- | --- | --- |
| `skill` | Markdown with YAML-like frontmatter (`SKILL.md` or `skill.md`) | Markdown with YAML-like frontmatter (`SKILL.md`) | Yes |
| `instructions` | Markdown file (`CLAUDE.md`) | Markdown file (`AGENTS.md`) | Yes |
| `plugin` | Markdown frontmatter (`plugin.md`) or `plugin.json` | Markdown with YAML-like frontmatter (`plugin.md`) | Yes |
| `subagent` | Markdown frontmatter (`agent.md`, `AGENT.md`, or `subagent.md`) | Markdown with YAML-like frontmatter (`agent.md`) | Yes |
| `mcp` | JSON configuration (`.mcp.json`) | TOML configuration (`{name}.toml`) | Yes |

---

## Field Mapping Tables

### 1. Document Assets (`skill`, `plugin`, `subagent`)

| Source Field (`claude`) | Target Field (`codex`) | Behavior & Fallback |
| --- | --- | --- |
| `name` (frontmatter) | `name` (frontmatter) | Direct copy. Extracted verbatim. |
| `description` (frontmatter) | `description` (frontmatter) | Direct copy. Extracted verbatim. |
| Unrecognized frontmatter keys | `## Compatibility notes` (markdown body) | Appended under notes heading in body. Sets `lossy: true`. |
| Main markdown body | Main markdown body | Preserved verbatim above compatibility notes. |
| Auxiliary files (`scripts/`, references) | Auxiliary files | Preserved verbatim and copied into target package. |

### 2. Instructions (`instructions`)

| Source Field (`claude`) | Target Field (`codex`) | Behavior & Fallback |
| --- | --- | --- |
| File path: `CLAUDE.md` | File path: `AGENTS.md` | Renamed from Claude instruction file to standard `AGENTS.md`. |
| Full markdown content | Full markdown content | Transferred verbatim with guaranteed trailing newline. |

### 3. MCP Servers (`mcp`)

| Source Field (`claude` JSON) | Target Field (`codex` TOML) | Behavior & Fallback |
| --- | --- | --- |
| `mcpServers.<name>` key | `name = "<name>"` & filename `{name}.toml` | Top-level server entry name and target TOML filename. |
| `command` | `command = "..."` | Command binary or executable path. |
| `transport` | `transport = "..."` | Transport protocol string (`stdio` or `http`). Defaults to `http` if `url` is set, otherwise `stdio`. |
| `args` | `args = [...]` | Array of command-line argument strings. |
| `url` | `url = "..."` | Remote endpoint URL string. |
| Extra keys in server object | Response notes / unmapped | Serialized into warning notes. Sets `lossy: true`. |

---

## Whole-Bucket Layout Mapping

When unpacking an entire bucket translated for `codex`, directories are mapped as follows:

| Asset Type | Source Layout (`claude`) | Target Layout (`codex`) |
| --- | --- | --- |
| `skill` | `skills/{name}/` | `.codex/skills/{name}/` |
| `plugin` | `plugins/{name}/` | `.codex/plugins/{name}/` |
| `subagent` | `.claude/agents/{name}/` | `.codex/agents/{name}/` |
| `instructions` | `CLAUDE.md` | `AGENTS.md` |
| `mcp` | `.mcp.json` | `.codex/mcp-servers/{name}.toml` |

---

## User-Facing Migration Notes

- **Fetching via CLI:** Use `curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=codex" -H "Accept: text/plain" | sh` to install translated assets into a Codex project (self-hosted instances use `$RED_BUCKET_URL`).
- **Instruction Renaming:** `CLAUDE.md` is converted to `AGENTS.md`.
- **MCP Conversion:** `.mcp.json` server definitions are split into individual `.codex/mcp-servers/{name}.toml` configurations.
- **Subagent Path:** `.claude/agents/{name}/agent.md` is relocated to `.codex/agents/{name}/agent.md`.

---

## Behavioral Changes & Runtime Expectations

1. **Instruction Ingestion:** Codex loads instructions from `AGENTS.md` rather than `CLAUDE.md`.
2. **MCP Tool Ingestion:** Codex reads individual TOML files inside `.codex/mcp-servers/`.
3. **Subagent Execution:** Codex looks for subagents under `.codex/agents/`.

---

## Equivalence Checklist

- [x] Frontmatter keys `name` and `description` are preserved.
- [x] Instructions file is renamed to `AGENTS.md` with complete markdown content intact.
- [x] `.mcp.json` accurately translates to Codex `{name}.toml` format.
- [x] Subagents relocate to `.codex/agents/{name}/agent.md`.
- [x] Unmapped fields are placed under `## Compatibility notes`.
- [x] Output is deterministic and cacheable by `(commit, target)`.
