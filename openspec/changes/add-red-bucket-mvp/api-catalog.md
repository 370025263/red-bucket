# Phase 1 REST API 目录

本文是 `add-red-bucket-mvp` 的 API 契约。实现必须按本表暴露 `/api/v1/` 资源；Web UI、日后的 CLI、移动端、MCP 客户端共用这一套，Phase 1 不为后三类客户端另开端点。Logo 与静态文件走静态资源（`assets/logo.svg`），不是 API，也不是数据库表。

字段名、路径、错误码是稳定契约。业务范围与现行 OpenSpec 对齐：不做市场、星标、计费、协作者、git 协议 clone。用户改名只改元数据（见 `PATCH /users/me`），磁盘仓库仍按不可变 `user.id` 存放。

---

## Conventions

### Versioning

全部面向用户的 JSON API 挂在 `/api/v1/`。破坏性变更升主版本（`/api/v2/`）。Phase 1 不使用自定义版本头。

HTML 页面（`/`、`/<username>/<bucket-name>` 等）不是本目录的一部分；它们只消费本目录中的端点。

### Auth header

写操作以及读取自己的私有 bucket，必须带：

```
Authorization: Bearer <token>
```

`token` 由 `POST /api/v1/auth/login` 签发，由 `POST /api/v1/auth/logout` 撤销当前这一枚。服务端只存 token 的哈希。每次成功通过认证的请求更新该行的 `last_used_at`。

公开 bucket 的读（列表、树、blob、raw、翻译拉取、安装脚本文本、issues、PRs、能力矩阵、模板目录、用户公开资料）允许匿名，不带头。

未带有效 token 的写请求：HTTP 401，`code=unauthorized`，状态不变。

### Content types

请求默认 `Content-Type: application/json`。

响应默认 `application/json; charset=utf-8`。

例外：

- `GET .../assets/{asset_id}/raw`：单文件为该文件的字节（`Content-Type` 按扩展名，未知则 `application/octet-stream`）；多文件资产为 zip，`application/zip`。
- `GET .../translated`（整 bucket）：zip 归档，`application/zip`。响应头带 `X-Red-Bucket-Lossy: true|false`。
- `GET .../assets/{asset_id}/translated`：单文件直接字节，多文件 zip。头同样带 `X-Red-Bucket-Lossy`。JSON 元数据走查询 `?meta=1`（见该端点）。
- `GET .../install-script`：默认 JSON `{target, script}`；`Accept: text/plain` 时只返回脚本正文。

上传与 PR 的文件体用 `content_text`（UTF-8 文本）或 `content_base64`（任意字节）二选一，不要 git patch。

### Pagination

凡返回数组的列表端点（含模板目录、能力矩阵、一层目录树）都分页。Phase 1 只实现 `page` + `per_page`，不实现 cursor 查询，也不要求客户端回传游标。

查询参数：

- `page`：从 1 起，缺省 1。
- `per_page`：默认 30，最大 100；小于 1 按 30。

列表 JSON 外壳：

```json
{
  "items": [],
  "page": 1,
  "per_page": 30,
  "total": 0,
  "has_more": false,
  "next_cursor": null
}
```

`next_cursor` 不是第二套分页协议：有下一页时等于下一页 `page` 的十进制字符串，否则 `null`。翻页只许再传 `page` 与 `per_page`。出现 `cursor` 查询参数 → 422，点名 `cursor`（防止两套实现分叉）。超出最大 `per_page` → 422，点名 `per_page`。

### Location on 201

凡 201 必须带 `Location`，值为该新资源的规范 GET 路径（绝对路径，以 `/api/v1/` 开头）。正文仍是该资源的 JSON。各创建端点的 Location 模板写在对应行。

### Error envelope

4xx/5xx 的 JSON 一律：

```json
{
  "error": {
    "code": "validation_failed",
    "message": "human readable",
    "details": []
  }
}
```

`code` 非空且稳定。`details` 缺省为 `[]`。校验类条目形如 `{"field":"username","rule":"username_invalid","path":null,"message":"..."}`。资产校验条目必须含 `rule`（rule id）与 `path`（资产内文件路径）。

稳定 `code` 一览：

| code | HTTP | 何时 |
| --- | --- | --- |
| `unauthorized` | 401 | 缺 token、token 已撤销、登录凭证不对（不区分用户是否存在） |
| `not_found` | 404 | 资源不存在，或私有 bucket 对非 owner（含匿名） |
| `forbidden` | 403 | 公开资源上角色不够（例如第三人关 issue、第三人评 issue）；以及自己的 bucket 数量触顶 |
| `bucket_quota_exceeded` | 403 | 第 N+1 个 bucket；`details` 含 `limit`、`current` |
| `conflict` | 409 | 用户名、邮箱、bucket 名大小写不敏感冲突 |
| `username_taken` | 409 | 注册或改名时用户名占用 |
| `email_taken` | 409 | 注册时邮箱占用 |
| `bucket_name_taken` | 409 | 同用户下 bucket 名占用 |
| `bucket_storage_exceeded` | 413 | 工作树将超过上限；`details` 含 `usage_bytes`、`limit_bytes` |
| `validation_failed` | 422 | 字段或资产格式 |
| `translation_unsupported` | 501 | 矩阵里没有的翻译对；不得回退未翻译正文 |
| `internal_error` | 500 | 未预期失败 |

### Visibility 404 rule

私有 bucket 的任何子资源（元数据、资产、树、blob、raw、翻译、安装脚本、copies、issues、PRs、commits）对匿名与非 owner：HTTP 404，`code=not_found`，响应体与「该 username 下没有这个 bucket」不可区分。Owner：200（或该子资源自己的 4xx）。不要用 403 表示「私有但存在」。

用户是否存在可以区分：`GET /users/{username}` 在用户不存在时 404；用户存在但只有私有 bucket 时 200，且匿名列表为空。

`GET /users/{username}/buckets`：匿名或非本人只看到 `visibility=public`；owner 看自己的全部（含 private）。私有项不会以 404 出现在别人的列表里，而是直接省略。

已删除 bucket：`buckets.deleted_at` 非空。解析 `{username}/{bucket}` 时必须带 `deleted_at IS NULL`；命不中则 404，与从未存在不可区分。所有挂在该桶下的查询（assets、tree、blob、raw、translated、install-script、copies、issues、comments、pulls、commits）都先走这次解析，禁止只凭子表主键访问。子表行可仍留在 SQLite，但不得再经任何 API 读出。

### Nesting depth

最深集合路径是 4 层：`/users/{username}/buckets/{bucket}/issues/{number}/comments/{comment_id}`（GitHub 同形）。没有第 5 层集合。`.../assets/{id}/raw`、`.../assets/{id}/translated`、`.../pulls/{n}/files|merge|reject` 是既有资源上的表示或动作，不另加一层集合。Phase 1 不把评论再挂到更长的路径下。

### 三个「install」名字（禁止混用一个动词）

