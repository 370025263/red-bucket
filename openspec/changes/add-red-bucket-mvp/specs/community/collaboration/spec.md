## Purpose

定义公开 buckets 上类似 GitHub 的协作——issues、一等评论、pull requests——以及把另一用户可读 bucket 中的资产复制进自己 bucket 的能力（`copies`，不是安装脚本文本）。

## ADDED Requirements

### Requirement: Issues on public buckets
系统 MUST 让任何已认证用户在公开 bucket 上开 issue（标题 + markdown 正文），并让 issue 作者和 bucket owner 关闭它。Issues 在公开 buckets 上必须可被匿名读取。私有 buckets 不得接受非 owner 的 issues（404）；owner 可以在自己的私有桶上开 issue。编号按该 bucket 从 1 递增，与 PR 序号独立。Phase 1 只接受关闭，不提供 reopen。

#### Scenario: Issue opened on public bucket
- **WHEN** 一名已认证的非 owner 在公开 bucket 上开 issue
- **THEN** 系统以 HTTP 201 返回一个按该 bucket 范围递增的 issue 编号，带 `Location`，并且该 issue 出现在匿名读者可见的 bucket issue 列表中

#### Scenario: Issue on private bucket rejected
- **WHEN** 非 owner 尝试在私有 bucket 上开 issue
- **THEN** 系统响应 HTTP 404

#### Scenario: Only author or owner closes
- **WHEN** 第三名用户（既不是作者也不是 bucket owner）尝试关闭一个 issue
- **THEN** 系统响应 HTTP 403，错误码为 `forbidden`，并且该 issue 保持打开

### Requirement: Issue comments as first-class resources
系统 MUST 把评论作为挂在 issue 下的一等资源：`GET` 与 `POST .../issues/{number}/comments`，以及按 `comment_id` 读取。公开桶上匿名可读。仅 issue 作者与 bucket owner 可发评论；第三人 MUST 得到 HTTP 403、`forbidden`。Phase 1 不提供编辑或删除评论。

#### Scenario: Author comments on own issue
- **WHEN** issue 作者在公开 bucket 的该 issue 下提交一条非空 markdown 评论
- **THEN** 系统以 HTTP 201 返回 IssueComment，带 `Location`，并且匿名读者能列出该评论

#### Scenario: Third party cannot comment
- **WHEN** 既不是作者也不是 bucket owner 的第三名用户尝试评论
- **THEN** 系统响应 HTTP 403，并且没有评论被创建

### Requirement: Pull requests on public buckets
系统 MUST 让已认证用户以 pull request 的形式对公开 bucket 提出变更，其中包含标题、描述和一份提议的文件树替换列表 `files`（每一项为 `path` 加 `content_text` 或 `content_base64`，可选 `delete`），不是 git patch。`files` 在 merge 前存在 SQLite。Bucket owner 必须能够审阅（GET 详情与 `GET .../files`）、merge 或拒绝。Merge 必须把该变更作为归属于 PR 作者的一次 git commit 应用到当时 HEAD（未出现在 `files` 里的路径保持不动），并且必须在应用前重新跑资产格式校验和配额检查。私有桶对非 owner 全部 404；owner 向自己的私有桶开 PR 允许。

#### Scenario: PR lifecycle
- **WHEN** 非 owner 向公开 bucket 提交带 `files` 的 PR，并且 owner merge 它
- **THEN** bucket 内容反映所提议的路径级替换，bucket 历史显示一次归属于 PR 作者的 commit，并且 PR 状态变为 `merged`

#### Scenario: Merge blocked by validation
- **WHEN** owner merge 一份所提议内容未通过资产格式校验、或会超出 10MB 配额的 PR
- **THEN** merge 被拒绝，HTTP 422（校验）或 413（配额），PR 保持打开，并且 bucket 不变

#### Scenario: Rejected PR leaves bucket untouched
- **WHEN** owner 拒绝一份 PR
- **THEN** PR 状态变为 `rejected`，并且 bucket 内容不变

### Requirement: Cross-bucket copy
系统 MUST 让已认证用户把任何自己可读的资产（公开桶，或自己的私有桶）复制进自己拥有的目标 bucket，端点为 `POST .../copies`。副本必须记录 provenance（源 full_name、源路径、源 commit、复制时间、`dest_path` 与 `dest_type` 快照），必须通过与上传相同的校验流水线和目标 bucket 的原子配额检查，并留下一次归属于当前用户的 git commit。从他人私有桶或已软删源桶复制 MUST 返回 HTTP 404。JSON 类型名为 InstallRecord，只描述本行出处，不得再用 `POST .../install`。

#### Scenario: Successful copy
- **WHEN** 用户把另一用户公开 bucket 中的一份 skill 复制进自己的 bucket
- **THEN** 该资产出现在目标 bucket 中，带有引用源 bucket 和 commit 的 provenance 元数据，并被记录为一次 git commit

#### Scenario: Copy blocked by quota
- **WHEN** 一次 copy 会把目标 bucket 推过 10MB
- **THEN** 系统响应 HTTP 413，并且目标 bucket 不变

#### Scenario: Copy from private bucket denied
- **WHEN** 用户尝试从自己不拥有的私有 bucket 复制一份资产
- **THEN** 系统响应 HTTP 404
