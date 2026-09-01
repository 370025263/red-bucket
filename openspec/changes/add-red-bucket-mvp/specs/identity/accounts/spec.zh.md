> 本文是同目录 `spec.md` 的逐句中文译本。标识符、路径、状态码、错误码保持原文。

## Purpose

定义用户注册、认证，以及匿名读取边界：写操作一律需要已认证账号，而公开内容无需账号即可读取。

## ADDED Requirements

### Requirement: User registration
系统必须允许访客用唯一用户名和一份凭证（Phase 1 为 email + password）注册账号。用户名必须唯一（大小写不敏感），3-39 个字符，匹配 `[a-z0-9]([a-z0-9-]*[a-z0-9])?`，因为用户名是每个 bucket URL 的命名空间前缀。

#### Scenario: Successful registration
- **WHEN** 访客提交一次注册，用户名为未使用且合法、邮箱合法、密码至少 8 个字符
- **THEN** 系统创建该账号，并以 HTTP 201 返回用户的公开资料（响应中不含凭证材料）

#### Scenario: Duplicate username rejected
- **WHEN** 访客用一个仅字母大小写不同于已有用户名的用户名注册
- **THEN** 系统以 HTTP 409 拒绝该请求，并给出表明用户名已被占用的错误码

#### Scenario: Invalid username rejected
- **WHEN** 访客用含有 `[a-z0-9-]` 以外字符的用户名注册，或以 `-` 开头/结尾，或短于 3 个字符
- **THEN** 系统以 HTTP 422 拒绝该请求，并给出点名 `username` 字段的校验错误

### Requirement: Authentication for write operations
系统必须对每一个创建、修改或删除数据的操作（buckets、assets、issues、pull requests、installs）要求认证。未认证的写尝试必须以 HTTP 401 拒绝。

#### Scenario: Unauthenticated write rejected
- **WHEN** 一个没有有效凭证的请求尝试创建 bucket 或上传资产
- **THEN** 系统响应 HTTP 401，并且不发生任何状态变化

#### Scenario: Authenticated session issued
- **WHEN** 一名已注册用户向登录端点提交正确凭证
- **THEN** 系统返回一个 API token（或 session），可作为后续请求上的 Bearer 凭证使用

#### Scenario: Invalid credentials rejected
- **WHEN** 用户提交错误密码
- **THEN** 系统响应 HTTP 401，且不透露该用户名是否存在

### Requirement: Anonymous read access to public content
系统必须在不要求注册或认证的情况下，提供对公开 buckets 的读操作（浏览、列出资产、拉取/下载、查看 issues 和 pull requests）。

#### Scenario: Anonymous fetch of public bucket
- **WHEN** 未认证客户端请求某个公开 bucket 的资产列表或某份资产下载
- **THEN** 系统以 HTTP 200 返回该内容

#### Scenario: Anonymous access to private bucket denied
- **WHEN** 未认证客户端请求某个私有 bucket 的任何内容
- **THEN** 系统响应 HTTP 404（不是 403），从而不披露私有 bucket 是否存在

### Requirement: Owner-only access to private buckets
系统必须在 Phase 1 把对私有 bucket 的全部访问限制为其 owner（尚无协作者模型）。

#### Scenario: Non-owner denied on private bucket
- **WHEN** 一名已认证但并非 owner 的用户请求另一用户私有 bucket 的内容
- **THEN** 系统响应 HTTP 404