| 名字 | 含义 | 端点 |
| --- | --- | --- |
| copy（跨 bucket 复制） | 把公开（或自己的）资产拷进自己的 bucket，写 provenance | `POST .../copies` |
| install-script（安装程序文本） | 返回自包含的 Node 程序正文，给 agent 在本机落盘 | `GET .../install-script` |
| translated fetch（翻译拉取） | 按目标 harness 返回翻译后的内容字节 | `GET .../translated` |

不要用 `POST .../install` 同时表示这三件事。JSON 类型 `InstallRecord` 只描述 copy 的出处行。

### 路径与 ID

对外路径键是 `username` + `bucket`（bucket 名）。内部不可变键是整数 `user.id`、`bucket.id`。资产、评论、copy 用整数 id。Issue / PR 用 bucket 内从 1 递增的 `number`（两套独立序号）。

路径参数 `{*path}` 表示可含 `/` 的相对路径。服务必须拒绝 `..`、绝对路径、`.git/`、逃出工作树的符号链接 → 422 `validation_failed`，树外无读写。

时间戳一律 UTC ISO-8601 字符串。

### 内容写入与 git 归属

凡改工作树的 API 都必须落一笔归属于操作用户（PR merge 则归属于 PR 作者）的 git commit。不改工作树的元数据（可见性、description、改用户名、issue、评论、开/拒 PR）不写 git。对照见文末「写操作 → git」表。

---

## JSON object schemas

未标注 optional 的字段在对应响应里必出现。

### User

```json
{
  "id": 1,
  "username": "alice",
  "created_at": "2026-09-01T00:00:00Z",
  "email": "alice@example.com",
  "bucket_quota": 5,
  "bucket_count": 2
}
```

| 字段 | 类型 | 可见性 |
| --- | --- | --- |
| `id` | int | 公开 |
| `username` | string | 公开 |
| `created_at` | string | 公开 |
| `email` | string | 仅本人（`GET /users/me`、login/register 不回 email 哈希或密码） |
| `bucket_quota` | int | 仅本人 |
| `bucket_count` | int | 仅本人（未删除 bucket 数） |

公开资料（`GET /users/{username}`）只有 `id`、`username`、`created_at`。任何响应都不得含密码、password_hash、token 明文（login 的 `token` 字段除外）。

### Bucket

```json
{
  "id": 10,
  "full_name": "alice/tools",
  "username": "alice",
  "name": "tools",
  "visibility": "public",
  "description": "",
  "template": "claude",
  "usage_bytes": 4096,
  "limit_bytes": 10485760,
  "open_issues_count": 2,
  "open_pulls_count": 1,
  "harness_mix": {"claude": 3, "codex": 1},
  "created_at": "2026-09-01T00:00:00Z",
  "updated_at": "2026-09-01T00:00:00Z"
}
```

`template`：创建时选用的风格，未选则为 `null`。`harness_mix`：当前资产索引里按 `source_harness` 计数。`limit_bytes` 默认 10485760（10 × 1024 × 1024）。`description` 默认 `""`，最长 350。

### Asset

```json
{
  "id": 44,
  "bucket_id": 10,
  "full_name": "alice/tools",
  "type": "skill",
  "source_harness": "claude",
  "path": "skills/demo",
  "size_bytes": 1200,
  "uploader": {"id": 1, "username": "alice"},
  "head_commit_sha": "abc123...",
  "provenance": null,
  "created_at": "2026-09-01T00:00:00Z",
  "updated_at": "2026-09-01T00:00:00Z"
}
```

`type`：`skill` | `mcp` | `instructions` | `subagent` | `plugin`。

`source_harness`：`codex` | `agents` | `claude` | `openclaw`。

`path`：bucket 内资产根路径（目录或单文件）。`provenance`：若由 copy 写入，则为对应 `InstallRecord` 的摘要（`id`、`source_full_name`、`source_commit_sha`、`created_at`），否则 `null`。资产被 DELETE 后该 Asset 对象不再出现；旧 `InstallRecord.dest_asset.id` 为 `null`，`path` 与 `type` 仍来自 copies 快照。

`updated_at` 即 listing 要求的 last-modified time。

### TreeEntry

```json
{
  "name": "skills",
  "path": "skills",
  "entry_type": "dir",
  "size_bytes": 0,
  "last_commit_sha": "abc123...",
  "last_commit_message": "Upload skill skills/demo",
  "last_commit_at": "2026-09-01T00:00:00Z",
  "asset": {"id": 44, "type": "skill", "source_harness": "claude"}
}
```

`entry_type`：`dir` | `file`。`asset`：该路径是已登记资产的根或资产内文件时带类型与源 harness，否则 `null`。目录在前、文件在后（与 Code 页签一致）。一层列表，不递归。

### Commit

```json
{
  "sha": "abc123def456...",
  "short_sha": "abc123d",
  "message": "Upload skill skills/demo",
  "author": {"id": 1, "username": "alice"},
  "authored_at": "2026-09-01T00:00:00Z",
  "paths": ["skills/demo/SKILL.md"]
}
```

`sha` 与 git 对象一致。作者从 commit 的约定邮箱映射回 `users.id`（见 schema 文档）。

### Issue

```json
{
  "id": 7,
  "number": 1,
  "bucket_full_name": "alice/tools",
  "title": "broken skill",
  "body": "markdown",
  "state": "open",
  "author": {"id": 2, "username": "bob"},
  "closed_by": null,
  "created_at": "2026-09-01T00:00:00Z",
  "updated_at": "2026-09-01T00:00:00Z",
  "closed_at": null
}
```

`state`：`open` | `closed`。

### IssueComment

```json
{
  "id": 90,
  "issue_number": 1,
  "bucket_full_name": "alice/tools",
  "body": "markdown",
  "author": {"id": 1, "username": "alice"},
  "created_at": "2026-09-01T00:00:00Z",
  "updated_at": "2026-09-01T00:00:00Z"
}
```

### PullRequest

```json
{
  "id": 3,
  "number": 1,
  "bucket_full_name": "alice/tools",
  "title": "fix skill",
  "body": "markdown",
  "state": "open",
  "author": {"id": 2, "username": "bob"},
  "files": [
    {"path": "skills/demo/SKILL.md", "content_text": "...", "content_base64": null}
  ],
  "merged_commit_sha": null,
  "created_at": "2026-09-01T00:00:00Z",
  "updated_at": "2026-09-01T00:00:00Z",
  "closed_at": null
}
```

`state`：`open` | `merged` | `rejected`。

`files` 是提议的文件树替换列表，不是 git patch。每一项：

| 字段 | 规则 |
| --- | --- |
| `path` | bucket 相对路径，经同一套路径清洗 |
| `content_text` | 与 `content_base64` 互斥；文本文件用这个 |
| `content_base64` | 二进制或调用方不愿猜编码时用这个 |
| `delete` | optional bool；`true` 表示 merge 时删除该路径，此时不得带内容 |

