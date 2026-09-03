# Cross-Transfer Specification: claude to openclaw

This document defines the translation rules, schema mappings, layout transformations, and behavioral expectations when converting `red-bucket` assets authored for the **Claude Code** harness into the **OpenClaw** harness format.

Experiment validation record: [cross-transfer/experiments/claude-2-openclaw.md](experiments/claude-2-openclaw.md)

---

## Asset Formats on Both Sides

| Asset Type | Source Format (`claude`) | Target Format (`openclaw`) | Supported in Phase 1 |
| --- | --- | --- | --- |
| `skill` | Markdown with YAML-like frontmatter (`SKILL.md` or `skill.md`) | Markdown with YAML-like frontmatter (`SKILL.md`) | Yes |
| `instructions` | Markdown file (`CLAUDE.md`) | Markdown file (`AGENTS.md`) | Yes |
| `plugin` | Markdown frontmatter (`plugin.md`) or `plugin.json` | Markdown with YAML-like frontmatter (`plugin.md`) | Yes |
| `subagent` | Markdown frontmatter (`agent.md`, `AGENT.md`, or `subagent.md`) | Markdown with YAML-like frontmatter (`agent.md`) | Yes |
| `mcp` | JSON configuration (`.mcp.json`) | N/A | No (returns HTTP 501 `translation_unsupported`) |

---

## Field Mapping Tables

### 1. Document Assets (`skill`, `plugin`, `subagent`)

| Source Field (`claude`) | Target Field (`openclaw`) | Behavior & Fallback |
| --- | --- | --- |
| `name` (frontmatter) | `name` (frontmatter) | Direct copy. Extracted verbatim. |
| `description` (frontmatter) | `description` (frontmatter) | Direct copy. Extracted verbatim. |
| Unrecognized frontmatter keys | `## Compatibility notes` (markdown body) | Appended under notes heading in body. Sets `lossy: true`. |
| Main markdown body | Main markdown body | Preserved verbatim above compatibility notes. |
| Auxiliary files (`scripts/`, references) | Auxiliary files | Preserved verbatim and copied into target package. |

### 2. Instructions (`instructions`)

| Source Field (`claude`) | Target Field (`openclaw`) | Behavior & Fallback |
| --- | --- | --- |
| File path: `CLAUDE.md` | File path: `AGENTS.md` | Renamed to standard `AGENTS.md`. |
| Full markdown content | Full markdown content | Transferred verbatim with guaranteed trailing newline. |

### 3. MCP Servers (`mcp`)

MCP translation from `claude` to `openclaw` is **unsupported** in Phase 1:
- Direct asset requests (`GET /translated?target=openclaw`) return HTTP `501 Not Implemented` with error code `translation_unsupported`.
- Whole-bucket fetches skip the asset and record it in archive notes.

---

## Whole-Bucket Layout Mapping

When unpacking an entire bucket translated for `openclaw`, directories are mapped as follows:

| Asset Type | Source Layout (`claude`) | Target Layout (`openclaw`) |
| --- | --- | --- |
| `skill` | `skills/{name}/` | `.openclaw/skills/{name}/` |
| `plugin` | `plugins/{name}/` | `.openclaw/plugins/{name}/` |
| `subagent` | `.claude/agents/{name}/` | `.openclaw/agents/{name}/` |
| `instructions` | `CLAUDE.md` | `AGENTS.md` |
| `mcp` | `.mcp.json` | Skipped (unsupported) |

---

## User-Facing Migration Notes

- **Fetching via CLI:** Use `curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=openclaw" -H "Accept: text/plain" | sh` to install translated assets into OpenClaw (self-hosted instances use `$RED_BUCKET_URL`).
- **Prefix Namespacing:** Skills, plugins, and subagents are relocated under `.openclaw/`.
- **Instruction Renaming:** `CLAUDE.md` is converted to root `AGENTS.md`.

---

## Behavioral Changes & Runtime Expectations

1. **Discovery:** OpenClaw scans `.openclaw/skills/`, `.openclaw/plugins/`, and `.openclaw/agents/` for executable extensions and subagent definitions.
2. **Instruction Ingestion:** `AGENTS.md` is read on session initialization.
3. **MCP Non-Translation:** Any MCP tools configured under `claude` must be manually configured in the target environment if needed.

---

## Equivalence Checklist

- [x] Frontmatter keys `name` and `description` are preserved.
- [x] Instructions filename is converted to `AGENTS.md`.
- [x] Target directory layout maps to `.openclaw/` subdirectories.
- [x] Auxiliary files retain their relative structure.
- [x] Single-asset MCP fetch cleanly returns HTTP 501.
