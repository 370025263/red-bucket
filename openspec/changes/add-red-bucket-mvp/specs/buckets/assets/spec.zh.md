> 本文是同目录 `spec.md` 的逐句中文译本。标识符、路径、状态码、错误码保持原文。

## Purpose

定义资产（skills、MCP 工具配置、CLAUDE.md/AGENTS.md 指令文件、subagents、plugins）如何带着按类型的格式校验上传进 bucket，以及如何按所存储的形态被列出和下载。

## ADDED Requirements

### Requirement: Supported asset types
系统必须在 Phase 1 支持这些资产类型：`skill`、`mcp`（MCP 工具/服务配置）、`instructions`（CLAUDE.md / AGENTS.md 类文件）、`subagent`、`plugin`。每一份已存储资产必须携带：资产类型、源 harness（`codex`、`claude`、`agents`、`openclaw`）、在 bucket 内的路径，以及上传元数据（上传者、时间戳、大小）。

#### Scenario: Asset metadata returned on listing
- **WHEN** 客户端列出某个 bucket 的资产
- **THEN** 每一项都包含 type、source harness、path、size，以及 last-modified time

### Requirement: Format validation on upload
系统必须在接受之前按所声明类型的格式规则校验每一份上传资产，并且必须以 HTTP 422 和一份机器可读的违规列表拒绝无效上传。Phase 1 的最低规则：一份 `skill` 必须包含带有可解析 frontmatter/name 和 description 的 SKILL.md（或 harness 等价物）；一份 `mcp` 资产必须按其所在 harness 约定是可解析的 JSON/TOML，并至少声明 server name 和 transport；一份 `instructions` 资产必须是大小限制内的合法 UTF-8 markdown；`subagent` 和 `plugin` 必须满足其所声明源 harness 的结构规则。

#### Scenario: Valid skill accepted
- **WHEN** 用户上传一个含有格式良好、带 name 和 description 的 SKILL.md 的 skill 目录，并声明源 harness 为 `claude`
- **THEN** 系统以 HTTP 201 接受它，并且该资产出现在 bucket 列表中

#### Scenario: Malformed skill rejected
- **WHEN** 用户上传一份 SKILL.md 缺少 name 或 frontmatter 不可解析的 skill
- **THEN** 系统响应 HTTP 422，列出每一条带规则标识符和文件路径的违规，并且没有任何内容写入该 bucket

#### Scenario: Malformed MCP config rejected
- **WHEN** 用户上传一份配置在语法上不是合法 JSON 的 `mcp` 资产
- **THEN** 系统响应 HTTP 422，并指出解析错误位置

#### Scenario: Undeclared type rejected
- **WHEN** 一次上传省略了资产类型，或声明了不受支持的类型
- **THEN** 系统响应 HTTP 422，并且不存储任何内容

### Requirement: Upload commits to bucket history
系统必须把每一次被接受的上传（创建或更新）记录为该 bucket 仓库中的一次 git commit，并把该 commit 归属于上传用户，从而使 bucket 历史可检查、可恢复。

#### Scenario: Upload creates a commit
- **WHEN** 用户上传一份新资产，然后再次上传修改后的版本
- **THEN** 该 bucket 的历史端点显示两次归属于该用户的 commit，且顺序正确

### Requirement: Per-bucket storage quota
系统必须把每个 bucket 的内容限制为 10MB（已存资产的工作树大小）。会超出该上限的上传必须以 HTTP 413 和错误码 `bucket_storage_exceeded` 拒绝，并报告当前用量与上限；该 bucket 必须保持不变。

#### Scenario: Oversize upload rejected atomically
- **WHEN** 一个 bucket 已有 9.5MB，用户上传一份 1MB 资产
- **THEN** 系统响应 HTTP 413，带上当前用量与上限，并且该 bucket 仍恰好包含其先前内容

#### Scenario: Usage visible to owner
- **WHEN** owner 请求 bucket 元数据
- **THEN** 响应包含以字节计的当前存储用量以及 10MB 上限

### Requirement: Raw asset download
系统必须让经授权的客户端通过 raw 端点按所存储原样下载任何资产（不做翻译），保持字节与目录结构（单文件直接下载；多文件资产作为归档）。

#### Scenario: Raw download is byte-identical
- **WHEN** 客户端上传一份资产并立即通过 raw 端点下载它
- **THEN** 下载到的内容与上传逐字节一致
