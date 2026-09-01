# 设计：add-red-bucket-mvp

## 背景

全新仓库；唯一既有产物是 `sdd/adr/platform.md` 中的 ADR。OpenSpec 细化前的原文冻在 `sdd/adr/platform.original.md`，不得改动。从中继承的约束：存储是文件系统上的 git（不用对象存储），配额是每用户 5 个 bucket、每 bucket 10MB，Phase 1 不含移动应用和 git 协议访问，前端遵循 pi.dev 的轻量风格，头条验收是 1000 用户 / 并发 10 下 p95 < 1s。动机见 `proposal.md`；行为契约见各 delta specs。

## 目标 / 非目标

**目标：**

- 一个可单独部署的服务（API + 服务端渲染 UI），外加一个可隔离测试的 formatter 引擎。
- 确定性的、由矩阵驱动的翻译，使不支持的对大声失败，已支持的对可用 golden fixtures 做回归测试。
- 全部验收标准都可以作为自动化测试执行（见 `test-plan.md`）。

**非目标：**

- 水平扩展 / 多节点存储；Phase 1 目标是单节点，负载画像见各 specs。
- 协作者/团队权限模型（Phase 1 私有访问仅限 owner）。
- 市场策展、搜索排序、计费。
- bucket 页上的 GitHub 社交控件（Star、Watch、Fork）以及额外的 GitHub 页签（Actions、Projects、Wiki、Security、Insights、Discussions）。

## 决策

1. 单体，服务端渲染 UI，JSON API 位于 `/api/v1/`。
   理由：1000 用户规模不需要微服务；服务端渲染能低成本满足「只读路径在没有 JavaScript 时也能工作」的要求。备选（SPA + 独立 API 服务）因更重、且对匿名抓取/读取延迟更不利而被否决。

2. Formatter 作为带翻译对注册表的纯库。
   每一个（资产类型, src, dst）对注册一个纯函数 `translate(sourceTree) -> targetTree + lossyNotes`。能力矩阵端点读取该注册表，因此代码与矩阵不会漂移。无 I/O 的纯函数给出确定性（规格要求），并使 golden-fixture 测试变得简单。Phase 1 矩阵：skill、instructions、plugin、subagent 各覆盖 `{codex, agents, claude, openclaw}` 的 12 个有序异对加恒等；mcp 只做 claude 与 codex 互译加恒等。plugin 与 subagent 与 skill 同等，必须翻译，不能只存不转。备选（LLM 辅助翻译）在 Phase 1 被否决：非确定性，违反确定性要求；以后可以作为 cross-transfer 文档的离线撰写辅助再回来。

3. 存储布局为 `<storage-root>/<user-id>/<bucket-id>.git`，使用裸仓库 + 每次变更的 worktree，变更按 bucket 用每 bucket 一把锁串行化。
   不可变 id 让用户名/bucket 重命名只动元数据。每 bucket 锁提供规格要求的原子配额「先检查再提交」；在此规模下争用可忽略。备选（非裸仓库加长期存活的 worktree）被否决：更难做成并发安全。

4. 元数据放在 SQLite（WAL）；权威 DDL 与字段映射见本次变更的 `schema-sqlite.md`。
   九张表：`schema_migrations`、`users`、`tokens`、`buckets`、`assets`、`copies`、`issues`、`issue_comments`、`pull_requests`。git 只保存文件字节与 commit 对象，不建 commits 表。列表、配额、issue/PR/copy 出处需要可查询性；为这些去解析 git 会打爆延迟预算。SQLite 足以支撑 1000 用户 / 并发 10。备选（Postgres）延后到规模需要时再做；数据访问层保持很薄，列类型按可迁 Postgres 来选。API JSON 与表列的对应写在 schema 文档里，实现不得另发明一套字段名。

