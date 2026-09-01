## Purpose

定义存储契约：每一个 bucket 都是服务器文件系统上的一个 git 仓库（不用对象存储），按 user id 做命名空间与隔离，带有配额记账和可检查的历史。文件字节与 commit 对象只在 git 里；可查询元数据在 SQLite（见 `platform/metadata-store`）。

## ADDED Requirements

### Requirement: Git repository per bucket
系统 MUST 把每个 bucket 存为文件系统上的独立 git 仓库，布局在按不可变 user id（不是 username）键控的每用户目录下，例如 `<storage-root>/<user-id>/<bucket-id>.git`。全部内容变更（upload、单资产删除、PR merge、copy、带 template 的创建）必须经过 git commits；任何 bucket 内容都不得存在于 git 历史之外。不改工作树的元数据（可见性、description、改用户名、issue、评论、开或拒 PR）不得写 git。不建 commits 业务表；历史从 git 对象现读。commit 作者邮箱约定为 `user-{id}@users.red-bucket.invalid`，author name 为当时的 username。

#### Scenario: Every mutation is a commit
- **WHEN** 任何一串内容变更被应用到某个 bucket
- **THEN** 该 bucket 仓库的 `git log` 对每次变更显示一次带作者归属的 commit，并且工作树等于 API 所服务的状态

#### Scenario: Rename-safe storage
- **WHEN** 用户更改其 username
- **THEN** 既有 buckets 保持完整，并在新 username 下可寻址，而无需在磁盘上移动仓库

### Requirement: Per-user isolation
系统 MUST 隔离各用户的存储，使任何 API 操作都不能读或写另一用户的目录，除非经过已文档化的公开 bucket 读取和协作路径。路径输入（bucket 名称、资产路径）必须被清洗，使 `..`、绝对路径、符号链接或 git 内部路径（`.git/`）不能逃出该 bucket 工作树。

#### Scenario: Path traversal blocked
- **WHEN** 一次上传声明的资产路径含有 `../`、前导 `/`，或 `.git/` 前缀
- **THEN** 系统响应 HTTP 422，并且没有任何文件在该 bucket 工作树之外被创建或读取

#### Scenario: Symlink escape blocked
- **WHEN** 一份上传的归档含有指向该 bucket 工作树之外的符号链接
- **THEN** 系统拒绝该上传或剥离该符号链接，并且任何树外路径都不会被解析

### Requirement: Quota accounting
系统 MUST 跟踪每个 bucket 的工作树大小，并在提交任何变更之前强制执行 10MB 上限。记账必须基于该变更将会生效后的大小（每桶一把锁，原子的先检查再提交），并且报告的用量必须与实际工作树相差在 1% 以内。成功 commit 后把实测工作树字节写入 `buckets.storage_usage_bytes`。

#### Scenario: Concurrent uploads cannot overshoot
- **WHEN** 对同一 bucket 的两次并发上传各自都能装下，但合在一起会超过 10MB
- **THEN** 至多一次被提交，另一次以 HTTP 413 被拒绝；最终工作树在上限之下

### Requirement: History inspectability
系统 MUST 通过 API 暴露 bucket 历史（带作者、时间戳、说明、变更路径的 commit 列表），并支持按某个历史 commit 拉取资产。实现从 git 现读，不把 commit 行镜像进 SQLite。

#### Scenario: Fetch at historical commit
- **WHEN** 客户端按 bucket 历史中的某个 commit hash 请求一份资产
- **THEN** 响应匹配该资产在该 commit 时的内容
