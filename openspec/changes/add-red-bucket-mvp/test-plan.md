# Test Plan: add-red-bucket-mvp

本文件定义 Phase 1 的测试 suite 与验收条件。行为契约以 `specs/**/spec.md` 中的 Scenario 为准：每条 Scenario 都是一个必须自动化（或明确标注为人工实验）的用例。HTTP 路径、JSON 字段、错误码以 `api-catalog.md` 为准；表与列以 `schema-sqlite.md` 为准。本文负责组织成 suite、补充测试数据与判定口径，并给出发布验收清单。

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
| S11 元数据 schema | platform/metadata-store | 集成 |

## 各 suite 用例

### S1 账号与权限（spec: identity/accounts）

1. 注册成功：合法用户名/邮箱/密码（≥8）→ 201，`Location: /api/v1/users/{username}`，响应无凭证材料、无 email。
2. 用户名大小写冲突 → 409 `username_taken`。
2a. 邮箱大小写冲突 → 409 `email_taken`。
2b. 密码短于 8 → 422，点名 `password`。
3. 非法用户名（越界字符、首尾 `-`、<3 字符，各一例）→ 422 且指明字段。
4. 未认证写操作（建 bucket、传资产各一例）→ 401 `unauthorized` 且无状态变化（事后 GET 验证）。
5. 登录成功签发 token，token 可用于后续写；错密码或不存在的邮箱 → 401 且两种响应不可区分。
5a. 登出 → 204；再用同一 token 访问 `GET /users/me` → 401。
5b. `PATCH /users/me` 改成未占用用户名 → 既有桶在新名下可寻址，磁盘 `<storage-root>/<user-id>/` 未移动；改成他人占用名 → 409 `username_taken`。
6. 匿名读公开 bucket（列表 + 下载）→ 200。
7. 匿名访问私有 bucket → 404；非 owner 认证用户访问他人私有 bucket → 404（与不存在的 bucket 响应不可区分）。
8. owner 列出自己的桶含 private；陌生人列出同一用户只见 public，不是 404。

### S2 Bucket 生命周期（spec: buckets/management）

1. 建 bucket 成功：201，`Location` 正确，元数据齐全（含 description，默认空，以及 usage/limit/harness_mix），出现在 owner 的 bucket 列表。
1a. 创建或 PATCH description（≤350 字）后元数据与详情页 About 可见；超长 → 422 点名 `description`。
2. 同名（大小写）重复 → 409 `bucket_name_taken`。
3. 非法名（含 `/`、空格、大写各一例）→ 422。
4. 第 6 个 bucket → 403 `bucket_quota_exceeded`，错误体含 `limit` 与 `current`；删 1 个后再建成功。
5. 限额是存储中的每用户字段：把某用户 `users.bucket_quota` 改为 6 后第 6 个可建（无公开改配额 API）。
6. public→private 切换后：匿名 404、owner 正常。
7. 4 种 template（codex、agents、claude、openclaw）各建一次：工作树路径与内容与 `api-catalog.md` Template 一节逐文件比对，且为首个 git commit；`GET /templates` 返回 4 种且各带 `files`。
7a. 不传 template → 空工作树、零 commit。
8. 删除后所有引用该 bucket 的 API 路由（含 assets、issues、copies、tree）→ 404；同名可再建成新 id。

### S3 资产上传与校验（spec: buckets/assets）

1. 5 种类型 × 合法样本各 1 → 201，`Location` 指向该资产，列表项含 type、source harness、path、size、mtime。
2. 非法样本矩阵（每类型至少 2 例）：skill 缺 name、frontmatter 不可解析；mcp JSON 语法错、缺 transport；instructions 非 UTF-8、超限；subagent/plugin 结构违规 → 全部 422，violations 含 rule id + 文件路径，bucket 无写入。
3. 未声明类型或未知类型 → 422。
4. 上传、再上传修改版 → 历史端点 2 个 commit，作者归属正确、顺序正确。
5. 9.5MB 基础 + 1MB 上传 → 413 `bucket_storage_exceeded`，报告 usage 与 limit，bucket 内容不变（逐字节比对）。
6. 元数据端点报告 usage 与 10MB limit，usage 与实际工作树差 <1%。
7. 上传后 raw 下载逐字节一致（单文件与多文件归档各一例）。
8. owner DELETE 单份资产 → 该 id GET 404，列表无此项，git 多一次删除 commit；曾作为 copy 目标时 `GET .../copies` 仍列出该记录，`dest_asset.id` 为 null，path/type 为快照。

