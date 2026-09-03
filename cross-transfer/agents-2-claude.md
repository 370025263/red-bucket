# Cross-Transfer Specification: agents to claude

This document defines the translation rules, schema mappings, layout transformations, and behavioral expectations when converting `red-bucket` assets authored for the **Agents** harness format into the **Claude Code** harness format.

Experiment validation record: [cross-transfer/experiments/agents-2-claude.md](experiments/agents-2-claude.md)

---

## Asset Formats on Both Sides

| Asset Type | Source Format (`agents`) | Target Format (`claude`) | Supported in Phase 1 |
| --- | --- | --- | --- |
| `skill` | Markdown with YAML-like frontmatter (`SKILL.md` or `skill.md`) | Markdown with YAML-like frontmatter (`SKILL.md`) | Yes |
| `instructions` | Markdown file (`AGENTS.md`) | Markdown file (`CLAUDE.md`) | Yes |
| `plugin` | Markdown frontmatter (`plugin.md`) or `plugin.json` | Markdown with YAML-like frontmatter (`plugin.md`) | Yes |
| `subagent` | Markdown frontmatter (`agent.md`, `AGENT.md`, or `subagent.md`) | Markdown with YAML-like frontmatter (`agent.md`) | Yes |
| `mcp` | JSON configuration (`mcp/{name}.json`) | N/A | No (returns HTTP 501 `translation_unsupported`) |

---

## Field Mapping Tables

### 1. Document Assets (`skill`, `plugin`, `subagent`)

| Source Field (`agents`) | Target Field (`claude`) | Behavior & Fallback |
| --- | --- | --- |
| `name` (frontmatter) | `name` (frontmatter) | Direct copy. Extracted verbatim. |
| `description` (frontmatter) | `description` (frontmatter) | Direct copy. Extracted verbatim. |
| Unrecognized frontmatter keys | `## Compatibility notes` (markdown body) | Appended under notes heading in body. Sets `lossy: true`. |
| Main markdown body | Main markdown body | Preserved verbatim above compatibility notes. |
| Auxiliary files (`scripts/`, references) | Auxiliary files | Preserved verbatim and copied into target package. |

### 2. Instructions (`instructions`)

| Source Field (`agents`) | Target Field (`claude`) | Behavior & Fallback |
| --- | --- | --- |
| File path: `AGENTS.md` | File path: `CLAUDE.md` | Renamed to Claude Code standard instruction file. |
| Full markdown content | Full markdown content | Transferred verbatim with guaranteed trailing newline. |

### 3. MCP Servers (`mcp`)

MCP translation from `agents` to `claude` is **unsupported** in Phase 1:
- Direct asset requests (`GET /translated?target=claude`) return HTTP `501 Not Implemented` with error code `translation_unsupported`.
- Whole-bucket fetches skip the asset and record it in archive notes.

---

## Whole-Bucket Layout Mapping

When unpacking an entire bucket translated for `claude`, directories are mapped as follows:

| Asset Type | Source Layout (`agents`) | Target Layout (`claude`) |
| --- | --- | --- |
| `skill` | `skills/{name}/` | `skills/{name}/` |
| `plugin` | `plugins/{name}/` | `plugins/{name}/` |
| `subagent` | `agents/{name}/` | `.claude/agents/{name}/` |
| `instructions` | `AGENTS.md` | `CLAUDE.md` |
| `mcp` | `mcp/{name}.json` | Skipped (unsupported) |

---

## User-Facing Migration Notes

- **Fetching via CLI:** Use `curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=claude" -H "Accept: text/plain" | sh` to install translated assets into Claude Code (self-hosted instances use `$RED_BUCKET_URL`).
- **Instruction Renaming:** System instructions authored as `AGENTS.md` are converted to `CLAUDE.md`.
- **Subagent Relocation:** Subagents from `agents/{name}/` are moved to `.claude/agents/{name}/`.

---

## Behavioral Changes & Runtime Expectations

1. **Instruction Ingestion:** Claude Code reads system prompt instructions from `CLAUDE.md`.
2. **Subagent Delegation:** Subagents placed in `.claude/agents/{name}/` are discoverable by Claude Code subagent delegators.
3. **MCP Non-Translation:** Any MCP tools configured under `agents` must be manually configured in the target environment if needed.

---

## Equivalence Checklist

- [x] Frontmatter keys `name` and `description` are preserved.
- [x] Instructions file is renamed to `CLAUDE.md` without dropping markdown body text.
- [x] Subagents relocate to `.claude/agents/{name}/agent.md`.
- [x] Auxiliary files and folders are retained.
- [x] Single-asset MCP fetch cleanly returns HTTP 501.
