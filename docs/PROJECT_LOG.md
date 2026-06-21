# 小布的旅行：项目日志与 Agent 交接

> 本文件是项目当前状态的单一事实源。所有 Agent 开始工作前必须完整阅读，结束每次项目相关对话前必须更新。禁止记录任何真实密码、API Key、Session Token、Cookie、邮箱、照片内容、数据库记录、`.env` 内容或视觉特征缓存内容。

## 日志元数据

- 最后更新：2026-06-22 00:44（Asia/Hong_Kong，UTC+8）
- 仓库：`D:\Xiaobu's travel`
- 当前分支：`feat/xiaobu-travel`
- 上游仓库：`https://github.com/lt614258384-cyber/xiaobu-travel`
- 当前产品阶段：可运行的单用户本地 MVP；多用户和公网部署尚未实施
- 当前首要工作：完成基础可靠性修复，然后设计并原子实现认证与数据隔离

## Agent 更新协议

1. 开始工作前完整阅读本文件，并查看“当前最优先的下一步”及相关规格和计划。
2. 结束每次项目相关对话前更新本文件。即使没有代码改动，也必须记录新发现、已确认决策或“无状态变化”。
3. 同时维护“当前状态”“问题表”“下一步”和“会话记录”，避免彼此矛盾。
4. 只有存在文件、提交或验证输出作为证据时，才能标记“已完成”。设计稿和实施计划不等于代码已实现。
5. 会话记录按时间倒序排列，使用 Asia/Hong_Kong 时间。
6. 不得记录秘密值和个人数据；只记录秘密用途、存储位置和保护要求。
7. 不得擅自修改或提交 `data/`、`xiaobu.db`、`test.db`、`.env`、上传照片及其他用户运行时数据。

每条会话记录至少包含：用户目标、执行结果、验证证据、代码是否变化、遗留问题、下一步。

## 项目目标

“小布的旅行”是一个 AI 驱动的“旅行青蛙”式陪伴应用。它通过生成小布在汪星旅行和生活的照片，为用户提供持续、温暖的陪伴与慰藉。

长期目标：

- 从单用户本地应用升级为多用户服务。
- 每位用户可注册、登录、建立自己的小布档案并查看独立时间线。
- 用户档案、旅程、任务、API Key、上传照片和生成图片严格隔离。
- 支持 Railway、Render 一类 PaaS，使用 PostgreSQL 和持久化对象存储或明确的持久卷。
- 在公网发布前完成认证、授权、CSRF、限速、秘密保护、上传验证、审计和依赖升级。

## 当前产品与架构

### 技术栈

- Python 3.13，Windows 11
- FastAPI + Jinja2 服务端渲染
- SQLAlchemy ORM
- SQLite 开发数据库；代码预留 PostgreSQL URL
- APScheduler 后台计划任务
- 纯 HTML/CSS/JavaScript，无前端构建工具
- 火山引擎 Seedream 4.5 图生图
- Doubao Vision 提取小布外貌特征并缓存

### 已有产品功能

- `/profile`：编辑小布档案、外貌、偏好、API Key 和参考照片。
- `/`：Hero 卡片和历史时间线。
- `POST /generate`：手动触发图片生成。
- 每日定时规划 1–3 个生成任务。
- 状态机叙事：地点、活动、天气、心情和文案模板。
- 图片生成适配器：Seedream、通义万相、OpenAI、Fake。

### 当前数据与文件边界

- 没有 `User` 表或登录机制。
- 数据库只有共享 Profile 设计；代码查询第一条 Profile。
- `JourneyState`、`JourneyLog`、`ScheduledTask` 均没有 `user_id`。
- 上传图片位于 `data/uploads/`，生成图片位于 `data/generated/`。
- 整个 `data/` 当前通过 `/data` 静态挂载。
- API Key 当前保存在 `Profile.image_api_key`，未加密。
- 调度器和生成目录是全局资源，不具备多用户隔离。

### 关键生成流程

