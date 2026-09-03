# Translation Verification Experiment: codex to openclaw

- **Source Harness:** `codex`
- **Target Harness:** `openclaw`
- **Verification Level:** Phase 1 Golden-Fixture & Structural Verification
- **Execution Note:** Live harness runtime versions were not run on this host; verification is performed via unit test suite, deterministic codec test fixtures, and AST/frontmatter structure checks.

## Verification Matrix

| Asset Type | Source Format | Target Format | Structural Result | Status |
| --- | --- | --- | --- | --- |
| `skill` | `.codex/skills/{name}/SKILL.md` | `.openclaw/skills/{name}/SKILL.md` | Frontmatter `name`, `description` preserved; directory mapped | PASS |
| `instructions` | `AGENTS.md` | `AGENTS.md` | Markdown body preserved verbatim | PASS |
| `plugin` | `.codex/plugins/{name}/plugin.md` | `.openclaw/plugins/{name}/plugin.md` | Frontmatter preserved; directory mapped | PASS |
| `subagent` | `.codex/agents/{name}/agent.md` | `.openclaw/agents/{name}/agent.md` | Frontmatter preserved; directory mapped | PASS |
| `mcp` | `.codex/mcp-servers/{name}.toml` | N/A (unsupported) | Single fetch returns HTTP 501 `translation_unsupported`; bucket fetch skips asset | PASS |

## Test Assertions
1. Root layouts mapped from `.codex/` to `.openclaw/`.
2. Main files retain canonical naming and frontmatter metadata.
3. Unmapped keys preserved in `## Compatibility notes`.
4. Deterministic byte-for-byte output verified.
