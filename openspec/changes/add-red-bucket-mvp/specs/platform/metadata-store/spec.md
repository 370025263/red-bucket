## Purpose

定义 Phase 1 元数据存储：SQLite（WAL）只存可查询元数据；每个 bucket 的文件字节与 git 历史只在文件系统仓库里。权威 DDL、活桶谓词、配额记账和 API JSON 字段映射以本次变更中的 `schema-sqlite.md` 为准。数据访问层保持很薄，以便日后迁 Postgres。

## ADDED Requirements

### Requirement: SQLite schema is the metadata contract
系统 MUST 使用 SQLite，打开后启用 WAL 与 `PRAGMA foreign_keys = ON`，并实现 `schema-sqlite.md` 中的九张表：`schema_migrations`、`users`、`tokens`、`buckets`、`assets`、`copies`、`issues`、`issue_comments`、`pull_requests`。实现不得增删面向当前 spec 业务的表或改名权威列。模板骨架、翻译注册表、翻译结果缓存、logo 都不是表。

#### Scenario: Required tables exist
- **WHEN** 服务在空数据目录上首次启动
- **THEN** 上述九张表都存在，并且列名、CHECK、UNIQUE 与 `schema-sqlite.md` 的 Full SQL DDL 一致

### Requirement: API fields map to schema columns
`api-catalog.md` 中的 JSON 对象字段 MUST 按 `schema-sqlite.md` 的字段映射表从列或约定计算得出，不得另发明一套对外名字。git 权威字段（commit 对象、blob 字节、目录树）不得进 SQLite 业务表。`users.id` 与 `buckets.id` 一经分配不得复用到另一主体。

#### Scenario: Bucket JSON comes from live row
- **WHEN** 客户端 GET 一个未删除 bucket
- **THEN** `full_name`、`visibility`、`description`、`template`、`usage_bytes`、`limit_bytes` 分别来自对应用户名、`buckets` 列或工作树刷新后的 `storage_usage_bytes`，并且响应不含 `deleted_at`

### Requirement: Live bucket predicate
解析 `{username}/{bucket}` MUST 使用 `schema-sqlite.md` 中的活桶谓词（`deleted_at IS NULL`）。命不中则 HTTP 404，与从未存在不可区分。所有挂在该桶下的查询 MUST 先得到这个活 `bucket.id`，禁止只凭子表主键读出已软删父桶下的行。

#### Scenario: Soft-deleted bucket hides child rows
- **WHEN** owner 删除一个仍留有 assets、issues、copies 行的 bucket，随后任何客户端用原子 id 或路径请求这些子资源
- **THEN** 系统对引用该 bucket 的全部 API 路由响应 HTTP 404

### Requirement: Copies survive dest asset hard delete
删除目标资产 MUST 硬删 `assets` 行；指向该行的 `copies.dest_asset_id` MUST 由外键 `ON DELETE SET NULL` 置空；`dest_path` 与 `dest_type` 保持复制时快照，使 `GET .../copies` 仍能列出出处。

#### Scenario: Copy provenance remains after dest delete
- **WHEN** owner 删除一份曾作为 copy 目标的资产，随后列出该桶的 copies
- **THEN** 该 InstallRecord 仍在，`dest_asset.id` 为 `null`，`dest_asset.path` 与 `type` 仍是复制当时的值

### Requirement: Thin DAL for later Postgres
数据访问 MUST 集中在薄模块后面，列类型按可迁 Postgres 选择（整数主键、TEXT 时间戳、不把业务约束写成 SQLite 专有 JSON1）。Phase 1 不引入第二套元数据库。

#### Scenario: Mutations go through one store
- **WHEN** 一次注册、建桶、开 issue、提交 PR、跨桶 copy 被执行
- **THEN** 对应行出现在上述 SQLite 表中，并且没有并行写入另一套元数据存储