1. 手动或定时触发生成。
2. 读取共享 Profile 和 JourneyState。
3. 状态机选择地点、活动、天气和心情。
4. 首次使用最多三张参考图提取外貌特征并缓存。
5. 组装 Prompt，调用图片 API，保存到本地生成目录。
6. 写入 JourneyLog 并更新 JourneyState。

## 当前状态摘要

- MVP 功能存在并有 19 个测试。
- 项目上下文文档已经建立。
- 可靠性清理已有设计与实施计划，但代码尚未实施。
- 多用户目标和部分关键架构选择已经确认，但尚未形成可执行的认证与数据隔离规格。
- 安全审计已完成；结论是当前应用不适合公网部署。
- 跨 Agent 日志机制已建立：根目录 `AGENTS.md` 负责发现，本文件负责状态与历史。
- 工作区存在未跟踪运行时数据和旧设计文件，后续 Agent 必须保留。

## 已完成并验证

| 日期 | 状态 | 内容 | 证据 |
|---|---|---|---|
| 2026-06-21 | 已完成 | 单用户 MVP、状态机、模板叙事、手动/定时生成 | 当前源码与测试目录 |
| 2026-06-21 | 已完成 | Seedream 图生图和视觉模型特征提取/缓存 | 提交 `375ae31`、`97cc09a` |
| 2026-06-21 | 已完成 | 项目上下文整理 | `docs/CONTEXT.md`，提交 `f80dc55` |
| 2026-06-22 | 仅设计完成 | 可靠性清理设计 | `docs/superpowers/specs/2026-06-22-reliability-cleanup-design.md`，提交 `b73cb37` |
| 2026-06-22 | 仅计划完成 | 可靠性清理实施计划 | `docs/superpowers/plans/2026-06-22-reliability-cleanup.md`，提交 `8a6f599` |
| 2026-06-22 | 已完成 | Better Auth 安全技能查找、来源验证和安装 | 安装目录中存在对应 `SKILL.md`；新会话仍需确认技能可发现 |
| 2026-06-22 | 已完成 | 当前框架只读安全审计 | 代码证据、OWASP 官方指导、OSV 直接依赖查询；无代码改动 |
| 2026-06-22 | 已完成 | 跨 Agent 项目日志设计与计划 | 提交 `1efe590`、`e77b163` |

## 当前问题与安全隐患

### 风险登记表

