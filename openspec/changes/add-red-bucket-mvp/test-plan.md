# Test Plan: add-red-bucket-mvp

本文件定义 Phase 1 的测试 suite 与验收条件。行为契约以 `specs/**/spec.md` 中的 Scenario 为准（中文译本为同目录 `spec.zh.md`）：每条 Scenario 都是一个必须自动化（或明确标注为人工实验）的用例，本文负责组织成 suite、补充测试数据与判定口径，并给出发布验收清单。

## 测试层次

- 单元：validator、formatter 纯函数、路径清洗、配额计算。无 I/O，毫秒级。
- 集成（API 级）：起真实服务 + 临时存储根 + 临时 SQLite，按 HTTP 契约断言。Scenario 用例的主要归宿。
- 端到端：UI 渲染、安装脚本在干净环境执行。
- 性能：负载测试，发布门禁。
- 实验（人工一次 + 记录）：跨 harness 功能等价性，结果归档后转回归。

## Suite 一览

| Suite | 覆盖 spec | 层次 |
| --- | --- | --- |
| S1 账号与权限 | identity/accounts | 集成 |
| S2 Bucket 生命周期 | buckets/management | 集成 |
| S3 资产上传与校验 | buckets/assets | 单元 + 集成 |
| S4 Formatter 翻译 | translation/harness-formatter | 单元 + 集成 |
| S5 协作 | community/collaboration | 集成 |
| S6 UI 与安装脚本 | platform/web-ui, platform/rest-api(安装脚本) | 端到端 |
| S7 存储安全与配额 | platform/git-storage | 单元 + 集成 |
| S8 跨 harness 等价性 | translation/harness-formatter(功能等价) | 实验 + 回归 |
| S9 性能门禁 | platform/rest-api(延迟目标) | 性能 |
| S10 API 契约一致性 | platform/rest-api | 集成 |

## 各 suite 用例

### S1 账号与权限（spec: identity/accounts）

1. 注册成功：合法用户名/邮箱/密码 → 201，响应无凭证材料。
2. 用户名大小写冲突 → 409。
3. 非法用户名（越界字符、首尾 `-`、<3 字符，各一例）→ 422 且指明字段。
4. 未认证写操作（建 bucket、传资产各一例）→ 401 且无状态变化（事后 GET 验证）。
5. 登录成功签发 token，token 可用于后续写；错密码 → 401 且响应不区分「用户不存在」与「密码错」。
6. 匿名读公开 bucket（列表 + 下载）→ 200。
7. 匿名访问私有 bucket → 404；非 owner 认证用户访问他人私有 bucket → 404（与不存在的 bucket 响应不可区分）。

### S2 Bucket 生命周期（spec: buckets/management）

1. 建 bucket 成功：201，元数据齐全，出现在 owner 的 bucket 列表。
2. 同名（大小写）重复 → 409。
3. 非法名（含 `/`、空格、大写各一例）→ 422。
4. 第 6 个 bucket → 403 `bucket_quota_exceeded`，错误体含当前限额；删 1 个后再建成功。
5. 限额是存储中的每用户字段：把某用户限额改为 6 后第 6 个可建（配置生效性测试）。
6. public→private 切换后：匿名 404、owner 正常。
7. 4 种 template（codex、agents、claude、openclaw）各建一次：骨架内容正确且为首个 git commit；template 目录端点返回 4 种。
8. 删除后所有引用该 bucket 的 API 路由 → 404。

### S3 资产上传与校验（spec: buckets/assets）

1. 5 种类型 × 合法样本各 1 → 201，列表项含 type、source harness、path、size、mtime。
2. 非法样本矩阵（每类型至少 2 例）：skill 缺 name、frontmatter 不可解析；mcp JSON 语法错、缺 transport；instructions 非 UTF-8、超限；subagent/plugin 结构违规 → 全部 422，violations 含 rule id + 文件路径，bucket 无写入。
3. 未声明类型或未知类型 → 422。
4. 上传、再上传修改版 → 历史端点 2 个 commit，作者归属正确、顺序正确。
5. 9.5MB 基础 + 1MB 上传 → 413 `bucket_storage_exceeded`，报告 usage 与 limit，bucket 内容不变（逐字节比对）。
6. 元数据端点报告 usage 与 10MB limit，usage 与实际工作树差 <1%。
7. 上传后 raw 下载逐字节一致（单文件与多文件归档各一例）。

### S4 Formatter 翻译（spec: translation/harness-formatter）

1. 能力矩阵端点枚举 (type, src, dst)，与注册表一致；Phase 1 最小集：skill、instructions 全 4 harness 两两 12 对，mcp claude↔codex。
2. 每个支持的翻译对配 golden fixture：源树 → 期望目标树，逐字节比对（矩阵驱动，新增对必须带 fixture）。
3. 恒等翻译（target == source）与 raw 下载逐字节一致。
4. 不支持的对 → 501 `translation_unsupported`，不得回退返回未翻译内容。
5. 整 bucket 翻译 fetch：归档内每个可翻译资产落在目标 harness 期望位置。
6. 有损字段：构造含目标侧无对应字段的源资产 → 输出含 compatibility notes，响应带 `lossy: true`。
7. 确定性：同 commit 同 target 连续 fetch 两次逐字节一致（含缓存命中与未命中两个路径）。
8. 文档一致性（静态检查）：矩阵中每个支持对 ⇒ `cross-transfer/<src>-2-<dst>.md` 存在、含该类型映射表、链接实验记录；反向：无验证文档的对不得出现在矩阵。