5. 校验作为上传、PR merge 和跨桶 copy 共用的流水线。
   每种资产类型一个校验器，产出机器可读的违规项（`rule id + path`），在内容进入 bucket 的所有入口复用，因此 PR merge 和 `POST .../copies` 不能绕过上传规则（规格要求）。PR 提议内容是文件树替换列表 `{path, content_text|content_base64, delete?}`，存在 SQLite，不是 git patch。

6. 认证：email+password 加盐哈希，Bearer API tokens；私有 bucket 拒绝一律回答 404。
   返回 404 而不是 403 是规格层的反枚举决策。OAuth/社交登录延后。

7. 把负载测试作为仓库一等产物（k6 或 Locust 场景 + 1000 个 mock 用户的 seeder），作为预发布门禁运行并产出归档报告。
   p95 验收是规格要求；让该 harness 在仓库内可复现，是「回归门禁」场景能诚实让一次发布失败的唯一办法。

8. Bucket 详情页照搬 GitHub 的仓库信息结构，不照搬 GitHub 的视觉素材。
   ADR 要求一个 GitHub 风格的 `user/bucket` 枢纽。因此路径 `/<username>/<bucket-name>` 的页面遵循 GitHub 仓库首页使用的分区：owner/name 标题、可见性标识、仓库导航页签栏、带最近 commit 条的一层文件表、文件下方渲染的 `README.md`，以及右侧 About 侧栏。clone/Code 按钮对应 Install（目标 harness 选择器 + 可复制脚本）。Phase 1 页签是 Code、Issues、Pull requests，以及 Settings（仅 owner）。备选（没有页签的扁平资产倾倒）被否决：它不符合 ADR 所描述的 GitHub 风格产品。

9. 视觉系统是两层混合：全局框对照 pi.dev，仓库页控件对照 GitHub；标识是一只红桶。
   pi.dev 是接近印刷品的长文站点（白底、近黑字、稀疏页头、很少装饰）。GitHub 仓库首页是更密的 Primer 式控件（下划线页签、文件表、About、徽章）。red-bucket 有意两层都用：落地页和站点头感觉像 pi.dev；bucket 详情页的分区像 GitHub。品牌强调色不是 GitHub 绿，也不是未改过的 emoji：它是 bucket emoji（U+1FAA3）的第一方 SVG，桶身涂成品牌红。不要引入 pi.dev 素材、GitHub Primer CSS 或 octicons。权威源文件：`openspec/changes/add-red-bucket-mvp/assets/logo.svg`；实现时复制进服务静态文件，归档本变更后仍以服务内那份为准。

10. HTTP 契约以 `api-catalog.md` 为唯一表面，三个「install」名字不得混用。
    全部面向用户的 JSON 走 `/api/v1/`。Web UI、日后 CLI、移动端、官方 skill 或 MCP 客户端都消费这一套，Phase 1 不为后几类另开端点。分页只实现 `page` + `per_page`（默认 30，最大 100）；出现 `cursor` 查询参数一律 422。凡 201 带 `Location`。三个名字：`copy` 是 `POST .../copies`（跨桶复制加 provenance，JSON 类型叫 InstallRecord）；`install-script` 是 `GET .../install-script`（给本机落盘的 shell 文本）；`translated fetch` 是 `GET .../translated`。不要做 `POST .../install`。错误信封与稳定 `code` 以目录 Conventions 为准。私有桶对非 owner 一律 404 不是 403。

11. 实现栈以 `tech-stack.md` 为准：Python 3.12、FastAPI、Jinja2、uvicorn、标准库 sqlite3 薄 DAL、系统 git 子进程、Argon2id、pytest、Locust、uv、ruff。
    用户怎么走完注册、建桶、上传、翻译拉取、安装脚本、copy、issue、PR，以 `user-flows.md` 的时序为准。换语言或框架必须先改选型文档。备选里最强的是 Go，本期不用。

## Bucket 详情页（GitHub 对照）

默认 URL：`/<username>/<bucket-name>`（Code 页签，工作树根）。子路由遵循 GitHub 的仓库 URL 形状，以便熟悉 GitHub 的用户能够猜到：

