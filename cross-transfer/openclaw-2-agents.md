# Cross-Transfer Specification: openclaw to agents

This document defines the translation rules, schema mappings, layout transformations, and behavioral expectations when converting `red-bucket` assets authored for the **OpenClaw** harness format into the **Agents** harness format.

Experiment validation record: [cross-transfer/experiments/openclaw-2-agents.md](experiments/openclaw-2-agents.md)

---

## Asset Formats on Both Sides

| Asset Type | Source Format (`openclaw`) | Target Format (`agents`) | Supported in Phase 1 |
| --- | --- | --- | --- |
| `skill` | Markdown with YAML-like frontmatter (`SKILL.md` or `skill.md`) | Markdown with YAML-like frontmatter (`SKILL.md`) | Yes |
| `instructions` | Markdown file (`AGENTS.md`) | Markdown file (`AGENTS.md`) | Yes |
| `plugin` | Markdown frontmatter (`plugin.md`) or `plugin.json` | Markdown with YAML-like frontmatter (`plugin.md`) | Yes |
| `subagent` | Markdown frontmatter (`agent.md`, `AGENT.md`, or `subagent.md`) | Markdown with YAML-like frontmatter (`agent.md`) | Yes |
| `mcp` | JSON configuration (`.openclaw/mcp/{name}.json`) | N/A | No (returns HTTP 501 `translation_unsupported`) |

---

## Field Mapping Tables

### 1. Document Assets (`skill`, `plugin`, `subagent`)

| Source Field (`openclaw`) | Target Field (`agents`) | Behavior & Fallback |
| --- | --- | --- |
| `name` (frontmatter) | `name` (frontmatter) | Direct copy. Extracted verbatim. |
| `description` (frontmatter) | `description` (frontmatter) | Direct copy. Extracted verbatim. |
| Unrecognized frontmatter keys | `## Compatibility notes` (markdown body) | Appended under notes heading in body. Sets `lossy: true`. |
| Main markdown body | Main markdown body | Preserved verbatim above compatibility notes. |
| Auxiliary files (`scripts/`, references) | Auxiliary files | Preserved verbatim and copied into target package. |

### 2. Instructions (`instructions`)

| Source Field (`openclaw`) | Target Field (`agents`) | Behavior & Fallback |
| --- | --- | --- |
| File path: `AGENTS.md` | File path: `AGENTS.md` | Preserved at workspace root. |
| Full markdown content | Full markdown content | Transferred verbatim with guaranteed trailing newline. |

### 3. MCP Servers (`mcp`)

MCP translation from `openclaw` to `agents` is **unsupported** in Phase 1:
- Direct asset requests (`GET /translated?target=agents`) return HTTP `501 Not Implemented` with error code `translation_unsupported`.
- Whole-bucket fetches skip the asset and record it in archive notes.

---

## Whole-Bucket Layout Mapping

When unpacking an entire bucket translated for `agents`, directories are mapped as follows:

| Asset Type | Source Layout (`openclaw`) | Target Layout (`agents`) |
| --- | --- | --- |
| `skill` | `.openclaw/skills/{name}/` | `skills/{name}/` |
| `plugin` | `.openclaw/plugins/{name}/` | `plugins/{name}/` |
| `subagent` | `.openclaw/agents/{name}/` | `agents/{name}/` |
| `instructions` | `AGENTS.md` | `AGENTS.md` |
| `mcp` | `.openclaw/mcp/{name}.json` | Skipped (unsupported) |

---

## User-Facing Migration Notes

- **Fetching via CLI:** Use `curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=agents" -H "Accept: text/plain" | sh` to install translated assets into an Agents project (self-hosted instances use `$RED_BUCKET_URL`).
- **Root Elevation:** Assets stored under `.openclaw/` are unpacked into top-level `skills/`, `plugins/`, and `agents/` directories.
- **Preserved Content:** Instructions remain in `AGENTS.md`.

---

## Behavioral Changes & Runtime Expectations

1. **Discovery:** The `agents` harness resolves skills and agents in root `skills/` and `agents/`.
2. **Instruction Ingestion:** `AGENTS.md` is loaded as system instruction text.
3. **MCP Non-Translation:** Any MCP tools configured under `openclaw` must be manually configured in the target environment if needed.

---

## Equivalence Checklist

- [x] Frontmatter metadata (`name`, `description`) is preserved accurately.
- [x] Directories map from `.openclaw/` to root folders `skills/`, `plugins/`, `agents/`.
- [x] Instructions file remains `AGENTS.md`.
- [x] Auxiliary files and references maintain relative paths.
- [x] Single-asset MCP fetch cleanly returns HTTP 501.
