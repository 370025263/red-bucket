# Phase 1 SQLite 元数据 schema

本文是 `add-red-bucket-mvp` 的元数据契约。SQLite（WAL）只存可查询元数据。每个 bucket 的文件字节与历史只在文件系统 git：`<storage-root>/<user-id>/<bucket-id>.git`。数据访问层保持很薄，列类型按可迁 Postgres 来选（整数主键、TEXT 时间戳、不写 SQLite 专有 JSON1 约束）。

Logo / 静态文件不是表。模板骨架、翻译注册表、翻译结果缓存都不是表：模板与矩阵来自代码；翻译缓存键 `(commit, target)` 落在文件系统缓存目录。

---

## ER description

```
users 1──* tokens
users 1──* buckets
users 1──* issues          (as author / closed_by)
users 1──* issue_comments  (as author)
users 1──* pull_requests   (as author)
users 1──* copies          (as actor)
users 1──* assets          (as uploader)

buckets 1──* assets
buckets 1──* copies        (destination)
buckets 1──* issues
buckets 1──* pull_requests

issues  1──* issue_comments
assets  0..1──* copies     (destination asset after copy)
```

没有协作者表、没有 star、没有 billing、没有 marketplace。`schema_migrations` 不参与业务 ER。

关系要点：

- `users.id` 与 `buckets.id` 不可变。磁盘路径只用这两个整数。`username` / `bucket.name` 只出现在元数据，改名不搬仓。
- `assets` 是 git 路径上的索引，不存文件正文。
- `copies` 是跨桶复制的 provenance（API 类型 InstallRecord）。`source_bucket_id` 无 FK。`dest_asset_id` 有 FK，`ON DELETE SET NULL`；`dest_path` / `dest_type` 为复制时快照。
- `pull_requests.proposed_files_json` 在 merge 前是提议树的唯一存储；merge 成功后工作树进 git，该列仍保留审阅底稿。
- 每桶一把进程/文件锁（不是 SQL 表）。配额「先检查再提交」在锁内用短事务改 `buckets.storage_usage_bytes`。
- 软删只打在 `buckets.deleted_at`。子行不级联删除，也不得在父桶已删时被 API 读出。

---

## Full SQL DDL

实现启动时执行（或等价 migration）。`PRAGMA foreign_keys = ON;`。打开后 `PRAGMA journal_mode = WAL;`。

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE schema_migrations (
  version     INTEGER PRIMARY KEY,
  applied_at  TEXT    NOT NULL
);

CREATE TABLE users (
  id                   INTEGER PRIMARY KEY,
  username             TEXT    NOT NULL,
  username_normalized  TEXT    NOT NULL,
  email                TEXT    NOT NULL,
  email_normalized     TEXT    NOT NULL,
  password_hash        TEXT    NOT NULL,
  bucket_quota         INTEGER NOT NULL DEFAULT 5,
  created_at           TEXT    NOT NULL,
  updated_at           TEXT    NOT NULL,
  CONSTRAINT users_username_normalized_uq UNIQUE (username_normalized),
  CONSTRAINT users_email_normalized_uq UNIQUE (email_normalized),
  CONSTRAINT users_bucket_quota_ck CHECK (bucket_quota >= 0)
);

CREATE TABLE tokens (
  id           INTEGER PRIMARY KEY,
  user_id      INTEGER NOT NULL,
  token_hash   TEXT    NOT NULL,
  created_at   TEXT    NOT NULL,
  last_used_at TEXT    NOT NULL,
  revoked_at   TEXT,
  CONSTRAINT tokens_user_fk
    FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT tokens_token_hash_uq UNIQUE (token_hash)
);

CREATE INDEX tokens_user_id_idx ON tokens(user_id);
CREATE INDEX tokens_active_idx ON tokens(user_id, revoked_at);

