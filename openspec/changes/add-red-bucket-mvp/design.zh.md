> 本文是同目录 `design.md` 的逐句中文译本。标识符、路径、状态码、错误码保持原文。

# 设计：add-red-bucket-mvp

## 背景

全新仓库；唯一既有产物是 `sdd/adr/platform.md` 中的 ADR。从中继承的约束：存储是文件系统上的 git（不用对象存储），配额是每用户 5 个 bucket、每 bucket 10MB，Phase 1 不含移动应用和 git 协议访问，前端遵循 pi.dev 的轻量风格，头条验收是 1000 用户 / 并发 10 下 p95 < 1s。动机见 `proposal.md`；行为契约见各 delta specs。

## 目标 / 非目标

**目标：**

- 一个可单独部署的服务（API + 服务端渲染 UI），外加一个可隔离测试的 formatter 引擎。
- 确定性的、由矩阵驱动的翻译，使不支持的对大声失败，已支持的对可用 golden fixtures 做回归测试。
- 全部验收标准都可以作为自动化测试执行（见 `test-plan.md`）。

**非目标：**

- 水平扩展 / 多节点存储；Phase 1 目标是单节点，负载画像见各 specs。
- 协作者/团队权限模型（Phase 1 私有访问仅限 owner）。
- 市场策展、搜索排序、计费。

## 决策

1. 单体，服务端渲染 UI，JSON API 位于 `/api/v1/`。
   理由：1000 用户规模不需要微服务；服务端渲染能低成本满足「只读路径在没有 JavaScript 时也能工作」的要求。备选（SPA + 独立 API 服务）因更重、且对匿名抓取/读取延迟更不利而被否决。

2. Formatter 作为带翻译对注册表的纯库。
   每一个（资产类型, src, dst）对注册一个纯函数 `translate(sourceTree) -> targetTree + lossyNotes`。能力矩阵端点读取该注册表，因此代码与矩阵不会漂移。无 I/O 的纯函数给出确定性（规格要求），并使 golden-fixture 测试变得简单。备选（LLM 辅助翻译）在 Phase 1 被否决：非确定性，违反确定性要求；以后可以作为 cross-transfer 文档的离线撰写辅助再回来。

3. 存储布局为 `<storage-root>/<user-id>/<bucket-id>.git`，使用裸仓库 + 每次变更的 worktree，变更按 bucket 用每 bucket 一把锁串行化。
   不可变 id 让用户名/bucket 重命名只动元数据。每 bucket 锁提供规格要求的原子配额「先检查再提交」；在此规模下争用可忽略。备选（非裸仓库加长期存活的 worktree）被否决：更难做成并发安全。

4. 元数据放在 SQLite（用户、buckets、配额、issues、PRs、安装出处）；git 只保存内容。
   列表、配额查询，以及 issue/PR 状态需要可查询性；为这些去解析 git 会打爆延迟预算。SQLite（WAL 模式）足以支撑 1000 用户 / 并发 10，并保持运维简单。备选（Postgres）延后到规模需要时再做；数据访问层保持很薄，以便那次迁移成本低。

5. 校验作为上传、PR merge 和 install 共用的流水线。
   每种资产类型一个校验器，产出机器可读的违规项（`rule id + path`），在内容进入 bucket 的所有入口复用，因此 PR merge 和 install 不能绕过上传规则（规格要求）。

6. 认证：email+password 加盐哈希，Bearer API tokens；私有 bucket 拒绝一律回答 404。
   返回 404 而不是 403 是规格层的反枚举决策。OAuth/社交登录延后。

7. 把负载测试作为仓库一等产物（k6 或 Locust 场景 + 1000 个 mock 用户的 seeder），作为预发布门禁运行并产出归档报告。
   p95 验收是规格要求；让该 harness 在仓库内可复现，是「回归门禁」场景能诚实让一次发布失败的唯一办法。

## 风险 / 权衡

- [功能等价由我们无法控制的 harness 行为来判定] → 在 cross-transfer 文档的实验环境中固定 harness 版本；每一对的等价性 checklist 放在文档中，并在 harness 更新时重跑。
- [对整个 10MB bucket 做翻译拉取可能威胁 1s p95] → 翻译对每个 commit 是确定的，因此按 (commit, target) 缓存翻译后的归档；负载测试的流量混合包含翻译拉取，以便抓住回归。
- [并发协作突发下的 SQLite 写争用] → WAL 模式 + 短事务；记录规模上限；数据层保持可替换为 Postgres。
- [Git worktree 大小 ≠ 用户对 10MB 的直觉（历史会超出工作树）] → 配额按工作树定义（规格）；定期跑 `git gc`，并写明历史开销不向用户计费。
- [pi.dev 风格「照抄」带来复制风险] → 复现布局/字体排印做法，不复现素材；全部文案和品牌都是 red-bucket 自己的。

## 迁移计划

全新部署；没有迁移。回滚 = 重新部署上一份构建；SQLite 文件和 git 存储根都是升级前应备份的向后兼容产物。

## 未决问题

- 域名未定（ADR 留空）——不影响规格；安装脚本必须把基础 URL 做成模板。
- Phase 1 等价性实验要固定哪些 harness 版本（首次运行时记入各 cross-transfer 文档）。
