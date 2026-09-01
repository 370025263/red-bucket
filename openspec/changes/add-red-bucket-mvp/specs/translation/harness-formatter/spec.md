## Purpose

formatter 是 red-bucket 的核心价值：在拉取时，它把以某一种 harness 格式存储的资产转换成请求方 harness 的格式，保持功能行为，并且每一对的规则都有文档、都经实验验证。Phase 1 对 plugin 与 subagent 必须翻译，与 skill 同等，不能只存不转。

## ADDED Requirements

### Requirement: Fetch-time translation
系统 MUST 提供拉取端点，接受目标 harness（`codex`、`claude`、`agents`、`openclaw`），并把所请求的资产（或整个 bucket）从其源 harness 格式转换成目标 harness 格式后返回，包括目标侧合适的文件名、目录布局和元数据 schema。当目标等于源 harness 时拉取，必须返回与 raw 下载逐字节一致的内容。单资产不支持的对必须以 HTTP 501 和错误码 `translation_unsupported` 失败，绝不能返回未翻译正文。整桶默认能译则译，跳过的资产写入 notes，不得把未翻译原文冒充目标格式；调用方传 `strict=1` 且存在不支持对时整桶也以 501 失败。

#### Scenario: Claude skill fetched as codex
- **WHEN** 客户端拉取一份源 harness 为 `claude` 的 skill，并指定目标 harness 为 `codex`
- **THEN** 响应包含按 codex 约定重新布局的 skill，name、description、instructions 以及被引用的辅助文件得以保留，定义见 `cross-transfer/claude-2-codex.md`

#### Scenario: Identity translation is byte-identical
- **WHEN** 客户端拉取一份资产，并指定目标 harness 等于该资产的源 harness
- **THEN** 返回的内容与该资产的 raw 下载逐字节一致

#### Scenario: Whole-bucket fetch
- **WHEN** 客户端按某个目标 harness 拉取整个 bucket，且桶内资产对该目标均可翻译
- **THEN** 响应是一份归档，其中每一个可翻译资产都已转换，并按目标 harness 期望的目录位置排布，可直接解包进用户的本地 harness 配置

#### Scenario: Whole-bucket skips unsupported assets
- **WHEN** 客户端按某个目标 harness 拉取整个 bucket，桶内有一份 mcp 的源 harness 对该目标不在矩阵中，并且请求未带 `strict=1`
- **THEN** 响应仍是 HTTP 200 归档，该 mcp 不被以源格式写入目标布局，并且归档内 notes 列出被跳过的资产

#### Scenario: Whole-bucket strict fails
- **WHEN** 同一请求带上 `strict=1`
- **THEN** 系统响应 HTTP 501，错误码为 `translation_unsupported`，并且不返回一份假装完整的目标归档

### Requirement: Supported translation pairs declared
系统 MUST 暴露一个能力矩阵端点，按资产类型声明哪些源到目标 harness 对受支持。对不受支持的对的单资产请求必须以 HTTP 501 和错误码 `translation_unsupported` 失败，绝不能静默返回未翻译内容。Phase 1 矩阵 MUST 包含（identity 另计）：`skill`、`instructions`、`plugin`、`subagent` 在 `{codex, agents, claude, openclaw}` 上各 12 个有序异对加 4 个恒等；`mcp` 仅 `claude→codex`、`codex→claude`，外加任意已存 mcp 在源等于目标时的恒等。

#### Scenario: Capability matrix served
- **WHEN** 客户端请求翻译能力矩阵
- **THEN** 响应枚举受支持的（资产类型, source, target）三元组，并与已发布的 cross-transfer 文档一致，且含 plugin 与 subagent 的 12 个异对

#### Scenario: Unsupported pair rejected explicitly
- **WHEN** 客户端对单份资产请求矩阵中不存在的翻译对（例如 mcp 从 agents 到 claude）
- **THEN** 系统响应 HTTP 501，带上 `translation_unsupported`，并且不返回未翻译的源内容

### Requirement: Functional equivalence of translated assets
翻译 MUST 保持资产的功能行为：翻译之后，安装进目标 harness 的资产必须在等价条件下触发，并产生与源资产在源 harness 中等价的效果。在目标侧没有等价物的信息必须保存在输出内指定的兼容性说明中，而不是被静默丢掉。

#### Scenario: Migrated skill behaves equivalently
- **WHEN** 一份基准 skill 被安装进其源 harness，其译本被安装进目标 harness，并且两者都用同一任务 prompt 行使
- **THEN** 两个 harness 都识别并调用该 skill，可观察结果按对应 cross-transfer 文档中的等价性 checklist 匹配

#### Scenario: Untranslatable fields preserved as notes
- **WHEN** 一份源资产含有在目标 harness 中没有等价物的字段
- **THEN** 翻译输出把该字段放在 compatibility-notes 一节中，并且拉取响应用 `lossy: true` 标记该资产

### Requirement: Translation rule documents
每一对受支持的源到目标都 MUST 记录在 `cross-transfer/<src>-2-<dst>.md` 中，覆盖：两种 harness 对 skill、plugin、mcp、subagent 和 instructions 内容的格式；逐字段映射；迁移期间面向用户的操作；以及用户会观察到的行为变化。每一份文档必须在该对被标为能力矩阵中的 supported 之前，由一次有记录的实验验证。恒等对（source 等于 target）不要求独立文档，拉取走 raw 字节。

#### Scenario: Doc exists for every supported pair
- **WHEN** 能力矩阵把某个非恒等的（type, src, dst）三元组报告为 supported
- **THEN** `cross-transfer/<src>-2-<dst>.md` 存在，并包含覆盖该资产类型的映射表，以及指向其实验记录的链接

#### Scenario: Undocumented pair not exposed
- **WHEN** 某一翻译对没有经过验证的 cross-transfer 文档
- **THEN** 能力矩阵把它报告为 unsupported，或不列出该行

### Requirement: Deterministic translation
翻译 MUST 是确定的：同一源内容和同一目标 harness 必须始终产出相同的输出字节，从而使拉取可缓存、可 diff。缓存键为 `(commit, target)`。

#### Scenario: Repeated fetch identical
- **WHEN** 同一 commit 上的同一资产为同一目标 harness 被拉取两次
- **THEN** 两次响应逐字节一致