### S5 协作（spec: community/collaboration）

1. 非 owner 在公开 bucket 开 issue → 201，编号按 bucket 内递增，匿名可读。
2. 私有 bucket 非 owner 开 issue → 404。
3. 第三人关 issue → 403；作者与 owner 可关。
4. PR 全生命周期：提交 → owner merge → 内容生效、commit 作者为 PR 作者、状态 `merged`。
5. merge 触发校验失败 → 422、触发配额超限 → 413，PR 保持 open，bucket 不变。
6. reject → 状态 `rejected`，bucket 不变。
7. 跨 bucket install：目标 bucket 出现资产 + provenance（源 bucket、源 commit、时间），git commit 记录。
8. install 超配额 → 413 目标不变；从他人私有 bucket install → 404。

### S6 UI 与安装脚本（spec: platform/web-ui, platform/rest-api）

1. 匿名打开公开 bucket 页：资产列表 + 可复制安装脚本可见，无登录墙。
2. 私有 bucket 页与不存在 bucket 页渲染一致。
3. 禁用 JavaScript 加载公开 bucket 页：HTML 中含资产列表与脚本文本。
4. 登录后 UI 建 bucket（agents template + public）→ 跳转新 bucket 页，骨架与 public 标识正确。
5. UI 操作期间网络日志仅访问 `/api/v1/`。
6. 安装脚本端到端：干净容器内执行 target=claude 的脚本 → 下载翻译内容、落位 claude 本地布局、退出码 0。

### S7 存储安全与配额（spec: platform/git-storage）

1. 每次变更（上传、merge、install、template 初始化）在 git log 中一一对应 commit，工作树与 API 服务内容一致。
2. 改用户名后旧 bucket 全部可用，磁盘 repo 未移动（路径按 user-id）。
3. 路径穿越矩阵：`../`、绝对路径、`.git/` 前缀 → 422，树外无任何读写（用哨兵文件验证）。
4. 归档内符号链接指向树外 → 拒绝或剥离，树外路径不被解析。
5. 并发配额：两个各自合规、合计超限的并发上传 → 至多一个成功，另一个 413，最终工作树 ≤10MB（重复运行 ≥20 次防 flake）。
6. 按历史 commit fetch 资产 → 内容与该 commit 一致。

### S8 跨 harness 功能等价性（spec: translation/harness-formatter）

基准资产集：每种资产类型至少 1 个有代表性的基准样本（含触发条件 + 可观察效果，例如「读 skill 后按指令输出固定标记」的探针型 skill）。

流程（每个支持翻译对执行一次，harness 版本 pin 在 cross-transfer 文档中）：

1. 源 harness 安装源资产，跑固定任务 prompt，记录：是否识别、是否触发、输出效果。
2. 翻译后安装到目标 harness，同 prompt 重跑，记录同三项。
3. 按该翻译对文档中的等价性 checklist 判定：识别与触发必须一致；效果按 checklist 条目逐项比对。
4. 结果（环境、版本、记录、判定）归档并从 cross-transfer 文档链接；任何一项不等价 ⇒ 该对不得标记 supported。

回归：harness 版本更新或翻译器改动时重跑受影响对。

### S9 性能门禁（spec: platform/rest-api）

数据准备：seeder 生成 1000 个 mock 用户，每用户 1-5 个 bucket，资产类型与大小分布覆盖典型与接近 10MB 上限的 bucket。

负载模型：10 个并发客户端，持续 ≥5 分钟，读为主的混合流量，按端点类分桶统计：

| 端点类 | 混合占比（建议） |
| --- | --- |
| 浏览（用户页、bucket 元数据） | 30% |
| 资产列表 | 25% |
| raw 下载 | 20% |
| 翻译 fetch（单资产 + 整 bucket） | 15% |
| 写混入（上传、开 issue） | 10% |

判定：每个端点类 p95 < 1000ms 全部达标才通过；任一超标 → 门禁失败并按端点类输出报告。报告随版本归档。冷缓存约束：翻译 fetch 桶中至少 20% 请求命中未缓存的 (commit, target) 组合，防止全命中缓存虚高。

### S10 API 契约一致性（spec: platform/rest-api）

1. 纯 API 全生命周期脚本：注册→登录→template 建 bucket→上传→改可见性→翻译 fetch→删除，全部走 `/api/v1/`，状态码逐步断言。
2. 错误模型扫描：对 401/404/409/413/422 各触发点断言响应体解析为统一 `{"error":{"code","message","details"}}`，code 非空且稳定（快照测试防漂移）。

## 发布验收清单（Phase 1 出厂判定）

1. S1-S7、S10 全绿（CI 必跑）。
2. S8：能力矩阵中每个 supported 翻译对都有归档的等价性实验且判定通过。
3. S9：负载报告归档，全部端点类 p95 < 1s。
4. 静态一致性：能力矩阵 ⇔ cross-transfer 文档双向一致（S4.8）。
5. openspec validate --strict 通过，specs 与实现无已知偏差。

原 ADR 中两条验收（p95 延迟、迁移前后功能一致）分别由 S9 与 S8 细化落地；ADR 其余功能点逐条落在 S1-S7 对应 Scenario。
