> Chinese translation: `spec.zh.md`

## Purpose

Defines the lightweight web frontend (pi.dev-style visual language with red-bucket copy): browse and search public buckets, manage one's own buckets, and surface the one-click install script.

## ADDED Requirements

### Requirement: Public browsing pages
The web UI SHALL provide anonymous-accessible pages for: the landing page, a user profile page listing that user's public buckets, and a bucket detail page at path `/<username>/<bucket-name>` showing description, asset listing with types and source harness, visibility, storage usage, and the install-script snippet with a target-harness selector.

#### Scenario: Bucket page renders anonymously
- **WHEN** an unauthenticated visitor opens a public bucket's page
- **THEN** the page renders the asset listing and a copyable install script, with no login prompt blocking the content

#### Scenario: Private bucket page hidden
- **WHEN** an unauthenticated visitor opens a private bucket's URL
- **THEN** the UI shows the same not-found page as for a nonexistent bucket

### Requirement: Authenticated management pages
The web UI SHALL let a logged-in user register/login, create a bucket (with template and visibility selection), upload assets, toggle visibility, view quota usage, delete buckets, and manage issues and pull requests on their public buckets — all backed exclusively by the public `/api/v1/` endpoints.

#### Scenario: Bucket created through UI
- **WHEN** a logged-in user completes the create-bucket form choosing the `agents` template and `public` visibility
- **THEN** the UI navigates to the new bucket page showing the template skeleton and public badge

#### Scenario: UI uses public API only
- **WHEN** any UI management action is performed with the browser network log recorded
- **THEN** every backend call targets documented `/api/v1/` endpoints (no private endpoints)

### Requirement: Visual style baseline
The web UI SHALL follow the pi.dev lightweight visual style (minimal, fast-loading, content-first) with red-bucket's own naming and copy. Pages MUST be usable without client-side JavaScript for read-only browsing paths.

#### Scenario: Read path works without JavaScript
- **WHEN** a public bucket page is loaded with JavaScript disabled
- **THEN** the asset listing and install-script text are still visible in the served HTML