语义：这是一组路径级替换（upsert / delete），应用到 merge 当时的 HEAD，而不是整仓抹掉重写。未出现在 `files` 里的路径保持不动。

为什么不用不透明 git patch：校验器吃的是文件树（rule id + path）；merge 必须重跑格式校验和 10MB 配额，patch 还要先 apply 才能校验。CLI、移动端、MCP 不必会生成 unified diff。二进制与多文件资产用 base64 比 patch 字面量稳。审阅就是 `GET` 这份 `files`。

列表项可省略 `files`（用 `GET .../pulls/{n}/files` 取全文），详情默认带 `files`。

### InstallRecord

```json
{
  "id": 5,
  "dest_full_name": "alice/tools",
  "dest_asset": {"id": 44, "path": "skills/demo", "type": "skill"},
  "source_full_name": "bob/public-skills",
  "source_bucket_id": 22,
  "source_path": "skills/demo",
  "source_commit_sha": "def456...",
  "dest_commit_sha": "abc123...",
  "actor": {"id": 1, "username": "alice"},
  "created_at": "2026-09-01T00:00:00Z"
}
```

只由 `POST .../copies` 产生。目标资产后来被 DELETE 时本行仍在：`dest_asset.id` 为 `null`，`dest_asset.path` 与 `type` 仍是复制当时的快照。源桶被软删不影响本行（`source_full_name` 与 `source_commit_sha` 是快照）。

### Template

```json
{
  "name": "claude",
  "description": "Claude Code 风格目录骨架",
  "files": [
    {"path": "README.md", "content_text": "# bucket\n"},
    {"path": "CLAUDE.md", "content_text": "# CLAUDE.md\n\nProject instructions go here.\n"},
    {"path": "skills/.gitkeep", "content_text": ""},
    {"path": ".claude/settings.json", "content_text": "{}\n"},
    {"path": ".claude/skills/.gitkeep", "content_text": ""},
    {"path": ".claude/agents/.gitkeep", "content_text": ""},
    {"path": ".mcp.json", "content_text": "{\n  \"mcpServers\": {}\n}\n"}
  ]
}
```

Phase 1 四种模板的权威骨架（实现与 S2.7 按此比对）。不选 `template` 的创建得到空工作树、零 commit。

#### template=codex

- `README.md` — `# bucket\n`
- `AGENTS.md` — `# AGENTS.md\n\nProject instructions for Codex-style agents.\n`
- `.codex/config.toml` — `# codex bucket config\n`
- `.codex/skills/.gitkeep` — 空
- `.codex/agents/.gitkeep` — 空
- `.codex/plugins/.gitkeep` — 空
- `.codex/mcp-servers/.gitkeep` — 空

#### template=agents

- `README.md` — `# bucket\n`
- `AGENTS.md` — `# AGENTS.md\n\nGeneric agents-style instructions.\n`
- `skills/.gitkeep` — 空
- `agents/.gitkeep` — 空
- `plugins/.gitkeep` — 空
- `mcp/.gitkeep` — 空

#### template=claude

- `README.md` — `# bucket\n`
- `CLAUDE.md` — `# CLAUDE.md\n\nProject instructions go here.\n`
- `skills/.gitkeep` — 空（与 management spec 示例一致）
- `.claude/settings.json` — `{}\n`
- `.claude/skills/.gitkeep` — 空
- `.claude/agents/.gitkeep` — 空
- `.mcp.json` — `{ "mcpServers": {} }\n`

#### template=openclaw

- `README.md` — `# bucket\n`
- `AGENTS.md` — `# AGENTS.md\n\nOpenClaw-style workspace instructions.\n`
- `.openclaw/openclaw.json` — `{}\n`
- `.openclaw/skills/.gitkeep` — 空
- `.openclaw/agents/.gitkeep` — 空
- `.openclaw/plugins/.gitkeep` — 空
- `.openclaw/mcp/.gitkeep` — 空

选模板创建时，上述文件作为第一次 git commit 写入，作者为创建者。

### TranslationMatrixEntry

```json
{
  "asset_type": "skill",
  "source": "claude",
  "target": "codex",
  "supported": true,
  "identity": false,
  "doc": "cross-transfer/claude-2-codex.md"
}
```

`identity` 为 true 时表示 `source == target`，拉取必须与 raw 逐字节一致，`doc` 可为 `null`。

`supported=false` 的行可以不列出；客户端以「未出现即不支持」为准。列出的 `supported=true` 必须有已验证的 `cross-transfer/<src>-2-<dst>.md`（identity 除外）。

Phase 1 矩阵必须包含（与产品方约束一致；identity 另计）：

- `skill`：`{codex, agents, claude, openclaw}` 的 12 个有序异对 + 4 个 identity
- `instructions`：同上 12 + 4 identity
- `plugin`：同上 12 + 4 identity（与 skill 同等一等公民）
- `subagent`：同上 12 + 4 identity（与 skill 同等一等公民）
- `mcp`：`claude→codex`、`codex→claude`；任意已存 mcp 的 identity（src=dst）仍走 raw 字节

不在上表的对（例如 `mcp` 的 `agents→claude`）→ 501 `translation_unsupported`。

### Error

见 Conventions 中的 envelope。`details` 为对象数组。

### FileEntry（上传与 PR 共用，不是独立顶层资源）

```json
{
  "path": "SKILL.md",
  "content_text": "---\nname: demo\n",
  "content_base64": null,
  "delete": false
}
```

---

## Endpoint table

路径均相对 origin。`Auth` 列：`none` 可匿名；`bearer` 必须登录；`owner` 必须是该 bucket 的 owner（否则按 404 规则，用户级资料则 401/403 见该行）。

私有 bucket 列里的「非 owner」包括匿名。

---

### Auth

#### POST /api/v1/auth/register

- Auth: none
- Request: `{"username":"alice","email":"alice@example.com","password":"secret123"}`
- Response 201: 公开 User（`id`,`username`,`created_at`）。`Location: /api/v1/users/{username}`。不签发 token，不含 email（email 只在 `GET /users/me`）。
- 规则：用户名唯一（大小写不敏感），3–39，`[a-z0-9]([a-z0-9-]*[a-z0-9])?`。邮箱唯一（大小写不敏感），须为可解析邮箱。密码长度 ≥ 8（这是接口硬规则，不只是场景叙述）。
- Errors: 409 `username_taken` 或 `email_taken`；422 `validation_failed`（点名 `username` / `email` / `password`）

#### POST /api/v1/auth/login

- Auth: none
- Request: `{"email":"alice@example.com","password":"secret123"}`
- Response 200: `{"token":"<opaque>","token_type":"bearer","user":{公开 User + email,bucket_quota,bucket_count}}`
- Errors: 401 `unauthorized`（用户不存在与密码错同一响应）；422 缺字段

#### POST /api/v1/auth/logout

- Auth: bearer（当前这枚 token）
- Request: `{}` 或空对象
- Response 204: 无正文。该 token 行设 `revoked_at`，之后再用 → 401
- Errors: 401 `unauthorized`

