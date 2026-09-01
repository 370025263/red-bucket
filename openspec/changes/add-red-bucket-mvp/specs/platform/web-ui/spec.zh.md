> 本文是同目录 `spec.md` 的逐句中文译本。标识符、路径、状态码、错误码保持原文。

## Purpose

定义轻量 Web 前端（pi.dev 风格的视觉语言，配 red-bucket 自己的文案）：浏览和搜索公开 buckets，管理自己的 buckets，并展示一键安装脚本。

## ADDED Requirements

### Requirement: Public browsing pages
Web UI 必须提供可匿名访问的页面，用于：落地页、列出该用户公开 buckets 的用户资料页，以及路径为 `/<username>/<bucket-name>` 的 bucket 详情页，展示描述、带类型和源 harness 的资产列表、可见性、存储用量，以及带目标 harness 选择器的安装脚本片段。

#### Scenario: Bucket page renders anonymously
- **WHEN** 未认证访客打开某个公开 bucket 的页面
- **THEN** 该页渲染资产列表和可复制的安装脚本，没有登录提示挡住内容

#### Scenario: Private bucket page hidden
- **WHEN** 未认证访客打开某个私有 bucket 的 URL
- **THEN** UI 展示与不存在的 bucket 相同的未找到页

### Requirement: Authenticated management pages
Web UI 必须让已登录用户注册/登录、创建 bucket（带模板和可见性选择）、上传资产、切换可见性、查看配额用量、删除 buckets，以及管理其公开 buckets 上的 issues 和 pull requests——全部只由公开的 `/api/v1/` 端点支撑。

#### Scenario: Bucket created through UI
- **WHEN** 已登录用户填完创建 bucket 表单，选择 `agents` 模板和 `public` 可见性
- **THEN** UI 导航到新 bucket 页，展示模板骨架和 public 标识

#### Scenario: UI uses public API only
- **WHEN** 任何 UI 管理动作在记录浏览器网络日志的情况下被执行
- **THEN** 每一次后端调用都指向已文档化的 `/api/v1/` 端点（没有私有端点）

### Requirement: Visual style baseline
Web UI 必须遵循 pi.dev 的轻量视觉风格（克制、加载快、内容优先），使用 red-bucket 自己的命名和文案。页面在只读浏览路径上必须在没有客户端 JavaScript 时仍可使用。

#### Scenario: Read path works without JavaScript
- **WHEN** 某个公开 bucket 页在禁用 JavaScript 的情况下被加载
- **THEN** 资产列表和安装脚本文本在所服务的 HTML 中仍然可见