- `/<username>/<bucket-name>/tree/<path>` — 目录
- `/<username>/<bucket-name>/blob/<path>` — 文件
- `/<username>/<bucket-name>/commits` — 历史列表
- `/<username>/<bucket-name>/commit/<sha>` — 一次 commit
- `/<username>/<bucket-name>/issues` 与 `/issues/<n>`
- `/<username>/<bucket-name>/pulls` 与 `/pulls/<n>`
- `/<username>/<bucket-name>/settings` — 仅 owner；其他人得到与缺失 bucket 相同的 404

Code 页签的布局（桌面）：

```
/<username>/<bucket-name>
┌─────────────────────────────────────────────────────────────┐
│  username / bucket-name                     [Public|Private] │
│  [Code]  Issues (n)  Pull requests (n)  Settings (owner)     │
├───────────────────────────────────┬─────────────────────────┤
│ Latest commit: msg · author · sha │ About                   │
│ path crumbs · Install + harness   │ description             │
│ File table (this directory)       │ visibility              │
│   name | last commit | time       │ usage / 10MB            │
│   + type, source harness if asset │ template (if any)       │
│ README.md rendered below          │ harness mix             │
│                                   │ README link             │
└───────────────────────────────────┴─────────────────────────┘
```

GitHub 分区 → Phase 1 映射：

- 标题 `owner / repo-name` → `username / bucket-name`。
- Public/Private 标识 → 相同。
- Star、Watch、Fork → 省略。
- 页签 Code、Issues、Pull requests、Settings → 同样四个；页签上带 open issue 与 open PR 计数。Actions、Projects、Wiki、Security、Insights、Discussions → 省略。
- 分支选择器 → 省略。Phase 1 没有 git 协议的分支 UI；Code 页签浏览当前工作树（HEAD）。历史内容使用 git-storage 已经要求的 commits 路由。
- Code / clone 按钮 → Install：目标 harness 选择器和可复制的安装脚本（既有的一键入口）。
- Add file → owner 在 Code 页签上传（既有上传流水线）。
- 文件表列 name、last commit message、last updated → 相同，并且当该行是一份已存资产时再加上资产类型和源 harness。列表是一层目录（GitHub 行为），从资产路径派生；它不是扁平的类型倾倒。
- 文件表下方的 `README.md` → 当前目录存在 `README.md` 时渲染它（名称大小写不敏感）。空 bucket 或没有 README 的 bucket 的 owner 看到添加提示；访客只是看不到 README 块。
- About：description、website、topics、releases、packages、contributors、languages → description（可选，最多 350 个字符，GitHub 的 About 上限）、可见性、存储用量和 10MB 上限、若从模板创建则带模板风格，以及按源 harness 统计的已存资产数量（languages 的对照物）。Phase 1 没有 website、topics、stars、releases 或贡献者图。
- Go to file / 仓内搜索 → Phase 1 省略；10MB 的一层列表已经足够。

空 bucket：文件表没有行（若选了模板则只有模板骨架），访客没有 README 块，owner 看到添加 README 与上传提示。Issues 和 PRs 页签仍然渲染它们的空列表。

全部 Code 页签只读分区（标题、页签、commit 条、文件表、README、About、安装片段）必须出现在所服务的 HTML 中，从而使无 JavaScript 的只读路径仍然工作。

## 品牌与视觉风格

Logo：产品标识就是 bucket emoji，并把桶身变成红色。交付一份第一方 SVG（`assets/logo.svg`），保持该 emoji 的桶身加提手轮廓，桶身填充 `--rb-bucket`（`#C41E3A`）。提手和桶沿使用 `--rb-bucket-ink`（`#9B1830`）。不要把系统字形 🪣 当作交付 logo：各平台会把它画成金属色或蓝色，而且无法改色。同一份 SVG 同时用作 favicon 和页头标识。字标是 UI 无衬线体里的 `red-bucket`，放在标识右侧，链到首页。

