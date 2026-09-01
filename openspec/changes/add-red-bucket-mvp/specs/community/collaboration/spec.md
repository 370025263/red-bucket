## Purpose

定义公开 buckets 上类似 GitHub 的协作——issues 和 pull requests——以及把另一用户公开 bucket 中的资产安装进自己 bucket 的能力。

## ADDED Requirements

### Requirement: Issues on public buckets
系统MUST让任何已认证用户在公开 bucket 上开 issue（标题 + markdown 正文），并让 issue 作者和 bucket owner 评论并关闭它。Issues 在公开 buckets 上必须可被匿名读取。私有 buckets 不得接受非 owner 的 issues。

#### Scenario: Issue opened on public bucket
- **WHEN** 一名已认证的非 owner 在公开 bucket 上开 issue
- **THEN** 系统以 HTTP 201 返回一个按该 bucket 范围递增的 issue 编号，并且该 issue 出现在匿名读者可见的 bucket issue 列表中

#### Scenario: Issue on private bucket rejected
- **WHEN** 非 owner 尝试在私有 bucket 上开 issue
- **THEN** 系统响应 HTTP 404

#### Scenario: Only author or owner closes
- **WHEN** 第三名用户（既不是作者也不是 bucket owner）尝试关闭一个 issue
- **THEN** 系统响应 HTTP 403，并且该 issue 保持打开

### Requirement: Pull requests on public buckets
系统MUST让已认证用户以 pull request 的形式对公开 bucket 提出变更，其中包含标题、描述和一份提议的内容 diff。Bucket owner 必须能够审阅、merge 或拒绝。Merge 必须把该变更作为归属于 PR 作者的一次 git commit 应用到 bucket，并且必须在应用前重新跑资产格式校验和配额检查。

#### Scenario: PR lifecycle
- **WHEN** 非 owner 向公开 bucket 提交 PR，并且 owner merge 它
- **THEN** bucket 内容反映所提议的变更，bucket 历史显示一次归属于 PR 作者的 commit，并且 PR 状态变为 `merged`

#### Scenario: Merge blocked by validation
- **WHEN** owner merge 一份所提议内容未通过资产格式校验、或会超出 10MB 配额的 PR
- **THEN** merge 被拒绝，HTTP 422（校验）或 413（配额），PR 保持打开，并且 bucket 不变

#### Scenario: Rejected PR leaves bucket untouched
- **WHEN** owner 拒绝一份 PR
- **THEN** PR 状态变为 `rejected`，并且 bucket 内容不变

### Requirement: Cross-bucket install
系统MUST让已认证用户把任何公开 bucket 中的资产安装（复制）进自己拥有的 bucket。安装后的副本必须记录 provenance（源 bucket、源 commit、安装时间），并且必须通过目标 bucket 的配额检查。

#### Scenario: Successful install
- **WHEN** 用户把另一用户公开 bucket 中的一份 skill 安装进自己的 bucket
- **THEN** 该资产出现在目标 bucket 中，带有引用源 bucket 和 commit 的 provenance 元数据，并被记录为一次 git commit

#### Scenario: Install blocked by quota
- **WHEN** 一次 install 会把目标 bucket 推过 10MB
- **THEN** 系统响应 HTTP 413，并且目标 bucket 不变

#### Scenario: Install from private bucket denied
- **WHEN** 用户尝试从自己不拥有的私有 bucket 安装一份资产
- **THEN** 系统响应 HTTP 404
