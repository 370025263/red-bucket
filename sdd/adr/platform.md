
### 域名
暂时不指定。

### 安装路径

提供github开源仓库形式，公布skill工具（背后本质是SaaS服务，以skill/mcp工具形式面向ai存在）作为用户入口端，提供一键安装脚本，复制给agent进行安装。

提供SaaS在线服务，支持官网通过一键安装脚本，复制给agent进行安装。

提供App服务，支持从AppStore或安卓应用商店或网站点选下载APK进行安装。(首期不包含，上架费用高)

### 功能设计

第一阶段，提供最为基础的功能。

用户新建bucket，上传经过格式校验的skill、mcp工具、CLAUDE.md/AGENTS.md。

提供UI页面，github-like或者说huigginface-like的用户name/bucket-name的组合来进行区分，然后用户能够设置private/public.

有点类似github，public情况下用户也可以提issue和pr。

### 业务设计
用户默认可以创建5个repo，每个repo 10M空间。
用户需要注册使用服务，但是访问public是不需要注册的。

用户新开repo的时候，可选是否提供template服务。template中，会提供一些基础的目录。目录template我们会提供多种，比如codex style，Agents style(通用），还有claude style， openclaw style等等。

#### 功能设计
用户上传的时候，可能是从各种harness来进行上传的，格式上会有所区别。
但是用户在fetch的时候，一定是基于某种harness，我们最具核心价值的formatter会将你的对应bucket中的harness来进行基础的格式转化。
当用户fetch到本地后，会按需填充到用户对应的位置。

用户可以install别人的skill，plugin等到自己的bucket，支持mcp市场、plugin市场。

我们的价值就在于将不同生态的subagent、plugin等组件能够进行交互翻译，并将这部分能力通过restful接口的方式暴露给用户。

如果有必要，我们需要进行详细设计。

具体迁移方式和文档定义见cross-transfer/codex-2-claude.md等。

每一个文档需要说明两个harness的skill，plugin，mcp，subagent等内容的格式，然后写一下用户在使用redbucket的时候需要的用户面操作还有会发生的变化, 文档要经过实际的实验检测。

#### 前端
我们采取轻量前端，https://pi.dev/, 照抄，按需添加和替换为我们自己的文案。

#### 接口
支持restful协议。
用户可以通过完备且覆盖全生命周期的restful api来操作。
用户也可以通过git方式来直接clone和下载。（第一期不做）

#### 存储
用户的repo（bucket)上传内容不放在对象存储，使用git存在文件系统。

按照用户id进行命名作为domain隔离符区分。

每个用户的单repo存储空间在10m。

提供APP安装入口，用户可以有图形化

#### 验收测试
用户面接口延迟，在1000用户下，并发10，能95% 接口延迟全部1s内。

测试使用mock用户，进行跨harness的迁移，同样功能在迁移前和迁移后保持一致。







