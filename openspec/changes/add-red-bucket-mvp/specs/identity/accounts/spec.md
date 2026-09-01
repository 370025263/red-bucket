## Purpose

定义用户注册、认证、登出、改用户名，以及匿名读取边界：写操作一律需要已认证账号，而公开内容无需账号即可读取。

## ADDED Requirements

### Requirement: User registration
系统 MUST 允许访客用唯一用户名和一份凭证（Phase 1 为 email + password）注册账号。用户名必须唯一（大小写不敏感），3-39 个字符，匹配 `[a-z0-9]([a-z0-9-]*[a-z0-9])?`，因为用户名是每个 bucket URL 的命名空间前缀。邮箱必须唯一（大小写不敏感），并且是可解析的邮箱地址。密码长度 MUST 至少 8 个字符；短于 8 个字符以 HTTP 422 拒绝，并点名 `password`。注册成功返回 HTTP 201、`Location: /api/v1/users/{username}`，正文是公开资料（`id`、`username`、`created_at`），不签发 token，不含 email、密码或哈希。

#### Scenario: Successful registration
- **WHEN** 访客提交一次注册，用户名为未使用且合法、邮箱合法且未占用、密码至少 8 个字符
- **THEN** 系统创建该账号，以 HTTP 201 返回公开资料，响应头带 `Location`，并且响应中不含凭证材料与 email

#### Scenario: Duplicate username rejected
- **WHEN** 访客用一个仅字母大小写不同于已有用户名的用户名注册
- **THEN** 系统以 HTTP 409 拒绝该请求，错误码为 `username_taken`，并且没有账号被创建

#### Scenario: Duplicate email rejected
- **WHEN** 访客用一个仅字母大小写不同于已有邮箱的邮箱注册
- **THEN** 系统以 HTTP 409 拒绝该请求，错误码为 `email_taken`，并且没有账号被创建

#### Scenario: Invalid username rejected
- **WHEN** 访客用含有 `[a-z0-9-]` 以外字符的用户名注册，或以 `-` 开头/结尾，或短于 3 个字符
- **THEN** 系统以 HTTP 422 拒绝该请求，并给出点名 `username` 字段的校验错误

#### Scenario: Short password rejected
- **WHEN** 访客提交一段短于 8 个字符的密码
- **THEN** 系统以 HTTP 422 拒绝该请求，并点名 `password` 字段

### Requirement: Authentication for write operations
系统 MUST 对每一个创建、修改或删除数据的操作（buckets、assets、issues、评论、pull requests、copies）要求认证。未认证的写尝试必须以 HTTP 401 和错误码 `unauthorized` 拒绝，并且不发生任何状态变化。登录签发一枚不透明 Bearer token；服务端只存 token 的哈希。

#### Scenario: Unauthenticated write rejected
- **WHEN** 一个没有有效凭证的请求尝试创建 bucket 或上传资产
- **THEN** 系统响应 HTTP 401，错误码为 `unauthorized`，并且不发生任何状态变化

#### Scenario: Authenticated session issued
- **WHEN** 一名已注册用户向登录端点提交正确邮箱和密码
- **THEN** 系统返回一个 API token，可作为后续请求上的 Bearer 凭证使用，并带上本人 User（含 email、bucket_quota、bucket_count）

#### Scenario: Invalid credentials rejected
- **WHEN** 用户提交错误密码，或提交一个不存在的邮箱
- **THEN** 系统响应 HTTP 401，错误码为 `unauthorized`，且两种情况的响应体不可区分

### Requirement: Token revocation
系统 MUST 提供登出：已认证客户端对当前这枚 token 调用登出后，该 token 被撤销，之后再用同一枚 token 必须以 HTTP 401 和错误码 `unauthorized` 拒绝。

#### Scenario: Logout revokes current token
- **WHEN** 已登录用户调用登出，随后用同一枚 token 请求 `GET /api/v1/users/me`
- **THEN** 登出返回 HTTP 204，随后的请求返回 HTTP 401

### Requirement: Username change is metadata only
系统 MUST 允许已认证用户通过 `PATCH /api/v1/users/me` 只改 username（Phase 1 不接受改邮箱、改密码、改 bucket_quota）。新用户名遵守与注册相同的规则。磁盘仓库路径按不可变 user id 保持不动；之后全部对外路径使用新用户名。

#### Scenario: Username change does not move storage
- **WHEN** 一名已有 buckets 的用户把 username 改成一个未占用的合法名
- **THEN** 既有 buckets 在新 username 下可寻址，磁盘上的 `<storage-root>/<user-id>/` 未被移动

#### Scenario: Username change conflict
- **WHEN** 用户把 username 改成一个仅大小写不同于他人的已占用名
- **THEN** 系统响应 HTTP 409，错误码为 `username_taken`，原用户名不变

### Requirement: Anonymous read access to public content
系统 MUST 在不要求注册或认证的情况下，提供对公开 buckets 的读操作（浏览、列出资产、树与 blob、raw 拉取、翻译拉取、安装脚本文本、查看 issues、评论和 pull requests、模板目录、能力矩阵、用户公开资料）。

#### Scenario: Anonymous fetch of public bucket
- **WHEN** 未认证客户端请求某个公开 bucket 的资产列表或某份资产下载
- **THEN** 系统以 HTTP 200 返回该内容

#### Scenario: Anonymous access to private bucket denied
- **WHEN** 未认证客户端请求某个私有 bucket 的任何内容
- **THEN** 系统响应 HTTP 404（不是 403），从而不披露私有 bucket 是否存在

### Requirement: Owner-only access to private buckets
系统 MUST 在 Phase 1 把对私有 bucket 的全部访问限制为其 owner（尚无协作者模型）。`GET /users/{username}/buckets` 对匿名或非本人只返回 `visibility=public` 的未删除项；owner 看自己时包含 private。私有项在他人列表里被省略，不以 404 逐条出现。

#### Scenario: Non-owner denied on private bucket
- **WHEN** 一名已认证但并非 owner 的用户请求另一用户私有 bucket 的内容
- **THEN** 系统响应 HTTP 404

#### Scenario: Owner lists own private buckets
- **WHEN** owner 认证后请求自己的 `GET /users/{username}/buckets`
- **THEN** 响应包含其未删除的 private 与 public buckets
