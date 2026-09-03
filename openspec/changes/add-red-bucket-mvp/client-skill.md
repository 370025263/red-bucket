# 客户端 skill 仓库设计

本文描述用户侧入口：一个可被 `npx skills` 安装的 red-bucket skill，以及通过本服务一句话把 bucket 资产落到本机的路径。实现业务代码之前只落设计和骨架。权威用户时序仍是 `user-flows.md`。HTTP 仍是 `api-catalog.md`。

## 结论

用户侧有两条安装，不要混成一个动词。

1. 把 red-bucket skill 装进 agent（Cursor、Claude Code、Codex 等）：走公开 GitHub 上的 skill 目录，用 `npx skills add`。
2. 把某个公开 bucket 的资产按目标 harness 落到本机：走服务端 `GET .../install-script`，一句话执行脚本。脚本内部再打 `GET .../translated`。

Phase 1 不把官方 skill 做成独立二进制，也不为它另开 API。skill 只教 agent 怎么调已有的 `/api/v1/`。

## 仓库形态（fancy GitHub）

对外只维护一个开源仓库：`https://github.com/370025263/red-bucket`（MIT，已公开）。

仓库同时是：

- 服务端源码（`src/redbucket/`，本期先有 lint 骨架）
- skill 发现根：`skills/red-bucket/SKILL.md`，满足 vercel-labs/skills 的发现约定（目录内有带 `name` 与 `description` 的 SKILL.md）
- skill 自带客户端：`skills/red-bucket/scripts/rb.mjs`，只依赖 Node 18+ 内建模块（无 `sh`/`curl`/`unzip`/`jq`/npm 包），提供 `login`/`logout`/`status`/`install`/`create`/`upload`；凭据落盘与 origin 归一化以它为准实现；发布侧（建桶、上传资产）也走它，agent 不手拼 `POST .../assets` 的请求体
- 规划与契约（`openspec/`、`sdd/adr/`）

这样做的原因：addyosmani/agent-skills 一类仓库就是「一个 GitHub 首页 + `npx skills add owner/repo`」。再拆 `red-bucket-skill` 兄弟仓可以以后再说；本期不建第二个远程，避免文档和 skill 正文分叉。

GitHub 首页要有：红桶 logo、一句话安装、`npx skills` 命令、install-script 命令、指向 `user-flows.md` 的用户路径、MIT 徽章、lint 徽章。README 正文由 Gemini Flash 写。

## npx skills

发现约定：本仓库根下 `skills/red-bucket/SKILL.md`。

用户侧命令（skill 仍从 GitHub 仓库发现）：

```bash
npx skills add 370025263/red-bucket --skill red-bucket -g -y
```

列出而不安装：

```bash
npx skills add 370025263/red-bucket --list
```

装进当前项目而不是用户全局：

```bash
npx skills add 370025263/red-bucket --skill red-bucket
```

skill 的 `name` 必须是 `red-bucket`。`description` 必须写清何时触发：用户要注册、建桶、上传资产、按 harness 翻译拉取、复制别人的资产、跑安装脚本、开 issue 或 PR 时。

## 一句话经 server 安装（资产，不是 skill 本身）

公开 bucket、目标 harness 为 `claude` 时：

```bash
curl -sSL "https://redbucket.store/api/v1/users/{username}/buckets/{bucket}/install-script?target=claude" \
  -H "Accept: text/plain" | sh
```

官方 origin 是 `https://redbucket.store`。安装脚本仍把基础 URL 做成可替换模板：未设 `RED_BUCKET_URL` 时落到官方 origin，本机与自建覆盖该变量。脚本只调用 catalog 里的公开 GET，下载 translated zip，按目标 harness 本地布局落盘，退出 0。

私有桶必须带 Bearer，不能把 token 写进可粘贴的公开脚本正文；私有安装走已登录 agent 调 `GET .../translated`（skill 里写清）。

## skill 必须覆盖的用户流程

与 `user-flows.md` 一一对应，禁止另写一套步骤：

1. 注册、登录、`GET /users/me`
2. 从模板创建 bucket
3. 上传五类资产
4. 匿名浏览公开桶，翻译拉取
5. 执行 install-script
6. `POST .../copies`
7. issue 与评论
8. PR 的 `files` 树与 merge
9. 登出
10. 私有桶 404 口径

三个名字在 skill 正文里也不得混用。

## 与服务端开源的关系

本仓库 MIT 开源。skill 是给用户看的入口，服务端是 SaaS；ADR 里「公布 skill 工具，背后是 SaaS」仍然成立。别人可以自建服务端，skill 里的 origin 可替换。

以后若拆出 `370025263/red-bucket-skill`，只做本目录的镜像发布仓，正文仍以本仓库 `skills/red-bucket/` 为权威。

## 本期交付

- 本设计文件
- `skills/red-bucket/SKILL.md` 骨架（正文由 Gemini Flash 按本文与 `user-flows.md` 撰写）
- 根 README（Gemini Flash）
- 不实现 skill 里的客户端 SDK
