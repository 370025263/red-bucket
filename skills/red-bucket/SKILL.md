---
name: red-bucket
description: "Manage AI agent assets on red-bucket hubs. Use this skill when registering users, authenticating, creating and managing buckets, uploading assets (skills, MCPs, instructions, subagents, plugins), fetching fetch-time cross-harness translations across codex, claude, agents, and openclaw, executing install-script one-liners, copying assets across buckets with provenance records, opening or reviewing file-tree pull requests and issues, and handling private bucket 404 access boundaries. Triggers include: red-bucket, bucket, translate harness, install-script, copy, npx skills."
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

### 2. The bundled client: `scripts/rb.mjs`

This skill ships its own client. It needs **Node 18+ and nothing else** —
no `sh`, no `curl`, no `unzip`, no `jq`, no npm install. Prefer it over
hand-rolling the HTTP calls; it already does origin normalisation, file
permissions and atomic writes correctly.

```bash
node <skill-dir>/scripts/rb.mjs login   --client claude
node <skill-dir>/scripts/rb.mjs status
node <skill-dir>/scripts/rb.mjs logout
node <skill-dir>/scripts/rb.mjs install alice/tools --target claude
node <skill-dir>/scripts/rb.mjs create  alice/tools --visibility private --description "my kit"
node <skill-dir>/scripts/rb.mjs upload  alice/tools ./my-skill --type skill --harness claude --path skills/my-skill
```

`install` writes into the current directory; `--dest DIR` or
`$RED_BUCKET_DEST` puts it elsewhere. `--origin URL` or `$RED_BUCKET_URL`
points at a self-hosted server. Private buckets work once you are signed
in — the same command, using the stored credential.

`create` and `upload` are the publishing side. `upload` sends every file
under the local directory as one asset: text files as text, anything
else as base64, rooted at `--path` (default: the directory's own name).
`--type` is what the asset is (`skill`, `mcp`, `instructions`,
`subagent`, `plugin`) and `--harness` is which harness it was *written
for* — the server translates from there. The server validates the asset
and the client prints exactly what it objected to, for example
`validation failed: SKILL.md: SKILL.md missing`. Both need a sign-in.
Prefer these over hand-built `POST .../assets` bodies: the raw endpoints
below are the contract, the client is the tool.

### 3. Installing a bucket without this skill

`GET .../install-script?target=<harness>` with `Accept: text/plain`
returns a self-contained Node program. Save the body as `rb-install.mjs`
and run `node rb-install.mjs`. Same Node-only dependency, same
`RED_BUCKET_URL` / `RED_BUCKET_DEST` overrides.

*(For private buckets there is no pasteable public program: fetch
`GET .../translated` with `Authorization: Bearer <token>` instead, or
just use `rb.mjs install` while signed in.)*

---

## Signing In, and Where the Token Lives

Reading public buckets needs nothing. Everything that writes — creating a
bucket, uploading an asset, opening an issue or a pull request — needs a
bearer token.

**Never ask the user for their red-bucket password.** Use the browser
hand-off below. It is the only sanctioned way for an agent to obtain a
token.

### Where the token is kept

```
$RED_BUCKET_AUTH                                     if set, that exact file
%APPDATA%\red-bucket\auth.json                       on Windows
${XDG_CONFIG_HOME:-~/.config}/red-bucket/auth.json   everywhere else
```

Look there first. If a live entry for this origin already exists, use it
— do not send the user through the browser again for a token they
already granted you.

Directory mode `0700`, file mode `0600`. Write it atomically (temp file
in the same directory, then rename) so an interrupted write cannot leave
a half file. Shape, keyed by origin so a self-hosted server and the
public one can coexist:

```json
{
  "version": 1,
  "hosts": {
    "https://redbucket.store": {
      "username": "stone91",
      "token": "...",
      "created_at": "2026-09-03T04:07:19Z",
      "client": "claude"
    }
  }
}
```

Resolve identity in this order: `$RED_BUCKET_TOKEN` if set, then the
entry in that file whose key matches the origin you are talking to, then
anonymous. Send it as `Authorization: Bearer <token>`.

**Normalise the origin before you use it as a key**, both when writing
and when looking up: lowercase the scheme and host, drop a trailing
slash, drop the port when it is the default for the scheme. So
`https://RedBucket.store:443/` and `https://redbucket.store` are one key,
not three. Skip this and you will send the user back through the browser
for a token you already have, and leave a duplicate entry behind.

If the file will not parse, or `version` is a number you do not
recognise, treat it as no credential — fall back to anonymous and tell
the user the file looks wrong. Never delete or overwrite a file you
could not read; it may hold another tool's tokens.

Read, change and write the whole file in one go, and keep the window
short. Two harnesses signing in at the same moment both read, both write,
and the slower one erases the other's entry. The temp-file-then-rename
above stops a *torn* file, not a lost update.

Never print the token, never echo it into the transcript, never write it
into a repository, never put it in a shell command the user can see in
their scrollback.

### Getting a token: the browser hand-off

The token is minted by the server and handed to your process directly.
It never travels through the conversation.

**1. Start it.**

```
POST /api/v1/auth/device
{"client": "claude"}
```

`201` gives you `device_code`, `user_code`, `verification_url_complete`,
`expires_in` (600) and `interval` (5).

The `device_code` is the secret half — it stays inside your process. The
`user_code` is the short one the human reads.

**2. Show the human the link.** Something like:

> Open this to sign in or create an account:
> https://redbucket.store/link/BQ7K-2M4X
> The page should show the code BQ7K-2M4X. I'll wait.

They open it in a browser, sign in if they are not already, and get one
screen naming your client and listing what they are granting. They press
Authorize or Refuse.

**3. Poll**, no faster than `interval` seconds:

```
POST /api/v1/auth/device/token
{"device_code": "..."}
```

- `{"status": "pending"}` — keep waiting.
- `{"status": "denied"}` — they said no. Stop, and say so plainly.
- `{"status": "approved", "token": ..., "user": {...}}` — you have it.
- `404` — the code expired, or was already collected. Offer to start
  over. The device_code is single use; a second successful poll is
  always a `404`.

**4. Save it** to the path above and say only `Signed in as <username>.`

### Signing out

`POST /api/v1/auth/logout` with the token revokes that one token
server-side. Then delete that host's entry from the auth file. Do both;
one without the other leaves either a live token on the server or a dead
one on disk.

### There is no red-bucket MCP server

`mcp` in red-bucket is a *kind of asset a bucket can hold*, not a server
we run. This skill talking to `/api/v1/` is the whole client integration.
Do not go looking for an MCP endpoint to connect to.

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

- Allowed templates: `codex`, `agents`, `claude`, `openclaw` (or omit for an empty bucket). This list grows; `GET /api/v1/templates` is the live one.
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
- Source harnesses: `claude`, `codex`, `agents`, `openclaw`. This list grows; `GET /api/v1/translation-matrix` is the live one. Never reject a harness the user names just because it is missing from this file — let the server answer.
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
