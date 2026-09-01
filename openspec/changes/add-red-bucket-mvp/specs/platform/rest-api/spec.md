## Purpose

定义 RESTful API 表面约定：对每一个平台操作的全生命周期覆盖、统一错误模型、版本，以及平台据以验收的延迟服务目标。

## ADDED Requirements

### Requirement: Full-lifecycle REST coverage
系统必须通过 `/api/v1/` 前缀下的版本化 RESTful HTTP API，暴露其他能力所定义的每一个面向用户的操作（accounts、buckets、assets、翻译拉取、issues、PRs、installs、templates、能力矩阵），使用面向资源的路径和标准方法（读用 GET，创建和动作用 POST，部分更新用 PATCH，删除用 DELETE）。Web UI 中可用的每一个操作都 MUST能仅通过 API 完成。

#### Scenario: End-to-end lifecycle via API only
- **WHEN** 一个脚本化客户端注册、登录、从模板创建 bucket、上传资产、更改可见性、按翻译拉取它，并删除该 bucket——只使用已文档化的 `/api/v1/` 端点
- **THEN** 每一步都以已文档化的状态码成功，并且没有任何一步需要 Web UI

### Requirement: Uniform error model
全部 API 错误MUST共享一种 JSON 形状：`{"error": {"code": "<machine_readable_code>", "message": "<human readable>", "details": [...]}}`，并带有合适的 HTTP 状态。错误码必须是稳定标识符（例如 `bucket_quota_exceeded`、`translation_unsupported`、`validation_failed`），适于被 agent 客户端做程序化处理。

#### Scenario: Consistent error shape
- **WHEN** 客户端在不同端点触发任意 4xx 错误（401、404、409、413、422）
- **THEN** 每一个响应体都解析为该统一错误形状，并带有非空且稳定的 `code`

### Requirement: Latency service objective
面向用户的 API MUST满足这一验收目标：在加载了 1000 名注册用户的数据、并且 10 个并发客户端持续行使读为主的混合流量（浏览、列表、raw 拉取、对 10MB bucket 上限内资产的翻译拉取）时，测量窗口内每个端点类的第 95 百分位响应延迟必须低于 1 秒。该目标必须由 CI 或预发布门禁中的可复现负载测试来验证。

#### Scenario: Load test meets p95 under 1s
- **WHEN** 负载测试套件植入 1000 个 mock 用户（每个带有代表性的 buckets 和 assets），并让 10 个并发客户端对读为主的混合流量运行至少 5 分钟
- **THEN** 每一个被行使的端点类测得的 p95 延迟低于 1000ms，并且该次运行报告随发布归档

#### Scenario: Regression gate
- **WHEN** 某个发布候选的负载测试 p95 在任一端点类上超过 1000ms
- **THEN** 发布门禁失败，并且按端点类报告该回归

### Requirement: One-click install script entry
系统MUST提供每 bucket 的安装脚本端点，返回一段可复制粘贴的 shell 命令/脚本，AI agent 可以执行它，把该 bucket 的资产拉取并放到所选目标 harness 的本地布局中。

#### Scenario: Install script fetches and places assets
- **WHEN** 用户复制某个公开 bucket、目标 harness 为 `claude` 的安装脚本，并在干净环境中执行它
- **THEN** 该脚本下载翻译后的 bucket 内容，并把文件放到 claude 风格的本地布局中，以 0 退出
