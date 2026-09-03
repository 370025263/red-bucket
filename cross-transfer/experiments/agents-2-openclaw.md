# Translation Verification Experiment: agents to openclaw

- **Source Harness:** `agents`
- **Target Harness:** `openclaw`
- **Verification Level:** Phase 1 Golden-Fixture & Structural Verification
- **Execution Note:** Live harness runtime versions were not run on this host; verification is performed via unit test suite, deterministic codec test fixtures, and AST/frontmatter structure checks.

## Verification Matrix

| Asset Type | Source Format | Target Format | Structural Result | Status |
| --- | --- | --- | --- | --- |
| `skill` | `skills/{name}/SKILL.md` | `.openclaw/skills/{name}/SKILL.md` | Frontmatter `name`, `description` preserved; layout moved to `.openclaw/skills/` | PASS |
| `instructions` | `AGENTS.md` | `AGENTS.md` | Markdown body preserved verbatim | PASS |
| `plugin` | `plugins/{name}/plugin.md` | `.openclaw/plugins/{name}/plugin.md` | Frontmatter preserved; layout moved to `.openclaw/plugins/` | PASS |
| `subagent` | `agents/{name}/agent.md` | `.openclaw/agents/{name}/agent.md` | Frontmatter preserved; layout moved to `.openclaw/agents/` | PASS |
| `mcp` | `mcp/{name}.json` | N/A (unsupported) | Single fetch returns HTTP 501 `translation_unsupported`; bucket fetch skips asset | PASS |

## Test Assertions
1. Root layouts mapped from root directory prefixes to `.openclaw/` subdirectories.
2. Frontmatter metadata and markdown instructions retained.
3. Auxiliary assets copied unchanged.
4. Deterministic byte-for-byte output verified.