从 pi.dev 对照（全局框和落地页）：

- 白底、近黑字、内容优先、绘制要快。
- 稀疏的站点头：左侧是标识 + 字标；右侧是 Login 或已登录用户名。没有厚营销导航、没有英雄区渐变、没有卡片网格。
- 系统字体栈（`-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`），落地页正文行宽舒服，很少阴影或圆角表演。
- 只读路径保持 HTML；装饰不得挡住内容。

从 GitHub 对照（bucket 详情页控件）：

- 仓库标题 `username / bucket-name`、Public/Private 胶囊、带未关闭计数的下划线页签栏。
- 带最近 commit 条的一层文件表；About 侧栏；文件下方的 README。
- 表面是带 1px `#d0d7de` 边框和约 6px 圆角的白色面板，仓库井后面是浅底 `#f6f8fa`（GitHub 的 canvas 与 subtle 分层）。
- 仓库框内的链接色是 `#0969da`，让文件名和 issue 标题读起来像 GitHub。
- 可见性徽章和 issue 的 open/closed 状态走 GitHub 那种安静的胶囊语言，不是营销芯片。

品牌强调色（我们自己的）：

- `--rb-bucket: #C41E3A` 是唯一响亮的颜色。它涂在 logo 上，也涂在主操作 Install 上（GitHub 的绿色 Code 按钮变成红色 Install）。
- 悬停/激活使用 `--rb-bucket-ink: #9B1830`。
- 不要把 GitHub 绿当作主色，也不要再引入第二种强调色。

实现必须命名并复用的 tokens：

- `--rb-bucket` `#C41E3A`
- `--rb-bucket-ink` `#9B1830`
- `--rb-fg` `#1f2328`
- `--rb-muted` `#656d76`
- `--rb-border` `#d0d7de`
- `--rb-canvas` `#f6f8fa`
- `--rb-surface` `#ffffff`
- `--rb-link` `#0969da`

## 风险 / 权衡

- [功能等价由我们无法控制的 harness 行为来判定] → 在 cross-transfer 文档的实验环境中固定 harness 版本；每一对的等价性 checklist 放在文档中，并在 harness 更新时重跑。
- [对整个 10MB bucket 做翻译拉取可能威胁 1s p95] → 翻译对每个 commit 是确定的，因此按 (commit, target) 缓存翻译后的归档；负载测试的流量混合包含翻译拉取，以便抓住回归。
- [并发协作突发下的 SQLite 写争用] → WAL 模式 + 短事务；记录规模上限；数据层保持可替换为 Postgres。
- [Git worktree 大小 ≠ 用户对 10MB 的直觉（历史会超出工作树）] → 配额按工作树定义（规格）；定期跑 `git gc`，并写明历史开销不向用户计费。
- [pi.dev 风格「照抄」带来复制风险] → 复现稀疏页头、白底和内容优先的字体，不复现 pi.dev 的素材或文案。
- [GitHub 风格仓库页「照抄」带来同样的复制风险] → 复现信息结构、URL 形状、文件表密度和安静边框；不要引入 Primer CSS、octicons 或 GitHub 品牌。主操作是红色 Install，不是绿色 Code。

## 迁移计划

全新部署；没有迁移。回滚 = 重新部署上一份构建；SQLite 文件和 git 存储根都是升级前应备份的向后兼容产物。

## 未决问题

- 域名未定（ADR 留空）——不影响规格；安装脚本必须把基础 URL 做成模板。
- Phase 1 等价性实验要固定哪些 harness 版本（首次运行时记入各 cross-transfer 文档）。
- Token 过期策略、速率限制（429）、CSRF、HTTPS 终止留给部署层；Phase 1 规格只要求 logout 撤销当前枚 token、服务端只存哈希。语言与框架已在 `tech-stack.md` 选定，不再是未决项。
