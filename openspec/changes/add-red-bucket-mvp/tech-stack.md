# Phase 1 技术选型

本文是 `add-red-bucket-mvp` 的实现栈契约。API 路径与 JSON 仍以 `api-catalog.md` 为准，表结构仍以 `schema-sqlite.md` 为准。换语言或框架必须先改本文并说明为什么旧结论不再成立，不得在实现里悄悄换栈。

用户时序见 `user-flows.md`。

## 结论

Phase 1 用 Python 3.12 做一个可单独部署的进程：FastAPI 同时挂 `/api/v1/` 与服务端渲染 HTML，Jinja2 出页，uvicorn 做 ASGI。元数据用标准库 `sqlite3`（WAL）放在薄 DAL 后面。bucket 内容用系统 `git` 子进程写裸仓库。密码用 Argon2id。测试用 pytest。负载门禁用 Locust。包管理用 uv，检查用 ruff。

只读 HTML 不依赖客户端 JavaScript。不要上 React、Vue、Vite SPA，也不要为本期引入 Postgres、ORM、pygit2。

## 约束（选型必须满足）

- 单一可部署物：JSON API 与 UI 同进程，见 design.md 决策 1。
- 只读路径无 JavaScript 仍可用，见 `platform/web-ui`。
- 元数据 SQLite WAL，列可迁 Postgres，见 `schema-sqlite.md`。
- 内容在文件系统 git，每桶一把 flock，见 `platform/git-storage`。
- formatter 是无 I/O 纯函数，要 golden fixture 与确定性，见 `translation/harness-formatter`。
- 1000 用户、并发 10、面向用户接口 p95 低于 1s。
- 日后 CLI、移动端、MCP 只复用 `/api/v1/`，不为它们加运行时。
- 实现与评审的人主要在 Python 工具链上（本机已有 uv、ruff、pytest 习惯）。

## 候选与否决

### 语言与 Web 框架

| 候选 | 结论 | 理由 |
| --- | --- | --- |
| Python 3.12 + FastAPI + Jinja2 | 选定 | 一份进程同时提供类型化 JSON 与 SSR；Pydantic 模型可直接对照 `api-catalog.md`；formatter 与校验器用纯函数加 fixture 最省事；和现有工具链一致。 |
| Go + chi 或 echo + html/template | 否决（最强备选） | 单二进制、git 与锁的同步模型更干净，并发也更省心。否决是因为 skill 或 plugin 的 frontmatter、YAML、Markdown 变换与大量 golden 文本夹具在 Python 里写得更快；本期规模用不上 Go 的吞吐。若 p95 在 Locust 下被 Python 自身拖死，再单独立项迁 Go，契约不变。 |
| Django | 否决 | 自带用户、admin、ORM 会和「薄 DAL + 自管 tokens 表 + 私有桶一律 404」打架，目录也会被框架形状带走。 |
| Flask | 否决 | 同步模型适合 git，但缺少 FastAPI 这种与 catalog 对齐的请求或响应模型；本期要给 agent 客户端看稳定 JSON，手写 Flask 序列化更容易漂。 |
| Node + Express 或 Next | 否决 | 只读无 JS 还要再拆一套 SSR；git 与 flock 在 Node 里别扭；本仓库没有 Node 工具链。 |
| Rust + axum | 否决 | 正确也能做，Phase 1 交付时间不可接受。 |

### 元数据访问

| 候选 | 结论 | 理由 |
| --- | --- | --- |
| 标准库 `sqlite3` + 薄模块 | 选定 | 与 `schema-sqlite.md` 的 DDL 一一对应；没有隐藏 schema 的 ORM 层；迁 Postgres 时只换连接与占位符。写路径已有每桶 flock，不必上异步驱动抢锁。 |
| SQLAlchemy ORM | 否决 | 薄 DAL 要求列名可见；ORM 会另生一套对象名，和映射表抢权威。 |
| aiosqlite 或 SQLAlchemy Core 异步 | 否决 | git 与 flock 是同步的；整条写路径进线程里跑同步 SQL 更简单，也避免半异步半同步。 |
| 本期直接 Postgres | 否决 | 规格写明 SQLite 先上；1000 用户用不上。 |

FastAPI 路由可以是 async。凡碰到 SQLite 写、flock、`git` 子进程，一律 `anyio.to_thread.run_sync`（或等价）进工作线程，不要在事件循环里阻塞。

### Git 绑定

| 候选 | 结论 | 理由 |
| --- | --- | --- |
| 系统 `git` 可执行文件（subprocess） | 选定 | 与「文件系统上的 git 仓库」心智一致；CI 只依赖官方 git；出问题可直接看 `git log`。作者邮箱按 `user-{id}@users.red-bucket.invalid` 写进环境变量再 commit。 |
| pygit2 或 GitPython | 否决 | pygit2 要本机 libgit2；GitPython 仍是调 git，再包一层只多故障面。 |

