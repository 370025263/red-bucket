> Chinese translation: `design.zh.md`

# Design: add-red-bucket-mvp

## Context

Greenfield repository; the only existing artifact is the ADR at `sdd/adr/platform.md`. Constraints inherited from it: storage is git-on-filesystem (no object storage), quotas are 5 buckets/user and 10MB/bucket, Phase 1 excludes mobile app and git protocol access, frontend follows pi.dev's lightweight style, and the headline acceptance is p95 < 1s at 1000 users / concurrency 10. See `proposal.md` for motivation; see the delta specs for behavior contracts.

## Goals / Non-Goals

**Goals:**

- A single deployable service (API + server-rendered UI) plus a formatter engine that is testable in isolation.
- Deterministic, matrix-driven translation so unsupported pairs fail loudly and supported pairs are regression-testable against golden fixtures.
- All acceptance criteria executable as automated tests (see `test-plan.md`).

**Non-Goals:**

- Horizontal scaling / multi-node storage; Phase-1 target is one node with the load profile in the specs.
- Collaborator/team permission model (owner-only private access in Phase 1).
- Marketplace curation, search ranking, billing.

## Decisions

1. Monolith with server-rendered UI, JSON API under `/api/v1/`.
   Rationale: 1000-user scale needs no microservices; server rendering satisfies the "read path works without JavaScript" requirement cheaply. Alternative (SPA + separate API service) rejected as heavier and worse for anonymous crawl/read latency.

2. Formatter as a pure library with a translation-pair registry.
   Each (asset type, src, dst) pair registers a pure function `translate(sourceTree) -> targetTree + lossyNotes`. The capability matrix endpoint reads the registry, so code and matrix cannot drift. Pure functions with no I/O give determinism (required by spec) and make golden-fixture testing trivial. Alternative (LLM-assisted translation) rejected for Phase 1: non-deterministic, violates the determinism requirement; may return as an offline authoring aid for cross-transfer docs.

3. Storage layout `<storage-root>/<user-id>/<bucket-id>.git` with bare repos + per-mutation worktree, mutations serialized per bucket with a per-bucket lock.
   Immutable ids keep username/bucket renames metadata-only. The per-bucket lock provides the atomic quota check-then-commit the spec requires; contention is negligible at this scale. Alternative (non-bare repo with long-lived worktree) rejected: harder to make concurrent-safe.

4. Metadata in SQLite (users, buckets, quotas, issues, PRs, install provenance); git holds only content.
   Listings, quota lookups, and issue/PR state need queryability; parsing git for them would blow the latency budget. SQLite (WAL mode) is sufficient for 1000 users / concurrency 10 and keeps ops simple. Alternative (Postgres) deferred until scale demands it; the data-access layer stays thin to keep that migration cheap.

5. Validation as a shared pipeline used by upload, PR merge, and install.
   One validator per asset type produces machine-readable violations (`rule id + path`), reused everywhere content enters a bucket, so PR merges and installs cannot bypass upload rules (spec requirement).

6. Auth: email+password with salted hash, Bearer API tokens; private-bucket denial always answers 404.
   404-not-403 is a spec-level anti-enumeration decision. OAuth/social login deferred.

7. Load test as a first-class repo artifact (k6 or Locust scenario + seeder for 1000 mock users), run as a pre-release gate producing an archived report.
   The p95 acceptance is a spec requirement; making the harness reproducible in-repo is the only way the "regression gate" scenario can fail a release honestly.

## Risks / Trade-offs

- [Functional equivalence is judged by harness behavior we don't control] → Pin harness versions in the experiment environment for cross-transfer docs; equivalence checklist per pair lives in the doc and is re-run when a harness updates.
- [Translated fetch of a whole 10MB bucket may threaten the 1s p95] → Translation is deterministic per commit, so cache translated archives keyed by (commit, target); load test includes translated-fetch in its mix to catch regressions.
- [SQLite write contention under concurrent collaboration bursts] → WAL mode + short transactions; scale ceiling documented; data layer kept swappable for Postgres.
- [Git worktree size ≠ user intuition of 10MB (history grows beyond working tree)] → Quota is defined on working tree (spec); run `git gc` periodically and document that history overhead is not billed to the user.
- [pi.dev style "照抄" carries copying risk] → Reproduce layout/typography approach, not assets; all copy and branding are red-bucket's own.

## Migration Plan

Greenfield deploy; no migration. Rollback = redeploy previous build; SQLite file and git storage root are both backward-compatible artifacts to back up before upgrades.

## Open Questions

- Domain name is undecided (ADR leaves it open) — does not affect specs; install scripts must template the base URL.
- Which harness versions to pin for Phase-1 equivalence experiments (record in each cross-transfer doc when first run).