---

### Users

#### POST /api/v1/auth/device

- Auth: 无
- Request: `{"client": "claude"}`（可选，最多 60 字符，只作展示用）
- Response 201:

```json
{
  "device_code": "<只回这一次，留在 agent 进程内>",
  "user_code": "BQ7K-2M4X",
  "verification_url": "https://redbucket.store/link",
  "verification_url_complete": "https://redbucket.store/link/BQ7K-2M4X",
  "expires_in": 600,
  "interval": 5
}
```

`user_code` 字母表排除 I L O U 0 1。库内只存 `device_code` 的 SHA-256。

#### POST /api/v1/auth/device/token

- Auth: 无（`device_code` 本身即凭证）
- Request: `{"device_code": "..."}`
- Response 200: `{"status":"pending"}`、`{"status":"denied"}`，
  或 `{"status":"approved","token":"...","token_type":"bearer","user":{...}}`
- Errors: 404 未知 / 已过期 / 已取走，三者不可区分。一次性：
  取走 token 之后同一个 code 永远 404。

#### GET /api/v1/auth/device/{user_code}

- Auth: 无
- Response 200: `{"user_code","client","state","created_at"}`，
  供 `/link/<user_code>` 页面展示。不含 `device_code`。
- Errors: 404 未知或已过期

#### POST /api/v1/auth/device/{user_code}/decision

- Auth: bearer，必须是要授权的那个人
- Request: `{"approve": true}`
- Response 200: `{"user_code","state"}`，state 为 `approved` 或 `denied`
- Errors: 401 未认证；404 未知或已过期；409 `device_code_used` 已经决定过

#### GET /api/v1/users/me

- Auth: bearer
- Request: 无
- Response 200: 本人 User（含 `email`、`bucket_quota`、`bucket_count`）
- Errors: 401

#### PATCH /api/v1/users/me

- Auth: bearer
- Request: `{"username":"alice2"}`（Phase 1 只接受 `username`；忽略未知字段或 422）
- Response 200: 更新后的本人 User
- 行为：只改 `users.username` / `username_normalized`。磁盘 `<storage-root>/<user-id>/` 不动。之后所有路径用新用户名。
- Errors: 401；409 `username_taken`；422 用户名规则

本端点是为 git-storage「改用户名后仓库不搬家」场景提供的元数据口子，不是改名 UI 产品。没有改邮箱、改密码、改 `bucket_quota` 的公开字段（`bucket_quota` 只允许运维改库，S2.5 测的是存储字段生效，不是本 PATCH）。

#### GET /api/v1/users/{username}

- Auth: none
- Request: 无
- Response 200: 公开 User（无 email）
- Errors: 404 用户不存在

---

### Buckets

#### GET /api/v1/users/{username}/buckets

- Auth: none（本人带 bearer 时看到私有）
- Query: `page`,`per_page`
- Request: 无
- Response 200: 分页 `items`: Bucket[]
- 可见性：用户不存在 → 404。匿名或非本人 → 只 `public`。`{username}` 等于当前用户 → 含 `private`。
- Errors: 404 用户不存在；422 分页参数

#### POST /api/v1/users/{username}/buckets

- Auth: bearer，且 `{username}` 必须是自己
- Request: `{"name":"tools","visibility":"public","description":"","template":"claude"}`
- 字段：`name` 必填，1–100，`[a-z0-9]([a-z0-9._-]*[a-z0-9])?`，每用户大小写不敏感唯一。`visibility`：`public`|`private`，缺省 `private`。`description` optional，默认 `""`，≤350。`template` optional：`codex`|`agents`|`claude`|`openclaw`。
- Response 201: Bucket。`Location: /api/v1/users/{username}/buckets/{name}`
- Git：有 template → 骨架为第一次 commit，作者=创建者。无 template → 空仓、零 commit。
- Errors: 401；403 `{username}` 不是自己（用户存在）或 `bucket_quota_exceeded`（`details.limit`,`details.current`）；404 用户不存在；409 `bucket_name_taken`；422 名称/description/未知 template

#### GET /api/v1/users/{username}/buckets/{bucket}

- Auth: none；私有仅 owner
- Response 200: Bucket（含 usage、limit、description、harness_mix、open counts）
- Errors: 404 不存在或私有对非 owner

#### PATCH /api/v1/users/{username}/buckets/{bucket}

- Auth: owner
- Request: `{"visibility":"private","description":"about"}`（字段皆 optional）
- Response 200: Bucket
- Git：无。public→private 之后匿名/非 owner 全部 404，owner 仍 200。
- Errors: 401；404 非 owner 或缺失；422 description>350 或非法 visibility

#### DELETE /api/v1/users/{username}/buckets/{bucket}

- Auth: owner
- Request: 无
- Response 204
- 行为：置 `deleted_at`，不删子表行。列表与 `bucket_count` 不再计入。底层 git 可带外保留。之后解析 `{username}/{bucket}` 必须 `deleted_at IS NULL`，所有子路由 404。允许之后用同名再创建一个新 bucket（新 `bucket.id`）。旧子表行仍挂在旧 `bucket.id` 上，不会漏到新桶。
- Errors: 401；404 非 owner 或缺失

---

### Templates

#### GET /api/v1/templates

- Auth: none
- Query: 分页
- Response 200: `items` 至少 4 个 Template（`name`,`description`,`files`）
- Errors: 422 分页

#### GET /api/v1/templates/{name}

- Auth: none
- Response 200: 单个 Template（含完整 `files` 骨架）
- Errors: 404 未知 name

---

### Assets

#### GET /api/v1/users/{username}/buckets/{bucket}/assets

- Auth: none；私有仅 owner
- Query: 分页；optional `type`、`source_harness`
- Response 200: `items`: Asset[]（每项含 type、source_harness、path、size_bytes、updated_at）
- Errors: 404 私有/缺失；422

#### POST /api/v1/users/{username}/buckets/{bucket}/assets

- Auth: owner
- Request:

```json
{
  "type": "skill",
  "source_harness": "claude",
  "path": "skills/demo",
  "files": [
    {"path": "SKILL.md", "content_text": "---\nname: demo\ndescription: d\n---\n"}
  ]
}
```

`files[].path` 相对 `path`（资产根）。`type` 与 `source_harness` 必填，未知或缺省 → 422，不写仓。先按类型校验，再在每 bucket 锁内原子「先检查工作树大小再 commit」。

同路径再 POST = 更新，新 commit。

- Response 201: Asset。`Location: /api/v1/users/{username}/buckets/{bucket}/assets/{asset_id}`
- Git: commit 作者=上传者
- Errors: 401；404 非 owner/缺失；413 `bucket_storage_exceeded`；422 `validation_failed`（violations 在 `details`，含 rule id + path）

#### GET /api/v1/users/{username}/buckets/{bucket}/assets/{asset_id}

- Auth: none；私有仅 owner
- Response 200: Asset
- Errors: 404

