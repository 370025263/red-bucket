> Chinese translation: `spec.zh.md`

## Purpose

Defines the storage contract: every bucket is a git repository on the server filesystem (no object storage), namespaced and isolated per user id, with quota accounting and inspectable history.

## ADDED Requirements

### Requirement: Git repository per bucket
The system SHALL store each bucket as a standalone git repository on the filesystem, laid out under a per-user directory keyed by immutable user id (not username), e.g. `<storage-root>/<user-id>/<bucket-id>.git`. All content mutations (upload, PR merge, install, template init) MUST go through git commits; no bucket content may exist outside git history.

#### Scenario: Every mutation is a commit
- **WHEN** any sequence of content mutations is applied to a bucket
- **THEN** `git log` of the bucket repository shows one commit per mutation with author attribution, and the working tree equals the state served by the API

#### Scenario: Rename-safe storage
- **WHEN** a user changes their username
- **THEN** existing buckets remain intact and addressable under the new username without moving repositories on disk

### Requirement: Per-user isolation
The system SHALL isolate users' storage so no API operation can read from or write to another user's directory except through the documented public-bucket read and collaboration paths. Path inputs (bucket names, asset paths) MUST be sanitized so `..`, absolute paths, symlinks, or git internals (`.git/`) cannot escape the bucket working tree.

#### Scenario: Path traversal blocked
- **WHEN** an upload declares an asset path containing `../`, a leading `/`, or a `.git/` prefix
- **THEN** the system responds HTTP 422 and no file outside the bucket working tree is created or read

#### Scenario: Symlink escape blocked
- **WHEN** an uploaded archive contains a symlink pointing outside the bucket working tree
- **THEN** the system rejects the upload or strips the symlink, and no out-of-tree path is ever resolved

### Requirement: Quota accounting
The system SHALL track each bucket's working-tree size and enforce the 10MB limit before committing any mutation. Accounting MUST be based on the size after the mutation would apply (atomic check-then-commit), and reported usage MUST match the actual working tree within 1%.

#### Scenario: Concurrent uploads cannot overshoot
- **WHEN** two concurrent uploads to the same bucket would each fit individually but together exceed 10MB
- **THEN** at most one is committed and the other is rejected with HTTP 413; the final working tree is under the limit

### Requirement: History inspectability
The system SHALL expose bucket history (commit list with author, timestamp, message, changed paths) through the API, and support fetching an asset at a specific historical commit.

#### Scenario: Fetch at historical commit
- **WHEN** a client requests an asset at a commit hash from the bucket's history
- **THEN** the response matches the asset's content as of that commit
