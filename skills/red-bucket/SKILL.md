---
name: red-bucket
description: Manage AI agent assets on red-bucket hubs. Use this skill when registering users, authenticating, creating and managing buckets, uploading assets (skills, MCPs, instructions, subagents, plugins), fetching fetch-time cross-harness translations across codex, claude, agents, and openclaw, executing install-script one-liners, copying assets across buckets with provenance records, opening or reviewing file-tree pull requests and issues, and handling private bucket 404 access boundaries. Triggers include: red-bucket, bucket, translate harness, install-script, copy, npx skills.
---

# red-bucket Skill

This skill guides AI agents in interacting with `red-bucket` servers. `red-bucket` is a hub for AI agent assets (skills, MCP configs, instructions such as `CLAUDE.md` and `AGENTS.md`, subagents, plugins) organized by `user/bucket` namespace, featuring on-the-fly cross-harness format translation across `codex`, `claude`, `agents`, and `openclaw`.

---

## Agent Guardrails & Invariants

1. **Authentication:** All write operations and access to private buckets owned by the user require `Authorization: Bearer <token>`. Public bucket reading is anonymous and requires no header.
2. **Credential Safety:** Never print, log, or leak passwords, API tokens, or secrets into output or user transcripts.
3. **Private Bucket 404 Invariant:** Any request to a private bucket or its sub-resources from an unauthenticated caller or a non-owner MUST return HTTP `404 Not Found` (never `403 Forbidden`). Non-owners cannot distinguish whether a private bucket exists or does not exist.
4. **Quotas & Limits:**
   - Default bucket quota: 5 buckets per user (exceeding returns `403` with code `bucket_quota_exceeded`).
   - Bucket storage limit: 10MB per bucket (exceeding returns `413` with code `bucket_storage_exceeded`).
5. **API Scope:** All endpoints reside under `/api/v1/`.

---

## The Three-Name Rule

Never conflate or mix these three operations:

- **`copy`** (`POST /api/v1/users/{username}/buckets/{bucket}/copies`): Duplicates an asset from a readable source bucket into your own destination bucket with provenance history. Returns an `InstallRecord` JSON object.
- **`install-script`** (`GET /api/v1/users/{username}/buckets/{bucket}/install-script`): Returns executable shell script text that downloads and places translated assets on the local filesystem.
- **`translated fetch`** (`GET .../translated`): Fetches raw translated bytes or a zip archive transformed on the fly for a specified target harness.

---

## Installation & Discovery

### 1. Agent Skill Installation (via `npx skills`)

To install this skill into an agent environment:

```bash
# Global installation for agent access
npx skills add 370025263/red-bucket --skill red-bucket -g -y

# List available skills without installing
npx skills add 370025263/red-bucket --list
```

### 2. Public Bucket Assets One-Liner (Shell Script)

To install assets from a public bucket to the local machine:

```bash
curl -sSL "$RED_BUCKET_URL/api/v1/users/{username}/buckets/{bucket}/install-script?target=claude" -H "Accept: text/plain" | sh
```

*(For private buckets, agents must fetch translated archives using `Authorization: Bearer <token>` against `GET .../translated` rather than generating a public pasteable script).*

---

## User-Side Flows & API Operations

### 1. User Registration, Login, and Profile

- **Register:**
  ```http
  POST /api/v1/auth/register
  Content-Type: application/json

  {
    "username": "alice",
    "email": "alice@example.com",
    "password": "strongpassword123"
  }
  ```
  - *Response:* `201 Created` with `Location: /api/v1/users/alice` and public `User` object (passwords hashed with Argon2id; no token issued at registration).

- **Login:**
  ```http
  POST /api/v1/auth/login
  Content-Type: application/json

  {
    "email": "alice@example.com",
    "password": "strongpassword123"
  }
  ```
  - *Response:* `200 OK` with `{"token": "<opaque_token>", "token_type": "bearer", "user": { ... }}`.

