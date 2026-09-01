> Chinese translation: `spec.zh.md`

## Purpose

Defines the bucket (repo) lifecycle: namespaced creation under `user/bucket-name`, public/private visibility, optional description, optional harness-style directory templates, and per-user quota limits.

## ADDED Requirements

### Requirement: Bucket creation under user namespace
The system SHALL let an authenticated user create a bucket addressed as `<username>/<bucket-name>`. Bucket names MUST be unique per user (case-insensitive), 1-100 characters, matching `[a-z0-9]([a-z0-9._-]*[a-z0-9])?`. At creation the user MUST choose visibility `public` or `private` (default `private`).

#### Scenario: Successful bucket creation
- **WHEN** an authenticated user creates a bucket with an unused valid name and visibility `public`
- **THEN** the system returns HTTP 201 with the bucket metadata (full name, visibility, description, quota, created time) and the bucket is immediately visible at `GET /users/<username>/buckets`

#### Scenario: Duplicate bucket name rejected
- **WHEN** a user creates a bucket whose name (case-insensitive) already exists under their namespace
- **THEN** the system responds HTTP 409 and no bucket is created

#### Scenario: Invalid bucket name rejected
- **WHEN** a user creates a bucket with a name containing `/`, spaces, or uppercase characters
- **THEN** the system responds HTTP 422 naming the invalid field

### Requirement: Bucket count quota
The system SHALL limit each user to 5 buckets by default. The limit MUST be enforced at creation time and MUST be a per-user configurable value in storage so it can be raised for individual users without code changes.

#### Scenario: Sixth bucket rejected
- **WHEN** a user who already owns 5 buckets attempts to create another
- **THEN** the system responds HTTP 403 with error code `bucket_quota_exceeded` and reports the current limit in the error body

#### Scenario: Deletion frees quota
- **WHEN** a user at the 5-bucket limit deletes one bucket and then creates a new one
- **THEN** the creation succeeds

### Requirement: Bucket description
The system SHALL store an optional owner-editable plain-text description on each bucket, at most 350 characters (the GitHub About description limit). The description MUST default to empty, MUST be returned on bucket metadata, and MUST be patchable by the owner after creation.

#### Scenario: Description set and returned
- **WHEN** an owner creates a bucket with a description, or later PATCHes the description
- **THEN** subsequent metadata responses and the bucket detail About sidebar show that description

#### Scenario: Description too long rejected
- **WHEN** a description longer than 350 characters is submitted
- **THEN** the system responds HTTP 422 naming the `description` field

### Requirement: Visibility change
The system SHALL allow the bucket owner to switch a bucket between `public` and `private` at any time. The change MUST take effect for all subsequent requests.

#### Scenario: Public to private hides content
- **WHEN** an owner switches a public bucket to private
- **THEN** subsequent anonymous requests to that bucket respond HTTP 404 while owner requests still succeed

### Requirement: Bucket creation from template
The system SHALL offer optional directory templates at bucket creation. Phase 1 MUST include at least these template styles: `codex`, `agents` (generic), `claude`, `openclaw`. Choosing a template initializes the bucket with that style's directory skeleton; choosing none creates an empty bucket.

#### Scenario: Template applied at creation
- **WHEN** a user creates a bucket selecting the `claude` template
- **THEN** the new bucket contains the claude-style skeleton (e.g. `skills/`, `CLAUDE.md` placeholder) as its initial content and the initial content is recorded as the first git commit

#### Scenario: Template list discoverable
- **WHEN** a client requests the template catalog endpoint
- **THEN** the system returns at least the 4 Phase-1 template styles with a name and description for each

### Requirement: Bucket deletion
The system SHALL allow the owner to delete a bucket. Deletion MUST remove the bucket from all listings and free its storage accounting; the underlying git repository MAY be retained out-of-band for disaster recovery but MUST NOT be addressable via any API afterwards.

#### Scenario: Deleted bucket unaddressable
- **WHEN** an owner deletes a bucket and any client subsequently requests it
- **THEN** the system responds HTTP 404 for all API routes referencing that bucket
