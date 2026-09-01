> Chinese translation: `spec.zh.md`

## Purpose

Defines how assets (skills, MCP tool configs, CLAUDE.md/AGENTS.md instruction files, subagents, plugins) are uploaded into a bucket with per-type format validation, listed, and downloaded in their stored form.

## ADDED Requirements

### Requirement: Supported asset types
The system SHALL support these asset types in Phase 1: `skill`, `mcp` (MCP tool/server config), `instructions` (CLAUDE.md / AGENTS.md class files), `subagent`, `plugin`. Every stored asset MUST carry: asset type, source harness (`codex`, `claude`, `agents`, `openclaw`), a path within the bucket, and upload metadata (uploader, timestamp, size).

#### Scenario: Asset metadata returned on listing
- **WHEN** a client lists the assets of a bucket
- **THEN** each entry includes type, source harness, path, size, and last-modified time

### Requirement: Format validation on upload
The system SHALL validate every uploaded asset against its declared type's format rules before accepting it, and MUST reject invalid uploads with HTTP 422 and a machine-readable list of violations. Minimum Phase-1 rules: a `skill` MUST contain a SKILL.md (or harness equivalent) with parseable frontmatter/name and description; an `mcp` asset MUST be parseable JSON/TOML per its harness convention and declare at least a server name and transport; an `instructions` asset MUST be valid UTF-8 markdown under the size limit; `subagent` and `plugin` MUST satisfy the structural rules of their declared source harness.

#### Scenario: Valid skill accepted
- **WHEN** a user uploads a skill directory containing a well-formed SKILL.md with name and description, declaring source harness `claude`
- **THEN** the system accepts it with HTTP 201 and the asset appears in the bucket listing

#### Scenario: Malformed skill rejected
- **WHEN** a user uploads a skill whose SKILL.md lacks a name or has unparseable frontmatter
- **THEN** the system responds HTTP 422 listing each violation with a rule identifier and file path, and nothing is written to the bucket

#### Scenario: Malformed MCP config rejected
- **WHEN** a user uploads an `mcp` asset whose config is syntactically invalid JSON
- **THEN** the system responds HTTP 422 identifying the parse error location

#### Scenario: Undeclared type rejected
- **WHEN** an upload omits the asset type or declares an unsupported type
- **THEN** the system responds HTTP 422 without storing anything

### Requirement: Upload commits to bucket history
The system SHALL record every accepted upload (create or update) as a git commit in the bucket's repository, attributing the commit to the uploading user, so bucket history is inspectable and recoverable.

#### Scenario: Upload creates a commit
- **WHEN** a user uploads a new asset and then re-uploads a modified version
- **THEN** the bucket's history endpoint shows two commits attributed to that user, in order

### Requirement: Per-bucket storage quota
The system SHALL limit each bucket's content to 10MB (working-tree size of stored assets). Uploads that would exceed the limit MUST be rejected with HTTP 413 and error code `bucket_storage_exceeded`, reporting current usage and limit; the bucket MUST remain unchanged.

#### Scenario: Oversize upload rejected atomically
- **WHEN** a bucket holds 9.5MB and a user uploads a 1MB asset
- **THEN** the system responds HTTP 413 with current usage and limit, and the bucket still contains exactly its previous content

#### Scenario: Usage visible to owner
- **WHEN** the owner requests bucket metadata
- **THEN** the response includes current storage usage in bytes and the 10MB limit

### Requirement: Raw asset download
The system SHALL let an authorized client download any asset exactly as stored (no translation) via a raw endpoint, preserving bytes and directory structure (single file directly; multi-file assets as an archive).

#### Scenario: Raw download is byte-identical
- **WHEN** a client uploads an asset and immediately downloads it via the raw endpoint
- **THEN** the downloaded content is byte-identical to the upload
