## Purpose

定义 bucket（repo）生命周期：在 `user/bucket-name` 下的命名空间创建、public/private 可见性、可选 description、可选的 harness 风格目录模板，以及每用户配额上限。

## ADDED Requirements

### Requirement: Bucket creation under user namespace
系统MUST让已认证用户创建一个地址为 `<username>/<bucket-name>` 的 bucket。Bucket 名称在每个用户下必须唯一（大小写不敏感），1-100 个字符，匹配 `[a-z0-9]([a-z0-9._-]*[a-z0-9])?`。创建时用户必须选择可见性 `public` 或 `private`（默认 `private`）。

#### Scenario: Successful bucket creation
- **WHEN** 已认证用户用一个未使用的合法名称和可见性 `public` 创建 bucket
- **THEN** 系统以 HTTP 201 返回 bucket 元数据（全名、可见性、description、配额、创建时间），并且该 bucket 立即在 `GET /users/<username>/buckets` 可见

#### Scenario: Duplicate bucket name rejected
- **WHEN** 用户创建一个名称（大小写不敏感）在其命名空间下已经存在的 bucket
- **THEN** 系统响应 HTTP 409，并且没有 bucket 被创建

#### Scenario: Invalid bucket name rejected
- **WHEN** 用户用含有 `/`、空格或大写字符的名称创建 bucket
- **THEN** 系统响应 HTTP 422，并点名无效字段

### Requirement: Bucket count quota
系统MUST默认把每个用户限制为 5 个 buckets。该上限必须在创建时强制执行，并且必须是存储中的每用户可配置值，以便在不改代码的情况下为个别用户提高上限。

#### Scenario: Sixth bucket rejected
- **WHEN** 一名已经拥有 5 个 buckets 的用户尝试再创建一个
- **THEN** 系统响应 HTTP 403，错误码为 `bucket_quota_exceeded`，并在错误体中报告当前限额

#### Scenario: Deletion frees quota
- **WHEN** 一名处于 5-bucket 上限的用户删除一个 bucket，然后再创建一个新的
- **THEN** 该创建成功

### Requirement: Bucket description
系统MUST为每个 bucket 存储一段可选的、由 owner 可编辑的纯文本 description，最多 350 个字符（GitHub About description 上限）。description 必须默认为空，必须在 bucket 元数据中返回，并且必须可由 owner 在创建后 PATCH。

#### Scenario: Description set and returned
- **WHEN** owner 在创建 bucket 时带上一段 description，或之后 PATCH 该 description
- **THEN** 随后的元数据响应和 bucket 详情 About 侧栏显示该 description

#### Scenario: Description too long rejected
- **WHEN** 提交一段长于 350 个字符的 description
- **THEN** 系统响应 HTTP 422，并点名 `description` 字段

### Requirement: Visibility change
系统MUST允许 bucket owner 随时在 `public` 与 `private` 之间切换 bucket。该变更必须对之后的全部请求生效。

#### Scenario: Public to private hides content
- **WHEN** owner 把一个公开 bucket 切换为私有
- **THEN** 随后对该 bucket 的匿名请求响应 HTTP 404，而 owner 的请求仍然成功

### Requirement: Bucket creation from template
系统MUST在创建 bucket 时提供可选的目录模板。Phase 1 必须至少包含这些模板风格：`codex`、`agents`（通用）、`claude`、`openclaw`。选择模板会用该风格的目录骨架初始化 bucket；不选择则创建一个空 bucket。

#### Scenario: Template applied at creation
- **WHEN** 用户选择 `claude` 模板创建 bucket
- **THEN** 新 bucket 包含 claude 风格骨架（例如 `skills/`、`CLAUDE.md` 占位）作为其初始内容，并且该初始内容被记录为第一个 git commit

#### Scenario: Template list discoverable
- **WHEN** 客户端请求模板目录端点
- **THEN** 系统返回至少 4 种 Phase 1 模板风格，每种带有名称和描述

### Requirement: Bucket deletion
系统MUST允许 owner 删除 bucket。删除必须把该 bucket 从所有列表中移除并释放其存储记账；底层 git 仓库可以在带外保留以供灾难恢复，但之后不得再通过任何 API 可寻址。

#### Scenario: Deleted bucket unaddressable
- **WHEN** owner 删除一个 bucket，随后任何客户端请求它
- **THEN** 系统对引用该 bucket 的全部 API 路由响应 HTTP 404
