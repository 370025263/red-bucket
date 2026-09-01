> Chinese translation: `spec.zh.md`

## Purpose

Defines GitHub-like collaboration on public buckets — issues and pull requests — plus the ability to install assets from another user's public bucket into one's own bucket.

## ADDED Requirements

### Requirement: Issues on public buckets
The system SHALL let any authenticated user open an issue (title + markdown body) on a public bucket, and let the issue author and the bucket owner comment on and close it. Issues MUST be readable anonymously on public buckets. Private buckets MUST NOT accept issues from non-owners.

#### Scenario: Issue opened on public bucket
- **WHEN** an authenticated non-owner opens an issue on a public bucket
- **THEN** the system returns HTTP 201 with a sequential issue number scoped to the bucket, and the issue appears in the bucket's issue list for anonymous readers

#### Scenario: Issue on private bucket rejected
- **WHEN** a non-owner attempts to open an issue on a private bucket
- **THEN** the system responds HTTP 404

#### Scenario: Only author or owner closes
- **WHEN** a third user (neither author nor bucket owner) attempts to close an issue
- **THEN** the system responds HTTP 403 and the issue stays open

### Requirement: Pull requests on public buckets
The system SHALL let an authenticated user propose changes to a public bucket as a pull request containing a title, description, and a proposed content diff. The bucket owner MUST be able to review, merge, or reject. Merging MUST apply the change as a git commit in the bucket attributed to the PR author, and MUST re-run asset format validation and quota checks before applying.

#### Scenario: PR lifecycle
- **WHEN** a non-owner submits a PR to a public bucket and the owner merges it
- **THEN** the bucket content reflects the proposed change, the bucket history shows a commit attributed to the PR author, and the PR state becomes `merged`

#### Scenario: Merge blocked by validation
- **WHEN** the owner merges a PR whose proposed content fails asset format validation or would exceed the 10MB quota
- **THEN** the merge is rejected with HTTP 422 (validation) or 413 (quota), the PR remains open, and the bucket is unchanged

#### Scenario: Rejected PR leaves bucket untouched
- **WHEN** the owner rejects a PR
- **THEN** the PR state becomes `rejected` and the bucket content is unchanged

### Requirement: Cross-bucket install
The system SHALL let an authenticated user install (copy) an asset from any public bucket into a bucket they own. The installed copy MUST record provenance (source bucket, source commit, install time) and MUST pass the destination bucket's quota check.

#### Scenario: Successful install
- **WHEN** a user installs a skill from another user's public bucket into their own bucket
- **THEN** the asset appears in the destination bucket with provenance metadata referencing the source bucket and commit, recorded as a git commit

#### Scenario: Install blocked by quota
- **WHEN** an install would push the destination bucket beyond 10MB
- **THEN** the system responds HTTP 413 and the destination bucket is unchanged

#### Scenario: Install from private bucket denied
- **WHEN** a user attempts to install an asset from a private bucket they do not own
- **THEN** the system responds HTTP 404
