> Chinese translation: `design.zh.md`

# Design: add-red-bucket-mvp

## Context

Greenfield repository; the only existing artifact is the ADR at `sdd/adr/platform.md`. The pre-OpenSpec wording is frozen at `sdd/adr/platform.original.md` and must not be edited. Constraints inherited from it: storage is git-on-filesystem (no object storage), quotas are 5 buckets/user and 10MB/bucket, Phase 1 excludes mobile app and git protocol access, frontend follows pi.dev's lightweight style, and the headline acceptance is p95 < 1s at 1000 users / concurrency 10. See `proposal.md` for motivation; see the delta specs for behavior contracts.

## Goals / Non-Goals

**Goals:**

- A single deployable service (API + server-rendered UI) plus a formatter engine that is testable in isolation.
- Deterministic, matrix-driven translation so unsupported pairs fail loudly and supported pairs are regression-testable against golden fixtures.
- All acceptance criteria executable as automated tests (see `test-plan.md`).

**Non-Goals:**

- Horizontal scaling / multi-node storage; Phase-1 target is one node with the load profile in the specs.
- Collaborator/team permission model (owner-only private access in Phase 1).
- Marketplace curation, search ranking, billing.
- GitHub social chrome on the bucket page (Star, Watch, Fork) and extra GitHub tabs (Actions, Projects, Wiki, Security, Insights, Discussions).

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

8. Bucket detail page copies GitHub's repository information architecture, not GitHub's visual assets.
   The ADR asks for a GitHub-like `user/bucket` hub. The page at `/<username>/<bucket-name>` therefore follows the regions a GitHub repository home uses: owner/name heading, visibility badge, a repository-navigation tab bar, a one-level file table with a latest-commit bar, a rendered `README.md` under the files, and a right-hand About sidebar. The clone/Code button maps to Install (target-harness selector + copyable script). Phase 1 tabs are Code, Issues, Pull requests, and Settings (owner only). Alternative (a flat asset dump with no tabs) rejected: it would not match the GitHub-like product the ADR describes.

9. Visual system is a two-layer blend: pi.dev for global chrome, GitHub for repo-page widgets; the mark is a red bucket.
   pi.dev is a long-form, almost print-like site (white canvas, near-black type, sparse header, little chrome). GitHub's repo home is denser Primer-like widgets (tab underline, file table, About, badges). red-bucket uses both on purpose: landing and site header feel like pi.dev; the bucket detail page's regions feel like GitHub. The brand accent is not GitHub green and not an unmodified emoji: it is a first-party SVG of the bucket emoji (U+1FAA3) with the pail body painted brand red. Do not vendor pi.dev assets, GitHub Primer CSS, or octicons. Canonical mark: `assets/logo.svg`.

## Bucket detail page (GitHub analogue)

Default URL: `/<username>/<bucket-name>` (Code tab, working-tree root). Sub-routes follow GitHub's repo URL shapes so users who know GitHub can guess them:

- `/<username>/<bucket-name>/tree/<path>` — directory
- `/<username>/<bucket-name>/blob/<path>` — file
- `/<username>/<bucket-name>/commits` — history list
- `/<username>/<bucket-name>/commit/<sha>` — one commit
- `/<username>/<bucket-name>/issues` and `/issues/<n>`
- `/<username>/<bucket-name>/pulls` and `/pulls/<n>`
- `/<username>/<bucket-name>/settings` — owner only; others get the same 404 as a missing bucket

Layout of the Code tab (desktop):

```
/<username>/<bucket-name>
┌─────────────────────────────────────────────────────────────┐
│  username / bucket-name                     [Public|Private] │
│  [Code]  Issues (n)  Pull requests (n)  Settings (owner)     │
├───────────────────────────────────┬─────────────────────────┤
│ Latest commit: msg · author · sha │ About                   │
│ path crumbs · Install + harness   │ description             │
│ File table (this directory)       │ visibility              │
│   name | last commit | time       │ usage / 10MB            │
│   + type, source harness if asset │ template (if any)       │
│ README.md rendered below          │ harness mix             │
│                                   │ README link             │
└───────────────────────────────────┴─────────────────────────┘
```

GitHub region → Phase 1 mapping:

