> Chinese translation: `spec.zh.md`

## Purpose

Defines the lightweight web frontend: pi.dev-like global chrome, a GitHub-like bucket detail page, red-bucket copy, and a red bucket mark. Browse public buckets, manage one's own buckets, and surface the one-click install script.

## ADDED Requirements

### Requirement: Public browsing pages
The web UI SHALL provide anonymous-accessible pages for: the landing page, a user profile page listing that user's public buckets, and a bucket detail page at path `/<username>/<bucket-name>` that follows the GitHub repository-home regions defined below.

#### Scenario: Bucket page renders anonymously
- **WHEN** an unauthenticated visitor opens a public bucket's page
- **THEN** the page renders the Code-tab regions (heading, tabs, file table, About, install snippet) with no login prompt blocking the content

#### Scenario: Private bucket page hidden
- **WHEN** an unauthenticated visitor opens a private bucket's URL
- **THEN** the UI shows the same not-found page as for a nonexistent bucket

### Requirement: Authenticated management pages
The web UI SHALL let a logged-in user register/login, create a bucket (with template, visibility, and optional description), upload assets, toggle visibility, edit description, view quota usage, delete buckets, and manage issues and pull requests on their public buckets — all backed exclusively by the public `/api/v1/` endpoints.

#### Scenario: Bucket created through UI
- **WHEN** a logged-in user completes the create-bucket form choosing the `agents` template and `public` visibility
- **THEN** the UI navigates to the new bucket page showing the template skeleton and public badge

#### Scenario: UI uses public API only
- **WHEN** any UI management action is performed with the browser network log recorded
- **THEN** every backend call targets documented `/api/v1/` endpoints (no private endpoints)

### Requirement: Visual style baseline
The web UI SHALL use a two-layer visual system: pi.dev-like global chrome (white canvas, near-black type, sparse header, content-first, fast-loading) and GitHub-like repo-page widgets (underlined tabs, one-level file table, About sidebar, 1px `#d0d7de` borders, modest radius, `#f6f8fa` canvas behind the repo well, `#0969da` links). Naming and copy MUST be red-bucket's own. The implementation MUST reuse the named tokens in `design.md` (`--rb-bucket`, `--rb-bucket-ink`, `--rb-fg`, `--rb-muted`, `--rb-border`, `--rb-canvas`, `--rb-surface`, `--rb-link`). Pages MUST be usable without client-side JavaScript for read-only browsing paths. The UI MUST NOT vendor pi.dev assets, GitHub Primer CSS, octicons, or GitHub branding.

#### Scenario: Read path works without JavaScript
- **WHEN** a public bucket page is loaded with JavaScript disabled
- **THEN** the heading, tab bar, file table, About fields, and install-script text are still visible in the served HTML

#### Scenario: Repo well uses GitHub-like chrome
- **WHEN** a visitor opens a public bucket detail page
- **THEN** the repo well sits on the canvas color, the file table and About are bordered surfaces, the tab bar is underlined, and the Install control uses the brand red (not GitHub green)

### Requirement: Red bucket mark
The product mark SHALL be a first-party SVG of the bucket emoji (U+1FAA3) with the pail body filled brand red (`#C41E3A`) and the handle/rim in `#9B1830`, as stored at `openspec/changes/add-red-bucket-mvp/assets/logo.svg` (and the same asset copied into the service static files at implementation). The system emoji 🪣 MUST NOT be used as the shipped logo. The mark MUST appear in the site header next to the `red-bucket` wordmark (linking home) and MUST be the favicon.

#### Scenario: Header shows red bucket mark
- **WHEN** a visitor opens the landing page or a public bucket page
- **THEN** the site header contains the red-bucket SVG mark and the `red-bucket` wordmark, and the document favicon is that same mark

### Requirement: GitHub-like bucket header and tabs
The bucket detail page SHALL use a GitHub-repository heading `username / bucket-name` with a Public or Private badge, and a repository-navigation tab bar with Code (default), Issues, Pull requests, and Settings. Issues and Pull requests tabs MUST show the count of open items. The Settings tab MUST be rendered only for the bucket owner; other viewers MUST NOT see the tab, and a non-owner request to `/<username>/<bucket-name>/settings` MUST receive the same not-found page as a missing bucket. Phase 1 MUST NOT render Star, Watch, Fork, or extra GitHub tabs (Actions, Projects, Wiki, Security, Insights, Discussions).