| 优先级 | 状态 | 问题 | 已确认的证据 | 要求的解决方向 |
|---|---|---|---|---|
| P0 | 未解决 | 无认证和用户隔离 | 路由公开，查询第一条 Profile 和全部 JourneyLog | 认证与 `user_id` 数据隔离必须同批上线 |
| P0 | 未解决 | API Key 明文存储并完整回填网页 | `Profile.image_api_key`、`templates/profile.html` | 加密存储、掩码显示、仅主人访问、禁止写日志 |
| P0 | 未解决 | `/generate` 可匿名触发付费生成 | POST 路由无鉴权、CSRF、限速和配额 | 登录、CSRF、用户限额、审计和失败隔离 |
| P0 | 未解决 | 上传和媒体暴露 | 无服务端大小/魔数校验，整个 `/data` 公开 | JPEG/PNG/WebP 白名单、大小限制、UUID、私有媒体访问 |
| P0 | 未解决 | 生产依赖有公开漏洞 | Pillow 10.4.0、Jinja2 3.1.4、python-multipart 0.0.12 | 升级并重新执行完整依赖审计 |
| P1 | 未解决 | 无 CSRF、速率限制和安全审计 | 所有状态修改接口缺少控制 | Session CSRF Token、Origin 校验、数据库/Redis 限速、审计事件 |
| P1 | 未解决 | 默认 SECRET_KEY 可预测 | `config.py` 使用开发默认值 | 生产启动拒绝默认或低熵秘密，要求 32+ 字符高熵值 |
| P1 | 未解决 | 调度器和生成目录全局共享 | Scheduler 查询共享 Profile、State、Task | 所有任务和文件绑定 `user_id`，使用幂等任务和唯一文件名 |
| P1 | 未解决 | PaaS 本地磁盘不保证持久 | `data/uploads`、`data/generated` | 对象存储优先，或使用平台明确提供的持久卷 |
| P1 | 未解决 | 数据库缺少迁移机制 | 当前使用 `create_all`，无法可靠升级已有表 | 引入 Alembic，并显式迁移旧数据所有权 |
| P1 | 未解决 | 运行入口始终 `reload=True` 且监听 `0.0.0.0` | `run.py` | 开发/生产配置分离，生产禁用 reload 并启用 HTTPS/可信代理配置 |
| P1 | 未解决 | 数据库和特征缓存可能被误提交 | `.gitignore` 未覆盖 `*.db` 和特征缓存 | 扩充忽略规则并保留用户现有文件 |
| P1 | 未解决 | Python 3.13 下 psycopg2 依赖解析/构建失败 | 依赖审计因缺少适配 wheel/`pg_config` 中断 | 评估 psycopg 3 或兼容的 PostgreSQL 驱动版本 |
| P1 | 未解决 | 测试数据库状态不稳定 | 默认配置可能导向 PostgreSQL；旧 `test.db` 缺列 | 测试使用隔离临时数据库和统一 fixture |
| P1 | 未解决 | 测试期间后台线程出现未捕获异常 | 全新临时 SQLite 下 19 tests passed，但 `gen_first` 线程对空种子库访问 None | 测试中禁用后台生成，并让首次生成处理无地点/活动状态 |
| P2 | 已规划未实施 | FastAPI `on_event` 已弃用 | 可靠性设计和计划已提交 | 迁移 lifespan，保存并关闭唯一 Scheduler |
| P2 | 已规划未实施 | 中文上传文件名兼容和路径安全 | 文件名拼接档案名与原始扩展名 | 使用 ASCII UUID 与图片扩展白名单 |
| P2 | 已规划未实施 | 种子 Prompt 残留旧风格词 | `seed/activities_data.py` | 清理源数据和已有数据库，移除运行时替换补丁 |
| P2 | 未解决 | `python-dotenv` 未写入 requirements | `config.py` 导入但依赖清单缺失 | 补充并锁定依赖 |
| P3 | 未解决 | 角色纵向一致性不足 | Seedream 参考图不能精确复刻五官 | 后续评估 LoRA，不阻塞多用户安全改造 |
| P3 | 待验证 | Seedream 5.0 | 新模型未做兼容和质量测试 | 独立实验，不直接替换生产模型 |

### 依赖审计记录

2026-06-22 通过 OSV 查询直接依赖，确认当前固定版本存在公开漏洞记录：

- Pillow 10.4.0：图片解析越界写入、解压炸弹和资源耗尽风险；已知修复线至少到 12.2.0。
- Jinja2 3.1.4：存在沙箱逃逸记录；已知修复线至少到 3.1.6。当前项目未使用不可信模板沙箱，但仍需升级。
- python-multipart 0.0.12：存在多项 multipart/querystring CPU、内存和参数混淆风险；已知修复线至少到 0.0.31。
- pytest 8.3.0：开发环境存在 tmpdir 处理漏洞记录；已知修复线至少到 9.0.3。

完整传递依赖审计尚未完成：审计器在 Python 3.13 环境解析 psycopg2-binary 2.9.9 时因构建要求失败。后续必须在修复驱动依赖后重新审计。

## 多用户与部署路线图

### Phase 1：基础可靠性与依赖修复

- 补齐和升级依赖。
- FastAPI `on_event` 迁移到 lifespan。
- Scheduler 安全关闭。
- 上传文件改用安全 ASCII UUID。
- 清理旧 Prompt 风格词和已有数据库模板。
- 修复测试数据库隔离和后台线程异常。

### Phase 2：认证与数据隔离（必须原子上线）

