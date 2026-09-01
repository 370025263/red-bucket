# Phase 1 用户时序

本文画人怎么用 red-bucket。端点、状态码、JSON 字段以 `api-catalog.md` 为准。表与锁以 `schema-sqlite.md` 为准。实现栈见 `tech-stack.md`。

图里的「服务」是同一个 FastAPI 进程：它后面再碰 SQLite、git、formatter。浏览器 HTML 与 JSON 客户端走同一套 `/api/v1/`。日后 CLI、移动端、MCP 只是换一个最左列的调用方，不另开时序。

三个名字在图里也不混用：copy 是写入自己的桶；install-script 是拿一段本机 shell；translated fetch 是按 harness 取译本。

## 谁参与

- 访客：未带 token。
- 本人：已登录的 owner。
- 他人：已登录，但不是该桶 owner。
- 本机 agent：执行安装脚本的本地环境（curl 或 shell）。
- 服务：red-bucket 进程。
- SQLite、git、formatter：服务内部，不是用户能直接打的面。

## 入口总览

```mermaid
flowchart LR
  browser[浏览器 HTML]
  agent[本机 agent]
  later[日后 CLI 或 MCP]
  api["/api/v1/"]
  html[Jinja2 页面]
  sqlite[(SQLite)]
  git[(文件系统 git)]
  fmt[formatter 纯库]

  browser --> html
  html --> api
  browser --> api
  agent --> api
  later --> api
  api --> sqlite
  api --> git
  api --> fmt
```

## 1. 注册、登录、看自己

访客先注册。注册成功不签发 token。再登录拿到 Bearer。之后写操作都带这个头。

```mermaid
sequenceDiagram
  actor Guest as 访客
  participant API as 服务 /api/v1
  participant DB as SQLite

  Guest->>API: POST /auth/register {username,email,password}
  API->>DB: 查 username_normalized、email_normalized
  alt 用户名或邮箱占用
    API-->>Guest: 409 username_taken 或 email_taken
  else 密码短于 8 或字段不合法
    API-->>Guest: 422 validation_failed
  else 通过
    API->>DB: INSERT users（password 只存 Argon2id）
    API-->>Guest: 201 User 公开字段<br/>Location /users/{username}
  end

  Guest->>API: POST /auth/login {email,password}
  alt 邮箱不存在或密码错
    API-->>Guest: 401 unauthorized（两种不可区分）
  else 通过
    API->>DB: INSERT tokens（只存哈希）
    API-->>Guest: 200 {token, token_type, user}
  end

  Guest->>API: GET /users/me<br/>Authorization Bearer
  API->>DB: 用 token_hash 找未撤销行
  API-->>Guest: 200 本人 User（含 email、bucket_quota、bucket_count）
```

## 2. 从模板创建 bucket

本人在自己的命名空间下建桶。选了 template 才有第一次 git commit。

```mermaid
sequenceDiagram
  actor Owner as 本人
  participant API as 服务 /api/v1
  participant DB as SQLite
  participant Git as git 裸仓

  Owner->>API: POST /users/{me}/buckets<br/>{name, visibility, description, template}
  API->>DB: BEGIN IMMEDIATE<br/>COUNT 活桶 vs bucket_quota
  alt 已达个数上限
    API-->>Owner: 403 bucket_quota_exceeded
  else 同名活桶已在
    API-->>Owner: 409 bucket_name_taken
  else 通过
    API->>DB: INSERT buckets
    alt 带 template
      API->>Git: 写骨架文件并 commit<br/>作者 user-{id}@users.red-bucket.invalid
      API->>DB: 刷新 storage_usage_bytes
    else 不带 template
      Note over Git: 空树，零 commit
    end
    API-->>Owner: 201 Bucket<br/>Location /users/{me}/buckets/{name}
  end
```

## 3. 上传资产

上传、copy、PR merge 走同一条校验再加配额的路径。

