> 本文是同目录 `spec.md` 的逐句中文译本。标识符、路径、状态码、错误码保持原文。

## Purpose

formatter 是 red-bucket 的核心价值：在拉取时，它把以某一种 harness 格式存储的资产转换成请求方 harness 的格式，保持功能行为，并且每一对的规则都有文档、都经实验验证。

## ADDED Requirements

### Requirement: Fetch-time translation
系统必须提供一个拉取端点，接受目标 harness（`codex`、`claude`、`agents`、`openclaw`），并把所请求的资产（或整个 bucket）从其源 harness 格式转换成目标 harness 格式后返回，包括目标侧合适的文件名、目录布局和元数据 schema。当目标等于源 harness 时拉取，必须返回与 raw 下载逐字节一致的内容。

#### Scenario: Claude skill fetched as codex
- **WHEN** 客户端拉取一份源 harness 为 `claude` 的 skill，并指定目标 harness 为 `codex`
- **THEN** 响应包含按 codex 约定重新布局的 skill，name、description、instructions 以及被引用的辅助文件得以保留，定义见 `cross-transfer/claude-2-codex.md`

#### Scenario: Identity translation is byte-identical
- **WHEN** 客户端拉取一份资产，并指定目标 harness 等于该资产的源 harness
- **THEN** 返回的内容与该资产的 raw 下载逐字节一致

#### Scenario: Whole-bucket fetch
- **WHEN** 客户端按某个目标 harness 拉取整个 bucket
- **THEN** 响应是一份归档，其中每一个可翻译资产都已转换，并按目标 harness 期望的目录位置排布，可直接解包进用户的本地 harness 配置

### Requirement: Supported translation pairs declared
系统必须暴露一个能力矩阵端点，按资产类型声明哪些源到目标 harness 对受支持。对不受支持的对的请求必须以 HTTP 501 和错误码 `translation_unsupported` 失败，绝不能静默返回未翻译内容。Phase 1 必须至少支持：`skill` 和 `instructions` 在全部四种 harness 风格之间，以及 `mcp` 在 `claude` 与 `codex` 之间。

#### Scenario: Capability matrix served
- **WHEN** 客户端请求翻译能力矩阵
- **THEN** 响应枚举受支持的（资产类型, source, target）三元组，并与已发布的 cross-transfer 文档一致

#### Scenario: Unsupported pair rejected explicitly
- **WHEN** 客户端请求矩阵中不存在的翻译对
- **THEN** 系统响应 HTTP 501，带上 `translation_unsupported`，并且不返回未翻译的源内容

### Requirement: Functional equivalence of translated assets
翻译必须保持资产的功能行为：翻译之后，安装进目标 harness 的资产必须在等价条件下触发，并产生与源资产在源 harness 中等价的效果。在目标侧没有等价物的信息必须保存在输出内指定的兼容性说明中，而不是被静默丢掉。

#### Scenario: Migrated skill behaves equivalently
- **WHEN** 一份基准 skill 被安装进其源 harness，其译本被安装进目标 harness，并且两者都用同一任务 prompt 行使
- **THEN** 两个 harness 都识别并调用该 skill，可观察结果按对应 cross-transfer 文档中的等价性 checklist 匹配

#### Scenario: Untranslatable fields preserved as notes
- **WHEN** 一份源资产含有在目标 harness 中没有等价物的字段
- **THEN** 翻译输出把该字段放在 compatibility-notes 一节中，并且拉取响应用 `lossy: true` 标记该资产

### Requirement: Translation rule documents
每一对受支持的源到目标都必须记录在 `cross-transfer/<src>-2-<dst>.md` 中，覆盖：两种 harness 对 skill、plugin、mcp 和 subagent 内容的格式；逐字段映射；迁移期间面向用户的操作；以及用户会观察到的行为变化。每一份文档必须在该对被标为能力矩阵中的 supported 之前，由一次有记录的实验验证。

#### Scenario: Doc exists for every supported pair
- **WHEN** 能力矩阵把某个（type, src, dst）三元组报告为 supported
- **THEN** `cross-transfer/<src>-2-<dst>.md` 存在，并包含覆盖该资产类型的映射表，以及指向其实验记录的链接

#### Scenario: Undocumented pair not exposed
- **WHEN** 某一翻译对没有经过验证的 cross-transfer 文档
- **THEN** 能力矩阵把它报告为 unsupported

### Requirement: Deterministic translation
翻译必须是确定的：同一源内容和同一目标 harness 必须始终产出相同的输出字节，从而使拉取可缓存、可 diff。

#### Scenario: Repeated fetch identical
- **WHEN** 同一 commit 上的同一资产为同一目标 harness 被拉取两次
- **THEN** 两次响应逐字节一致
