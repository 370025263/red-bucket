## Purpose

定义轻量 Web 前端：对照 pi.dev 的全局框、对照 GitHub 的 bucket 详情页、red-bucket 自己的文案，以及红色 bucket 标识。浏览公开 buckets，管理自己的 buckets，并展示一键安装脚本。

## ADDED Requirements

### Requirement: Public browsing pages
Web UI MUST 提供可匿名访问的页面，用于：落地页、列出该用户公开 buckets 的用户资料页，以及路径为 `/<username>/<bucket-name>`、并遵循下文所定义的 GitHub 仓库首页分区的 bucket 详情页。

#### Scenario: Bucket page renders anonymously
- **WHEN** 未认证访客打开某个公开 bucket 的页面
- **THEN** 该页渲染 Code 页签分区（标题、页签、文件表、About、安装片段），没有登录提示挡住内容

#### Scenario: Private bucket page hidden
- **WHEN** 未认证访客打开某个私有 bucket 的 URL
- **THEN** UI 展示与不存在的 bucket 相同的未找到页

### Requirement: Authenticated management pages
Web UI MUST 让已登录用户注册、登录、登出、创建 bucket（带模板、可见性和可选 description）、上传或删除单份资产、切换可见性、编辑 description、查看配额用量、删除 buckets，以及管理其公开 buckets 上的 issues、评论和 pull requests——全部只由 `api-catalog.md` 中的 `/api/v1/` 端点支撑。跨桶复制走 copies；页上的可复制脚本走 install-script；不要调用未写入该目录的私有端点。About 与页签计数消费 Bucket JSON 的 `description`、`usage_bytes`、`limit_bytes`、`template`、`harness_mix`、`open_issues_count`、`open_pulls_count`；文件表与 README 消费 tree 与 blob。

#### Scenario: Bucket created through UI
- **WHEN** 已登录用户填完创建 bucket 表单，选择 `agents` 模板和 `public` 可见性
- **THEN** UI 导航到新 bucket 页，展示模板骨架和 public 标识

#### Scenario: UI uses public API only
- **WHEN** 任何 UI 管理动作在记录浏览器网络日志的情况下被执行
- **THEN** 每一次后端调用都指向已文档化的 `/api/v1/` 端点（没有私有端点）

### Requirement: Visual style baseline
Web UI MUST 使用两层视觉系统：对照 pi.dev 的全局框（白底、近黑字、稀疏页头、内容优先、加载快）和对照 GitHub 的仓库页控件（下划线页签、一层文件表、About 侧栏、1px `#d0d7de` 边框、克制圆角、仓库井后的 `#f6f8fa` 底、`#0969da` 链接）。命名和文案必须是 red-bucket 自己的。实现必须复用 `design.md` 中已命名的 tokens（`--rb-bucket`、`--rb-bucket-ink`、`--rb-fg`、`--rb-muted`、`--rb-border`、`--rb-canvas`、`--rb-surface`、`--rb-link`）。页面在只读浏览路径上必须在没有客户端 JavaScript 时仍可使用。UI 不得引入 pi.dev 素材、GitHub Primer CSS、octicons 或 GitHub 品牌。

#### Scenario: Read path works without JavaScript
- **WHEN** 某个公开 bucket 页在禁用 JavaScript 的情况下被加载
- **THEN** 标题、页签栏、文件表、About 字段和安装脚本文本在所服务的 HTML 中仍然可见

#### Scenario: Repo well uses GitHub-like chrome
- **WHEN** 访客打开某个公开 bucket 详情页
- **THEN** 仓库井坐在 canvas 色上，文件表和 About 是带边框的表面，页签栏带下划线，并且 Install 控件使用品牌红（不是 GitHub 绿）

### Requirement: Red bucket mark
产品标识 MUST 是 bucket emoji（U+1FAA3）的第一方 SVG，桶身填充品牌红（`#C41E3A`），提手和桶沿为 `#9B1830`。权威源文件是本次变更里的 `assets/logo.svg`；实现时 MUST 把同一份资源复制进服务的静态文件，归档本变更后仍以服务内那份为准，不得继续依赖 openspec 路径。系统 emoji 不得当作交付 logo。该标识必须出现在站点头里、`red-bucket` 字标旁边（链到首页），并且必须是 favicon。

#### Scenario: Header shows red bucket mark
- **WHEN** 访客打开落地页或某个公开 bucket 页
- **THEN** 站点头包含 red-bucket SVG 标识和 `red-bucket` 字标，并且文档 favicon 是同一标识

