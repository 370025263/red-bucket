# Cross-Transfer Specification: codex to openclaw

This document defines the translation rules, schema mappings, layout transformations, and behavioral expectations when converting `red-bucket` assets authored for the **Codex** harness into the **OpenClaw** harness format.

Experiment validation record: [cross-transfer/experiments/codex-2-openclaw.md](experiments/codex-2-openclaw.md)

---

## Asset Formats on Both Sides

| Asset Type | Source Format (`codex`) | Target Format (`openclaw`) | Supported in Phase 1 |
| --- | --- | --- | --- |
| `skill` | Markdown with YAML-like frontmatter (`SKILL.md` or `skill.md`) | Markdown with YAML-like frontmatter (`SKILL.md`) | Yes |
| `instructions` | Markdown file (`AGENTS.md`) | Markdown file (`AGENTS.md`) | Yes |
| `plugin` | Markdown frontmatter (`plugin.md`) or `plugin.json` | Markdown with YAML-like frontmatter (`plugin.md`) | Yes |
| `subagent` | Markdown frontmatter (`agent.md`, `AGENT.md`, or `subagent.md`) | Markdown with YAML-like frontmatter (`agent.md`) | Yes |
| `mcp` | TOML configuration (`{name}.toml`) | N/A | No (returns HTTP 501 `translation_unsupported`) |

---

## Field Mapping Tables

### 1. Document Assets (`skill`, `plugin`, `subagent`)

| Source Field (`codex`) | Target Field (`openclaw`) | Behavior & Fallback |
| --- | --- | --- |
| `name` (frontmatter) | `name` (frontmatter) | Direct copy. Extracted verbatim. |
| `description` (frontmatter) | `description` (frontmatter) | Direct copy. Extracted verbatim. |
| Unrecognized frontmatter keys | `## Compatibility notes` (markdown body) | Appended under notes heading in body. Sets `lossy: true`. |
| Main markdown body | Main markdown body | Preserved verbatim above compatibility notes. |
| Auxiliary files (`scripts/`, references) | Auxiliary files | Preserved verbatim and copied into target package. |

### 2. Instructions (`instructions`)

| Source Field (`codex`) | Target Field (`openclaw`) | Behavior & Fallback |
| --- | --- | --- |
| File path: `AGENTS.md` | File path: `AGENTS.md` | Preserved at workspace root. |
| Full markdown content | Full markdown content | Transferred verbatim with guaranteed trailing newline. |

### 3. MCP Servers (`mcp`)

MCP translation from `codex` to `openclaw` is **unsupported** in Phase 1:
- Direct asset requests (`GET /translated?target=openclaw`) return HTTP `501 Not Implemented` with error code `translation_unsupported`.
- Whole-bucket fetches skip the asset and record it in archive notes.

---

## Whole-Bucket Layout Mapping

When unpacking an entire bucket translated for `openclaw`, directories are mapped as follows:

| Asset Type | Source Layout (`codex`) | Target Layout (`openclaw`) |
| --- | --- | --- |
| `skill` | `.codex/skills/{name}/` | `.openclaw/skills/{name}/` |
| `plugin` | `.codex/plugins/{name}/` | `.openclaw/plugins/{name}/` |
| `subagent` | `.codex/agents/{name}/` | `.openclaw/agents/{name}/` |
| `instructions` | `AGENTS.md` | `AGENTS.md` |
| `mcp` | `.codex/mcp-servers/{name}.toml` | Skipped (unsupported) |

---

## User-Facing Migration Notes

- **Fetching via CLI:** Use `curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=openclaw" -H "Accept: text/plain" | sh` to install translated assets into OpenClaw workspace configurations (self-hosted instances use `$RED_BUCKET_URL`).
- **Prefix Isolation:** All skills, plugins, and subagents are namespaced under the `.openclaw/` directory tree.
- **Lossy Metadata:** Any unsupported frontmatter parameters are captured in `## Compatibility notes` rather than discarded.

---

## Behavioral Changes & Runtime Expectations

1. **Discovery:** OpenClaw scans `.openclaw/skills/`, `.openclaw/plugins/`, and `.openclaw/agents/` for executable extensions and subagent definitions.
2. **Instruction Context:** Root `AGENTS.md` is ingested as system prompt guidance during session initialization.
3. **MCP Non-Translation:** Any MCP tools configured under `.codex/mcp-servers/` must be manually configured in the target environment if needed.

---

## Equivalence Checklist

- [x] Frontmatter `name` and `description` retained accurately across markdown headers.
- [x] Target directory layout maps `.codex/` paths to corresponding `.openclaw/` paths.
- [x] Unmapped frontmatter keys append under `## Compatibility notes` with `lossy: true`.
- [x] Auxiliary files and references maintain relative path relationships.
- [x] MCP single-asset fetch returns HTTP 501.
