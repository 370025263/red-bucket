# Translation Verification Experiment: codex to claude

- **Source Harness:** `codex`
- **Target Harness:** `claude`
- **Verification Level:** Phase 1 Golden-Fixture & Structural Verification
- **Execution Note:** Live harness runtime versions were not run on this host; verification is performed via unit test suite, deterministic codec test fixtures, and AST/frontmatter structure checks.

## Verification Matrix

| Asset Type | Source Format | Target Format | Structural Result | Status |
| --- | --- | --- | --- | --- |
| `skill` | `.codex/skills/{name}/SKILL.md` | `skills/{name}/SKILL.md` | Frontmatter `name`, `description` preserved; aux files intact | PASS |
| `instructions` | `AGENTS.md` | `CLAUDE.md` | Filename mapped to `CLAUDE.md`; body preserved verbatim | PASS |
| `plugin` | `.codex/plugins/{name}/plugin.md` | `plugins/{name}/plugin.md` | Frontmatter preserved; layout moved to `plugins/` | PASS |
| `subagent` | `.codex/agents/{name}/agent.md` | `.claude/agents/{name}/agent.md` | Frontmatter preserved; layout moved to `.claude/agents/` | PASS |
| `mcp` | `.codex/mcp-servers/{name}.toml` | `.mcp.json` | TOML mapped to JSON `mcpServers.{name}` with command, transport, args, url | PASS |

## Test Assertions
1. Instructions renamed from `AGENTS.md` to `CLAUDE.md`.
2. MCP TOML keys (`name`, `transport`, `command`, `args`, `url`) converted to `.mcp.json` schema.
3. Subagents relocated into `.claude/agents/{name}`.
4. Output bytes are strictly deterministic for any given `(commit, target)`.
