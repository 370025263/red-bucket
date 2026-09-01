## Purpose

定义 bucket（repo）生命周期：在 `user/bucket-name` 下的命名空间创建、public/private 可见性、可选 description、可选的 harness 风格目录模板，以及每用户配额上限。

## ADDED Requirements

### Requirement: Bucket creation under user namespace
系统 MUST 让已认证用户创建一个地址为 `<username>/<bucket-name>` 的 bucket。Bucket 名称在每个用户下必须唯一（大小写不敏感），1-100 个字符，匹配 `[a-z0-9]([a-z0-9._-]*[a-z0-9])?`。创建时用户必须选择可见性 `public` 或 `private`（默认 `private`）。201 响应 MUST 带 `Location: /api/v1/users/{username}/buckets/{name}`。

#### Scenario: Successful bucket creation
- **WHEN** 已认证用户用一个未使用的合法名称和可见性 `public` 创建 bucket
- **THEN** 系统以 HTTP 201 返回 bucket 元数据（全名、可见性、description、配额、创建时间），并且该 bucket 立即在 `GET /users/{username}/buckets` 可见

#### Scenario: Duplicate bucket name rejected
- **WHEN** 用户创建一个名称（大小写不敏感）在其命名空间下已经存在的未删除 bucket
- **THEN** 系统响应 HTTP 409，错误码为 `bucket_name_taken`，并且没有 bucket 被创建

#### Scenario: Invalid bucket name rejected
- **WHEN** 用户用含有 `/`、空格或大写字符的名称创建 bucket
- **THEN** 系统响应 HTTP 422，并点名无效字段

### Requirement: Bucket list visibility
`GET /api/v1/users/{username}/buckets` MUST 遵守：用户不存在则 404；匿名或非本人只返回 `visibility=public` 且 `deleted_at` 为空的项；`{username}` 等于当前用户时包含其未删除的 private 项。软删桶不得出现在任何列表中，也不得计入 `bucket_count`。

#### Scenario: Stranger omits private buckets
- **WHEN** 未认证客户端列出一个同时拥有 public 与 private 未删除桶的用户
- **THEN** 列表只含 public 项，并且响应不是 404

### Requirement: Bucket count quota
系统 MUST 默认把每个用户限制为 5 个未删除 buckets。该上限必须在创建时强制执行，并且必须是存储中的每用户可配置值（`users.bucket_quota`），以便在不改代码、也不提供公开改配额 API 的情况下为个别用户提高上限。

#### Scenario: Sixth bucket rejected
- **WHEN** 一名已经拥有 5 个未删除 buckets 的用户尝试再创建一个
- **THEN** 系统响应 HTTP 403，错误码为 `bucket_quota_exceeded`，并在错误体中报告 `limit` 与 `current`

#### Scenario: Deletion frees quota
- **WHEN** 一名处于 5-bucket 上限的用户删除一个 bucket，然后再创建一个新的
- **THEN** 该创建成功

### Requirement: Bucket description
系统 MUST 为每个 bucket 存储一段可选的、由 owner 可编辑的纯文本 description，最多 350 个字符（GitHub About description 上限）。description 必须默认为空字符串，必须在 bucket 元数据中返回，并且必须可由 owner 在创建后 PATCH。

#### Scenario: Description set and returned
- **WHEN** owner 在创建 bucket 时带上一段 description，或之后 PATCH 该 description
- **THEN** 随后的元数据响应和 bucket 详情 About 侧栏显示该 description

#### Scenario: Description too long rejected
- **WHEN** 提交一段长于 350 个字符的 description
- **THEN** 系统响应 HTTP 422，并点名 `description` 字段

### Requirement: Visibility change
系统 MUST 允许 bucket owner 随时在 `public` 与 `private` 之间切换 bucket。该变更必须对之后的全部请求生效。

#### Scenario: Public to private hides content
- **WHEN** owner 把一个公开 bucket 切换为私有
- **THEN** 随后对该 bucket 的匿名请求响应 HTTP 404，而 owner 的请求仍然成功

### Requirement: Bucket creation from template
系统 MUST 在创建 bucket 时提供可选的目录模板。Phase 1 必须恰好包含这些模板风格：`codex`、`agents`、`claude`、`openclaw`。选择模板会用 `api-catalog.md` Template 一节列出的文件骨架初始化 bucket，并作为第一次 git commit（作者为创建者）。不选择 template 则创建空工作树、零 commit。未知 template 名称以 HTTP 422 拒绝。

#### Scenario: Template applied at creation
- **WHEN** 用户选择 `claude` 模板创建 bucket
- **THEN** 新 bucket 的工作树恰好包含 `api-catalog.md` 中 `template=claude` 列出的路径与内容，并且该初始内容被记录为第一个 git commit

#### Scenario: Template list discoverable
- **WHEN** 客户端请求模板目录端点
- **THEN** 系统返回这 4 种 Phase 1 模板，每种带有名称、描述和 `files` 列表

#### Scenario: Empty bucket has zero commits
- **WHEN** 用户创建 bucket 时不传 template
- **THEN** 工作树为空，历史端点没有 commit

### Requirement: Bucket deletion
系统 MUST 允许 owner 删除 bucket。删除 MUST 置 `buckets.deleted_at`，把该 bucket 从所有列表中移除并释放其个数配额记账；底层 git 仓库可以在带外保留以供灾难恢复，但之后不得再通过任何 API 可寻址。允许之后用同名再创建一个新 bucket（新 `bucket.id`）。

#### Scenario: Deleted bucket unaddressable
- **WHEN** owner 删除一个 bucket，随后任何客户端请求它或其子路由
- **THEN** 系统对引用该 bucket 的全部 API 路由响应 HTTP 404
