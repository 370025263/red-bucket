> Chinese translation: `proposal.zh.md`

# Proposal: add-red-bucket-mvp

## Why

AI agent assets (skills, MCP tool configs, CLAUDE.md/AGENTS.md, subagents, plugins) are fragmented across incompatible harness ecosystems (Codex, Claude Code, OpenClaw, generic Agents style). Users cannot share or reuse assets across harnesses without manual rewriting. red-bucket provides a GitHub/HuggingFace-style hub (`user/bucket` namespaces) whose core value is fetch-time cross-harness format translation, exposed via a RESTful API and a lightweight web UI. This change turns the rough ADR in `sdd/adr/platform.md` into implementable, testable specifications for Phase 1 (MVP).

## What Changes

- Introduce user accounts: registration and authentication required for writes; anonymous read access to public buckets.
- Introduce bucket management: create/delete buckets under `user/bucket-name` namespaces, public/private visibility, optional directory templates (codex, agents, claude, openclaw styles), quotas (5 buckets per user, 10MB per bucket).
- Introduce asset upload with format validation for supported asset types (skill, MCP tool config, CLAUDE.md/AGENTS.md, subagent, plugin), tagged with source harness.
- Introduce fetch-time harness translation: the formatter converts bucket assets to the requesting harness's format; per-pair translation rules documented in `cross-transfer/<src>-2-<dst>.md` and verified by experiments.
- Introduce community collaboration on public buckets: issues and pull requests; installing assets from other users' buckets into one's own.
- Introduce a full-lifecycle RESTful API covering all above operations, with a p95 latency service objective.
- Introduce git-on-filesystem storage, one git repo per bucket, isolated per user id, with quota enforcement.
- Introduce a lightweight web UI (pi.dev-style) for browsing, bucket management, and install-script entry points.

Explicitly out of scope for Phase 1 (deferred, 以后再说):

- Mobile app (App Store / APK distribution) — cost of listing too high for Phase 1.
- Direct `git clone`/git protocol access to buckets — API and UI only in Phase 1.
- MCP/plugin marketplace beyond basic cross-bucket install.

## Capabilities

### New Capabilities

- `identity/accounts`: user registration, authentication, and anonymous public read access.
- `buckets/management`: bucket lifecycle, `user/bucket` namespace, visibility, templates, quota limits.
- `buckets/assets`: asset upload with per-type format validation, listing, and download within a bucket.
- `translation/harness-formatter`: fetch-time conversion of assets between harness formats; translation-rule documents and functional-equivalence guarantees.
- `community/collaboration`: issues, pull requests on public buckets, and cross-bucket asset install.
- `platform/rest-api`: RESTful API conventions, full lifecycle coverage, error model, and latency service objective.
- `platform/git-storage`: git-backed filesystem storage layout, per-user isolation, quota enforcement, durability of history.
- `platform/web-ui`: lightweight frontend pages and one-click install-script entry point.

### Modified Capabilities

(none — this is the first change; no existing specs.)

## Impact

- New codebase: backend API service, formatter engine, git storage layer, web frontend. No existing code is affected.
- New documentation family: `cross-transfer/<src>-2-<dst>.md` translation rule docs, each validated by experiment.
- Test suite and acceptance criteria are defined alongside the specs (see `test-plan.md` in this change and per-spec scenarios); headline acceptance: with 1000 registered users at concurrency 10, 95% of user-facing API requests complete within 1s; cross-harness migration preserves functional behavior of migrated assets.
