# Cross-Transfer Specification: codex to agents

This document defines the translation rules, schema mappings, layout transformations, and behavioral expectations when converting `red-bucket` assets authored for the **Codex** harness into the **Agents** harness format.

Experiment validation record: [cross-transfer/experiments/codex-2-agents.md](experiments/codex-2-agents.md)

---

## Asset Formats on Both Sides

| Asset Type | Source Format (`codex`) | Target Format (`agents`) | Supported in Phase 1 |
| --- | --- | --- | --- |
| `skill` | Markdown with YAML-like frontmatter (`SKILL.md` or `skill.md`) | Markdown with YAML-like frontmatter (`SKILL.md`) | Yes |
| `instructions` | Markdown file (`AGENTS.md`) | Markdown file (`AGENTS.md`) | Yes |
| `plugin` | Markdown frontmatter (`plugin.md`) or `plugin.json` | Markdown with YAML-like frontmatter (`plugin.md`) | Yes |
| `subagent` | Markdown frontmatter (`agent.md`, `AGENT.md`, or `subagent.md`) | Markdown with YAML-like frontmatter (`agent.md`) | Yes |
| `mcp` | TOML configuration (`{name}.toml`) | N/A | No (returns HTTP 501 `translation_unsupported`) |

---

## Field Mapping Tables

### 1. Document Assets (`skill`, `plugin`, `subagent`)

| Source Field (`codex`) | Target Field (`agents`) | Behavior & Fallback |
| --- | --- | --- |
| `name` (frontmatter) | `name` (frontmatter) | Direct copy. Extracted verbatim. |
| `description` (frontmatter) | `description` (frontmatter) | Direct copy. Extracted verbatim. |
| Unrecognized frontmatter keys | `## Compatibility notes` (markdown body) | Appended under notes heading in body. Sets `lossy: true`. |
| Main markdown body | Main markdown body | Preserved verbatim above compatibility notes. |
| Auxiliary files (`scripts/`, references) | Auxiliary files | Preserved verbatim and copied into target package. |

### 2. Instructions (`instructions`)

| Source Field (`codex`) | Target Field (`agents`) | Behavior & Fallback |
| --- | --- | --- |
| File path: `AGENTS.md` | File path: `AGENTS.md` | Retains filename at workspace root. |
| Full markdown content | Full markdown content | Transferred verbatim with guaranteed trailing newline. |

### 3. MCP Servers (`mcp`)

MCP translation from `codex` to `agents` is **unsupported** in Phase 1:
- Direct asset requests (`GET /translated?target=agents`) return HTTP `501 Not Implemented` with error code `translation_unsupported`.
- Whole-bucket fetches skip the asset and record it in archive notes.

---

## Whole-Bucket Layout Mapping

When unpacking an entire bucket translated for `agents`, directories are mapped as follows:

| Asset Type | Source Layout (`codex`) | Target Layout (`agents`) |
| --- | --- | --- |
| `skill` | `.codex/skills/{name}/` | `skills/{name}/` |
| `plugin` | `.codex/plugins/{name}/` | `plugins/{name}/` |
| `subagent` | `.codex/agents/{name}/` | `agents/{name}/` |
| `instructions` | `AGENTS.md` | `AGENTS.md` |
| `mcp` | `.codex/mcp-servers/{name}.toml` | Skipped (unsupported) |

---

## User-Facing Migration Notes

- **Fetching via CLI:** Use `curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=agents" -H "Accept: text/plain" | sh` to unpack translated bucket contents directly into standard agent directories (self-hosted instances use `$RED_BUCKET_URL`).
- **Directory Flattening:** Hidden dot-folder paths like `.codex/skills/` are relocated into top-level `skills/` and `agents/` directories expected by the `agents` harness.
- **Lossy Metadata:** Any custom Codex execution hints not covered by standard `name` and `description` frontmatter are placed in the `## Compatibility notes` section of the resulting markdown file.

---

## Behavioral Changes & Runtime Expectations

1. **Discovery:** The `agents` harness searches for skills and agents in the top-level `skills/` and `agents/` directories rather than inside `.codex/`.
2. **Execution Context:** Subagent markdown files named `agent.md` are loaded by the `agents` runtime using their frontmatter description as system invocation context.
3. **MCP Non-Translation:** Any MCP tools configured under `.codex/mcp-servers/` must be manually configured in the target environment if needed.

---

## Equivalence Checklist

- [x] Primary frontmatter fields `name` and `description` match source definitions.
- [x] Target main file names conform to `SKILL.md`, `plugin.md`, `agent.md`, and `AGENTS.md`.
- [x] Unmapped frontmatter keys are preserved in `## Compatibility notes` without silent data drop.
- [x] All auxiliary helper scripts, prompts, and templates are retained in the asset bundle.
- [x] Whole-bucket archive roots target `skills/{name}`, `plugins/{name}`, `agents/{name}`.
- [x] Single-asset MCP fetch explicitly fails with HTTP 501.