#### DELETE /api/v1/users/{username}/buckets/{bucket}/assets/{asset_id}

- Auth: owner
- Response 204
- 行为：从工作树删除该资产路径下全部文件，硬删 `assets` 行，usage 重算。指向该行的 `copies.dest_asset_id` 由 FK `ON DELETE SET NULL` 置空；`copies` 行保留，`dest_asset.path` 与 `type` 读复制时写入的快照列，`dest_asset.id` 为 `null`。`GET .../copies` 仍列出这些记录。`GET .../assets/{id}` 404。Code 页签需要这一笔，与「整桶 DELETE」分开。
- Git: commit 作者=owner，说明删除路径
- Errors: 401；404 非 owner/缺失资产/缺失桶

#### GET /api/v1/users/{username}/buckets/{bucket}/assets/{asset_id}/raw

- Auth: none；私有仅 owner
- Query: optional `commit`（历史 sha；缺省 HEAD）
- Response 200: 所存原样字节（单文件或 zip）。不做翻译。
- Errors: 404；422 非法 commit / 该 commit 无此路径

---

### Tree and blob（Code 页签）

#### GET /api/v1/users/{username}/buckets/{bucket}/tree

- Auth: none；私有仅 owner
- Query: 分页；optional `commit`
- Response 200: 分页 TreeEntry[]（工作树根，一层）。另在对象外可带 `latest_commit`: Commit 或 `null`（空仓）。实现上允许在 JSON 外壳增加 `latest_commit`、`commit_count` 字段（非 items）。
- 空 bucket：`items=[]`，`latest_commit=null`，`commit_count=0`。Owner 与访客同一 JSON；UI 用是否 owner 决定是否显示添加提示。
- Errors: 404；422

#### GET /api/v1/users/{username}/buckets/{bucket}/tree/{*path}

- Auth: none；私有仅 owner
- Query: 分页；optional `commit`
- Response 200: 该目录一层 TreeEntry[]。`README.md` 大小写不敏感：若存在，条目 `name` 保留真实大小写。
- Errors: 404 桶或路径不是目录；422 路径清洗失败

#### GET /api/v1/users/{username}/buckets/{bucket}/blob/{*path}

- Auth: none；私有仅 owner
- Query: optional `commit`；optional `encoding=text|base64`（默认文本若是合法 UTF-8，否则 base64）
- Response 200:

```json
{
  "path": "README.md",
  "size_bytes": 12,
  "content_text": "# bucket\n",
  "content_base64": null,
  "last_commit_sha": "abc...",
  "last_commit_message": "...",
  "last_commit_at": "..."
}
```

- Errors: 404 桶或文件不存在或私有；422 路径是目录或穿越

---

### Commits

#### GET /api/v1/users/{username}/buckets/{bucket}/commits

- Auth: none；私有仅 owner
- Query: 分页
- Response 200: `items`: Commit[]，新到旧
- Errors: 404；422

#### GET /api/v1/users/{username}/buckets/{bucket}/commits/{sha}

- Auth: none；私有仅 owner
- Response 200: Commit（含 `paths`）
- Errors: 404

按历史取内容：`raw` / `tree` / `blob` / `translated` 的 `?commit=`。

---

### Translation

#### GET /api/v1/translation-matrix

- Auth: none
- Query: 分页；optional `asset_type`、`source`、`target`
- Response 200: `items`: TranslationMatrixEntry[]，与代码注册表一致
- Errors: 422

#### GET /api/v1/users/{username}/buckets/{bucket}/translated

- Auth: none；私有仅 owner
- Query: `target` 必填（`codex`|`agents`|`claude`|`openclaw`）；optional `commit`
- Response 200: zip。每个可翻译资产已转换并放在目标 harness 布局。头 `X-Red-Bucket-Lossy`。缓存键 `(commit, target)`。
- 某资产对 `(type,src,target)` 不支持：整桶请求仍 200，但跳过该资产并在可选旁路 `GET .../translated?meta=1` 的 JSON 里列出 skipped（默认 zip 内附 `_red_bucket/lossy-notes.md` 与 skipped 清单，避免静默丢文件却 200 无提示）。不支持且调用方传 `?strict=1` → 501。
- 默认（无 `strict`）：能译则译，不能译的写入 notes，不回未翻译原文冒充目标格式。
- Errors: 404；400/422 缺 `target`；501 仅 `strict=1` 且存在不支持对

整桶默认「能译则译」是为了 S4.5（归档内每个可翻译资产落位）。对单资产端点，不支持必须 501。

#### GET /api/v1/users/{username}/buckets/{bucket}/assets/{asset_id}/translated

- Auth: none；私有仅 owner
- Query: `target` 必填；optional `commit`；optional `meta=1`
- Response 200: 翻译后字节（或 zip）。Identity（`target == source_harness`）与同 `commit` 的 raw 逐字节一致。有损则头 `X-Red-Bucket-Lossy: true`，体内含 compatibility notes（按该对文档的位置）。`meta=1` 时响应改为 JSON：`{"lossy":true,"notes":"...","filename":"..."}` 加链接头指向同一 URL 无 meta 的字节。
- 确定性：同 commit 同 target 两次字节一致（缓存命中与未命中）。
- Errors: 404；422 缺 target；501 `translation_unsupported`（不得返回未翻译源正文）

---

### Install-script（文本，不是 copy）

#### GET /api/v1/users/{username}/buckets/{bucket}/install-script

- Auth: none；私有仅 owner
- Query: `target` 必填
- Response 200 JSON: `{"target":"claude","script":"#!/usr/bin/env node\n...","translated_url":"/api/v1/users/alice/buckets/tools/translated?target=claude"}`
- `Accept: text/plain` → 200，正文即 `script`。
- `script` 是自包含的 Node 程序（Node 18+，ESM，存成 `.mjs` 后 `node` 执行），只用 Node 内建模块；不依赖 `sh`、`curl`、`unzip`、`jq` 或 npm 包。
- 官方 origin 是 `https://redbucket.store`。程序必须把基础 URL 做成可替换模板（未设 `RED_BUCKET_URL` 时落到官方 origin），落盘根目录由 `RED_BUCKET_DEST` 覆盖。执行后：下载该 bucket 的 translated 归档，按目标 harness 本地布局落盘，退出 0。程序只调用本目录中的公开 GET，并拒绝归档里的绝对路径与目录逃逸。
- Errors: 404；422 缺 target / 非法 target（四种之外）

非法 target 是参数错（422），不是 501。501 留给「target 合法但某个资产对不在矩阵」。脚本内部拉 translated 时走默认整桶行为。

---

### Copies（跨 bucket 复制 + provenance）

#### GET /api/v1/users/{username}/buckets/{bucket}/copies

- Auth: none；私有仅 owner（读的是目标桶上的出处记录）
- Query: 分页
- Response 200: `items`: InstallRecord[]
- Errors: 404 目标桶不存在或私有对非 owner；422 分页