### S4 Formatter 翻译（spec: translation/harness-formatter）

1. 能力矩阵端点枚举 (type, src, dst)，与注册表一致；Phase 1 最小集：skill、instructions、plugin、subagent 全 4 harness 两两 12 异对加恒等，mcp claude↔codex 加恒等。
2. 每个支持的非恒等翻译对配 golden fixture：源树 → 期望目标树，逐字节比对（矩阵驱动，新增对必须带 fixture）。覆盖 plugin 与 subagent，不得只测 skill。
3. 恒等翻译（target == source）与 raw 下载逐字节一致。
4. 单资产不支持的对 → 501 `translation_unsupported`，不得回退返回未翻译内容。
5. 整 bucket 翻译 fetch：归档内每个可翻译资产落在目标 harness 期望位置。
5a. 整桶含一份对该 target 不支持的 mcp、未带 `strict=1` → 200，该资产不按源格式冒充目标，notes 列出 skipped。
5b. 同一请求 `strict=1` → 501。
6. 有损字段：构造含目标侧无对应字段的源资产 → 输出含 compatibility notes，响应带 `lossy: true`。
7. 确定性：同 commit 同 target 连续 fetch 两次逐字节一致（含缓存命中与未命中两个路径）。
8. 文档一致性（静态检查）：矩阵中每个非恒等支持对 ⇒ `cross-transfer/<src>-2-<dst>.md` 存在、含该类型映射表、链接实验记录；反向：无验证文档的对不得出现在矩阵。

### S5 协作（spec: community/collaboration）

1. 非 owner 在公开 bucket 开 issue → 201，编号按 bucket 内递增，`Location` 正确，匿名可读。
2. 私有 bucket 非 owner 开 issue → 404；owner 可在自己的私有桶开 issue。
3. 第三人关 issue → 403 `forbidden`；作者与 owner 可关；Phase 1 不测 reopen。
3a. 作者发评论 → 201，匿名可列出；第三人发评论 → 403，无新行。
4. PR 全生命周期：提交 `files` 文件树（不是 patch）→ owner merge → 内容按路径级替换生效、未列出的路径不动、commit 作者为 PR 作者、状态 `merged`。
5. merge 触发校验失败 → 422、触发配额超限 → 413，PR 保持 open，bucket 不变。
6. reject → 状态 `rejected`，bucket 不变。
7. 跨 bucket copy（`POST .../copies`）：目标 bucket 出现资产 + provenance（源 full_name、源 commit、dest_path/type 快照、时间），git commit 记录。
8. copy 超配额 → 413 目标不变；从他人私有 bucket copy → 404。
9. 不要存在 `POST .../install`（对该路径断言 404）。

### S6 UI 与安装脚本（spec: platform/web-ui, platform/rest-api）

1. 匿名打开公开 bucket 页：站点头含红色 bucket SVG（来自服务静态文件，不是系统字形）与 `red-bucket` 字标、标题 `username / bucket-name`、Public 标识、Code/Issues/PRs 页签、文件表、About、可复制安装脚本可见，Install 为品牌红而非 GitHub 绿，无登录墙，无 Settings、Star、Watch、Fork。
2. 私有 bucket 页与不存在 bucket 页渲染一致；非 owner 打开 `/settings` 同样是未找到页。
3. 禁用 JavaScript 加载公开 bucket 页：HTML 中含标题、页签、文件表、About 与脚本文本。
4. 登录后 UI 建 bucket（agents template + public）→ 跳转新 bucket 页，骨架与 public 标识正确。
5. UI 操作期间网络日志仅访问 `/api/v1/`（静态资源除外）；跨桶复制若暴露则走 copies，脚本走 install-script。
6. 安装脚本端到端：干净容器内执行 target=claude 的脚本 → 下载翻译内容、落位 claude 本地布局、退出码 0。
7. Code 页：根目录文件表按一层列出目录与文件，含最近 commit 条；进入 `/tree/<path>` 只列该目录子项；文件打开 `/blob/<path>`。
8. 根目录有 `README.md` 与 description 时，README 在文件表下方渲染，About 含 description、可见性、用量、10MB 上限、harness mix（字段与 GET bucket JSON 一致）。
9. 空 bucket：文件表无内容行；owner 看到添加 README 与上传提示。
10. Issues 页签列出一条 open issue（编号、标题、状态、作者、时间）并链到 `/issues/<n>`；页签上的 open 计数与 `open_issues_count` 一致。
11. Owner 可见 Settings 页签，可改 description 与可见性。

