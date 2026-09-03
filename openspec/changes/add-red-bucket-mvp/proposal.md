# 提案：add-red-bucket-mvp

## Why

AI agent 资产（skills、MCP 工具配置、CLAUDE.md/AGENTS.md、subagents、plugins）分散在互不兼容的 harness 生态中（Codex、Claude Code、OpenClaw、通用 Agents 风格）。用户无法在不手工改写的情况下跨 harness 分享或复用资产。red-bucket 提供一个 GitHub/HuggingFace 风格的枢纽（`user/bucket` 命名空间），其核心价值是拉取时的跨 harness 格式翻译，通过一套 RESTful API 和轻量 Web UI 对外提供。日后的 CLI、移动端、MCP 客户端共用这一套 API，Phase 1 不为它们另开端点。本次变更把 `sdd/adr/platform.md` 中的粗略 ADR 转成 Phase 1（MVP）可实现、可测试的规格。

## What Changes

- 引入用户账号：写操作必须注册并认证；公开 bucket 允许匿名读取。邮箱大小写不敏感唯一；密码至少 8 个字符。提供登出撤销当前 token。改用户名只改元数据，磁盘仓库按不可变 user id 存放。
- 引入 bucket 管理：在 `user/bucket-name` 命名空间下创建或删除 bucket，public/private 可见性，可选目录模板（`codex`、`agents`、`claude`、`openclaw`，骨架文件以 `api-catalog.md` 为准），配额（每用户 5 个 bucket，每个 bucket 10MB）。owner 列出自己的桶时能看到私有项；他人列表只省略私有项，不用 404。
- 引入带格式校验的资产上传，覆盖 skill、mcp、instructions、subagent、plugin，并标记源 harness。owner 可删除单份资产。
- 引入拉取时的 harness 翻译：formatter 把资产转换成请求方 harness 的格式。Phase 1 对 skill、instructions、plugin、subagent 在四种 harness 之间各做 12 个有序异对加恒等；mcp 只做 claude 与 codex 互译加恒等。每一对规则写在 `cross-transfer/<src>-2-<dst>.md` 中，并由实验验证。
- 引入公开 bucket 上的社区协作：issues 与一等评论资源；pull requests 的提议内容是文件树替换列表，不是 git patch；跨 bucket 复制走 `copies`（provenance），不要和安装脚本文本、翻译拉取共用一个动词。
- 引入覆盖上述全部操作的全生命周期 RESTful API。路径、JSON 字段、错误码以本次变更中的 `api-catalog.md` 为准。分页只用 `page` 与 `per_page`。201 带 `Location`。
- 引入 SQLite（WAL）元数据存储，表结构以本次变更中的 `schema-sqlite.md` 为准；git 只保存 bucket 文件字节与 commit 对象。
- 引入文件系统上的 git 存储，每个 bucket 一个 git 仓库，按 user id 隔离，并强制执行配额。
- 引入轻量 Web UI（pi.dev 风格全局框、GitHub 风格仓库页、红色 bucket logo），用于浏览、bucket 管理，以及安装脚本入口。UI 只消费同一套 `/api/v1/`。
- 确立 Phase 1 技术选型（`tech-stack.md`）：Python 3.12、FastAPI、Jinja2、SQLite 薄 DAL、系统 git、Argon2id、pytest、Locust。
- 画出用户时序（`user-flows.md`）：注册登录、建桶、上传、翻译拉取、安装脚本、跨桶 copy、issue、PR、登出、私有桶 404。
- 引入用户侧 skill 入口（`client-skill.md`）：本仓库 `skills/red-bucket/` 供 `npx skills add`；资产落盘走服务端 install-script（自包含 Node 程序）或 skill 自带的 `scripts/rb.mjs`；客户端只依赖 Node。仓库 MIT 开源。
- 代码门禁对齐 SkillNerds/xskill：semgrep 自定义规则、ruff（含 PEP8 E/W）、pylint 命名、vulture。先有 lint 再写业务。

明确不在 Phase 1 范围内（延后，以后再说）：

- 移动应用（App Store / APK 分发）——上架费用对 Phase 1 来说过高。客户端以后复用同一套 API。
- 对 bucket 的直接 `git clone` 或 git 协议访问——Phase 1 只提供 API 和 UI。
- 超出基础跨 bucket 复制的 MCP/plugin 市场。
- 官方第一方 skill 或 MCP 客户端本体——以后作为本 API 的调用方再做，不为它们另开 Phase 1 端点。
- Star、Watch、Fork，以及额外的 GitHub 页签。
- 落地页搜索与市场排序。

## Capabilities

### New Capabilities

- `identity/accounts`：用户注册、认证、登出、改用户名，以及匿名公开读取。
- `buckets/management`：bucket 生命周期、`user/bucket` 命名空间、可见性、模板骨架、配额上限。
- `buckets/assets`：带按类型格式校验的资产上传、列表、raw 下载、单资产删除。
- `translation/harness-formatter`：拉取时在 harness 格式之间转换资产；skill、instructions、plugin、subagent 全矩阵，mcp 仅 claude 与 codex；翻译规则文档与功能等价保证。
- `community/collaboration`：公开 bucket 上的 issues、评论、pull requests，以及跨 bucket 资产复制（`copies`）。
- `platform/rest-api`：RESTful API 约定，以 `api-catalog.md` 为权威目录；错误模型、分页、Location，以及延迟服务目标。
- `platform/metadata-store`：SQLite 元数据表与字段，以 `schema-sqlite.md` 为权威 DDL；与 API JSON 一一对应。
- `platform/git-storage`：以 git 为后端的文件系统存储布局、按用户隔离、配额强制执行、历史耐久性。
- `platform/web-ui`：轻量前端页面、GitHub 风格的 bucket 详情页、红色 bucket 标识，以及一键安装脚本入口。

### Modified Capabilities

（无——这是第一次变更；尚无既有规格。）

## 影响

- 新代码库：后端 API 服务、formatter 引擎、SQLite 元数据层、git 存储层、Web 前端。没有既有代码会受影响。
- 新的文档族：`cross-transfer/<src>-2-<dst>.md` 翻译规则文档，每一份都由实验验证。
- 测试套件与验收标准与规格一并定义（见本次变更中的 `test-plan.md` 以及各 spec 中的 scenarios）；头条验收：在 1000 名注册用户、并发 10 的条件下，95% 的面向用户的 API 请求在 1s 内完成；跨 harness 迁移保持被迁移资产的功能行为。
