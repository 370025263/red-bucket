# Translation Verification Experiment: codex to agents

- **Source Harness:** `codex`
- **Target Harness:** `agents`
- **Verification Level:** Phase 1 Golden-Fixture & Structural Verification
- **Execution Note:** Live harness runtime versions were not run on this host; verification is performed via unit test suite, deterministic codec test fixtures, and AST/frontmatter structure checks.

## Verification Matrix

| Asset Type | Source Format | Target Format | Structural Result | Status |
| --- | --- | --- | --- | --- |
| `skill` | `.codex/skills/{name}/SKILL.md` | `skills/{name}/SKILL.md` | Frontmatter `name`, `description` preserved; extras mapped to compatibility notes; aux files intact | PASS |
| `instructions` | `AGENTS.md` | `AGENTS.md` | Markdown body preserved verbatim with trailing newline | PASS |
| `plugin` | `.codex/plugins/{name}/plugin.md` | `plugins/{name}/plugin.md` | Frontmatter preserved, deterministic output | PASS |
| `subagent` | `.codex/agents/{name}/agent.md` | `agents/{name}/agent.md` | Frontmatter preserved; layout moved from `.codex/agents/` to `agents/` | PASS |
| `mcp` | `.codex/mcp-servers/{name}.toml` | N/A (unsupported) | Single fetch returns HTTP 501 `translation_unsupported`; bucket fetch skips asset | PASS |

## Test Assertions
1. Frontmatter parser normalizes `name` and `description` to top of target document.
2. Unmapped source keys append under `## Compatibility notes` and trigger `lossy: true`.
3. Whole-bucket layout maps `.codex/` paths to `agents/` root paths.
4. Output bytes are strictly deterministic for any given `(commit, target)`.