- 新增 User、AuthSession、CSRF/速率限制/审计相关模型。
- 注册、登录、退出页面和路由。
- Argon2id 密码哈希。
- 数据库存储随机 Session 的哈希，浏览器使用安全 Cookie。
- 所有受保护路由通过 FastAPI 依赖取得当前用户。
- Profile、JourneyState、JourneyLog、ScheduledTask 关联非空 `user_id`。
- 所有查询按当前用户过滤，并测试跨用户访问返回 404/拒绝。
- 使用显式部署命令创建初始主人并迁移旧数据，禁止首个注册者自动认领。

### Phase 3：用户级秘密与媒体保护

- API Key 加密存储、掩码展示和最小权限读取。
- 上传、生成图和视觉特征按用户隔离。
- 取消公开 `/data`，使用鉴权下载或对象存储签名 URL。
- 服务端验证图片字节、尺寸、格式、数量和解压限制。

### Phase 4：多用户调度

- 每日任务遍历有效用户。
- 每个计划和生成调用携带 `user_id`。
- 用户级配额、重试、幂等、并发限制和失败隔离。
- 不允许一个用户的错误阻塞其他用户。

### Phase 5：PaaS 部署

- PostgreSQL 和 Alembic 迁移。
- 对象存储或持久卷。
- Dockerfile、健康检查和生产启动命令。
- Railway/Render 环境变量、HTTPS、可信 Host/Origin/代理配置。
- 备份、恢复、日志保留和依赖审计。

## 已确认的设计决策

| 决策 | 状态 | 理由 |
|---|---|---|
| 使用数据库支持的不透明随机 Session，不使用浏览器 JWT | 已确认 | 更适合 Jinja2 SSR，便于撤销和强制退出 |
| Session Cookie 使用 HttpOnly、Secure、SameSite=Lax | 已确认 | 降低脚本窃取和跨站请求风险；CSRF Token 仍必须存在 |
| 首版不做邮箱验证和忘记密码 | 已确认 | 避免首版引入邮件服务，范围保持可控 |
| 旧 Profile/旅程由部署命令显式归属初始主人 | 已确认 | 防止陌生注册者抢占旧数据 |
| 每位用户继续填写自己的火山引擎 API Key | 已确认 | 保持现有计费与使用模式，后台暂不统一承担费用 |
| 认证和数据隔离必须同一个发布单元 | 已确认 | 避免出现“已开放注册但所有用户仍共享数据”的危险中间态 |
| 密码优先使用 Argon2id | 建议，待规格确认 | 符合当前密码存储指导；需在认证规格中固定参数 |
| 媒体存储优先对象存储 | 建议，待部署阶段确认 | 多实例 PaaS 本地磁盘通常不持久且难共享 |

## 当前最优先的下一步

### 推荐交接顺序

1. 阅读并执行 `docs/superpowers/plans/2026-06-22-reliability-cleanup.md`。
2. 将依赖升级、测试隔离和后台线程异常纳入 Phase 1 的修订范围。
3. Phase 1 完成并验证后，编写“认证 + 数据隔离”联合设计规格。
4. 在该规格中使用 `better-auth-security-best-practices`、`fastapi-python`、`security-requirement-extraction`，并将通用安全原则映射到 FastAPI，而不是照搬 Better Auth 的 TypeScript 配置。
5. 认证与隔离实现完成前，不部署公网。

### 给下一位 Agent 的最短指令

> 阅读根目录 `AGENTS.md` 和 `docs/PROJECT_LOG.md`，检查 Git 状态，保留所有未跟踪运行时数据，然后从“当前最优先的下一步”继续。结束对话前更新项目日志。

## 重要文件索引