机器上必须有 `git`。服务启动时检查版本，缺了就拒绝启动。

### 密码、会话、渲染、测试

| 项 | 选定 | 否决 |
| --- | --- | --- |
| 密码哈希 | Argon2id（`argon2-cffi`） | 明文、可逆加密、单轮 SHA；bcrypt 可作备选，本期统一 Argon2id |
| API token | `secrets.token_urlsafe` 签发，库内只存 SHA-256 | JWT（本期无过期与刷新产品需求，撤销要黑名单，多一套） |
| README 与 issue 正文 | `markdown-it-py` 转 HTML，默认关原始 HTML | 客户端 marked 等（破坏无 JS 只读） |
| 单元与 API 测试 | pytest + httpx ASGI 客户端 | 只测 mock 不启应用 |
| 负载门禁 | Locust | 本期不双轨；k6 留作以后若 CI 镜像更适合再换，场景文件另写 |
| 包管理与锁 | uv（`pyproject.toml` + `uv.lock`） | 散装 pip freeze |
| Lint 与格式 | ruff | 再叠一层 black 或 flake8 |
| CSS | 手写一份，只用 `design.md` 的 `--rb-*` tokens | Primer、Bootstrap、Tailwind 作为运行时依赖 |

Token 过期、429、CSRF、HTTPS 终止仍按 design.md 留给部署层。HTML 表单写操作若走 cookie 会话，本期仍只认 Bearer：浏览器管理页用页面内持有的 token 调同一套 `/api/v1/`（可用极薄的渐进增强）。不要为 UI 做第二套 session cookie 认证协议。

## 选定清单（实现按此建目录）

| 层 | 选型 | 版本下限 |
| --- | --- | --- |
| 语言 | Python | 3.12 |
| 包管理 | uv | 锁定在仓库里 |
| Web | FastAPI | 0.115 及以上 |
| 模板 | Jinja2 | 3.x |
| 服务器 | uvicorn | 标准 ASGI |
| 请求或响应模型 | Pydantic v2 | 字段名与 `api-catalog.md` 一致 |
| 元数据 | `sqlite3` + 薄 DAL | WAL，`foreign_keys=ON` |
| 内容 | 系统 git | 2.40 及以上（支持本机已有版本即可，记入 README） |
| 哈希 | argon2-cffi | Argon2id |
| Markdown | markdown-it-py | 服务端渲染 |
| 测试 | pytest、httpx | S1–S7、S10、S11 |
| 负载 | Locust | S9 |
| 静态文件 | Starlette StaticFiles | logo 从服务静态目录出，不读 openspec 路径 |

建议仓库布局（实现时可微调，但不要把 formatter 和 Web 揉进一个文件）：

```
src/redbucket/
  main.py              # 组装 FastAPI：挂 /api/v1 与 HTML
  api/                 # 只做 HTTP，对照 api-catalog.md
  web/                 # Jinja2 路由与模板
  store/               # sqlite DAL，对照 schema-sqlite.md
  gitstore/            # 裸仓、worktree、flock、commit
  formatters/          # 纯库，无 I/O
  validators/          # 上传、copy、merge 共用
  security/            # 密码、token 哈希
tests/
scripts/locust/        # S9
```

依赖写进 `pyproject.toml`。生产启动形如：`uv run uvicorn redbucket.main:app`。存储根与 SQLite 路径用环境变量，不要写死。

## 与契约如何对上

- FastAPI 路由表必须能对上 `api-catalog.md` 的 43 个 method 加 path，多一个面向用户的 `/api/v1/` 也不行。
- Pydantic 模型字段必须能对上 catalog 的 JSON 对象；改字段先改 catalog 与 schema 映射，再改模型。
- `store/` 只许出现 `schema-sqlite.md` 里的九张表。
- `formatters/` 的注册表就是 `GET /translation-matrix` 的数据源。
- HTML 路由不是 API。页面里的数据请求只许打 catalog 里的端点。
- Locust 场景按 test-plan S9 的端点类占比打 catalog，不打 HTML。

## 部署形态

单节点、单进程、本机磁盘。前面可以放反向代理做 TLS。Phase 1 不做多副本抢同一 git 根。备份对象就是 SQLite 文件加 git 存储根。

## 以后再说（不改本期结论）

- 迁 Postgres：换 DAL 驱动，表列保持映射表。
- 官方 skill 或 MCP 客户端：仍当本 API 的调用方，不换服务端语言。
- 若负载门禁证明 Python 是 p95 瓶颈：另开变更评估 Go，不在本期预留双实现。
