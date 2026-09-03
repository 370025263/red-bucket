# 任务：add-red-bucket-mvp

实现以 `api-catalog.md` 与 `schema-sqlite.md` 为契约，行为以 `specs/**/spec.md` 为准。栈以 `tech-stack.md` 为准。用户路径以 `user-flows.md` 为准。不要另发明 `/api/v1/` 路径或表列。

## 1. 项目骨架与存储基础

- [x] 1.0 `make lint` 与 `make test` 在空业务树上全绿（semgrep / ruff PEP8 / pylint 命名 / vulture）；CI 跑同一条。未绿之前不写业务代码
- [x] 1.1 按 `tech-stack.md` 搭起服务骨架：Python 3.12、uv、FastAPI + Jinja2 + uvicorn、pytest、单一可部署物、README、CI；目录按选型文档的 `src/redbucket/` 划分
- [x] 1.6 按 `client-skill.md` 维护 `skills/red-bucket/`，保证 `npx skills add 370025263/red-bucket --list` 能发现；不另开客户端 API
- [x] 1.2 按 `schema-sqlite.md` 实现 SQLite 元数据层（九张表、WAL、`foreign_keys=ON`、活桶谓词、字段映射），放在薄数据访问模块后面
- [x] 1.3 实现 git 存储层：每个 bucket 一个裸仓库，位于 `<root>/<user-id>/<bucket-id>.git`，每 bucket 变更锁，每次内容变更一次 commit，作者邮箱 `user-{id}@users.red-bucket.invalid`，成功后按工作树刷新 `storage_usage_bytes`
- [x] 1.4 实现路径清洗（拒绝 `..`、绝对路径、`.git/`、指向树外的符号链接），并用 test-plan suite S7 的单元测试覆盖
- [x] 1.5 把 `assets/logo.svg` 复制进服务静态文件；运行时只从静态目录取 logo

## 2. 身份

- [x] 2.1 注册端点：用户名规则、邮箱大小写不敏感唯一、密码长度至少 8；201 带 `Location`；响应不含 email 与凭证
- [x] 2.2 登录签发 Bearer tokens（只存哈希）；登出撤销当前枚；认证中间件对未认证写操作以 401 `unauthorized` 拒绝
- [x] 2.3 `GET/PATCH /users/me`：PATCH 只改 username 元数据，磁盘不搬家；`GET /users/{username}` 公开资料
- [x] 2.4 可见性强制执行：匿名可读公开内容；非 owner 访问私有 bucket 返回 404（不是 403）；owner 列表含自己的 private
- [x] 2.5 测试套件 S1（accounts）全绿

## 3. Buckets 与资产

- [x] 3.1 Bucket CRUD：创建时带可见性 + 可选 description + 名称规则，列表可见性规则，元数据（usage/limit/description/harness_mix/open counts），可见性与 description PATCH，软删置 `deleted_at`
- [x] 3.2 Bucket 数量配额强制执行（`users.bucket_quota`，默认 5），错误为 `bucket_quota_exceeded`（`details.limit`、`details.current`）
- [x] 3.3 模板目录与详情端点；`codex`、`agents`、`claude`、`openclaw` 骨架文件与内容严格按 `api-catalog.md` Template 一节；无 template 则空树零 commit
- [x] 3.4 资产校验流水线：按类型的校验器（skill、mcp、instructions、subagent、plugin），产出 rule-id 违规项；上传、copy、PR merge 共用
- [x] 3.5 上传端点：校验、10MB 原子配额检查、git commit 归属、201 Location；raw 下载（逐字节一致）
- [x] 3.6 owner DELETE 单份资产：硬删 `assets` 行、工作树删除、copies `dest_asset_id` SET NULL、用量重算
- [x] 3.7 tree、blob、commits、按 commit 拉取端点（从 git 现读，不建 commits 表）
- [x] 3.8 测试套件 S2（buckets）和 S3（assets）全绿

## 4. Harness formatter

