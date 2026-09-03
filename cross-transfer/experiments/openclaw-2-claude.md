# Translation Verification Experiment: openclaw to claude

- **Source Harness:** `openclaw`
- **Target Harness:** `claude`
- **Verification Level:** Phase 1 Golden-Fixture & Structural Verification
- **Execution Note:** Live harness runtime versions were not run on this host; verification is performed via unit test suite, deterministic codec test fixtures, and AST/frontmatter structure checks.

## Verification Matrix

| Asset Type | Source Format | Target Format | Structural Result | Status |
| --- | --- | --- | --- | --- |
| `skill` | `.openclaw/skills/{name}/SKILL.md` | `skills/{name}/SKILL.md` | Frontmatter `name`, `description` preserved; layout moved from `.openclaw/skills/` to `skills/` | PASS |
| `instructions` | `AGENTS.md` | `CLAUDE.md` | Filename mapped to `CLAUDE.md`; content preserved verbatim | PASS |
| `plugin` | `.openclaw/plugins/{name}/plugin.md` | `plugins/{name}/plugin.md` | Frontmatter preserved; layout moved to `plugins/` | PASS |
| `subagent` | `.openclaw/agents/{name}/agent.md` | `.claude/agents/{name}/agent.md` | Frontmatter preserved; layout moved to `.claude/agents/` | PASS |
| `mcp` | `.openclaw/mcp/{name}.json` | N/A (unsupported) | Single fetch returns HTTP 501 `translation_unsupported`; bucket fetch skips asset | PASS |

## Test Assertions
1. Instructions re-encoded as `CLAUDE.md`.
2. Subagent directories moved from `.openclaw/agents/` to `.claude/agents/`.
3. Skill and plugin directories moved to `skills/` and `plugins/`.
4. Deterministic byte-for-byte output verified.