CREATE TABLE buckets (
  id                   INTEGER PRIMARY KEY,
  user_id              INTEGER NOT NULL,
  name                 TEXT    NOT NULL,
  name_normalized      TEXT    NOT NULL,
  visibility           TEXT    NOT NULL DEFAULT 'private',
  description          TEXT    NOT NULL DEFAULT '',
  template             TEXT,
  storage_usage_bytes  INTEGER NOT NULL DEFAULT 0,
  storage_limit_bytes  INTEGER NOT NULL DEFAULT 10485760,
  created_at           TEXT    NOT NULL,
  updated_at           TEXT    NOT NULL,
  deleted_at           TEXT,
  CONSTRAINT buckets_user_fk
    FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT buckets_visibility_ck
    CHECK (visibility IN ('public', 'private')),
  CONSTRAINT buckets_template_ck
    CHECK (template IS NULL OR template IN ('codex', 'agents', 'claude', 'openclaw')),
  CONSTRAINT buckets_description_len_ck
    CHECK (length(description) <= 350),
  CONSTRAINT buckets_usage_ck CHECK (storage_usage_bytes >= 0),
  CONSTRAINT buckets_limit_ck CHECK (storage_limit_bytes > 0)
);

-- 未删除行上 (user_id, name_normalized) 唯一；删除后允许同名重建（新 id）。
CREATE UNIQUE INDEX buckets_user_name_live_uq
  ON buckets(user_id, name_normalized)
  WHERE deleted_at IS NULL;

CREATE INDEX buckets_user_id_idx ON buckets(user_id);
CREATE INDEX buckets_user_visibility_idx
  ON buckets(user_id, visibility)
  WHERE deleted_at IS NULL;

CREATE TABLE assets (
  id               INTEGER PRIMARY KEY,
  bucket_id        INTEGER NOT NULL,
  type             TEXT    NOT NULL,
  source_harness   TEXT    NOT NULL,
  path             TEXT    NOT NULL,
  size_bytes       INTEGER NOT NULL,
  uploader_id      INTEGER NOT NULL,
  source_copy_id   INTEGER,
  head_commit_sha  TEXT    NOT NULL,
  created_at       TEXT    NOT NULL,
  updated_at       TEXT    NOT NULL,
  CONSTRAINT assets_bucket_fk
    FOREIGN KEY (bucket_id) REFERENCES buckets(id),
  CONSTRAINT assets_uploader_fk
    FOREIGN KEY (uploader_id) REFERENCES users(id),
  CONSTRAINT assets_type_ck
    CHECK (type IN ('skill', 'mcp', 'instructions', 'subagent', 'plugin')),
  CONSTRAINT assets_harness_ck
    CHECK (source_harness IN ('codex', 'agents', 'claude', 'openclaw')),
  CONSTRAINT assets_size_ck CHECK (size_bytes >= 0),
  CONSTRAINT assets_bucket_path_uq UNIQUE (bucket_id, path)
);

CREATE INDEX assets_bucket_id_idx ON assets(bucket_id);
CREATE INDEX assets_bucket_type_idx ON assets(bucket_id, type);
CREATE INDEX assets_uploader_id_idx ON assets(uploader_id);

CREATE TABLE copies (
  id                 INTEGER PRIMARY KEY,
  dest_bucket_id     INTEGER NOT NULL,
  dest_asset_id      INTEGER,
  dest_path          TEXT    NOT NULL,
  dest_type          TEXT    NOT NULL,
  source_bucket_id   INTEGER NOT NULL,
  source_full_name   TEXT    NOT NULL,
  source_path        TEXT    NOT NULL,
  source_commit_sha  TEXT    NOT NULL,
  dest_commit_sha    TEXT    NOT NULL,
  actor_id           INTEGER NOT NULL,
  created_at         TEXT    NOT NULL,
  CONSTRAINT copies_dest_bucket_fk
    FOREIGN KEY (dest_bucket_id) REFERENCES buckets(id),
  CONSTRAINT copies_dest_asset_fk
    FOREIGN KEY (dest_asset_id) REFERENCES assets(id)
    ON DELETE SET NULL,
  CONSTRAINT copies_actor_fk
    FOREIGN KEY (actor_id) REFERENCES users(id),
  CONSTRAINT copies_dest_type_ck
    CHECK (dest_type IN ('skill', 'mcp', 'instructions', 'subagent', 'plugin'))
);

-- source_bucket_id 不建 FK：源桶软删后 provenance 仍要可读（source_full_name / source_commit_sha 是快照）。
-- dest_asset_id 可空：owner DELETE 目标资产时硬删 assets 行，本列 SET NULL；dest_path / dest_type 是复制时快照，避免悬空后 InstallRecord 缺 path/type。
CREATE INDEX copies_dest_bucket_id_idx ON copies(dest_bucket_id);
CREATE INDEX copies_dest_asset_id_idx ON copies(dest_asset_id);
CREATE INDEX copies_actor_id_idx ON copies(actor_id);

