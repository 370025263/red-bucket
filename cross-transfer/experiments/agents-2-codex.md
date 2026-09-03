# Translation Verification Experiment: agents to codex

- **Source Harness:** `agents`
- **Target Harness:** `codex`
- **Verification Level:** Phase 1 Golden-Fixture & Structural Verification
- **Execution Note:** Live harness runtime versions were not run on this host; verification is performed via unit test suite, deterministic codec test fixtures, and AST/frontmatter structure checks.

## Verification Matrix

| Asset Type | Source Format | Target Format | Structural Result | Status |
| --- | --- | --- | --- | --- |
| `skill` | `skills/{name}/SKILL.md` | `.codex/skills/{name}/SKILL.md` | Frontmatter `name`, `description` preserved; root mapped to `.codex/skills/` | PASS |
| `instructions` | `AGENTS.md` | `AGENTS.md` | Markdown body preserved verbatim | PASS |
| `plugin` | `plugins/{name}/plugin.md` | `.codex/plugins/{name}/plugin.md` | Frontmatter preserved; root mapped to `.codex/plugins/` | PASS |
| `subagent` | `agents/{name}/agent.md` | `.codex/agents/{name}/agent.md` | Frontmatter preserved; root mapped to `.codex/agents/` | PASS |
| `mcp` | `mcp/{name}.json` | N/A (unsupported) | Single fetch returns HTTP 501 `translation_unsupported`; bucket fetch skips asset | PASS |

## Test Assertions
1. Root directories mapped from root `skills/`, `plugins/`, `agents/` to `.codex/` subdirectories.
2. Frontmatter keys ordered and preserved.
3. Instructions remain in `AGENTS.md`.
4. Deterministic byte-for-byte output verified.