- Heading `owner / repo-name` → `username / bucket-name`.
- Public/Private badge → same.
- Star, Watch, Fork → omitted.
- Tabs Code, Issues, Pull requests, Settings → same four; open-issue and open-PR counts on the tabs. Actions, Projects, Wiki, Security, Insights, Discussions → omitted.
- Branch selector → omitted. Phase 1 has no git-protocol branch UI; the Code tab browses the current working tree (HEAD). Historical content uses the commits routes already required by git-storage.
- Code / clone button → Install: target-harness selector and a copyable install script (the existing one-click entry).
- Add file → owner upload on the Code tab (existing upload pipeline).
- File table columns name, last commit message, last updated → same, plus asset type and source harness when the row is a stored asset. Listing is one directory level (GitHub behavior), derived from asset paths; it is not a flat type dump.
- `README.md` under the file table → render the `README.md` in the current directory when present (case-insensitive name). Owner of an empty or README-less bucket sees a prompt to add one; visitors just see no README block.
- About: description, website, topics, releases, packages, contributors, languages → description (optional, max 350 characters, GitHub's About limit), visibility, storage usage and 10MB limit, template style if the bucket was created from one, and a count of stored assets by source harness (the languages analogue). No website, topics, stars, releases, or contributor graph in Phase 1.
- Go to file / in-repo search → omitted in Phase 1; a 10MB one-level listing is enough.

Empty bucket: file table has no rows (or only the template skeleton if a template was chosen), no README block for visitors, and the owner sees the add-README and upload prompts. Issues and PRs tabs still render their empty lists.

All Code-tab read regions (heading, tabs, commit bar, file table, README, About, install snippet) MUST be in the served HTML so the no-JavaScript read path still works.

## Brand and visual style

Logo: the product mark is the bucket emoji, with the bucket turned red. Ship a first-party SVG (`assets/logo.svg`) that keeps the emoji's pail-and-handle silhouette and fills the body with `--rb-bucket` (`#C41E3A`). The handle and rim use `--rb-bucket-ink` (`#9B1830`). Do not use the system glyph 🪣 as the shipped logo: host fonts paint it metal or blue, and it cannot be recolored. The same SVG is the favicon and the header mark. The wordmark is `red-bucket` in the UI sans, placed to the right of the mark, linking home.

From pi.dev (global chrome and landing):

- White page, near-black text, content-first, fast to paint.
- Sparse site header: mark + wordmark on the left; Login or the signed-in username on the right. No fat marketing nav, no hero gradient, no card grid.
- System font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`), comfortable body measure on the landing page, little shadow or radius theater.
- Read paths stay HTML; decoration never blocks content.

From GitHub (bucket detail page widgets):

- Repo heading `username / bucket-name`, Public/Private pill, underlined tab bar with open counts.
- One-level file table with a latest-commit bar; About sidebar; README under the files.
- Surfaces are white panels with a 1px `#d0d7de` border and modest radius (~6px), on a light canvas `#f6f8fa` behind the repo well (GitHub's canvas/subtle split).
- Link color `#0969da` inside repo chrome, so file names and issue titles read like GitHub.
- Visibility badges and open/closed issue state follow GitHub's quiet pill language, not marketing chips.

Brand accent (ours):

- `--rb-bucket: #C41E3A` is the only loud color. It paints the logo and the primary Install action (GitHub's green Code button becomes a red Install).
- Hover/active uses `--rb-bucket-ink: #9B1830`.
- Do not use GitHub green as a primary, and do not introduce a second accent.

Tokens the implementation MUST name and reuse:

- `--rb-bucket` `#C41E3A`
- `--rb-bucket-ink` `#9B1830`
- `--rb-fg` `#1f2328`
- `--rb-muted` `#656d76`
- `--rb-border` `#d0d7de`
- `--rb-canvas` `#f6f8fa`
- `--rb-surface` `#ffffff`
- `--rb-link` `#0969da`

## Risks / Trade-offs

- [Functional equivalence is judged by harness behavior we don't control] → Pin harness versions in the experiment environment for cross-transfer docs; equivalence checklist per pair lives in the doc and is re-run when a harness updates.
- [Translated fetch of a whole 10MB bucket may threaten the 1s p95] → Translation is deterministic per commit, so cache translated archives keyed by (commit, target); load test includes translated-fetch in its mix to catch regressions.
- [SQLite write contention under concurrent collaboration bursts] → WAL mode + short transactions; scale ceiling documented; data layer kept swappable for Postgres.
- [Git worktree size ≠ user intuition of 10MB (history grows beyond working tree)] → Quota is defined on working tree (spec); run `git gc` periodically and document that history overhead is not billed to the user.
- [pi.dev style "照抄" carries copying risk] → Reproduce the sparse header, white canvas, and content-first type, not pi.dev assets or copy.
- [GitHub-like repo page "照抄" carries the same copying risk] → Reproduce information architecture, URL shapes, file-table density, and quiet borders; do not vendor Primer CSS, octicons, or GitHub branding. The primary action is red Install, not green Code.

## Migration Plan

Greenfield deploy; no migration. Rollback = redeploy previous build; SQLite file and git storage root are both backward-compatible artifacts to back up before upgrades.

## Open Questions

- Domain name is undecided (ADR leaves it open) — does not affect specs; install scripts must template the base URL.
- Which harness versions to pin for Phase-1 equivalence experiments (record in each cross-transfer doc when first run).
