# Translation Verification Experiment: claude to openclaw

- **Source Harness:** `claude`
- **Target Harness:** `openclaw`
- **Verification Level:** Phase 1 Golden-Fixture & Structural Verification
- **Execution Note:** Live harness runtime versions were not run on this host; verification is performed via unit test suite, deterministic codec test fixtures, and AST/frontmatter structure checks.

## Verification Matrix

| Asset Type | Source Format | Target Format | Structural Result | Status |
| --- | --- | --- | --- | --- |
| `skill` | `skills/{name}/SKILL.md` | `.openclaw/skills/{name}/SKILL.md` | Frontmatter `name`, `description` preserved; layout moved to `.openclaw/skills/` | PASS |
| `instructions` | `CLAUDE.md` | `AGENTS.md` | Filename mapped to `AGENTS.md`; content preserved verbatim | PASS |
| `plugin` | `plugins/{name}/plugin.md` | `.openclaw/plugins/{name}/plugin.md` | Frontmatter preserved; layout moved to `.openclaw/plugins/` | PASS |
| `subagent` | `.claude/agents/{name}/agent.md` | `.openclaw/agents/{name}/agent.md` | Frontmatter preserved; layout moved to `.openclaw/agents/` | PASS |
| `mcp` | `.mcp.json` | N/A (unsupported) | Single fetch returns HTTP 501 `translation_unsupported`; bucket fetch skips asset | PASS |

## Test Assertions
1. Instructions re-encoded as `AGENTS.md`.
2. Skill, plugin, subagent paths remapped to `.openclaw/` directories.
3. Frontmatter fields normalized with extras placed in compatibility notes.
4. Deterministic byte-for-byte output verified.