- 项目上下文：`docs/CONTEXT.md`
- 原始设计：`docs/superpowers/specs/2026-06-21-xiaobu-travel-design.md`
- 原始实施计划：`docs/superpowers/plans/2026-06-21-xiaobu-travel-plan.md`
- 可靠性设计：`docs/superpowers/specs/2026-06-22-reliability-cleanup-design.md`
- 可靠性计划：`docs/superpowers/plans/2026-06-22-reliability-cleanup.md`
- 项目日志设计：`docs/superpowers/specs/2026-06-22-project-log-design.md`
- 项目日志计划：`docs/superpowers/plans/2026-06-22-project-log.md`
- Agent 规则：`AGENTS.md`
- Web 路由：`app.py`
- 数据模型：`models.py`
- 调度与生成管线：`scheduler.py`
- 图片适配器：`engine/image_gen.py`
- Prompt 与文案：`engine/storyteller.py`
- 状态机：`engine/state_machine.py`
- 测试：`tests/`

## 会话与开发记录（倒序）

### 2026-06-22 00:44 — 建立实际项目日志

- 用户目标：先建立实际项目日志，方便其他 Agent 立即接手；当前只允许日志和 Agent 指令文档修改。
- 执行结果：创建根目录 `AGENTS.md` 和本文件，汇总项目目标、架构、已完成事项、风险、路线图、决策、下一步与历史记录。
- 验证证据：仅检查两个新文档的必需标题、交叉引用、状态一致性、格式和常见秘密值模式。
- 代码变化：无代码改动；未修改应用、测试、数据库、图片、配置或依赖。
- 遗留问题：所有 Phase 1–5 工程工作仍待实施。
- 下一步：让下一位 Agent 从可靠性实施计划开始，并在结束前更新本日志。

### 2026-06-22 00:30 — 当前框架安全审计

- 用户目标：使用 Better Auth 安全最佳实践和安全需求提取方法检查当前框架。
- 执行结果：确认当前版本仅适合可信本地环境，不适合公网；提取认证、授权、Session、CSRF、限速、上传、媒体、API Key、审计、调度和部署安全要求。
- 验证证据：只读检查 `app.py`、`models.py`、`config.py`、模板、JavaScript、调度器、图片适配器、依赖清单和 `.gitignore`；访问 OWASP/FastAPI 官方文档；查询 OSV 直接依赖。
- 代码变化：无代码改动。
- 遗留问题：传递依赖审计被 psycopg2/Python 3.13 构建问题阻塞；安全控制均未实施。
- 下一步：先完成基础可靠性和依赖修复，再设计认证与隔离联合发布。

### 2026-06-22 00:20 — 安装 Better Auth 安全技能

- 用户目标：通过 find-skills 查找并安装 `better-auth-security-best-practices`。
- 执行结果：找到 `better-auth/skills@better-auth-security-best-practices`，确认来源仓库未归档并具有公开使用记录，完成全局安装。
- 验证证据：用户技能目录中存在对应 `SKILL.md`。
- 代码变化：无项目代码改动。
- 遗留问题：新 Codex 会话仍需确认技能已被发现，并在使用前完整读取。
- 下一步：在认证安全设计中只迁移通用安全原则，不照搬 Better Auth 的 JavaScript 实现。

### 2026-06-22 00:10 — 明确多用户与 PaaS 目标

- 用户目标：将单用户本地应用升级为可部署的多用户服务。
- 执行结果：确认采用数据库支持的不透明 Session；首版不做邮箱验证/找回；旧数据由显式创建的初始主人认领；认证和数据隔离必须原子上线。
- 验证证据：用户逐项确认架构边界。
- 代码变化：无代码改动。
- 遗留问题：认证与数据隔离联合规格尚未编写。
- 下一步：基础修复完成后进入联合规格设计。

### 2026-06-22 00:00 — 可靠性清理设计与计划

- 用户目标：完成 lifespan、中文上传文件名和旧 Prompt 风格词三项清理。
- 执行结果：设计规格和实施计划已编写并提交。
- 验证证据：提交 `b73cb37`、`8a6f599`。
- 代码变化：仅文档；应用代码尚未修改。
- 遗留问题：实施计划尚未执行，不能标记工程任务完成。
- 下一步：按计划采用测试驱动实施并验证。