#### POST /api/v1/users/{username}/buckets/{bucket}/copies

- Auth: bearer，且 `{username}/{bucket}` 必须是自己的目标桶（owner）
- Request:

```json
{
  "source_username": "bob",
  "source_bucket": "public-skills",
  "source_asset_id": 12,
  "dest_path": "skills/demo"
}
```

`dest_path` optional，缺省为源资产的 `path`。源必须是调用方可读的桶：公开，或调用方自己的私有桶。从他人私有桶 copy → 404（与源不存在不可区分）。源桶已软删 → 404。先跑与上传相同的校验流水线，再在目标桶锁内原子配额检查，然后写入文件、assets 行、InstallRecord，并 commit。写入 copies 时同时记下 `dest_path` 与 `dest_type` 快照。目标 `dest_path` 已有资产时与再次上传同路径相同：更新该行、新 commit、新 InstallRecord（`assets.source_copy_id` 指向最新一条）。

- Response 201: InstallRecord（`dest_asset` 已填）。`Location: /api/v1/users/{username}/buckets/{bucket}/copies/{copy_id}`
- Git: commit 作者=actor（当前用户），说明含源 `full_name` 与 `source_commit_sha`
- Errors: 401；404 目标非自己的桶、或源不可见/不存在；413 目标将超 10MB，目标仓不变；422 校验失败或路径清洗

#### GET /api/v1/users/{username}/buckets/{bucket}/copies/{copy_id}

- Auth: none；私有仅 owner
- Response 200: InstallRecord
- Errors: 404

---

### Issues

私有桶：非 owner 开、读、评、关全部 404。Owner 可以在自己的私有桶上开 issue（spec 只禁止非 owner，不禁止 owner）。公开桶：匿名可读；任何已认证用户可开；仅 issue 作者与 bucket owner 可评论、可关闭。第三人关或评 → 403 `forbidden`（这是公开资源上的角色拒绝，不是私有隐藏，故不用 404）。

#### GET /api/v1/users/{username}/buckets/{bucket}/issues

- Auth: none；私有仅 owner
- Query: 分页；optional `state=open|closed`
- Response 200: `items`: Issue[]（编号、标题、state、作者、created_at）
- Errors: 404；422

#### POST /api/v1/users/{username}/buckets/{bucket}/issues

- Auth: bearer
- Request: `{"title":"broken skill","body":"markdown"}`
- Response 201: Issue，`number` 为该桶内从 1 递增。`Location: /api/v1/users/{username}/buckets/{bucket}/issues/{number}`
- Git: 无
- Errors: 401；404 私有对非 owner 或桶不存在；422 缺 title

#### GET /api/v1/users/{username}/buckets/{bucket}/issues/{number}

- Auth: none；私有仅 owner
- Response 200: Issue
- Errors: 404

#### PATCH /api/v1/users/{username}/buckets/{bucket}/issues/{number}

- Auth: bearer，且必须是 issue 作者或 bucket owner
- Request: `{"state":"closed"}`（Phase 1 只接受关；不发明 reopen）
- Response 200: Issue（`closed_by`、`closed_at` 已填）
- Git: 无
- Errors: 401；403 第三人；404 私有/缺失；422 非法 state

---

### Issue comments

评论是一等资源。作者与 owner 可发。第三人 → 403。匿名可读公开桶上的评论。

#### GET /api/v1/users/{username}/buckets/{bucket}/issues/{number}/comments

- Auth: none；私有仅 owner
- Query: 分页
- Response 200: `items`: IssueComment[]
- Errors: 404；422

#### POST /api/v1/users/{username}/buckets/{bucket}/issues/{number}/comments

- Auth: bearer，且必须是 issue 作者或 bucket owner
- Request: `{"body":"markdown"}`
- Response 201: IssueComment。`Location: /api/v1/users/{username}/buckets/{bucket}/issues/{number}/comments/{comment_id}`
- Git: 无
- Errors: 401；403 第三人；404 私有/缺失 issue；422 空 body

#### GET /api/v1/users/{username}/buckets/{bucket}/issues/{number}/comments/{comment_id}

- Auth: none；私有仅 owner
- Response 200: IssueComment
- Errors: 404

Phase 1 不提供编辑或删除评论。

---

### Pull requests

仅公开桶接受非 owner 的 PR。私有桶：非 owner 全部 404；owner 向自己的私有桶开 PR 允许（与 issue 相同口径）。提议内容为 `files` 文件树替换列表，见 PullRequest schema。

审阅 = `GET` 详情与 `GET .../files`。没有独立 review 资源。

#### GET /api/v1/users/{username}/buckets/{bucket}/pulls

- Auth: none；私有仅 owner
- Query: 分页；optional `state=open|merged|rejected`
- Response 200: `items`: PullRequest[]（列表省略 `files`）
- Errors: 404；422

#### POST /api/v1/users/{username}/buckets/{bucket}/pulls

- Auth: bearer
- Request: `{"title":"fix skill","body":"markdown","files":[{"path":"skills/demo/SKILL.md","content_text":"..."}]}`
- Response 201: PullRequest（含 `files`），`number` 该桶 PR 序号从 1 递增。`Location: /api/v1/users/{username}/buckets/{bucket}/pulls/{number}`
- Git: 此时不写工作树。`files` 存在 SQLite。
- Errors: 401；404 私有对非 owner 或桶不存在；422 缺 title / 空 files / 路径清洗 / 同一 path 重复

#### GET /api/v1/users/{username}/buckets/{bucket}/pulls/{number}

- Auth: none；私有仅 owner
- Response 200: PullRequest（含 `files`）
- Errors: 404

#### GET /api/v1/users/{username}/buckets/{bucket}/pulls/{number}/files

- Auth: none；私有仅 owner
- Query: 分页（按 path 排序）
- Response 200: `items`: FileEntry[]（与创建时 payload 相同）
- Errors: 404；422

#### POST /api/v1/users/{username}/buckets/{bucket}/pulls/{number}/merge

- Auth: owner
- Request: `{}`
- Response 200: PullRequest（`state=merged`，`merged_commit_sha` 已填）
- 行为：在每桶锁内，把 `files` apply 到 HEAD，重跑与上传相同的校验 + 原子配额检查，通过则 commit，作者=PR 作者（不是 merge 的 owner），状态 `merged`。失败则 PR 保持 `open`，工作树不变。
- Git: 一笔 commit，author = PR 作者
- Errors: 401；404 非 owner/缺失/已非 open；413 配额；422 校验失败

对已 `merged`/`rejected` 再 merge → 409 `conflict`（不是 404，公开 PR 存在性可披露）。

#### POST /api/v1/users/{username}/buckets/{bucket}/pulls/{number}/reject

- Auth: owner
- Request: `{}`
- Response 200: PullRequest（`state=rejected`）
- Git: 无，工作树不变
- Errors: 401；404 非 owner/缺失；409 已非 open

---

## 写操作 → git 归属