### Requirement: GitHub-like bucket header and tabs
Bucket 详情页 MUST 使用 GitHub 仓库式标题 `username / bucket-name` 加上 Public 或 Private 标识，以及带有 Code（默认）、Issues、Pull requests 和 Settings 的仓库导航页签栏。Issues 和 Pull requests 页签必须显示未关闭条目的数量。Settings 页签必须只为 bucket owner 渲染；其他查看者不得看到该页签，并且非 owner 请求 `/<username>/<bucket-name>/settings` 必须得到与缺失 bucket 相同的未找到页。Phase 1 不得渲染 Star、Watch、Fork，或额外的 GitHub 页签（Actions、Projects、Wiki、Security、Insights、Discussions）。

#### Scenario: Public header and tabs
- **WHEN** 未认证访客打开一个有 2 个未关闭 issues 和 1 个未关闭 pull request 的公开 bucket
- **THEN** 页面标题是 `username / bucket-name`，Public 标识可见，页签栏包含 Code、Issues (2) 和 Pull requests (1)，并且不包含 Settings、Star、Watch 或 Fork

#### Scenario: Owner sees Settings
- **WHEN** bucket owner 打开同一个公开 bucket
- **THEN** 页签栏还包含 Settings，并且打开 `/<username>/<bucket-name>/settings` 会显示可见性、description、配额和删除控件

### Requirement: Code tab file browser
Code 页签 MUST 把当前工作树（HEAD）呈现为一层目录浏览器，而不是扁平的类型倾倒，根目录在 `/<username>/<bucket-name>`，目录在 `/<username>/<bucket-name>/tree/<path>`。每一文件行必须显示 name、last commit message 和 last-updated time；当该行是一份已存资产时，还必须显示资产类型和源 harness。最近 commit 条必须显示当前树的最新 commit message、author、短 hash（链到 `/commit/<sha>`）、时间戳，以及 commit 计数（链到 `/commits`）。点击目录必须导航到其 `tree` URL；点击文件必须导航到 `/<username>/<bucket-name>/blob/<path>`。GitHub 的 clone/Code 按钮由 Install 控件替代：目标 harness 选择器外加可复制的安装脚本。Owner 必须在此页签上拥有上传入口。Phase 1 没有分支选择器。

#### Scenario: Directory listing with commit bar
- **WHEN** 访客打开一个根目录含有 `skills/` 目录和 `README.md` 文件、并且至少有一次 commit 的公开 bucket
- **THEN** Code 页签显示最近 commit 条，以及含有那两行的文件表（目录在前，文件在后），每个文件行包含 last commit message 和 last-updated time

#### Scenario: Nested path and blob
- **WHEN** 访客打开 `/<username>/<bucket-name>/tree/skills`，然后打开其下的一个文件
- **THEN** 文件表只列出该目录的子项，并且该文件在 `/<username>/<bucket-name>/blob/skills/<filename>` 打开

### Requirement: About sidebar and README
Code 页签 MUST 包含右侧 About 侧栏（GitHub About 的对照物），展示：可选 description（纯文本，最多 350 个字符）、可见性、当前存储用量和 10MB 上限、若该 bucket 从模板创建则带模板风格、按源 harness 统计的已存资产数量，以及当前目录存在 `README.md` 时指向它的链接。当当前目录存在 `README.md`（名称大小写不敏感）时，页面必须把它作为 HTML 渲染在文件表下方。当它不存在时，访客必须看不到 README 块；owner 必须看到添加提示。Phase 1 的 About 不得包含 website、topics、stars、releases、packages 或贡献者图。

#### Scenario: README rendered and About populated
- **WHEN** 一个公开 bucket 在根目录有 `README.md`、有非空 description，并存有来自 harness `claude` 的资产
- **THEN** Code 页签在文件表下方渲染该 README，并且 About 显示 description、可见性、用量、10MB 上限，以及包含 `claude` 的 harness mix

#### Scenario: Empty bucket owner prompt
- **WHEN** owner 打开一个新创建的空公开 bucket
- **THEN** 文件表没有内容行，访客会看不到 README 块，并且 owner 看到添加 README 与上传的提示

### Requirement: Issues and pull-request tabs
Issues 和 Pull requests 页签 MUST 在 `/<username>/<bucket-name>/issues` 和 `/<username>/<bucket-name>/pulls` 列出该 bucket 的 issues 和 pull requests，每一行显示编号、标题、open 或 closed 状态、作者和创建时间，并且必须链到 `/issues/<n>` 和 `/pulls/<n>` 详情页。已认证用户必须能从 Issues 页签在公开 bucket 上开 issue。角色规则仍是 `community/collaboration` 中的那些。

#### Scenario: Issues tab lists open items
- **WHEN** 访客打开一个有一条标题为 `broken skill` 的未关闭 issue 的公开 bucket 的 Issues 页签
- **THEN** 列表显示该 issue 及其编号、标题、open 状态、作者和创建时间，并且标题链到 `/<username>/<bucket-name>/issues/<n>`
