> 本文是同目录 `proposal.md` 的逐句中文译本。标识符、路径、状态码、错误码保持原文。

# 提案：add-red-bucket-mvp

## 为什么

AI agent 资产（skills、MCP 工具配置、CLAUDE.md/AGENTS.md、subagents、plugins）分散在互不兼容的 harness 生态中（Codex、Claude Code、OpenClaw、通用 Agents 风格）。用户无法在不手工改写的情况下跨 harness 分享或复用资产。red-bucket 提供一个 GitHub/HuggingFace 风格的枢纽（`user/bucket` 命名空间），其核心价值是拉取时的跨 harness 格式翻译，通过 RESTful API 和轻量 Web UI 对外提供。本次变更把 `sdd/adr/platform.md` 中的粗略 ADR 转成 Phase 1（MVP）可实现、可测试的规格。

## 改动内容

- 引入用户账号：写操作必须注册并认证；公开 bucket 允许匿名读取。
- 引入 bucket 管理：在 `user/bucket-name` 命名空间下创建或删除 bucket，public/private 可见性，可选目录模板（codex、agents、claude、openclaw 风格），配额（每用户 5 个 bucket，每个 bucket 10MB）。
- 引入带格式校验的资产上传，覆盖受支持的资产类型（skill、MCP 工具配置、CLAUDE.md/AGENTS.md、subagent、plugin），并标记源 harness。
- 引入拉取时的 harness 翻译：formatter 把 bucket 资产转换成请求方 harness 的格式；每一对翻译规则写在 `cross-transfer/<src>-2-<dst>.md` 中，并由实验验证。
- 引入公开 bucket 上的社区协作：issues 和 pull requests；把其他用户 bucket 中的资产安装到自己的 bucket。
- 引入覆盖上述全部操作的全生命周期 RESTful API，并带有 p95 延迟服务目标。
- 引入文件系统上的 git 存储，每个 bucket 一个 git 仓库，按 user id 隔离，并强制执行配额。
- 引入轻量 Web UI（pi.dev 风格），用于浏览、bucket 管理，以及安装脚本入口。

明确不在 Phase 1 范围内（延后，以后再说）：

- 移动应用（App Store / APK 分发）——上架费用对 Phase 1 来说过高。
- 对 bucket 的直接 `git clone`/git 协议访问——Phase 1 只提供 API 和 UI。
- 超出基础跨 bucket 安装的 MCP/plugin 市场。

## 能力

### 新增能力

- `identity/accounts`：用户注册、认证，以及匿名公开读取。
- `buckets/management`：bucket 生命周期、`user/bucket` 命名空间、可见性、模板、配额上限。
- `buckets/assets`：带按类型格式校验的资产上传，以及 bucket 内的列表与下载。
- `translation/harness-formatter`：拉取时在 harness 格式之间转换资产；翻译规则文档与功能等价保证。
- `community/collaboration`：公开 bucket 上的 issues、pull requests，以及跨 bucket 资产安装。
- `platform/rest-api`：RESTful API 约定、全生命周期覆盖、错误模型，以及延迟服务目标。
- `platform/git-storage`：以 git 为后端的文件系统存储布局、按用户隔离、配额强制执行、历史耐久性。
- `platform/web-ui`：轻量前端页面，以及一键安装脚本入口。

### 修改的能力

（无——这是第一次变更；尚无既有规格。）

## 影响

- 新代码库：后端 API 服务、formatter 引擎、git 存储层、Web 前端。没有既有代码会受影响。
- 新的文档族：`cross-transfer/<src>-2-<dst>.md` 翻译规则文档，每一份都由实验验证。
- 测试套件与验收标准与规格一并定义（见本次变更中的 `test-plan.md` 以及各 spec 中的 scenarios）；头条验收：在 1000 名注册用户、并发 10 的条件下，95% 的面向用户的 API 请求在 1s 内完成；跨 harness 迁移保持被迁移资产的功能行为。
