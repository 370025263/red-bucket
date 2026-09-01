> Chinese translation: `tasks.zh.md`

# Tasks: add-red-bucket-mvp

## 1. Project skeleton and storage foundation

- [ ] 1.1 Scaffold the service (single deployable: API + server-rendered UI), dependency manifest, README, lint/test tooling, CI pipeline
- [ ] 1.2 Implement SQLite metadata layer (users, buckets, quota fields, issues, PRs, provenance) behind a thin data-access module
- [ ] 1.3 Implement git storage layer: bare repo per bucket at `<root>/<user-id>/<bucket-id>.git`, per-bucket mutation lock, commit-per-mutation, working-tree size accounting
- [ ] 1.4 Implement path sanitization (reject `..`, absolute paths, `.git/`, out-of-tree symlinks) with unit tests from test-plan suite S7

## 2. Identity

- [ ] 2.1 Registration endpoint with username/email/password validation rules per `identity/accounts` spec
- [ ] 2.2 Login endpoint issuing Bearer tokens; auth middleware rejecting unauthenticated writes with 401
- [ ] 2.3 Visibility enforcement: anonymous read of public content; 404 (not 403) for private buckets to non-owners
- [ ] 2.4 Test suite S1 (accounts) green

## 3. Buckets and assets

- [ ] 3.1 Bucket CRUD endpoints: create with visibility + name rules, list, metadata (usage/limit), visibility PATCH, delete
- [ ] 3.2 Bucket-count quota enforcement (per-user configurable limit, default 5) with `bucket_quota_exceeded` error
- [ ] 3.3 Template catalog endpoint and template initialization for `codex`, `agents`, `claude`, `openclaw` skeletons
- [ ] 3.4 Asset validation pipeline: per-type validators (skill, mcp, instructions, subagent, plugin) emitting rule-id violations
- [ ] 3.5 Upload endpoint: validation, 10MB atomic quota check, git commit attribution; raw download endpoint (byte-identical)
- [ ] 3.6 Bucket history endpoint and fetch-at-commit
- [ ] 3.7 Test suites S2 (buckets) and S3 (assets) green

## 4. Harness formatter

- [ ] 4.1 Formatter library skeleton: translation-pair registry, pure translate functions, lossy-notes mechanism, capability matrix endpoint driven by registry
- [ ] 4.2 Write `cross-transfer/` docs with field mappings for Phase-1 pairs: skill + instructions across all four harness styles, mcp between claude and codex
- [ ] 4.3 Implement skill translators for all 12 ordered pairs of {codex, agents, claude, openclaw} with golden fixtures
- [ ] 4.4 Implement instructions translators for the same pairs; mcp translators claude<->codex
- [ ] 4.5 Translated fetch endpoints: single asset and whole-bucket archive; identity translation byte-identical; 501 `translation_unsupported` for absent pairs; cache keyed by (commit, target)
- [ ] 4.6 Run equivalence experiments per cross-transfer doc (pinned harness versions), record results, link from docs; mark pairs supported only after experiment passes
- [ ] 4.7 Test suite S4 (formatter) green including determinism and golden-fixture checks

## 5. Collaboration

- [ ] 5.1 Issues: open/comment/close endpoints with role rules (author/owner close), anonymous read on public buckets
- [ ] 5.2 Pull requests: submit diff, review, merge (re-runs validation + quota, commits as PR author), reject
- [ ] 5.3 Cross-bucket install endpoint with provenance metadata and destination quota check
- [ ] 5.4 Test suite S5 (collaboration) green

## 6. Web UI

- [ ] 6.1 Server-rendered public pages: landing, user profile, bucket detail with install-script snippet and harness selector; JS-free read path
- [ ] 6.2 Authenticated pages: register/login, bucket create (template + visibility), upload, visibility toggle, quota display, delete, issues/PR management — all via `/api/v1/` only
- [ ] 6.3 Per-bucket install-script endpoint that fetches translated bucket content and places files into the target harness layout
- [ ] 6.4 Test suite S6 (UI + install script) green

## 7. Acceptance and release gate

- [ ] 7.1 Mock-data seeder: 1000 users with representative buckets/assets
- [ ] 7.2 Load-test scenario (10 concurrent clients, read-heavy mix incl. translated fetch, >=5 min) producing per-endpoint-class p95 report; wire into pre-release gate failing on p95 >= 1s
- [ ] 7.3 Cross-harness migration acceptance run: benchmark assets migrated per pair, equivalence checklist executed, results archived (suite S8)
- [ ] 7.4 Full test plan (test-plan.md) executed; archive reports; update ADR `sdd/adr/platform.md` 验收测试 section to point at the spec scenarios and test plan