| API | 改工作树 | git commit 作者 | 说明 |
| --- | --- | --- | --- |
| POST /auth/register, login, logout | 否 | — | |
| PATCH /users/me | 否 | — | 只改 username 元数据 |
| POST .../buckets（无 template） | 否（空树） | — | 零 commit |
| POST .../buckets（有 template） | 是 | 创建者 | 骨架为第一次 commit |
| PATCH .../buckets | 否 | — | visibility / description |
| DELETE .../buckets | 否（API 不可寻址） | — | git 可带外留存 |
| POST .../assets | 是 | 上传者 | 创建或更新 |
| DELETE .../assets/{id} | 是 | owner | 单资产删除 |
| POST .../copies | 是 | actor | 拷贝 + provenance |
| POST .../issues, PATCH issue, 评论 | 否 | — | |
| POST .../pulls | 否 | — | files 只进 SQLite |
| POST .../pulls/{n}/merge | 是 | PR 作者 | 重跑校验与配额 |
| POST .../pulls/{n}/reject | 否 | — | |

每次内容变更在该桶 `git log` 中恰好一笔，工作树与 API 所见一致。改工作树的写只有上表五行「是」：带 template 的创建、POST assets、DELETE assets、POST copies、POST merge。没有漏网的内容写。

---

## 私有桶读：404 与 200

对 `GET /users/{username}/buckets/{bucket}` 及其全部子资源（assets、tree、blob、raw、translated、install-script、copies、issues、comments、pulls、commits）：

- 桶不存在：404
- 桶 private 且请求方不是 owner（含匿名）：404，与上一种不可区分
- 桶 private 且请求方是 owner：200（子资源自身缺失仍 404，但桶的存在已由兄弟路由可观察，仅对 owner）
- 桶 public：200（子资源缺失 404）

`GET /users/{username}/buckets`：见该端点，私有项对非本人是省略不是 404。软删桶（`deleted_at` 非空）对任何人都不得出现在该列表，其子路由一律 404。

---

## Coverage matrix

### OpenSpec requirements → endpoints

| Spec requirement | Endpoint(s) |
| --- | --- |
| identity: User registration | POST /auth/register |
| identity: Authentication for write operations | POST /auth/login；POST /auth/logout；全部写端点 401 |
| identity: Anonymous read access to public content | 全部公开 GET（buckets 列表与详情、assets、raw、tree、blob、commits、translated、install-script、issues、comments、pulls、templates、translation-matrix） |
| identity: Owner-only access to private buckets | 上列资源对非 owner 404 |
| identity: Token revocation | POST /auth/logout |
| identity: Username change is metadata only | PATCH /users/me |
| identity / git-storage: 改用户名不搬家 | PATCH /users/me |
| management: Bucket creation under user namespace | POST /users/{u}/buckets；GET /users/{u}/buckets |
| management: Bucket list visibility | GET /users/{u}/buckets |
| management: Bucket count quota | POST /users/{u}/buckets → 403 bucket_quota_exceeded |
| management: Bucket description | POST/PATCH buckets；GET bucket |
| management: Visibility change | PATCH buckets |
| management: Bucket creation from template | POST buckets + `template`；GET /templates；GET /templates/{name} |
| management: Bucket deletion | DELETE buckets |
| assets: Supported asset types | POST/GET assets（五类） |
| assets: Format validation on upload | POST assets → 422 details |
| assets: Upload commits to bucket history | POST assets；GET commits |
| assets: Per-bucket storage quota | POST assets / copies / merge → 413；GET bucket.usage_bytes |
| assets: Raw asset download | GET .../assets/{id}/raw |
| assets: Owner can delete a single asset | DELETE .../assets/{id} |
| formatter: Fetch-time translation | GET .../translated；GET .../assets/{id}/translated |
| formatter: Supported translation pairs declared | GET /translation-matrix；单资产 501 |
| formatter: Functional equivalence | 无新端点；S8 实验 + 矩阵 `supported` |
| formatter: Translation rule documents | 矩阵 `doc` 字段；静态文件 |
| formatter: Deterministic translation | GET translated（缓存键 commit,target） |
| formatter: plugin/subagent 12 异对（与 skill 同等；tasks 4.2–4.4） | GET /translation-matrix |
| collaboration: Issues on public buckets | GET/POST/PATCH .../issues |
| collaboration: Issue comments as first-class resources | GET/POST .../issues/{n}/comments |
| collaboration: Pull requests on public buckets | GET/POST .../pulls；GET .../files；POST merge；POST reject |
| collaboration: Cross-bucket copy | POST/GET .../copies |
| rest-api: Full-lifecycle REST coverage | 本目录全部；S10 脚本 |
| rest-api: List pagination | 全部列表端点 `page`/`per_page` |
| rest-api: Created resources expose Location | 全部 201 |
| metadata-store: SQLite schema is the metadata contract | 非端点；S11 对表 |
| metadata-store: API fields map to schema columns | 本目录 JSON ⇔ schema 映射表 |
| metadata-store: Live bucket predicate | 全部桶作用域路由 |
| metadata-store: Copies survive dest asset hard delete | DELETE asset；GET copies |
| rest-api: Uniform error model | 全部 4xx/5xx |
| rest-api: Latency service objective | 无新端点；S9 按端点类打本目录 |
| rest-api: One-click install script entry | GET .../install-script |
| git-storage: Git repository per bucket | 内容写入端点的 commit 故事 |
| git-storage: Per-user isolation | 路径清洗 422；存储按 user.id |
| git-storage: Quota accounting | usage 字段 + 锁内 check-then-commit |
| git-storage: History inspectability | GET commits；`?commit=` on raw/tree/blob/translated |
| web-ui: Public browsing pages | GET user、GET buckets、GET bucket、tree、blob、install-script、issues、pulls（HTML 另述） |
| web-ui: Authenticated management pages | register/login/logout、POST/PATCH/DELETE buckets、POST/DELETE assets、issues/comments/PRs、copies；禁止私有 UI 端点 |
| web-ui: Visual style / red mark / tabs / About | 非 API；数据来自 GET bucket（counts、usage、description、harness_mix、template）+ tree + blob(README) |
| web-ui: Settings 仅 owner | 无 /settings API；非 owner 对 PATCH/DELETE 404；HTML /settings 自行 404 |

### Test-plan suite items → endpoints