```mermaid
sequenceDiagram
  actor Owner as 本人
  participant API as 服务 /api/v1
  participant Val as validators
  participant Lock as 每桶 flock
  participant Git as git
  participant DB as SQLite

  Owner->>API: POST /users/{me}/buckets/{bucket}/assets
  API->>Val: 按 type 与 source_harness 校验
  alt 格式不通过
    API-->>Owner: 422 validation_failed（rule + path）
  else 通过
    API->>Lock: LOCK_EX
    API->>Git: 在临时工作树写入文件
    API->>Git: 测工作树字节
    alt 将超过 10MB
      API->>Git: 丢弃临时变更
      API-->>Owner: 413 bucket_storage_exceeded
    else 通过
      API->>Git: commit（作者=本人）
      API->>DB: UPSERT assets，刷新 usage
      API-->>Owner: 201 Asset<br/>Location .../assets/{id}
    end
    API->>Lock: 释放
  end
```

## 4. 匿名浏览公开桶，再按 harness 翻译拉取

核心价值在这一条：读可以不登录；译本由 formatter 现算，不改 git 里的源。

```mermaid
sequenceDiagram
  actor Guest as 访客
  participant API as 服务 /api/v1
  participant DB as SQLite
  participant Git as git
  participant Fmt as formatter

  Guest->>API: GET /users/{name}/buckets/{bucket}
  API->>DB: 活桶谓词 deleted_at IS NULL
  alt 不存在或 private
    API-->>Guest: 404 not_found
  else public
    API-->>Guest: 200 Bucket（含 harness_mix、open counts）
    Guest->>API: GET .../tree
    API->>Git: ls-tree HEAD 一层
    API-->>Guest: 200 items TreeEntry
    Guest->>API: GET .../blob/README.md
    API->>Git: 读 blob
    API-->>Guest: 200 文本或 base64
    Guest->>API: GET .../translated?target=codex
    API->>Git: 读该 commit 工作树
    API->>Fmt: 按矩阵翻译每个资产
    alt 单资产端点且对不在矩阵
      API-->>Guest: 501 translation_unsupported
    else 整桶默认
      Note over API: 能译则译；跳过的写入 notes<br/>strict=1 才整桶 501
      API-->>Guest: 200 zip（X-Red-Bucket-Lossy）
    end
  end
```

## 5. 本机执行安装脚本

用户从 Code 页签复制脚本。agent 在干净环境执行。脚本只打公开 GET，先取译本再落盘。这不是 copy。

```mermaid
sequenceDiagram
  actor Human as 用户
  actor Agent as 本机 agent
  participant API as 服务 /api/v1
  participant Disk as 本机 harness 目录

  Human->>API: GET .../install-script?target=claude
  API-->>Human: 200 {target, script, translated_url}
  Human->>Agent: 粘贴并执行 script
  Agent->>API: GET .../translated?target=claude
  API-->>Agent: 200 zip
  Agent->>Disk: 按 claude 本地布局解包
  Agent-->>Human: 退出码 0
```

## 6. 把别人的公开资产复制进自己的桶

本人读得到源（公开，或自己的私有），写进自己的目标桶。留下 copies 出处。

```mermaid
sequenceDiagram
  actor Owner as 本人
  participant API as 服务 /api/v1
  participant Val as validators
  participant DB as SQLite
  participant Git as 目标桶 git

  Owner->>API: POST /users/{me}/buckets/{dest}/copies<br/>{source_username, source_bucket, source_asset_id, dest_path}
  API->>DB: 解析源桶（活桶 + 可见）
  alt 源是他人私有或已软删
    API-->>Owner: 404 not_found
  else 可读
    API->>Val: 与上传相同的校验
    API->>Git: 锁内写入 + 配额
    alt 将超 10MB
      API-->>Owner: 413 bucket_storage_exceeded
    else 通过
      API->>DB: INSERT copies（dest_path、dest_type 快照）<br/>UPSERT assets.source_copy_id
      API->>Git: commit（作者=本人）
      API-->>Owner: 201 InstallRecord<br/>Location .../copies/{id}
    end
  end
```

## 7. 他人在公开桶开 issue 并评论

第三人不能评、不能关。私有桶对非 owner 一律 404。