- **Get Profile (`me`):**
  ```http
  GET /api/v1/users/me
  Authorization: Bearer <token>
  ```
  - *Response:* `200 OK` with user details (including `email`, `bucket_quota`, `bucket_count`).

---

### 2. Create Bucket from Template

Create a bucket under the authenticated user's namespace:

```http
POST /api/v1/users/{username}/buckets
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "dev-skills",
  "visibility": "public",
  "description": "General development agent skills",
  "template": "claude"
}
```

- Allowed templates: `codex`, `agents`, `claude`, `openclaw` (or omit for an empty bucket).
- Visibility: `public` or `private` (default is `private`).
- *Response:* `201 Created` with `Location: /api/v1/users/{username}/buckets/{name}` and `Bucket` JSON.
- *Errors:* `403` (`bucket_quota_exceeded` if exceeding 5 buckets), `409` (`bucket_name_taken`).

---

### 3. Upload Assets

Upload an asset with format validation and quota enforcement:

```http
POST /api/v1/users/{username}/buckets/{bucket}/assets
Authorization: Bearer <token>
Content-Type: application/json

{
  "type": "skill",
  "source_harness": "claude",
  "path": "skills/calculator",
  "files": [
    {
      "path": "SKILL.md",
      "content_text": "---\nname: calculator\ndescription: Perform arithmetic calculations\n---\n\n# Calculator Skill\n"
    }
  ]
}
```

- Asset types: `skill`, `mcp`, `instructions`, `subagent`, `plugin`.
- Source harnesses: `claude`, `codex`, `agents`, `openclaw`.
- File content can be provided as `content_text` (UTF-8) or `content_base64`.
- *Response:* `201 Created` with `Location: /api/v1/users/{username}/buckets/{bucket}/assets/{asset_id}`.
- *Errors:* `413` (`bucket_storage_exceeded` if bucket exceeds 10MB), `422` (`validation_failed` with specific rule and path violations).

---

### 4. Anonymous Browsing & Translated Fetch

- **Browse Bucket (Public / Anonymous):**
  ```http
  GET /api/v1/users/{username}/buckets/{bucket}
  ```

- **Browse File Tree & Blobs:**
  ```http
  GET /api/v1/users/{username}/buckets/{bucket}/tree
  GET /api/v1/users/{username}/buckets/{bucket}/blob/{*path}
  ```

- **Fetch Full Bucket Translated for Target Harness:**
  ```http
  GET /api/v1/users/{username}/buckets/{bucket}/translated?target=codex
  ```
  - *Response:* `200 OK` (binary zip archive, header `X-Red-Bucket-Lossy: true|false`).

- **Fetch Single Asset Translated:**
  ```http
  GET /api/v1/users/{username}/buckets/{bucket}/assets/{asset_id}/translated?target=codex
  ```
  - *Response:* `200 OK` (raw translated bytes or zip archive).

---

### 5. Run Install-Script

Retrieve the shell installation script generated for a target harness:

```http
GET /api/v1/users/{username}/buckets/{bucket}/install-script?target=claude
Accept: text/plain
```

- *Response:* `200 OK` with raw shell script text.
- Executes client-side to download the translated zip archive and place files into local harness directories.

---

### 6. Copy Asset to Own Bucket (Provenance Tracking)

Copy an asset from a source bucket into your own destination bucket:

```http
POST /api/v1/users/{username}/buckets/{dest_bucket}/copies
Authorization: Bearer <token>
Content-Type: application/json

{
  "source_username": "bob",
  "source_bucket": "public-skills",
  "source_asset_id": 12,
  "dest_path": "skills/calculator"
}
```

- *Response:* `201 Created` with `Location: /api/v1/users/{username}/buckets/{dest_bucket}/copies/{copy_id}` and `InstallRecord` JSON object.
- Validates the source asset, verifies the 10MB quota, and records provenance.

---

### 7. Issues and Comments

