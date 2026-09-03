# Cross-Transfer Specification: agents to openclaw

This document defines the translation rules, schema mappings, layout transformations, and behavioral expectations when converting `red-bucket` assets authored for the **Agents** harness format into the **OpenClaw** harness format.

Experiment validation record: [cross-transfer/experiments/agents-2-openclaw.md](experiments/agents-2-openclaw.md)

---

## Asset Formats on Both Sides

| Asset Type | Source Format (`agents`) | Target Format (`openclaw`) | Supported in Phase 1 |
| --- | --- | --- | --- |
| `skill` | Markdown with YAML-like frontmatter (`SKILL.md` or `skill.md`) | Markdown with YAML-like frontmatter (`SKILL.md`) | Yes |
| `instructions` | Markdown file (`AGENTS.md`) | Markdown file (`AGENTS.md`) | Yes |
| `plugin` | Markdown frontmatter (`plugin.md`) or `plugin.json` | Markdown with YAML-like frontmatter (`plugin.md`) | Yes |
| `subagent` | Markdown frontmatter (`agent.md`, `AGENT.md`, or `subagent.md`) | Markdown with YAML-like frontmatter (`agent.md`) | Yes |
| `mcp` | JSON configuration (`mcp/{name}.json`) | N/A | No (returns HTTP 501 `translation_unsupported`) |

---

## Field Mapping Tables

### 1. Document Assets (`skill`, `plugin`, `subagent`)

| Source Field (`agents`) | Target Field (`openclaw`) | Behavior & Fallback |
| --- | --- | --- |
| `name` (frontmatter) | `name` (frontmatter) | Direct copy. Extracted verbatim. |
| `description` (frontmatter) | `description` (frontmatter) | Direct copy. Extracted verbatim. |
| Unrecognized frontmatter keys | `## Compatibility notes` (markdown body) | Appended under notes heading in body. Sets `lossy: true`. |
| Main markdown body | Main markdown body | Preserved verbatim above compatibility notes. |
| Auxiliary files (`scripts/`, references) | Auxiliary files | Preserved verbatim and copied into target package. |

### 2. Instructions (`instructions`)

| Source Field (`agents`) | Target Field (`openclaw`) | Behavior & Fallback |
| --- | --- | --- |
| File path: `AGENTS.md` | File path: `AGENTS.md` | Preserved at workspace root. |
| Full markdown content | Full markdown content | Transferred verbatim with guaranteed trailing newline. |

### 3. MCP Servers (`mcp`)

MCP translation from `agents` to `openclaw` is **unsupported** in Phase 1:
- Direct asset requests (`GET /translated?target=openclaw`) return HTTP `501 Not Implemented` with error code `translation_unsupported`.
- Whole-bucket fetches skip the asset and record it in archive notes.

---

## Whole-Bucket Layout Mapping

When unpacking an entire bucket translated for `openclaw`, directories are mapped as follows:

| Asset Type | Source Layout (`agents`) | Target Layout (`openclaw`) |
| --- | --- | --- |
| `skill` | `skills/{name}/` | `.openclaw/skills/{name}/` |
| `plugin` | `plugins/{name}/` | `.openclaw/plugins/{name}/` |
| `subagent` | `agents/{name}/` | `.openclaw/agents/{name}/` |
| `instructions` | `AGENTS.md` | `AGENTS.md` |
| `mcp` | `mcp/{name}.json` | Skipped (unsupported) |

---

## User-Facing Migration Notes

- **Fetching via CLI:** Use `curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=openclaw" -H "Accept: text/plain" | sh` to install translated assets into OpenClaw (self-hosted instances use `$RED_BUCKET_URL`).
- **Path Encapsulation:** Root directory assets (`skills/`, `plugins/`, `agents/`) are encapsulated within `.openclaw/`.
- **Instruction Retention:** System instructions remain in root `AGENTS.md`.

---

## Behavioral Changes & Runtime Expectations

1. **Discovery:** OpenClaw inspects `.openclaw/skills/`, `.openclaw/plugins/`, and `.openclaw/agents/` for executable extensions and subagent definitions.
2. **Context Ingestion:** `AGENTS.md` is loaded at session start.
3. **MCP Non-Translation:** Any MCP tools configured under `agents` must be manually configured in the target environment if needed.

---

## Equivalence Checklist

- [x] Frontmatter metadata (`name`, `description`) is preserved accurately.
- [x] Directories are encapsulated into `.openclaw/` subdirectories.
- [x] Unmapped frontmatter keys are stored in `## Compatibility notes`.
- [x] Auxiliary files and references maintain relative paths.
- [x] Single-asset MCP fetch returns HTTP 501.