| Suite item | Endpoint(s) |
| --- | --- |
| S1.1 注册成功 201 Location 无凭证无 email | POST /auth/register |
| S1.2 用户名大小写冲突 409 username_taken | POST /auth/register |
| S1.2a 邮箱大小写冲突 409 email_taken | POST /auth/register |
| S1.2b 密码短于 8 → 422 | POST /auth/register |
| S1.3 非法用户名 422 | POST /auth/register |
| S1.4 未认证写 401 无变化 | POST .../buckets；POST .../assets |
| S1.5 登录发 token；错密码或不存在邮箱 401 不区分 | POST /auth/login |
| S1.5a 登出后 token 失效 | POST /auth/logout；GET /users/me |
| S1.5b PATCH 用户名不搬家 | PATCH /users/me |
| S1.6 匿名读公开列表+下载 | GET .../assets；GET .../raw |
| S1.7 匿名/非 owner 私有 404 | GET bucket 及子资源 |
| S1.8 owner 列表含 private；陌生人只见 public | GET /users/{u}/buckets |
| S2.1 / 2.1a 创建与 description ≤350 | POST/PATCH buckets；GET bucket |
| S2.2 同名大小写 409 | POST buckets |
| S2.3 非法名 422 | POST buckets |
| S2.4 第 6 个 403；删除后再建 | POST/DELETE buckets |
| S2.5 每用户限额字段改为 6 | 改库后 POST buckets（无公开改配额 API） |
| S2.6 public→private 匿名 404 owner 200 | PATCH buckets；GET bucket |
| S2.7 四模板骨架 + 目录 4 种 | POST buckets?template=；GET /templates |
| S2.8 删除后全路由 404 | DELETE buckets；其后任意引用 |
| S3.1 五类型合法上传 201 列表字段 | POST/GET assets |
| S3.2 非法样本 422 无写入 | POST assets |
| S3.3 未声明/未知类型 422 | POST assets |
| S3.4 两版本 → 两 commit | POST assets ×2；GET commits |
| S3.5 9.5+1MB → 413 内容不变 | POST assets |
| S3.6 元数据 usage 与 10MB | GET bucket |
| S3.7 raw 逐字节 | GET .../raw |
| S3.8 DELETE 单资产 + copies 快照 | DELETE .../assets/{id}；GET copies |
| S4.1 矩阵含 skill/instructions/plugin/subagent 12 + mcp claude↔codex | GET /translation-matrix |
| S4.2 golden fixture | GET .../translated（测 formatter，非新端点） |
| S4.3 identity = raw | GET translated 与 GET raw |
| S4.4 不支持 501 | GET .../assets/{id}/translated |
| S4.5 整桶翻译归档 | GET .../translated |
| S4.6 lossy + notes | GET translated（头与 notes） |
| S4.7 两次确定性 | GET translated ×2 |
| S4.8 文档一致性 | GET matrix + 静态 cross-transfer |
| S5.1 非 owner 开 issue 201 匿名可读 | POST/GET issues |
| S5.2 私有非 owner 开 issue 404 | POST issues |
| S5.3 第三人关 403；作者与 owner 可关 | PATCH issues |
| S5.3 补充：作者与 owner 评论 | POST .../comments |
| S5.4 PR 提交→merge 内容生效作者为 PR 作者 | POST pulls；POST merge；GET commits |
| S5.5 merge 校验 422 / 配额 413，PR 仍 open | POST merge |
| S5.6 reject 不改仓 | POST reject |
| S5.7 跨桶 copy + provenance + commit | POST copies；GET copies；GET assets |
| S5.8 copy 超配额 413；他人私有源 404 | POST copies |
| S6.1–S6.11 UI | 只读走 GET user/buckets/bucket/tree/blob/issues/pulls/install-script；写走本目录；无私有端点 |
| S7.1 每次变更一笔 commit | 见「写操作 → git」 |
| S7.2 改用户名不搬盘 | PATCH /users/me |
| S7.3 路径穿越 422 | POST assets / POST pulls |
| S7.4 符号链接剥离 | POST assets |
| S7.5 并发配额至多一次成功 | POST assets（锁） |
| S7.6 按历史 commit fetch | GET raw?commit= |
| S8 等价性实验 | 无新端点 |
| S9 浏览/列表/raw/翻译/写混入 | GET user、GET buckets、GET bucket；GET assets；GET raw；GET translated；POST assets、POST issues |
| S10.1 纯 API 生命周期含登出 | register→login→POST buckets+template→POST assets→PATCH visibility→GET translated→logout→再写失败→重登 DELETE |
| S10.2 错误模型 401/403/404/409/413/422/501 | 各触发点 |
| S10.3 分页 page/per_page；cursor 422 | 任一列表 GET |
| S10.4 Endpoint count 双向一致；无 POST .../install | 本目录全部 |
| S11.1–S11.4 schema 九表、活桶、字段映射、WAL | 非新端点 |

---

## Future CLI / MCP / App

Phase 1 不为这些客户端增加端点。它们复用上表。

CLI（日后）：`register`/`login`/`logout`；`GET/POST/PATCH/DELETE` buckets；`POST/GET/DELETE` assets 与 raw；`GET translated`；`POST copies`；`GET install-script`（可 `Accept: text/plain`）；issues/PRs 与 Web 相同。分页只用 `page` 与 `per_page`。

MCP server（日后）：只读工具走 `GET /translation-matrix`、`GET .../translated`、`GET .../assets`、`GET .../blob`、`GET /templates`；写入工具走 `POST assets`、`POST copies`。用 Bearer。不要为 MCP 做另一套 RPC。

移动 App（日后，ADR 明确首期不做上架）：登录与资料走 auth + `GET /users/me`；浏览走与 UI 相同的 GET；管理走相同写端点。安装体验调 `GET install-script` 或直接 `GET translated`。

Web UI 网络日志必须只有 `/api/v1/`（加静态 logo）。Settings 页没有独立 API。

---

## Endpoint count

上表独立路径（method + path 模板）共 43：

1. POST /api/v1/auth/register
2. POST /api/v1/auth/login
3. POST /api/v1/auth/logout
4. GET /api/v1/users/me
5. PATCH /api/v1/users/me
6. GET /api/v1/users/{username}
7. GET /api/v1/users/{username}/buckets
8. POST /api/v1/users/{username}/buckets
9. GET /api/v1/users/{username}/buckets/{bucket}
10. PATCH /api/v1/users/{username}/buckets/{bucket}
11. DELETE /api/v1/users/{username}/buckets/{bucket}
12. GET /api/v1/templates
13. GET /api/v1/templates/{name}
14. GET .../assets
15. POST .../assets
16. GET .../assets/{asset_id}
17. DELETE .../assets/{asset_id}
18. GET .../assets/{asset_id}/raw
19. GET .../tree
20. GET .../tree/{*path}
21. GET .../blob/{*path}
22. GET .../commits
23. GET .../commits/{sha}
24. GET /api/v1/translation-matrix
25. GET .../translated
26. GET .../assets/{asset_id}/translated
27. GET .../install-script
28. GET .../copies
29. POST .../copies
30. GET .../copies/{copy_id}
31. GET .../issues
32. POST .../issues
33. GET .../issues/{number}
34. PATCH .../issues/{number}
35. GET .../issues/{number}/comments
36. POST .../issues/{number}/comments
37. GET .../issues/{number}/comments/{comment_id}
38. GET .../pulls
39. POST .../pulls
40. GET .../pulls/{number}
41. GET .../pulls/{number}/files
42. POST .../pulls/{number}/merge
43. POST .../pulls/{number}/reject