- [x] 4.1 Formatter 库骨架：翻译对注册表、纯 translate 函数、lossy-notes 机制、由注册表驱动的能力矩阵端点
- [x] 4.2 撰写 `cross-transfer/` 文档，给出 Phase 1 各对的字段映射：skill、instructions、plugin、subagent 覆盖全部四种 harness 风格的 12 个有序异对；mcp 在 claude 与 codex 之间
- [x] 4.3 实现 {codex, agents, claude, openclaw} 全部 12 个有序异对的 skill 翻译器，并带 golden fixtures
- [x] 4.4 为同样的 12 个异对实现 instructions、plugin、subagent 翻译器；mcp 翻译器为 claude 与 codex 互译；恒等走 raw 字节
- [x] 4.5 翻译拉取端点：单资产不支持则 501 `translation_unsupported` 且不回未翻译正文；整桶默认能译则译并写 notes，`strict=1` 则 501；缓存键为 (commit, target)
- [x] 4.6 按每份 cross-transfer 文档跑等价性实验（固定 harness 版本），记录结果，从文档链接；仅在实验通过后把该对标为 supported
- [x] 4.7 测试套件 S4（formatter）全绿，含确定性与 golden-fixture 检查；S8 覆盖 plugin 与 subagent 基准样本

## 5. 协作

- [x] 5.1 Issues：开/关端点，带角色规则（作者/owner 可关），公开 bucket 匿名可读；评论为一等资源（作者/owner 可发，第三人 403，Phase 1 不编辑不删除）
- [x] 5.2 Pull requests：`files` 为文件树替换列表（存 SQLite），审阅走 GET 详情与 GET files，merge 重跑校验加配额且 commit 归属为 PR 作者，拒绝不改工作树
- [x] 5.3 `POST/GET .../copies`：provenance 快照、目标配额、源不可见则 404；不要做 `POST .../install`
- [x] 5.4 测试套件 S5（collaboration）全绿

## 6. Web UI

- [x] 6.1 落地页与站点头：红色 bucket SVG（来自服务静态文件）+ `red-bucket` 字标；design.md 命名颜色 tokens；无 JS 的只读框。必须对照 https://pi.dev/ 实页截图验收，不是只对照文字描述。
- [x] 6.2 GitHub 风格 bucket 详情 Code 页签：标题、页签计数、文件表、About（消费 catalog 字段）、README、Install（install-script，不是 copies）
- [x] 6.3 已认证页面：注册/登录/登出、建 bucket（模板 + 可见性 + 可选 description）、从 Code 页签上传与删资产、Settings、issues/评论/PR——全部只走 `/api/v1/`
- [x] 6.4 每 bucket 的安装脚本端点按 catalog：JSON 或 `text/plain`，基础 URL 可替换，执行后落位目标 harness
- [x] 6.5 实现 Code 页签路由 `tree`/`blob`/`commits`/`commit`、Issues 与 Pulls 的列表和详情路由，以及仅 owner 的 Settings 路由（非 owner 为 404）
- [x] 6.6 测试套件 S6（UI + 安装脚本）全绿

## 7. API 契约、元数据对齐与发布门禁

- [x] 7.1 对照 `api-catalog.md` Endpoint count 实现全部 method+path；分页只接受 `page`/`per_page`；凡 201 带 Location；错误信封与稳定 code 表
- [x] 7.2 对照 `schema-sqlite.md` 字段映射做静态或集成检查：API JSON 与列无较大差距；活桶谓词覆盖全部桶作用域查询
- [x] 7.3 Mock 数据 seeder：1000 个用户，带有代表性的 buckets/assets
- [x] 7.4 按 `tech-stack.md` 用 Locust 做负载测试（10 个并发客户端，读为主的混合流量，含翻译拉取，>=5 分钟），产出按端点类的 p95 报告；接入预发布门禁，在 p95 >= 1s 时失败
- [x] 7.5 跨 harness 迁移验收运行：按每对迁移基准资产（含 plugin、subagent），执行等价性 checklist，结果归档（suite S8）
- [x] 7.6 执行完整测试计划（test-plan.md，含 S10、S11）；归档报告；更新活文档 ADR `sdd/adr/platform.md` 的验收测试一节，指向 spec scenarios 与测试计划。不要改 `sdd/adr/platform.original.md`