- **Create Issue:**
  ```http
  POST /api/v1/users/{username}/buckets/{bucket}/issues
  Authorization: Bearer <token>
  Content-Type: application/json

  {
    "title": "Bug in calculator skill translation",
    "body": "When translating to codex format, YAML parameters are missing."
  }
  ```
  - *Response:* `201 Created` with `Location: /api/v1/users/{username}/buckets/{bucket}/issues/{number}`.

- **List Issues:**
  ```http
  GET /api/v1/users/{username}/buckets/{bucket}/issues?state=open
  ```

- **Comment on Issue:**
  ```http
  POST /api/v1/users/{username}/buckets/{bucket}/issues/{number}/comments
  Authorization: Bearer <token>
  Content-Type: application/json

  {
    "body": "Fix is proposed in PR #1."
  }
  ```
  - Note: Only the issue author and bucket owner may comment (third-party comments return `403 forbidden`).

- **Close Issue:**
  ```http
  PATCH /api/v1/users/{username}/buckets/{bucket}/issues/{number}
  Authorization: Bearer <token>
  Content-Type: application/json

  {
    "state": "closed"
  }
  ```
  - Note: Only the issue author and bucket owner may close an issue.

---

### 8. Pull Requests (File-Tree Replacements)

Pull requests propose whole file replacements stored in metadata, not git patches.

- **Create Pull Request:**
  ```http
  POST /api/v1/users/{username}/buckets/{bucket}/pulls
  Authorization: Bearer <token>
  Content-Type: application/json

  {
    "title": "Update calculator skill instructions",
    "body": "Refines prompt handling in SKILL.md",
    "files": [
      {
        "path": "skills/calculator/SKILL.md",
        "content_text": "---\nname: calculator\ndescription: High-precision calculation skill\n---\n\n# Calculator\n"
      }
    ]
  }
  ```
  - *Response:* `201 Created` with `Location: /api/v1/users/{username}/buckets/{bucket}/pulls/{number}`.

- **Inspect PR Files:**
  ```http
  GET /api/v1/users/{username}/buckets/{bucket}/pulls/{number}/files
  ```

- **Merge PR (Bucket Owner Only):**
  ```http
  POST /api/v1/users/{username}/buckets/{bucket}/pulls/{number}/merge
  Authorization: Bearer <token>
  Content-Type: application/json

  {}
  ```
  - *Response:* `200 OK` with `PullRequest` (status updated to `merged` and git commit authored under the PR submitter's identity).

- **Reject PR (Bucket Owner Only):**
  ```http
  POST /api/v1/users/{username}/buckets/{bucket}/pulls/{number}/reject
  Authorization: Bearer <token>
  Content-Type: application/json

  {}
  ```
  - *Response:* `200 OK` with status `rejected`.

---

### 9. Logout

Revoke the current authentication token:

```http
POST /api/v1/auth/logout
Authorization: Bearer <token>
Content-Type: application/json

{}
```

- *Response:* `204 No Content`.
- The revoked token becomes invalid immediately; subsequent use returns `401 unauthorized`.

---

### 10. Private Bucket 404 Access Boundary

- Unauthenticated or non-owner requests to private buckets:
  - `GET /api/v1/users/{username}/buckets/{private_bucket}` -> `404 Not Found`
  - `GET /api/v1/users/{username}/buckets/{private_bucket}/assets` -> `404 Not Found`
  - `GET /api/v1/users/{username}/buckets/{private_bucket}/tree` -> `404 Not Found`
  - `GET /api/v1/users/{username}/buckets/{private_bucket}/translated` -> `404 Not Found`
  - `GET /api/v1/users/{username}/buckets/{private_bucket}/install-script` -> `404 Not Found`
  - `GET /api/v1/users/{username}/buckets/{private_bucket}/issues` -> `404 Not Found`
  - `GET /api/v1/users/{username}/buckets/{private_bucket}/pulls` -> `404 Not Found`
- When listing buckets via `GET /api/v1/users/{username}/buckets`, private buckets are silently omitted for non-owners.
