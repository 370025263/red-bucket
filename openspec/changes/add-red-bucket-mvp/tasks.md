# 任务：add-red-bucket-mvp

## 1. 项目骨架与存储基础

- [ ] 1.1 搭起服务骨架（单一可部署物：API + 服务端渲染 UI）、依赖清单、README、lint/测试工具、CI 流水线
- [ ] 1.2 实现 SQLite 元数据层（users、buckets、配额字段、issues、PRs、provenance），放在薄数据访问模块后面
- [ ] 1.3 实现 git 存储层：每个 bucket 一个裸仓库，位于 `<root>/<user-id>/<bucket-id>.git`，每 bucket 变更锁，每次变更一次 commit，工作树大小记账
- [ ] 1.4 实现路径清洗（拒绝 `..`、绝对路径、`.git/`、指向树外的符号链接），并用 test-plan suite S7 的单元测试覆盖

## 2. 身份

- [ ] 2.1 注册端点，用户名/邮箱/密码校验规则按 `identity/accounts` spec
- [ ] 2.2 登录端点签发 Bearer tokens；认证中间件对未认证写操作以 401 拒绝
- [ ] 2.3 可见性强制执行：匿名可读公开内容；非 owner 访问私有 bucket 返回 404（不是 403）
- [ ] 2.4 测试套件 S1（accounts）全绿

## 3. Buckets 与资产

- [ ] 3.1 Bucket CRUD 端点：创建时带可见性 + 可选 description + 名称规则，列表，元数据（usage/limit/description），可见性与 description PATCH，删除
- [ ] 3.2 Bucket 数量配额强制执行（每用户可配置上限，默认 5），错误为 `bucket_quota_exceeded`
- [ ] 3.3 模板目录端点，以及 `codex`、`agents`、`claude`、`openclaw` 骨架的模板初始化
- [ ] 3.4 资产校验流水线：按类型的校验器（skill、mcp、instructions、subagent、plugin），产出 rule-id 违规项
- [ ] 3.5 上传端点：校验、10MB 原子配额检查、git commit 归属；raw 下载端点（逐字节一致）
- [ ] 3.6 Bucket 历史端点，以及按 commit 拉取
- [ ] 3.7 测试套件 S2（buckets）和 S3（assets）全绿

## 4. Harness formatter

- [ ] 4.1 Formatter 库骨架：翻译对注册表、纯 translate 函数、lossy-notes 机制、由注册表驱动的能力矩阵端点
- [ ] 4.2 撰写 `cross-transfer/` 文档，给出 Phase 1 各对的字段映射：skill + instructions 覆盖全部四种 harness 风格，mcp 在 claude 与 codex 之间
- [ ] 4.3 实现 {codex, agents, claude, openclaw} 全部 12 个有序对的 skill 翻译器，并带 golden fixtures
- [ ] 4.4 为同样的对实现 instructions 翻译器；mcp 翻译器为 claude<->codex
- [ ] 4.5 翻译拉取端点：单资产与整 bucket 归档；恒等翻译逐字节一致；缺失的对返回 501 `translation_unsupported`；缓存键为 (commit, target)
- [ ] 4.6 按每份 cross-transfer 文档跑等价性实验（固定 harness 版本），记录结果，从文档链接；仅在实验通过后把该对标为 supported
- [ ] 4.7 测试套件 S4（formatter）全绿，含确定性与 golden-fixture 检查

## 5. 协作

- [ ] 5.1 Issues：开/评论/关端点，带角色规则（作者/owner 可关），公开 bucket 匿名可读
- [ ] 5.2 Pull requests：提交 diff、审阅、merge（重新跑校验 + 配额，commit 归属为 PR 作者）、拒绝
- [ ] 5.3 跨 bucket install 端点，带 provenance 元数据与目标配额检查
- [ ] 5.4 测试套件 S5（collaboration）全绿

## 6. Web UI

- [ ] 6.1 服务端渲染的公开页面：落地页、用户资料、GitHub 风格的 bucket 详情（标题、页签、Code 页签文件表、About、README、安装片段）；无 JS 的只读路径；站点头带红色 bucket SVG + `red-bucket` 字标；使用 design.md 里的命名颜色 tokens
- [ ] 6.2 已认证页面：注册/登录、建 bucket（模板 + 可见性 + 可选 description）、从 Code 页签上传、Settings（可见性、description、配额、删除）、issues/PR 页签——全部只走 `/api/v1/`
- [ ] 6.3 每 bucket 的安装脚本端点，拉取翻译后的 bucket 内容并把文件放到目标 harness 布局中
- [ ] 6.4 实现 Code 页签路由 `tree`/`blob`/`commits`/`commit`、Issues 与 Pulls 的列表和详情路由，以及仅 owner 的 Settings 路由（非 owner 为 404）
- [ ] 6.5 测试套件 S6（UI + 安装脚本）全绿

## 7. 验收与发布门禁

- [ ] 7.1 Mock 数据 seeder：1000 个用户，带有代表性的 buckets/assets
- [ ] 7.2 负载测试场景（10 个并发客户端，读为主的混合流量，含翻译拉取，>=5 分钟），产出按端点类的 p95 报告；接入预发布门禁，在 p95 >= 1s 时失败
- [ ] 7.3 跨 harness 迁移验收运行：按每对迁移基准资产，执行等价性 checklist，结果归档（suite S8）
- [ ] 7.4 执行完整测试计划（test-plan.md）；归档报告；更新活文档 ADR `sdd/adr/platform.md` 的验收测试一节，指向 spec scenarios 与测试计划。不要改 `sdd/adr/platform.original.md`。