### S7 存储安全与配额（spec: platform/git-storage）

1. 每次内容变更（上传、删资产、merge、copy、template 初始化）在 git log 中一一对应 commit，工作树与 API 服务内容一致。不改工作树的操作（改可见性、开 issue、开 PR、登出）不新增 commit。
2. 改用户名后旧 bucket 全部可用，磁盘 repo 未移动（路径按 user-id）。
3. 路径穿越矩阵：`../`、绝对路径、`.git/` 前缀 → 422，树外无任何读写（用哨兵文件验证）。
4. 归档内符号链接指向树外 → 拒绝或剥离，树外路径不被解析。
5. 并发配额：两个各自合规、合计超限的并发上传 → 至多一个成功，另一个 413，最终工作树 ≤10MB（重复运行 ≥20 次防 flake）。
6. 按历史 commit fetch 资产 → 内容与该 commit 一致。SQLite 无 commits 业务表。

### S8 跨 harness 功能等价性（spec: translation/harness-formatter）

基准资产集：每种资产类型至少 1 个有代表性的基准样本（含 skill、instructions、plugin、subagent、mcp），含触发条件 + 可观察效果。

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

1. 纯 API 全生命周期脚本：注册→登录→template 建 bucket→上传→改可见性→翻译 fetch→登出后再写失败→用新登录删桶，全部走 `/api/v1/`，状态码与 `Location` 逐步断言。
2. 错误模型扫描：对 401/403/404/409/413/422/501 各触发点断言响应体解析为统一 `{"error":{"code","message","details"}}`，code 属于 catalog 稳定表（快照测试防漂移）。
3. 分页：某一列表传 `page`/`per_page` 外壳字段齐全；传 `cursor` → 422 点名 `cursor`；`per_page=101` → 422 点名 `per_page`。
4. 对照 `api-catalog.md` Endpoint count：每一个 method+path 可到达（鉴权按该行）；不存在未列入的面向用户 `/api/v1/` 路由；不存在 `POST .../install`。

### S11 元数据 schema（spec: platform/metadata-store）

1. 空库启动后九张表存在，列名与 `schema-sqlite.md` DDL 一致（可用 sqlite_master / pragma table_info 比对）。
2. 活桶谓词：软删后凭旧路径与子表主键都读不到；`bucket_count` 与个数配额不计软删行。
3. 字段映射抽查：User / Bucket / Asset / Issue / IssueComment / PullRequest / InstallRecord 的 JSON 键都能在 schema 映射表找到列或约定计算，没有只存在于 JSON 或只存在于表的业务字段（计算字段按映射表标注）。
4. WAL 与 `foreign_keys=ON` 在进程打开后生效。

## 发布验收清单（Phase 1 出厂判定）

1. S1-S7、S10、S11 全绿（CI 必跑）。
2. S8：能力矩阵中每个 supported 非恒等翻译对都有归档的等价性实验且判定通过（含 plugin、subagent）。
3. S9：负载报告归档，全部端点类 p95 < 1s。
4. 静态一致性：能力矩阵 ⇔ cross-transfer 文档双向一致（S4.8）；`api-catalog.md` ⇔ 实现端点双向一致（S10.4）；`schema-sqlite.md` ⇔ 表列双向一致（S11.1）。
5. openspec validate --strict 通过，specs 与实现无已知偏差。

原 ADR 中两条验收（p95 延迟、迁移前后功能一致）分别由 S9 与 S8 细化落地；ADR 其余功能点逐条落在 S1-S7 对应 Scenario。