#### Scenario: Public header and tabs
- **WHEN** an unauthenticated visitor opens a public bucket that has 2 open issues and 1 open pull request
- **THEN** the page heading is `username / bucket-name`, a Public badge is visible, and the tab bar includes Code, Issues (2), and Pull requests (1), and does not include Settings, Star, Watch, or Fork

#### Scenario: Owner sees Settings
- **WHEN** the bucket owner opens that same public bucket
- **THEN** the tab bar also includes Settings, and opening `/<username>/<bucket-name>/settings` shows visibility, description, quota, and delete controls

### Requirement: Code tab file browser
The Code tab SHALL present a one-level directory browser of the current working tree (HEAD), not a flat type dump, at `/<username>/<bucket-name>` for the root and `/<username>/<bucket-name>/tree/<path>` for a directory. Each file row MUST show name, last commit message, and last-updated time; when the row is a stored asset it MUST also show asset type and source harness. A latest-commit bar MUST show the current tree's latest commit message, author, short hash (linking to `/commit/<sha>`), timestamp, and commit count (linking to `/commits`). Clicking a directory MUST navigate to its `tree` URL; clicking a file MUST navigate to `/<username>/<bucket-name>/blob/<path>`. The GitHub clone/Code button is replaced by an Install control: target-harness selector plus a copyable install script. The owner MUST have an upload entry on this tab. There is no branch selector in Phase 1.

#### Scenario: Directory listing with commit bar
- **WHEN** a visitor opens a public bucket whose root contains a `skills/` directory and a `README.md` file, and the bucket has at least one commit
- **THEN** the Code tab shows a latest-commit bar and a file table with those two rows (directory then files), each file row including last commit message and last-updated time

#### Scenario: Nested path and blob
- **WHEN** a visitor opens `/<username>/<bucket-name>/tree/skills` and then a file under it
- **THEN** the file table lists only that directory's children, and the file opens at `/<username>/<bucket-name>/blob/skills/<filename>`

### Requirement: About sidebar and README
The Code tab SHALL include a right-hand About sidebar (GitHub About analogue) showing: optional description (plain text, max 350 characters), visibility, current storage usage and the 10MB limit, template style if the bucket was created from one, a count of stored assets by source harness, and a link to `README.md` when that file exists at the current directory. When a `README.md` exists in the current directory (case-insensitive name), the page MUST render it as HTML below the file table. When it is absent, visitors MUST see no README block; the owner MUST see a prompt to add one. Phase 1 About MUST NOT include website, topics, stars, releases, packages, or a contributor graph.

#### Scenario: README rendered and About populated
- **WHEN** a public bucket has a root `README.md`, a non-empty description, and stored assets from harness `claude`
- **THEN** the Code tab renders that README below the file table, and About shows the description, visibility, usage, 10MB limit, and a harness mix that includes `claude`

#### Scenario: Empty bucket owner prompt
- **WHEN** the owner opens a newly created empty public bucket
- **THEN** the file table has no content rows, visitors would see no README block, and the owner sees prompts to add a README and to upload

### Requirement: Issues and pull-request tabs
The Issues and Pull requests tabs SHALL list the bucket's issues and pull requests at `/<username>/<bucket-name>/issues` and `/<username>/<bucket-name>/pulls`, each row showing number, title, open or closed state, author, and created time, and SHALL link to `/issues/<n>` and `/pulls/<n>` detail pages. Authenticated users MUST be able to open an issue on a public bucket from the Issues tab. Role rules remain those in `community/collaboration`.

#### Scenario: Issues tab lists open items
- **WHEN** a visitor opens the Issues tab of a public bucket that has one open issue titled `broken skill`
- **THEN** the list shows that issue with its number, title, open state, author, and created time, and the title links to `/<username>/<bucket-name>/issues/<n>`
