# Cross-Transfer Specification: claude to agents

This document defines the translation rules, schema mappings, layout transformations, and behavioral expectations when converting `red-bucket` assets authored for the **Claude Code** harness into the **Agents** harness format.

Experiment validation record: [cross-transfer/experiments/claude-2-agents.md](experiments/claude-2-agents.md)

---

## Asset Formats on Both Sides

| Asset Type | Source Format (`claude`) | Target Format (`agents`) | Supported in Phase 1 |
| --- | --- | --- | --- |
| `skill` | Markdown with YAML-like frontmatter (`SKILL.md` or `skill.md`) | Markdown with YAML-like frontmatter (`SKILL.md`) | Yes |
| `instructions` | Markdown file (`CLAUDE.md`) | Markdown file (`AGENTS.md`) | Yes |
| `plugin` | Markdown frontmatter (`plugin.md`) or `plugin.json` | Markdown with YAML-like frontmatter (`plugin.md`) | Yes |
| `subagent` | Markdown frontmatter (`agent.md`, `AGENT.md`, or `subagent.md`) | Markdown with YAML-like frontmatter (`agent.md`) | Yes |
| `mcp` | JSON configuration (`.mcp.json`) | N/A | No (returns HTTP 501 `translation_unsupported`) |

---

## Field Mapping Tables

### 1. Document Assets (`skill`, `plugin`, `subagent`)

| Source Field (`claude`) | Target Field (`agents`) | Behavior & Fallback |
| --- | --- | --- |
| `name` (frontmatter) | `name` (frontmatter) | Direct copy. Extracted verbatim. |
| `description` (frontmatter) | `description` (frontmatter) | Direct copy. Extracted verbatim. |
| Unrecognized frontmatter keys | `## Compatibility notes` (markdown body) | Appended under notes heading in body. Sets `lossy: true`. |
| Main markdown body | Main markdown body | Preserved verbatim above compatibility notes. |
| Auxiliary files (`scripts/`, references) | Auxiliary files | Preserved verbatim and copied into target package. |

### 2. Instructions (`instructions`)

| Source Field (`claude`) | Target Field (`agents`) | Behavior & Fallback |
| --- | --- | --- |
| File path: `CLAUDE.md` | File path: `AGENTS.md` | Renamed to standard `AGENTS.md`. |
| Full markdown content | Full markdown content | Transferred verbatim with guaranteed trailing newline. |

### 3. MCP Servers (`mcp`)

MCP translation from `claude` to `agents` is **unsupported** in Phase 1:
- Direct asset requests (`GET /translated?target=agents`) return HTTP `501 Not Implemented` with error code `translation_unsupported`.
- Whole-bucket fetches skip the asset and record it in archive notes.

---

## Whole-Bucket Layout Mapping

When unpacking an entire bucket translated for `agents`, directories are mapped as follows:

| Asset Type | Source Layout (`claude`) | Target Layout (`agents`) |
| --- | --- | --- |
| `skill` | `skills/{name}/` | `skills/{name}/` |
| `plugin` | `plugins/{name}/` | `plugins/{name}/` |
| `subagent` | `.claude/agents/{name}/` | `agents/{name}/` |
| `instructions` | `CLAUDE.md` | `AGENTS.md` |
| `mcp` | `.mcp.json` | Skipped (unsupported) |

---

## User-Facing Migration Notes

- **Fetching via CLI:** Use `curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=agents" -H "Accept: text/plain" | sh` to install translated assets into an Agents project (self-hosted instances use `$RED_BUCKET_URL`).
- **Instruction Conversion:** `CLAUDE.md` is renamed to `AGENTS.md`.
- **Subagent Un-nesting:** Subagents in `.claude/agents/{name}/` are un-nested into top-level `agents/{name}/`.

---

## Behavioral Changes & Runtime Expectations

1. **Instruction Loading:** The `agents` harness reads project instructions from `AGENTS.md`.
2. **Subagent Resolution:** Subagents are discovered from `agents/{name}/agent.md`.
3. **MCP Non-Translation:** Any MCP tools configured under `claude` must be manually configured in the target environment if needed.

---

## Equivalence Checklist

- [x] Frontmatter metadata (`name`, `description`) is preserved accurately.
- [x] Instructions filename is converted to `AGENTS.md`.
- [x] Subagents move to `agents/{name}/agent.md`.
- [x] Auxiliary files and references are preserved.
- [x] Single-asset MCP fetch returns HTTP 501.
