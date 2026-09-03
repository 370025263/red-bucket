# Translation Verification Experiment: claude to codex

- **Source Harness:** `claude`
- **Target Harness:** `codex`
- **Verification Level:** Phase 1 Golden-Fixture & Structural Verification
- **Execution Note:** Live harness runtime versions were not run on this host; verification is performed via unit test suite, deterministic codec test fixtures, and AST/frontmatter structure checks.

## Verification Matrix

| Asset Type | Source Format | Target Format | Structural Result | Status |
| --- | --- | --- | --- | --- |
| `skill` | `skills/{name}/SKILL.md` | `.codex/skills/{name}/SKILL.md` | Frontmatter `name`, `description` preserved; layout moved to `.codex/skills/` | PASS |
| `instructions` | `CLAUDE.md` | `AGENTS.md` | Filename mapped to `AGENTS.md`; body preserved verbatim | PASS |
| `plugin` | `plugins/{name}/plugin.md` | `.codex/plugins/{name}/plugin.md` | Frontmatter preserved; layout moved to `.codex/plugins/` | PASS |
| `subagent` | `.claude/agents/{name}/agent.md` | `.codex/agents/{name}/agent.md` | Frontmatter preserved; layout moved to `.codex/agents/` | PASS |
| `mcp` | `.mcp.json` | `.codex/mcp-servers/{name}.toml` | JSON `mcpServers.{name}` table mapped to TOML format | PASS |

## Test Assertions
1. Instructions renamed from `CLAUDE.md` to `AGENTS.md`.
2. MCP JSON `.mcp.json` accurately converted to Codex TOML format with name, transport, command, args, url.
3. Frontmatter fields normalized with extras placed in `## Compatibility notes`.
4. Deterministic byte-for-byte output verified.
