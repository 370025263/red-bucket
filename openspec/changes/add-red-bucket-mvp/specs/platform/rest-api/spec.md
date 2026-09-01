## Purpose

Defines the RESTful API surface conventions: full-lifecycle coverage of every platform operation, a uniform error model, versioning, and the latency service objective the platform is accepted against.

## ADDED Requirements

### Requirement: Full-lifecycle REST coverage
The system SHALL expose every user-facing operation defined by the other capabilities (accounts, buckets, assets, translation fetch, issues, PRs, installs, templates, capability matrix) through a versioned RESTful HTTP API under a `/api/v1/` prefix, using resource-oriented paths and standard methods (GET for reads, POST for creation and actions, PATCH for partial update, DELETE for removal). Every operation available in the web UI MUST be achievable through the API alone.

#### Scenario: End-to-end lifecycle via API only
- **WHEN** a scripted client registers, logs in, creates a bucket from a template, uploads an asset, changes visibility, fetches it translated, and deletes the bucket — using only documented `/api/v1/` endpoints
- **THEN** every step succeeds with the documented status codes and no step requires the web UI

### Requirement: Uniform error model
All API errors SHALL share one JSON shape: `{"error": {"code": "<machine_readable_code>", "message": "<human readable>", "details": [...]}}` with an appropriate HTTP status. Error codes MUST be stable identifiers (e.g. `bucket_quota_exceeded`, `translation_unsupported`, `validation_failed`) suitable for programmatic handling by agent clients.

#### Scenario: Consistent error shape
- **WHEN** a client triggers any 4xx error (401, 404, 409, 413, 422) across different endpoints
- **THEN** every response body parses into the uniform error shape with a non-empty stable `code`

### Requirement: Latency service objective
The user-facing API SHALL meet this acceptance objective: with 1000 registered users' data loaded and 10 concurrent clients continuously exercising the read-heavy mix (browse, list, raw fetch, translated fetch of assets within the 10MB bucket limit), the 95th-percentile response latency over the measurement window MUST be under 1 second per endpoint class. This objective MUST be verified by a reproducible load test in CI or a pre-release gate.

#### Scenario: Load test meets p95 under 1s
- **WHEN** the load-test suite seeds 1000 mock users (each with representative buckets and assets) and runs 10 concurrent clients for at least 5 minutes against the read-heavy mix
- **THEN** the measured p95 latency of every exercised endpoint class is below 1000ms and the run report is archived with the release

#### Scenario: Regression gate
- **WHEN** a release candidate's load-test p95 exceeds 1000ms on any endpoint class
- **THEN** the release gate fails and the regression is reported per endpoint class

### Requirement: One-click install script entry
The system SHALL serve a per-bucket install script endpoint that returns a copy-pasteable shell command/script which an AI agent can execute to fetch and place the bucket's assets into the local harness layout for a chosen target harness.

#### Scenario: Install script fetches and places assets
- **WHEN** a user copies the install script for a public bucket with target harness `claude` and executes it in a clean environment
- **THEN** the script downloads the translated bucket content and places files into the claude-style local layout, exiting 0