```mermaid
sequenceDiagram
  actor Other as 他人
  actor Owner as 桶主
  actor Guest as 访客
  participant API as 服务 /api/v1
  participant DB as SQLite

  Other->>API: POST .../issues {title, body}
  API->>DB: INSERT issues（number = MAX+1）
  API-->>Other: 201 Issue

  Guest->>API: GET .../issues
  API-->>Guest: 200 分页 items

  Other->>API: POST .../issues/{n}/comments {body}
  API-->>Other: 201 IssueComment

  Note over API: 第三名路人 POST comment 或 PATCH close → 403 forbidden

  Owner->>API: PATCH .../issues/{n} {state: closed}
  API->>DB: 写 closed_by、closed_at
  API-->>Owner: 200 Issue
```

## 8. 他人提 PR，桶主 merge

提议内容是文件树替换列表，先躺在 SQLite，merge 时才进 git。校验与配额必须重跑。

```mermaid
sequenceDiagram
  actor Other as 他人
  actor Owner as 桶主
  participant API as 服务 /api/v1
  participant DB as SQLite
  participant Val as validators
  participant Git as git

  Other->>API: POST .../pulls {title, body, files[]}
  API->>DB: INSERT pull_requests（proposed_files_json）
  Note over Git: 此时不改工作树
  API-->>Other: 201 PullRequest

  Owner->>API: GET .../pulls/{n}/files
  API-->>Owner: 200 files（审阅）

  Owner->>API: POST .../pulls/{n}/merge
  API->>Val: 把 files 打到当前 HEAD 上再校验
  API->>Git: 锁内测工作树
  alt 校验失败
    API-->>Owner: 422，PR 仍 open，仓不变
  else 将超 10MB
    API-->>Owner: 413，PR 仍 open，仓不变
  else 通过
    API->>Git: commit（作者=PR 作者，不是桶主）
    API->>DB: state=merged，merged_commit_sha
    API-->>Owner: 200 PullRequest
  end
```

桶主拒绝则 `POST .../reject`，状态变 rejected，git 不动。

## 9. 登出

只撤销当前这一枚 token。

```mermaid
sequenceDiagram
  actor Owner as 本人
  participant API as 服务 /api/v1
  participant DB as SQLite

  Owner->>API: POST /auth/logout
  API->>DB: 该 token 行写 revoked_at
  API-->>Owner: 204
  Owner->>API: GET /users/me（旧 token）
  API-->>Owner: 401 unauthorized
```

## 10. 非 owner 撞上私有桶

存在与否对外不可区分。列表里私有项是省略，不是逐条 404。

```mermaid
sequenceDiagram
  actor Other as 他人或访客
  participant API as 服务 /api/v1
  participant DB as SQLite

  Other->>API: GET /users/{owner}/buckets
  API->>DB: 只选 visibility=public 且 deleted_at IS NULL
  API-->>Other: 200（私有项不出现）

  Other->>API: GET /users/{owner}/buckets/{private}
  API-->>Other: 404 not_found

  Other->>API: GET .../assets 或 /tree 或 /translated<br/>（同一私有桶）
  API-->>Other: 404 not_found
```

## 11. 改用户名（元数据，仓不搬家）

用来满足 git-storage 的 rename-safe。不是产品级改名页的完整设计。

```mermaid
sequenceDiagram
  actor Owner as 本人
  participant API as 服务 /api/v1
  participant DB as SQLite
  participant Disk as 磁盘 <user-id>/

  Owner->>API: PATCH /users/me {username}
  alt 新名占用
    API-->>Owner: 409 username_taken
  else 通过
    API->>DB: 只改 username、username_normalized
    Note over Disk: 目录不移动
    API-->>Owner: 200 User
  end
  Owner->>API: GET /users/{新名}/buckets/{bucket}
  API-->>Owner: 200 旧仓仍在
```

## 和 Web UI 的关系

浏览器打开 `/<username>/<bucket>` 时，服务先渲染 HTML（标题、页签、文件表、About、安装脚本文本都在首屏 HTML 里，满足无 JS）。页面上的写操作（建桶、上传、关 issue、merge）再打上图同一组 `/api/v1/` 端点。不要为页签再做一套私有 JSON。

## 不画进本期的时序

- 移动应用上架后的安装与推送。
- `git clone` 协议。
- 官方第一方 skill 或 MCP 客户端本体（它们将来复用第 4、5、6 节）。
- 市场浏览、Star、协作者邀请。