-- assets.source_copy_id 指向 copies.id；循环用延后 ADD。
-- SQLite 允许 CREATE 后再加 FK；实现按下列顺序：先插入 copies（dest_asset_id 已有），再 UPDATE assets.source_copy_id。
-- 不在 assets 上建 FK 到 copies，避免插入顺序死结。应用层保证：非空 source_copy_id 必存在于 copies.id。

CREATE TABLE issues (
  id           INTEGER PRIMARY KEY,
  bucket_id    INTEGER NOT NULL,
  number       INTEGER NOT NULL,
  author_id    INTEGER NOT NULL,
  title        TEXT    NOT NULL,
  body         TEXT    NOT NULL DEFAULT '',
  state        TEXT    NOT NULL DEFAULT 'open',
  closed_by_id INTEGER,
  created_at   TEXT    NOT NULL,
  updated_at   TEXT    NOT NULL,
  closed_at    TEXT,
  CONSTRAINT issues_bucket_fk
    FOREIGN KEY (bucket_id) REFERENCES buckets(id),
  CONSTRAINT issues_author_fk
    FOREIGN KEY (author_id) REFERENCES users(id),
  CONSTRAINT issues_closed_by_fk
    FOREIGN KEY (closed_by_id) REFERENCES users(id),
  CONSTRAINT issues_state_ck CHECK (state IN ('open', 'closed')),
  CONSTRAINT issues_number_ck CHECK (number >= 1),
  CONSTRAINT issues_bucket_number_uq UNIQUE (bucket_id, number)
);

CREATE INDEX issues_bucket_state_idx ON issues(bucket_id, state);
CREATE INDEX issues_author_id_idx ON issues(author_id);

CREATE TABLE issue_comments (
  id         INTEGER PRIMARY KEY,
  issue_id   INTEGER NOT NULL,
  author_id  INTEGER NOT NULL,
  body       TEXT    NOT NULL,
  created_at TEXT    NOT NULL,
  updated_at TEXT    NOT NULL,
  CONSTRAINT issue_comments_issue_fk
    FOREIGN KEY (issue_id) REFERENCES issues(id),
  CONSTRAINT issue_comments_author_fk
    FOREIGN KEY (author_id) REFERENCES users(id),
  CONSTRAINT issue_comments_body_ck CHECK (length(body) > 0)
);

CREATE INDEX issue_comments_issue_id_idx ON issue_comments(issue_id);
CREATE INDEX issue_comments_author_id_idx ON issue_comments(author_id);

CREATE TABLE pull_requests (
  id                   INTEGER PRIMARY KEY,
  bucket_id            INTEGER NOT NULL,
  number               INTEGER NOT NULL,
  author_id            INTEGER NOT NULL,
  title                TEXT    NOT NULL,
  body                 TEXT    NOT NULL DEFAULT '',
  state                TEXT    NOT NULL DEFAULT 'open',
  proposed_files_json  TEXT    NOT NULL,
  merged_commit_sha    TEXT,
  created_at           TEXT    NOT NULL,
  updated_at           TEXT    NOT NULL,
  closed_at            TEXT,
  CONSTRAINT pull_requests_bucket_fk
    FOREIGN KEY (bucket_id) REFERENCES buckets(id),
  CONSTRAINT pull_requests_author_fk
    FOREIGN KEY (author_id) REFERENCES users(id),
  CONSTRAINT pull_requests_state_ck
    CHECK (state IN ('open', 'merged', 'rejected')),
  CONSTRAINT pull_requests_number_ck CHECK (number >= 1),
  CONSTRAINT pull_requests_bucket_number_uq UNIQUE (bucket_id, number)
);

CREATE INDEX pull_requests_bucket_state_idx ON pull_requests(bucket_id, state);
CREATE INDEX pull_requests_author_id_idx ON pull_requests(author_id);
```

表共 9 张：`schema_migrations`、`users`、`tokens`、`buckets`、`assets`、`copies`、`issues`、`issue_comments`、`pull_requests`。

类型约定（迁 Postgres 时对照）：

| SQLite | 含义 | Postgres |
| --- | --- | --- |
| INTEGER PRIMARY KEY | 不可变代理键 | BIGSERIAL / BIGINT GENERATED |
| TEXT ISO-8601 UTC | 时间 | TIMESTAMPTZ |
| TEXT + CHECK enum | 枚举 | TEXT 或 ENUM |
| TEXT JSON | 提议文件列表 | JSONB |
| INTEGER 0/1 不用 | — | — |

`users.id` / `buckets.id` 一经分配永不复用到另一主体。软删只给 bucket（`deleted_at`）。资产是硬删（DROP 行），靠 copies 快照保留出处。

---

## Live bucket predicate（`deleted_at`）

解析 `{username}/{bucket}` 的唯一合法写法：

```sql
SELECT b.*
FROM buckets b
JOIN users u ON u.id = b.user_id
WHERE u.username_normalized = ?
  AND b.name_normalized = ?
  AND b.deleted_at IS NULL;
