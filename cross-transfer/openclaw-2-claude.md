# Cross-Transfer Specification: openclaw to claude

This document defines the translation rules, schema mappings, layout transformations, and behavioral expectations when converting `red-bucket` assets authored for the **OpenClaw** harness format into the **Claude Code** harness format.

Experiment validation record: [cross-transfer/experiments/openclaw-2-claude.md](experiments/openclaw-2-claude.md)

---

## Asset Formats on Both Sides

| Asset Type | Source Format (`openclaw`) | Target Format (`claude`) | Supported in Phase 1 |
| --- | --- | --- | --- |
| `skill` | Markdown with YAML-like frontmatter (`SKILL.md` or `skill.md`) | Markdown with YAML-like frontmatter (`SKILL.md`) | Yes |
| `instructions` | Markdown file (`AGENTS.md`) | Markdown file (`CLAUDE.md`) | Yes |
| `plugin` | Markdown frontmatter (`plugin.md`) or `plugin.json` | Markdown with YAML-like frontmatter (`plugin.md`) | Yes |
| `subagent` | Markdown frontmatter (`agent.md`, `AGENT.md`, or `subagent.md`) | Markdown with YAML-like frontmatter (`agent.md`) | Yes |
| `mcp` | JSON configuration (`.openclaw/mcp/{name}.json`) | N/A | No (returns HTTP 501 `translation_unsupported`) |

---

## Field Mapping Tables

### 1. Document Assets (`skill`, `plugin`, `subagent`)

| Source Field (`openclaw`) | Target Field (`claude`) | Behavior & Fallback |
| --- | --- | --- |
| `name` (frontmatter) | `name` (frontmatter) | Direct copy. Extracted verbatim. |
| `description` (frontmatter) | `description` (frontmatter) | Direct copy. Extracted verbatim. |
| Unrecognized frontmatter keys | `## Compatibility notes` (markdown body) | Appended under notes heading in body. Sets `lossy: true`. |
| Main markdown body | Main markdown body | Preserved verbatim above compatibility notes. |
| Auxiliary files (`scripts/`, references) | Auxiliary files | Preserved verbatim and copied into target package. |

### 2. Instructions (`instructions`)

| Source Field (`openclaw`) | Target Field (`claude`) | Behavior & Fallback |
| --- | --- | --- |
| File path: `AGENTS.md` | File path: `CLAUDE.md` | Renamed to standard `CLAUDE.md`. |
| Full markdown content | Full markdown content | Transferred verbatim with guaranteed trailing newline. |

### 3. MCP Servers (`mcp`)

MCP translation from `openclaw` to `claude` is **unsupported** in Phase 1:
- Direct asset requests (`GET /translated?target=claude`) return HTTP `501 Not Implemented` with error code `translation_unsupported`.
- Whole-bucket fetches skip the asset and record it in archive notes.

---

## Whole-Bucket Layout Mapping

When unpacking an entire bucket translated for `claude`, directories are mapped as follows:

| Asset Type | Source Layout (`openclaw`) | Target Layout (`claude`) |
| --- | --- | --- |
| `skill` | `.openclaw/skills/{name}/` | `skills/{name}/` |
| `plugin` | `.openclaw/plugins/{name}/` | `plugins/{name}/` |
| `subagent` | `.openclaw/agents/{name}/` | `.claude/agents/{name}/` |
| `instructions` | `AGENTS.md` | `CLAUDE.md` |
| `mcp` | `.openclaw/mcp/{name}.json` | Skipped (unsupported) |

---

## User-Facing Migration Notes

- **Fetching via CLI:** Use `curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=claude" -H "Accept: text/plain" | sh` to install translated assets into Claude Code (self-hosted instances use `$RED_BUCKET_URL`).
- **Instruction Renaming:** `AGENTS.md` is converted to `CLAUDE.md`.
- **Subagent Relocation:** Subagents move from `.openclaw/agents/{name}/` into `.claude/agents/{name}/`.

---

## Behavioral Changes & Runtime Expectations

1. **Instruction Ingestion:** Claude Code reads system prompt instructions from `CLAUDE.md`.
2. **Subagent Scoping:** Subagents under `.claude/agents/` are picked up by Claude Code subagent routing.
3. **MCP Non-Translation:** Any MCP tools configured under `openclaw` must be manually configured in the target environment if needed.

---

## Equivalence Checklist

- [x] Frontmatter metadata (`name`, `description`) is preserved accurately.
- [x] Instructions filename is converted to `CLAUDE.md`.
- [x] Subagents relocate to `.claude/agents/{name}/agent.md`.
- [x] Auxiliary files and references maintain relative paths.
- [x] Single-asset MCP fetch cleanly returns HTTP 501.
