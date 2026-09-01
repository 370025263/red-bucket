## Purpose

定义 RESTful API 表面约定：对每一个平台操作的全生命周期覆盖、统一错误模型、分页、版本，以及平台据以验收的延迟服务目标。实现 MUST 按本次变更中的 `api-catalog.md` 暴露路径、方法、JSON 字段和错误码；Web UI、日后的 CLI、移动端、MCP 客户端共用这一套，Phase 1 不为后三类另开端点。

## ADDED Requirements

### Requirement: Full-lifecycle REST coverage
系统 MUST 通过 `/api/v1/` 前缀下的版本化 RESTful HTTP API，暴露其他能力所定义的每一个面向用户的操作，使用面向资源的路径和标准方法（读用 GET，创建和动作用 POST，部分更新用 PATCH，删除用 DELETE）。路径、请求体、响应体、`Location` 模板以 `api-catalog.md` 的 Endpoint table 为准。Web UI 中可用的每一个操作都 MUST 能仅通过该目录中的 API 完成。三个名字不得混用：跨桶复制是 `POST .../copies`；本机落盘脚本是 `GET .../install-script`；按 harness 取译本是 `GET .../translated`。不要提供 `POST .../install`。

#### Scenario: End-to-end lifecycle via API only
- **WHEN** 一个脚本化客户端注册、登录、从模板创建 bucket、上传资产、更改可见性、按翻译拉取它，并删除该 bucket——只使用 `api-catalog.md` 中的 `/api/v1/` 端点
- **THEN** 每一步都以已文档化的状态码成功，创建步骤带 `Location`，并且没有任何一步需要 Web UI

#### Scenario: Catalog and implementation stay aligned
- **WHEN** 对照 `api-catalog.md` 的 Endpoint count 清点实现
- **THEN** 每一个列出的 method+path 都存在，并且没有未写入该目录的面向用户的 `/api/v1/` 端点

### Requirement: Uniform error model
全部 API 错误 MUST 共享一种 JSON 形状：`{"error": {"code": "<machine_readable_code>", "message": "<human readable>", "details": [...]}}`，并带有合适的 HTTP 状态。`code` 必须是 `api-catalog.md` Conventions 中列出的稳定标识符（例如 `unauthorized`、`not_found`、`forbidden`、`bucket_quota_exceeded`、`username_taken`、`email_taken`、`bucket_name_taken`、`bucket_storage_exceeded`、`validation_failed`、`translation_unsupported`），适于被 agent 客户端做程序化处理。私有 bucket 对非 owner 一律 HTTP 404、`not_found`，不得用 403 表示「私有但存在」。

#### Scenario: Consistent error shape
- **WHEN** 客户端在不同端点触发任意 4xx 错误（401、403、404、409、413、422）
- **THEN** 每一个响应体都解析为该统一错误形状，并带有非空且稳定的 `code`

### Requirement: List pagination
凡返回数组的列表端点 MUST 使用 `page`（从 1，缺省 1）与 `per_page`（默认 30，最大 100）分页，响应外壳为 `items`、`page`、`per_page`、`total`、`has_more`、`next_cursor`。`next_cursor` 不是第二套协议：有下一页时等于下一页 `page` 的十进制字符串，否则为 `null`。出现 `cursor` 查询参数 MUST 以 HTTP 422 拒绝并点名 `cursor`。超出最大 `per_page` MUST 以 HTTP 422 拒绝并点名 `per_page`。

#### Scenario: Page and per_page list
- **WHEN** 客户端请求某一列表端点并传 `page=1` 与 `per_page=30`
- **THEN** 响应包含 `items` 数组以及 `page`、`per_page`、`total`、`has_more`

#### Scenario: Cursor query rejected
- **WHEN** 客户端在列表端点上传入 `cursor` 查询参数
- **THEN** 系统响应 HTTP 422，并点名 `cursor`

### Requirement: Created resources expose Location
凡创建资源的 201 响应 MUST 带 `Location`，值为该新资源的规范 GET 路径（以 `/api/v1/` 开头），正文仍是该资源的 JSON。各端点的 Location 模板以 `api-catalog.md` 对应行为准。

#### Scenario: Register returns Location
- **WHEN** 访客注册成功
- **THEN** 响应为 HTTP 201，`Location` 为 `/api/v1/users/{username}`

### Requirement: Latency service objective
面向用户的 API MUST 满足这一验收目标：在加载了 1000 名注册用户的数据、并且 10 个并发客户端持续行使读为主的混合流量（浏览、列表、raw 拉取、对 10MB bucket 上限内资产的翻译拉取）时，测量窗口内每个端点类的第 95 百分位响应延迟必须低于 1 秒。该目标必须由 CI 或预发布门禁中的可复现负载测试来验证。

#### Scenario: Load test meets p95 under 1s
- **WHEN** 负载测试套件植入 1000 个 mock 用户（每个带有代表性的 buckets 和 assets），并让 10 个并发客户端对读为主的混合流量运行至少 5 分钟
- **THEN** 每一个被行使的端点类测得的 p95 延迟低于 1000ms，并且该次运行报告随发布归档

#### Scenario: Regression gate
- **WHEN** 某个发布候选的负载测试 p95 在任一端点类上超过 1000ms
- **THEN** 发布门禁失败，并且按端点类报告该回归

### Requirement: One-click install script entry
系统 MUST 提供每 bucket 的 `GET .../install-script` 端点，返回一段可复制粘贴的 shell 命令或脚本，AI agent 可以执行它，把该 bucket 的资产拉取并放到所选目标 harness 的本地布局中。默认 JSON 为 `{target, script, translated_url}`；`Accept: text/plain` 时只返回脚本正文。脚本 MUST 把基础 URL 做成可替换模板，并且只调用本目录中的公开 GET。本端点不是跨桶 `copies`，也不是翻译字节本身。

#### Scenario: Install script fetches and places assets
- **WHEN** 用户复制某个公开 bucket、目标 harness 为 `claude` 的安装脚本，并在干净环境中执行它
- **THEN** 该脚本下载翻译后的 bucket 内容，并把文件放到 claude 风格的本地布局中，以 0 退出
