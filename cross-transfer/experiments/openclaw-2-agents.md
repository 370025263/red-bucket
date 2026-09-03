# Translation Verification Experiment: openclaw to agents

- **Source Harness:** `openclaw`
- **Target Harness:** `agents`
- **Verification Level:** Phase 1 Golden-Fixture & Structural Verification
- **Execution Note:** Live harness runtime versions were not run on this host; verification is performed via unit test suite, deterministic codec test fixtures, and AST/frontmatter structure checks.

## Verification Matrix

| Asset Type | Source Format | Target Format | Structural Result | Status |
| --- | --- | --- | --- | --- |
| `skill` | `.openclaw/skills/{name}/SKILL.md` | `skills/{name}/SKILL.md` | Frontmatter `name`, `description` preserved; layout moved from `.openclaw/skills/` to `skills/` | PASS |
| `instructions` | `AGENTS.md` | `AGENTS.md` | Markdown body preserved verbatim | PASS |
| `plugin` | `.openclaw/plugins/{name}/plugin.md` | `plugins/{name}/plugin.md` | Frontmatter preserved; layout moved to `plugins/` | PASS |
| `subagent` | `.openclaw/agents/{name}/agent.md` | `agents/{name}/agent.md` | Frontmatter preserved; layout moved to `agents/` | PASS |
| `mcp` | `.openclaw/mcp/{name}.json` | N/A (unsupported) | Single fetch returns HTTP 501 `translation_unsupported`; bucket fetch skips asset | PASS |

## Test Assertions
1. Root layouts mapped from `.openclaw/` to root folders `skills/`, `plugins/`, `agents/`.
2. Frontmatter metadata and markdown instructions retained.
3. Unmapped fields placed in `## Compatibility notes`.
4. Deterministic byte-for-byte output verified.
