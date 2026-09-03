# red-bucket 模型分工

主 agent 自己不写前端、不写用户文档、不给自己验收。该派 subagent 就派，并写明模型。用户口头名与本环境 slug 对照如下；发 Task 时用 slug。

本项目允许 kimik3。前端相关 Task 必须带 `model` 为 `kimi-k3-high`（用户口头 kimik3；不要用光秃的 `kimi-k3`，当前 Task 不认）。不要改派成 grok、claude、gemini。

- kimik3：`kimi-k3-high`（允许，前端必用）
- Gemini 3.7（文档）：`gemini-3.7-flash-high`
- grok 4.6 fast：`cursor-grok-4.6-xhigh-fast`（对应用户口中的 grok 4.6 fast）

## 前端

落地页、模板、CSS、站点头、视觉对照（含按 pi.dev 或其它参考页改 UI）、浏览器里能看见的改动，一律另开 subagent，模型用 kimik3。主 agent 只给冻结事实、参考 URL、设计与验收条款，自己不改 `src/redbucket/web/`。

## 文档

README、CONTRIBUTING、用户可见 Markdown、`skills/red-bucket/SKILL.md`、GitHub 仓库介绍，先交给 Gemini 3.7 起草或改写，主 agent 核对事实后落盘。不要自己直接写或大改这类文档。

OpenSpec 的 Requirement 与 Scenario、DDL、API 目录、代码注释不走这条。

给 Gemini 的材料必须带上已冻结事实：产品名 red-bucket、`user/bucket`、三种名字（copy、install-script、translated fetch）、API 在 `/api/v1/`、开源地址 `https://github.com/370025263/red-bucket`、官方 origin `https://redbucket.store`。禁止让它发明新术语或新端点。

## 有清晰设计与验收要求时

设计、契约、验收条款已经写清时，实现用 grok 4.6 fast。做完后必须再另开一个 subagent，对照那份设计与验收条款看结果，由验收 agent 判定通过还是打回。实现用的那个 grok 不能自己验收自己。

前端实现未点名时仍走 kimik3，不改走 grok。用户点名用 Gemini 3.7 做前端实现时，走全局 `frontend-implement`（`~/.cursor/agents/frontend-implement.md`），模型 `gemini-3.7-flash-high`。前端验收另开 `frontend-acceptance`（全局 `~/.cursor/agents/frontend-acceptance.md`）。实现 agent 不得自己验收自己。

## 验收时对照什么

验收 subagent 要带着：书面设计或 OpenSpec、验收条款或 test-plan 条目、改动范围、如何在本机或 `https://redbucket.store` 复核。只报对照结果，不要顺手改实现。
