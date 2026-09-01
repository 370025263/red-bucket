<p align="center">
  <img src="assets/logo.svg" alt="red-bucket logo" width="128" height="128" />
</p>

<h1 align="center">red-bucket</h1>

<p align="center">
  <strong>Hub for AI agent assets with fetch-time cross-harness format translation.</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-red.svg" alt="License: MIT" /></a>
  <a href="pyproject.toml"><img src="https://img.shields.io/badge/Python-3.12-blue.svg" alt="Python 3.12" /></a>
  <a href="Makefile"><img src="https://img.shields.io/badge/Lint-make%20lint-brightgreen.svg" alt="Lint Gate" /></a>
</p>

---

`red-bucket` is an open-source, GitHub- and HuggingFace-style hub for AI agent assets organized under the `user/bucket` namespace. It hosts skills, Model Context Protocol (MCP) tool configurations, system instructions (such as `CLAUDE.md` and `AGENTS.md`), subagents, and plugins.

The core value of `red-bucket` is **on-the-fly, fetch-time cross-harness format translation** across four major agent ecosystems:
- **Codex**
- **Claude Code**
- **Agents**
- **OpenClaw**

Assets are authored and stored once in their native format, then automatically converted to the target harness structure whenever requested by an agent or client script.

---

## Installation & Usage Paths

There are two distinct installation paths. Do not conflate installing the agent skill with installing assets from a bucket.

### Path A: Install the Agent Skill (via `npx skills`)

To enable your AI agent (Cursor, Claude Code, Codex, etc.) to discover, interact with, and manage `red-bucket` repositories via natural language:

```bash
# Install globally into your agent environment
npx skills add 370025263/red-bucket --skill red-bucket -g -y

# Or install locally in the current project
npx skills add 370025263/red-bucket --skill red-bucket

# List available skills from the repository without installing
npx skills add 370025263/red-bucket --list
```

### Path B: Install Public Bucket Assets (via Server `install-script`)

To fetch and unpack assets from a public bucket directly into your local machine harness directory in one shell command:

```bash
# Example: Install assets from {username}/{bucket} formatted for Claude Code
curl -sSL "$RED_BUCKET_URL/api/v1/users/{username}/buckets/{bucket}/install-script?target=claude" \
  -H "Accept: text/plain" | sh
```

> **Note on Private Buckets:** Private buckets must never expose tokens in pasteable shell scripts. For private buckets, authenticated agents fetch translated archives directly using `Authorization: Bearer <token>` against `GET /api/v1/users/{username}/buckets/{bucket}/translated?target={target}`.

---

## The Three-Name Rule

To prevent conceptual ambiguity across tools, APIs, and client agents, three distinct operations must never be mixed or aliased:

| Concept | Endpoint | Description & Return Type |
| --- | --- | --- |
| **`copy`** | `POST /api/v1/users/{username}/buckets/{bucket}/copies` | Copies an asset from a source bucket into your own destination bucket with provenance history. Returns an `InstallRecord` JSON object. |
| **`install-script`** | `GET /api/v1/users/{username}/buckets/{bucket}/install-script` | Generates a portable shell script that downloads and unpacks translated assets onto the local machine filesystem. |
| **`translated fetch`** | `GET .../translated` | Streams raw translated bytes or a zip archive transformed on the fly for a specified target harness (`?target=...`). |

---

## What It Is & What Phase 1 Is Not

### What It Is

- **`user/bucket` Namespace:** Multi-tenant workspace model with user ownership and granular visibility (`public` or `private`).
- **Asset Coverage:** Supports `skill`, `mcp`, `instructions`, `subagent`, and `plugin` types.
- **Unified REST API:** Everything is accessible through a clean, predictable `/api/v1/` interface.
- **Lightweight Web UI:** Server-rendered HTML (FastAPI + Jinja2) that consumes the same `/api/v1/` endpoints.
- **Resilient Storage Architecture:** SQLite with WAL mode for structured metadata; isolated filesystem `git` repositories for immutable asset history and blob storage.
- **Strict Visibility Boundary:** Private buckets return HTTP `404 Not Found` (never `403 Forbidden`) to unauthenticated callers and non-owners to prevent namespace enumeration.
- **Storage Quotas:** Default limit of 5 buckets per user and 10MB storage per bucket.
- **Robust Authentication:** Argon2id password hashing and opaque bearer tokens stored as SHA-256 hashes.

### What Phase 1 Is Not

- **Not a mobile app or store listing:** Mobile client distribution is deferred; future mobile clients will consume the same `/api/v1/` API.
- **Not a `git clone` or Git protocol service:** Repositories are managed internally through API-driven transactions, not direct Git daemon / SSH clone endpoints.
- **Not a commercial marketplace:** No monetization, billing, or pricing tiers in Phase 1.
- **Not GitHub-style social vanity:** No Star, Watch, or Fork tabs in Phase 1.
- **Current Status:** Server business logic is not implemented yet. This repository currently ships the lint gate, a test skeleton, the agent skill, and the architectural specifications. The hosted SaaS service is not yet live.

---

## Architecture & Specifications

Detailed architectural decisions, API contracts, database schemas, and workflows are documented under the OpenSpec directory:

- [Proposal & Scope](openspec/changes/add-red-bucket-mvp/proposal.md)
- [System Architecture & Design Decisions](openspec/changes/add-red-bucket-mvp/design.md)
- [REST API Catalog (`/api/v1/`)](openspec/changes/add-red-bucket-mvp/api-catalog.md)
- [SQLite Schema & DDL Specifications](openspec/changes/add-red-bucket-mvp/schema-sqlite.md)
- [User Interaction & Sequence Flows](openspec/changes/add-red-bucket-mvp/user-flows.md)
- [Client Skill Architecture](openspec/changes/add-red-bucket-mvp/client-skill.md)
- [Technology Stack Decisions](openspec/changes/add-red-bucket-mvp/tech-stack.md)

---

## Development & Contributing

### Prerequisites

- **Python:** `>= 3.12`
- **Git:** `>= 2.40`
- **Package Manager:** `uv`

### Quality Gates

All contributions must strictly satisfy the project linter and test gates before any feature code is merged:

```bash
# Run complete lint gate (Semgrep, Ruff PEP8 E/W, Pylint naming, Vulture dead-code)
make lint

# Run offline custom rule checks
make lint-custom

# Run test suite
make test
```

> **Important Rule:** Do not start writing feature implementations until `make lint` and `make test` are green.

---

## License

This project is licensed under the [MIT License](LICENSE).
