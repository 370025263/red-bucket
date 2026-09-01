> Chinese translation: `spec.zh.md`

## Purpose

Defines user registration, authentication, and the anonymous-read boundary: writes always require an authenticated account, while public content is readable without one.

## ADDED Requirements

### Requirement: User registration
The system SHALL allow a visitor to register an account with a unique username and a credential (email + password in Phase 1). Usernames MUST be unique (case-insensitive), 3-39 characters, matching `[a-z0-9]([a-z0-9-]*[a-z0-9])?`, because the username is the namespace prefix of every bucket URL.

#### Scenario: Successful registration
- **WHEN** a visitor submits a registration with an unused valid username, valid email, and a password of at least 8 characters
- **THEN** the system creates the account and returns HTTP 201 with the user's public profile (no credential material in the response)

#### Scenario: Duplicate username rejected
- **WHEN** a visitor registers with a username that differs from an existing one only by letter case
- **THEN** the system rejects the request with HTTP 409 and an error code indicating the username is taken

#### Scenario: Invalid username rejected
- **WHEN** a visitor registers with a username containing characters outside `[a-z0-9-]`, or starting/ending with `-`, or shorter than 3 characters
- **THEN** the system rejects the request with HTTP 422 and a validation error naming the `username` field

### Requirement: Authentication for write operations
The system SHALL require authentication for every operation that creates, modifies, or deletes data (buckets, assets, issues, pull requests, installs). Unauthenticated write attempts MUST be rejected with HTTP 401.

#### Scenario: Unauthenticated write rejected
- **WHEN** a request without valid credentials attempts to create a bucket or upload an asset
- **THEN** the system responds HTTP 401 and performs no state change

#### Scenario: Authenticated session issued
- **WHEN** a registered user submits correct credentials to the login endpoint
- **THEN** the system returns an API token (or session) usable as a Bearer credential on subsequent requests

#### Scenario: Invalid credentials rejected
- **WHEN** a user submits a wrong password
- **THEN** the system responds HTTP 401 without revealing whether the username exists

### Requirement: Anonymous read access to public content
The system SHALL serve read operations on public buckets (browse, list assets, fetch/download, view issues and pull requests) without requiring registration or authentication.

#### Scenario: Anonymous fetch of public bucket
- **WHEN** an unauthenticated client requests the asset listing or an asset download from a public bucket
- **THEN** the system returns the content with HTTP 200

#### Scenario: Anonymous access to private bucket denied
- **WHEN** an unauthenticated client requests any content of a private bucket
- **THEN** the system responds HTTP 404 (not 403), so private bucket existence is not disclosed

### Requirement: Owner-only access to private buckets
The system SHALL restrict all access to a private bucket to its owner in Phase 1 (no collaborator model yet).

#### Scenario: Non-owner denied on private bucket
- **WHEN** an authenticated user who is not the owner requests content of another user's private bucket
- **THEN** the system responds HTTP 404