```

零行 → API 404。所有桶作用域查询必须先得到这个 `b.id`，再按 `bucket_id = b.id` 读子表。禁止：

- 只凭 `assets.id` / `issues.id` / `pull_requests.id` / `copies.id` / `issue_comments.id` 出结果而不检查父桶 `deleted_at IS NULL`
- `GET /users/{username}/buckets` 漏掉 `deleted_at IS NULL`（软删行不得出现在列表，也不得计入 `bucket_count` 与个数配额）
- 从已软删源桶 copy（源解析同一谓词，404）

子表行在软删后可以留着做带外恢复，对 API 不可见。`open_issues_count` / `open_pulls_count` / `harness_mix` 只在活桶的 GET 上计算，因此自然带该谓词。

`assets.source_copy_id` 仍无 FK（避免与 copies 插入顺序死结）。硬删资产时该行消失，旧 copies 靠 `dest_asset_id SET NULL` 与快照列继续可 GET。

Issue `number` 与 PR `number` 是两套序号：`MAX(number)+1` 放在对应表的短事务里分配（可与内容锁无关，但必须包在 SQLite 事务中防撞 UNIQUE）。

---

## Git-only fields（不进 SQLite，或仅缓存且 git 为权威）

不进 SQLite（每次从 git 读）：

- 工作树与历史中的文件字节
- commit 对象：`sha`、message、author name/email、authored_at、changed paths、parent
- 目录结构、blob、树对象
- 按历史 commit 取出的内容
- 翻译输出与 `(commit, target)` 缓存归档
- 安装脚本文本（现算）
- `README.md` 渲染原文（blob 现读）

只缓存、git 为权威（mutation 后按工作树重算；允许与实测差 <1%，与配额 spec 一致）：

| 列 | 权威来源 | 何时刷新 |
| --- | --- | --- |
| `buckets.storage_usage_bytes` | `git` 工作树字节合计（不含 `.git`） | 每次成功 commit 后实测写入 |
| `assets.size_bytes` | 该资产路径下工作树合计 | 上传 / copy / merge 触及该路径后；DELETE 资产则删行 |
| `assets.head_commit_sha` | 该路径最近一次改动的 commit | 同上；DELETE 资产则删行 |
| `assets.path` | 工作树相对路径 | 与 git 路径一致；不存正文 |

`TreeEntry.last_commit_*`、`Commit.*`、`blob` 正文：计算自 git，不建 commits 表。

Git author 邮箱约定（用于从 log 映射回 User）：`user-{id}@users.red-bucket.invalid`，author name = 当时的 `username`。历史 commit 不因改名重写。

---

## Quota accounting and the per-bucket lock

列：

| 列 | 作用 |
| --- | --- |
| `users.bucket_quota` | 该用户未删除 bucket 个数上限，默认 5。S2.5 只改这一列（无公开 API）。 |
| 计数 | `SELECT COUNT(*) FROM buckets WHERE user_id=? AND deleted_at IS NULL` |
| `buckets.storage_limit_bytes` | 默认 10485760。Phase 1 不按用户改；列留下是为了以后与 bucket 配额一样可配置。 |
| `buckets.storage_usage_bytes` | 上次成功 commit 后测得的工作树字节。 |

Bucket 个数：在创建事务里 `COUNT` 与 `INSERT` 同一 `BEGIN IMMEDIATE`。已达上限 → 403 `bucket_quota_exceeded`，`details.limit` = `users.bucket_quota`，`details.current` = 计数。DELETE 置 `deleted_at`，计数下降。

工作树 10MB 与每桶锁（与 design.md 一致：裸仓 + 每次变更的 worktree + 每桶一把锁）：

1. 取得该 `bucket.id` 的互斥锁。推荐：锁文件 `<storage-root>/<user-id>/<bucket-id>.lock` 上 `flock(LOCK_EX)`。不要另建 SQL 锁表。
2. 打开（或检出）该桶 worktree。
3. 在临时视图上应用变更（上传文件、copy、merge 的 `proposed_files_json`、删除资产路径、模板骨架）。尚未 `git commit`。
4. 测应用后工作树大小（walk 文件，跟随已清洗的树内符号链接，拒绝树外链接）。
5. 若 `new_size > storage_limit_bytes`：丢弃临时变更，释放锁，413 `bucket_storage_exceeded`，`details.usage_bytes` = 锁内读到的当前实测（或列上缓存），`details.limit_bytes` = `storage_limit_bytes`。仓与列都不变。
6. 通过则 `git commit`（作者按 api-catalog 归属表），`UPDATE buckets SET storage_usage_bytes = <实测>, updated_at = ? WHERE id = ?`，更新或插入 `assets` 行，必要时插 `copies`。这些 SQL 放在同一短事务。
7. 提交事务，释放 flock。

两笔各自能装下、合计超限的并发上传：锁串行化，第二笔在步骤 4 看到第一笔已经上去的树，于是 413。最终工作树 ≤ 上限。不要先 commit 再检查。

`storage_usage_bytes` 与实测差必须 <1%。以实测写入列为准，不要用「旧值 + 上传字节」长期漂移；加法只能当步骤 4 的快速预检，步骤 6 仍写实测。

历史 git 对象不计入配额（spec：按工作树）。`git gc` 带外做。

---

## Mapping: API JSON field → table.column / git / computed

### User

| API 字段 | 来源 |
| --- | --- |
| `id` | `users.id` |
| `username` | `users.username` |
| `created_at` | `users.created_at` |
| `email` | `users.email`（仅本人） |
| `bucket_quota` | `users.bucket_quota` |
| `bucket_count` | computed: `COUNT(buckets)` where `user_id` and `deleted_at IS NULL` |
| （不暴露） | `users.username_normalized`、`email_normalized`、`password_hash`、`updated_at`：归一化键、哈希与内部 mtime，不进 JSON |

### Token（login 响应）

| API 字段 | 来源 |
| --- | --- |
| `token` | 仅响应明文一次；库内 `tokens.token_hash` |
| `token_type` | computed: 恒为 `bearer` |
| （不暴露） | `tokens.id`：内部主键。`tokens.user_id`：鉴权查找。`tokens.created_at`、`tokens.last_used_at`：会话记账，logout 写 `revoked_at`。四列都不进 JSON |

### Bucket

| API 字段 | 来源 |
| --- | --- |
| `id` | `buckets.id` |
| `name` | `buckets.name` |
| `username` | `users.username` via `buckets.user_id` |
| `full_name` | computed: `username + '/' + name` |
| `visibility` | `buckets.visibility` |
| `description` | `buckets.description` |
| `template` | `buckets.template` |
| `usage_bytes` | `buckets.storage_usage_bytes`（git 工作树缓存） |
| `limit_bytes` | `buckets.storage_limit_bytes` |
| `open_issues_count` | computed: `COUNT(issues)` where `bucket_id` and `state='open'` |
| `open_pulls_count` | computed: `COUNT(pull_requests)` where `bucket_id` and `state='open'` |
| `harness_mix` | computed: `GROUP BY assets.source_harness` |
| `created_at` | `buckets.created_at` |
| `updated_at` | `buckets.updated_at` |
| （不暴露） | `buckets.name_normalized`：大小写不敏感唯一键。`buckets.deleted_at`：软删标记，API 只用来过滤，不出现在 Bucket JSON。`buckets.user_id`：经 `username` / `full_name` 暴露 |

### Asset

| API 字段 | 来源 |
| --- | --- |
| `id` | `assets.id` |
| `bucket_id` | `assets.bucket_id` |
| `full_name` | computed from owner username + bucket name |
| `type` | `assets.type` |
| `source_harness` | `assets.source_harness` |
| `path` | `assets.path`（git 路径索引） |
| `size_bytes` | `assets.size_bytes`（缓存） |
| `uploader.id` | `assets.uploader_id` |
| `uploader.username` | `users.username` |
| `head_commit_sha` | `assets.head_commit_sha`（缓存；权威 git） |
| `created_at` | `assets.created_at` |
| `updated_at` | `assets.updated_at` |
| `provenance` | computed from `copies` where `id = assets.source_copy_id`（摘要字段见 InstallRecord） |
| `provenance.id` | `copies.id` |
| `provenance.source_full_name` | `copies.source_full_name` |
| `provenance.source_commit_sha` | `copies.source_commit_sha` |
| `provenance.created_at` | `copies.created_at` |
| 文件正文 | git |
| （不暴露） | `assets.source_copy_id`：只驱动 `provenance`，不单独出列 |

### TreeEntry

| API 字段 | 来源 |
| --- | --- |
| `name`,`path`,`entry_type`,`size_bytes` | git ls-tree / 工作树一层 |
| `last_commit_sha`,`last_commit_message`,`last_commit_at` | git log -1 -- path |
| `asset` | computed: `assets` 行匹配该 path 或其前缀 |

### Commit

| API 字段 | 来源 |
| --- | --- |
| `sha`,`short_sha`,`message`,`authored_at`,`paths` | git |
| `author.id`,`author.username` | computed: git author email `user-{id}@...` → `users` |

### Issue

| API 字段 | 来源 |
| --- | --- |
| `id` | `issues.id` |
| `number` | `issues.number` |
| `bucket_full_name` | computed |
| `title` | `issues.title` |
| `body` | `issues.body` |
| `state` | `issues.state` |
| `author` | `issues.author_id` → users |
| `closed_by` | `issues.closed_by_id` → users |
| `created_at` | `issues.created_at` |
| `updated_at` | `issues.updated_at` |
| `closed_at` | `issues.closed_at` |
| （不暴露为列名） | `issues.bucket_id`、`issues.author_id`、`issues.closed_by_id`：经 `bucket_full_name` / `author` / `closed_by` |

### IssueComment

| API 字段 | 来源 |
| --- | --- |
| `id` | `issue_comments.id` |
| `issue_number` | `issues.number` via `issue_id` |
| `bucket_full_name` | computed |
| `body` | `issue_comments.body` |
| `author` | `issue_comments.author_id` → users |
| `created_at` | `issue_comments.created_at` |
| `updated_at` | `issue_comments.updated_at` |
| （不暴露为列名） | `issue_comments.issue_id`、`issue_comments.author_id`：经 `issue_number` / `author` |

### PullRequest

| API 字段 | 来源 |
| --- | --- |
| `id` | `pull_requests.id` |
| `number` | `pull_requests.number` |
| `bucket_full_name` | computed |
| `title` | `pull_requests.title` |
| `body` | `pull_requests.body` |
| `state` | `pull_requests.state` |
| `author` | `pull_requests.author_id` → users |
| `files` | `pull_requests.proposed_files_json`（JSON 数组，元素同 FileEntry） |
| `merged_commit_sha` | `pull_requests.merged_commit_sha`（merge 后与 git 一致） |
| `created_at` | `pull_requests.created_at` |
| `updated_at` | `pull_requests.updated_at` |
| `closed_at` | `pull_requests.closed_at` |
| merge 后的文件字节 | git |
| `files[].path` / `content_text` / `content_base64` / `delete` | `pull_requests.proposed_files_json` 元素 |
| （不暴露为列名） | `pull_requests.bucket_id`、`pull_requests.author_id`：经 `bucket_full_name` / `author` |

### InstallRecord

| API 字段 | 来源 |
| --- | --- |
| `id` | `copies.id` |
| `dest_full_name` | computed from `dest_bucket_id` → 活桶的 username/name；父桶已软删则整条 copies API 已 404 |
| `dest_asset.id` | `copies.dest_asset_id`（目标资产硬删后为 JSON `null`） |
| `dest_asset.path` | `copies.dest_path`（复制时快照；不随之后改名或删除而变） |
| `dest_asset.type` | `copies.dest_type`（快照） |
| `source_full_name` | `copies.source_full_name`（复制当时快照，源改名后仍显示旧名） |
| `source_bucket_id` | `copies.source_bucket_id` |
| `source_path` | `copies.source_path` |
| `source_commit_sha` | `copies.source_commit_sha` |
| `dest_commit_sha` | `copies.dest_commit_sha` |
| `actor` | `copies.actor_id` → users |
| `created_at` | `copies.created_at` |
| （不暴露为列名） | `copies.dest_bucket_id`：经 `dest_full_name`。`copies.actor_id`：经 `actor` |

### Template / TranslationMatrixEntry / Error / FileEntry / 列表外壳 / 其它响应

| API 字段 | 来源 |
| --- | --- |
| Template.`name` / `description` / `files` | computed：代码内骨架（见 api-catalog），无表 |
| TranslationMatrixEntry.`asset_type` / `source` / `target` / `supported` / `identity` / `doc` | computed：formatter 注册表，无表 |
| Error.`error.code` / `error.message` / `error.details` | computed |
| Error.details[].`field` / `rule` / `path` / `message` | computed |
| Error.details.`limit` / `current` | `users.bucket_quota` 与活桶 COUNT |
| Error.details.`usage_bytes` / `limit_bytes` | `buckets.storage_usage_bytes` / `storage_limit_bytes` |
| FileEntry（上传请求） | 请求体 → git；不落独立表 |
| FileEntry（PR） | `pull_requests.proposed_files_json` |
| 列表.`items` | 各资源行 |
| 列表.`page` / `per_page` | 查询参数（computed 回显） |
| 列表.`total` / `has_more` | computed |
| 列表.`next_cursor` | computed：有下一页时为下一页 `page` 的十进制字符串，否则 `null`。不是查询协议 |
| install-script.`target` | 查询参数回显 |
| install-script.`script` | computed |
| install-script.`translated_url` | computed：对应 `GET .../translated` 路径 |
| translated 归档字节 | computed / 文件系统缓存；无表 |
| translated meta.`lossy` / `notes` / `filename` | computed（`?meta=1`） |
| blob.`path` / `size_bytes` / `content_text` / `content_base64` | git |
| blob.`last_commit_sha` / `last_commit_message` / `last_commit_at` | git |
| raw 字节 | git |
| tree 外壳.`latest_commit` / `commit_count` | git |
| TreeEntry.`name` / `path` / `entry_type` / `size_bytes` | git（见上节） |
| Location 头 | computed：新资源规范 GET 路径 |

### 仅内部、不进 API 的表

| 列 | 原因 |
| --- | --- |
| `schema_migrations.version` | 迁移版本，无对应资源 |
| `schema_migrations.applied_at` | 迁移时间，无对应资源 |

### Auth 请求字段（不持久化明文）

| 请求字段 | 落库 |
| --- | --- |
| `password` | 只写 `users.password_hash` |
| `email` | `users.email` + `email_normalized` |
| `username` | `users.username` + `username_normalized` |
| copy 请求 `source_username` / `source_bucket` / `source_asset_id` | 解析后写入 `copies.source_bucket_id`、`source_full_name`、`source_path`、`source_commit_sha` |
| copy 请求 `dest_path` | `copies.dest_path`；并抄 `dest_type` 自源资产 type |

---

## Column inventory（每列：API 使用或明确不暴露）

| 列 | 去向 |
| --- | --- |
| `schema_migrations.version` / `applied_at` | 不暴露：迁移记账 |
| `users.id` / `username` / `email` / `bucket_quota` / `created_at` | User JSON |
| `users.username_normalized` / `email_normalized` / `password_hash` / `updated_at` | 不暴露：唯一键、哈希、内部 mtime |
| `tokens.token_hash` | login 签发；只存哈希 |
| `tokens.id` / `user_id` / `created_at` / `last_used_at` / `revoked_at` | 不暴露：会话内部 |
| `buckets.id` / `name` / `visibility` / `description` / `template` / `storage_usage_bytes` / `storage_limit_bytes` / `created_at` / `updated_at` | Bucket JSON（后两列缓存名为 usage/limit） |
| `buckets.user_id` | 不暴露为数字；经 username |
| `buckets.name_normalized` | 不暴露：唯一键 |
| `buckets.deleted_at` | 不暴露：活桶谓词 |
| `assets.*` 除 `source_copy_id` | Asset JSON |
| `assets.source_copy_id` | 不暴露为数字；驱动 provenance |
| `copies.*` | InstallRecord；`dest_bucket_id` / `actor_id` 经 full_name / actor |
| `issues.*` | Issue JSON；FK 列经嵌套对象 |
| `issue_comments.*` | IssueComment JSON；FK 列经嵌套对象 |
| `pull_requests.*` | PullRequest JSON；`proposed_files_json` 为 `files` |

---

## Gaps / assumptions

无。与现行 OpenSpec 原文的产品方加项（plugin/subagent 矩阵、PR 文件树、logout、单资产 DELETE、评论资源、密码/邮箱硬规则）仍记在 api-catalog coverage，不是本 schema 的未决项。
