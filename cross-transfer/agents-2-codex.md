# Cross-Transfer Specification: agents to codex

This document defines the translation rules, schema mappings, layout transformations, and behavioral expectations when converting `red-bucket` assets authored for the **Agents** harness format into the **Codex** harness format.

Experiment validation record: [cross-transfer/experiments/agents-2-codex.md](experiments/agents-2-codex.md)

---

## Asset Formats on Both Sides

| Asset Type | Source Format (`agents`) | Target Format (`codex`) | Supported in Phase 1 |
| --- | --- | --- | --- |
| `skill` | Markdown with YAML-like frontmatter (`SKILL.md` or `skill.md`) | Markdown with YAML-like frontmatter (`SKILL.md`) | Yes |
| `instructions` | Markdown file (`AGENTS.md`) | Markdown file (`AGENTS.md`) | Yes |
| `plugin` | Markdown frontmatter (`plugin.md`) or `plugin.json` | Markdown with YAML-like frontmatter (`plugin.md`) | Yes |
| `subagent` | Markdown frontmatter (`agent.md`, `AGENT.md`, or `subagent.md`) | Markdown with YAML-like frontmatter (`agent.md`) | Yes |
| `mcp` | JSON configuration (`mcp/{name}.json`) | N/A | No (returns HTTP 501 `translation_unsupported`) |

---

## Field Mapping Tables

### 1. Document Assets (`skill`, `plugin`, `subagent`)

| Source Field (`agents`) | Target Field (`codex`) | Behavior & Fallback |
| --- | --- | --- |
| `name` (frontmatter) | `name` (frontmatter) | Direct copy. Extracted verbatim. |
| `description` (frontmatter) | `description` (frontmatter) | Direct copy. Extracted verbatim. |
| Unrecognized frontmatter keys | `## Compatibility notes` (markdown body) | Appended under notes heading in body. Sets `lossy: true`. |
| Main markdown body | Main markdown body | Preserved verbatim above compatibility notes. |
| Auxiliary files (`scripts/`, references) | Auxiliary files | Preserved verbatim and copied into target package. |

### 2. Instructions (`instructions`)

| Source Field (`agents`) | Target Field (`codex`) | Behavior & Fallback |
| --- | --- | --- |
| File path: `AGENTS.md` | File path: `AGENTS.md` | Preserved at workspace root. |
| Full markdown content | Full markdown content | Transferred verbatim with guaranteed trailing newline. |

### 3. MCP Servers (`mcp`)

MCP translation from `agents` to `codex` is **unsupported** in Phase 1:
- Direct asset requests (`GET /translated?target=codex`) return HTTP `501 Not Implemented` with error code `translation_unsupported`.
- Whole-bucket fetches skip the asset and record it in archive notes.

---

## Whole-Bucket Layout Mapping

When unpacking an entire bucket translated for `codex`, directories are mapped as follows:

| Asset Type | Source Layout (`agents`) | Target Layout (`codex`) |
| --- | --- | --- |
| `skill` | `skills/{name}/` | `.codex/skills/{name}/` |
| `plugin` | `plugins/{name}/` | `.codex/plugins/{name}/` |
| `subagent` | `agents/{name}/` | `.codex/agents/{name}/` |
| `instructions` | `AGENTS.md` | `AGENTS.md` |
| `mcp` | `mcp/{name}.json` | Skipped (unsupported) |

---

## User-Facing Migration Notes

- **Fetching via CLI:** Use `curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=codex" -H "Accept: text/plain" | sh` to install translated assets into a Codex project (self-hosted instances use `$RED_BUCKET_URL`).
- **Directory Encapsulation:** Visible root folders (`skills/`, `plugins/`, `agents/`) are encapsulated into the `.codex/` configuration hierarchy (`.codex/skills/`, etc.).
- **Preserved Metadata:** Unmapped frontmatter keys are appended to `## Compatibility notes` so no authoring metadata is lost during translation.

---

## Behavioral Changes & Runtime Expectations

1. **Discovery:** Codex locates skills and subagents inside `.codex/skills/` and `.codex/agents/` rather than the project root.
2. **Instruction Ingestion:** Codex loads root `AGENTS.md` as contextual rules.
3. **MCP Non-Translation:** Any MCP tools configured under `agents` must be manually configured in the target environment if needed.

---

## Equivalence Checklist

- [x] Frontmatter keys `name` and `description` are preserved.
- [x] Output markdown filenames conform to `SKILL.md`, `plugin.md`, `agent.md`, and `AGENTS.md`.
- [x] Whole-bucket archive roots target `.codex/skills/{name}`, `.codex/plugins/{name}`, and `.codex/agents/{name}`.
- [x] Auxiliary files retain their relative structure.
- [x] MCP translation is cleanly rejected with HTTP 501.
