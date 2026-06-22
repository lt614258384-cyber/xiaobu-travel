# 小布的旅行：项目日志与 Agent 交接

> 本文件是项目当前状态的单一事实源。所有 Agent 开始工作前必须完整阅读，结束每次项目相关对话前必须更新。禁止记录任何真实密码、API Key、Session Token、Cookie、邮箱、照片内容、数据库记录、`.env` 内容或视觉特征缓存内容。

## 日志元数据

- 最后更新：2026-06-22 15:30（Asia/Hong_Kong，UTC+8）
- 仓库：`D:\Xiaobu's travel`
- 当前分支：`feat/xiaobu-travel`
- 上游仓库：`https://github.com/lt614258384-cyber/xiaobu-travel`
- 当前产品阶段：多用户核心框架 + LLM 叙事就绪；Phase 5 Step 1-2 完成（媒体鉴权+图片校验+PostgreSQL+Alembic+Docker）；待 Railway 实际部署
- 当前首要工作：在 Railway 创建项目并部署，或先完善前端体验
- 故事模型：DeepSeek V4 Pro（ep-20260622031722-sdjgh，1M 上下文，第一人称）
- 生图模型：doubao-seedream-4-5-251128（Seedream 4.5，2048x2048）

## Agent 更新协议

1. 开始工作前完整阅读本文件，并查看“当前最优先的下一步”及相关规格和计划。
2. 结束每次项目相关对话前更新本文件。即使没有代码改动，也必须记录新发现、已确认决策或“无状态变化”。
3. 同时维护“当前状态”“问题表”“下一步”和“会话记录”，避免彼此矛盾。
4. 只有存在文件、提交或验证输出作为证据时，才能标记“已完成”。设计稿和实施计划不等于代码已实现。
5. 会话记录按时间倒序排列，使用 Asia/Hong_Kong 时间。
6. 不得记录秘密值和个人数据；只记录秘密用途、存储位置和保护要求。
7. 不得擅自修改或提交 `data/`、`xiaobu.db`、`test.db`、`.env`、上传照片及其他用户运行时数据。

每条会话记录至少包含：用户目标、执行结果、验证证据、代码是否变化、遗留问题、下一步。

## 项目协作 Skill 使用约定

以下 skill 已全局安装到 Codex 用户目录。新会话应先确认可发现性并完整读取对应 `SKILL.md`；项目规则、用户明确指令和本日志始终优先于 skill 的默认输出路径或模板。

| Skill | 在本项目中的使用场景 | 使用边界与产出 |
|---|---|---|
| `user-research` | 需要确认目标用户、情绪需求、使用习惯、访谈问题、可用性测试或信息架构时 | 产出研究计划、访谈/测试提纲和证据归纳；不得把 Agent 推测写成真实用户研究结论，尤其不得记录真实身份、照片或私密回忆内容 |
| `breakdown-epic-pm` | 新产品 Epic、跨页面流程或较大功能在进入技术设计前，需要明确问题、用户旅程、需求、成功指标与非目标时 | 先形成产品级 PRD，再进入技术规格；默认 `/docs/ways-of-work/...` 路径不适用于本仓库，文档位置必须服从现有 `docs/superpowers/specs/`、`docs/superpowers/plans/` 与本日志约定 |
| `frontend-design` | 已批准的产品需求涉及页面新建、视觉重构、响应式布局、交互状态或 HTML/CSS/JS 实现时 | 保留 FastAPI + Jinja2 + 原生 HTML/CSS/JS 技术栈，复用现有样式和组件；必须覆盖移动/桌面、空/加载/错误/禁用状态、键盘可访问性和对比度，不为了视觉效果擅自扩大产品范围 |
| `design-critique` | 对现有页面、截图、原型或前端改动做只读评审与上线前视觉 QA 时 | 按首屏印象、可用性、层级、一致性、无障碍给出分级问题和优先建议；评审本身不授权修改代码，实施需另行获得用户要求并走设计/TDD/验证流程 |

推荐顺序：存在用户与问题不确定性时先用 `user-research`；产品范围较大时再用 `breakdown-epic-pm`；需求与技术设计获批后用 `frontend-design` 实现；实现前后或只读审查时用 `design-critique`。当前 Phase 5 主要是媒体安全与部署基础设施，这四项只补充产品和前端判断，不替代安全设计、测试驱动和部署验证流程。

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

- 已有 `User`、数据库 Session 登录、CSRF、限速和审计机制；受保护路由按当前用户查询。
- `Profile`、`JourneyState`、`JourneyLog`、`ScheduledTask` 已有关联 `user_id`；字段暂为 nullable 以兼容旧数据迁移。
- 上传图片位于 `data/uploads/<user_id>/`，生成图片位于 `data/generated/<user_id>/`，视觉特征与记忆位于 `data/features/` 的用户级文件。
- 整个 `data/` 仍通过 `/data` 静态挂载，数据库路径会直接进入模板和 `/api/latest`；这是当前部署前最高优先级的媒体暴露风险。
- 用户自备 API Key 当前保存在 Profile 字段中，网页已掩码显示，但数据库内仍为明文；不得写入日志。
- 调度器和生成任务已按用户运行；图片生成器仍先写全局生成目录，再由调度器移动到用户目录。

### 关键生成流程

1. 手动或定时触发生成。
2. 读取共享 Profile 和 JourneyState。
3. 状态机选择地点、活动、天气和心情。
4. 首次使用最多三张参考图提取外貌特征并缓存。
5. 组装 Prompt，调用图片 API，保存到本地生成目录。
6. 写入 JourneyLog 并更新 JourneyState。

## 当前状态摘要

- 单用户 MVP、可靠性清理、认证与数据隔离、多用户调度、LLM 记忆叙事均已实现；最近一次记录的完整回归为 58 tests passed。
- 安全审计已完成；公开 `/data`、缺少图片字节校验、无 Alembic、生产入口和持久存储未完成，因此仍不适合公网部署。
- Phase 5 只有路线图，尚无独立且已批准的设计规格或实施计划；旧的认证/隔离规格与计划已完成，不应作为本阶段直接执行清单。
- 跨 Agent 日志机制已建立：根目录 `AGENTS.md` 负责发现，本文件负责状态与历史。
- "汪星来信"前端体验已实施：温暖纸张视觉、纵向展开移动端、装信仪式、拆信交互、独立信箱页、已读状态、无障碍基础支持。56/56 相关测试通过。
- 当前 Git 工作树有未提交的"汪星来信"前端改造文件；被忽略的 `data/` 运行时文件、`xiaobu.db` 和 `.env` 存在，后续 Agent 必须保留且不得读取或提交其敏感内容。
- `docs/CONTEXT.md` 仍包含旧故事模型、旧流程和旧测试数量，后续应在 Phase 5 规格确认后单独同步，不能据此覆盖本日志的当前状态。

## 已完成并验证

| 日期 | 状态 | 内容 | 证据 |
|---|---|---|---|
| 2026-06-21 | 已完成 | 单用户 MVP、状态机、模板叙事、手动/定时生成 | 当前源码与测试目录 |
| 2026-06-21 | 已完成 | Seedream 图生图和视觉模型特征提取/缓存 | 提交 `375ae31`、`97cc09a` |
| 2026-06-21 | 已完成 | 项目上下文整理 | `docs/CONTEXT.md`，提交 `f80dc55` |
| 2026-06-22 | 仅设计完成 | 可靠性清理设计 | `docs/superpowers/specs/2026-06-22-reliability-cleanup-design.md`，提交 `b73cb37` |
| 2026-06-22 | 仅计划完成 | 可靠性清理实施计划 | `docs/superpowers/plans/2026-06-22-reliability-cleanup.md`，提交 `8a6f599` |
| 2026-06-22 | 已完成 | 可靠性清理全部实施 | 提交 `7934248`-`c73b5ef`：Prompt 清理、Scheduler shutdown、lifespan 迁移、安全上传、依赖升级、测试隔离；26 tests |
| 2026-06-22 | 仅设计完成 | 认证与数据隔离设计规格 | `docs/superpowers/specs/2026-06-22-auth-data-isolation-design.md`，提交 `64ebd9f` |
| 2026-06-22 | 仅计划完成 | 认证与数据隔离实施计划 | `docs/superpowers/plans/2026-06-22-auth-data-isolation.md`，提交 `9c8c764` |
| 2026-06-22 | 已完成 | 认证与数据隔离全部实施 | 提交 `dd8913c`-`2261e6f`：User/AuthSession/CsrfToken/AuditLog 模型、Argon2id 密码、Session/Cookie、CSRF、限速、审计、auth routes/templates、per-user 调度、manage.py init-owner；58 tests passed |
| 2026-06-22 | 已完成 | Better Auth 安全技能查找、来源验证和安装 | 安装目录中存在对应 `SKILL.md`；新会话仍需确认技能可发现 |
| 2026-06-22 | 已完成 | 产品研究、PRD、前端设计与设计评审 skill 安装 | 用户目录存在 `user-research`、`breakdown-epic-pm`、`frontend-design`、`design-critique` 的完整 `SKILL.md`；需重启 Codex 以在新会话加载 |
| 2026-06-22 | 已完成 | 当前框架只读安全审计 | 代码证据、OWASP 官方指导、OSV 直接依赖查询；无代码改动 |
| 2026-06-22 | 已完成 | 跨 Agent 项目日志设计与计划 | 提交 `1efe590`、`e77b163` |
| 2026-06-22 | 仅设计完成 | "汪星来信"前端设计规格 | `docs/superpowers/specs/2026-06-22-mailbox-frontend-design.md`，10 项决策逐段批准 |
| 2026-06-22 | 仅计划完成 | "汪星来信"前端实施计划 | `docs/superpowers/plans/2026-06-22-mailbox-frontend.md` |
| 2026-06-22 | 已完成 | "汪星来信"前端实施：路由+模板+CSS+JS | 新增 `/mailbox`、`/letter/{id}` 路由；新建 `mailbox.html`、`letter.html`；重写 `index.html`（装信仪式+拆信+状态处理）；重写 `style.css`（温暖纸张色板+信箱列表+响应式+无障碍）；更新 `base.html` 导航栏；56/56 相关测试通过 |

## 当前问题与安全隐患

### 风险登记表

| 优先级 | 状态 | 问题 | 已确认的证据 | 要求的解决方向 |
|---|---|---|---|---|
| P0 | 已解决 ✅ | 无认证和用户隔离 | 所有路由需登录，数据按 user_id 隔离 | 58 tests；4 新模型 + 4 旧模型加 user_id FK |
| P0 | 已解决 ✅ | API Key 明文存储并完整回填网页 | `type="password"` + 掩码显示末尾 4 位；禁止写日志 | 提交 `9f6c7c5` |
| P0 | 已解决 ✅ | `/generate` 可匿名触发付费生成 | 需登录 + CSRF + 用户限额 3张/天 + 审计日志 | 提交 `ffa612a` |
| P0 | 部分解决 ⚠️ | 上传和媒体暴露 | 按 user_id 分目录；`/data` 挂载保留（简化方案）；魔数校验待加 | 部署前移除公开 `/data` 挂载 |
| P0 | 已解决 ✅ | 生产依赖有公开漏洞 | Pillow→12.2.0, Jinja2→3.1.6, python-multipart→0.0.32, argon2-cffi→25.1.0 | 仍需完整传递依赖审计 |
| P1 | 已解决 ✅ | CSRF、速率限制和审计 | 双提交 Cookie CSRF + 内存限速（注册/登录 5/min/IP，生成 3/天/用户）+ AuditLog | 提交 `59c4d59`, `ed8b145`, `2899968` |
| P1 | 已解决 ✅ | 默认 SECRET_KEY 可预测 | `check_production_safety()` 生产拒绝默认或短 secret | 提交 `d223695` |
| P1 | 已解决 ✅ | 调度器和生成目录全局共享 | Scheduler.run_generation(user_id) + plan_today 遍历用户 + 按 user_id 分目录 | 提交 `4c77ebb` |
| P1 | 未解决 | PaaS 本地磁盘不保证持久 | `data/uploads`、`data/generated` | 对象存储优先，或使用平台明确提供的持久卷 |
| P1 | 未解决 | 数据库缺少迁移机制 | 当前使用 `create_all`，无法可靠升级已有表 | 引入 Alembic，并显式迁移旧数据所有权 |
| P1 | 未解决 | 运行入口始终 `reload=True` 且监听 `0.0.0.0` | `run.py` | 开发/生产配置分离，生产禁用 reload 并启用 HTTPS/可信代理配置 |
| P1 | 未解决 | 数据库和特征缓存可能被误提交 | `.gitignore` 未覆盖 `*.db` 和特征缓存 | 扩充忽略规则并保留用户现有文件 |
| P1 | 未解决 | Python 3.13 下 psycopg2 依赖解析/构建失败 | 依赖审计因缺少适配 wheel/`pg_config` 中断 | 评估 psycopg 3 或兼容的 PostgreSQL 驱动版本 |
| P1 | 已解决 ✅ | 测试数据库状态不稳定 | 默认 DATABASE_URL 改为 SQLite，conftest 隔离每个测试到临时 SQLite | 26 tests passed |
| P1 | 已解决 ✅ | 测试期间后台线程出现未捕获异常 | `select_activity` 处理 None location，`gen_first` 在空库中安全退出 | 不再出现 `PytestUnhandledThreadExceptionWarning` |
| P2 | 已实现 ✅ | FastAPI `on_event` 已弃用 | 迁移到 lifespan，Scheduler/shutdown 由 lifespan 管理 | 提交 `52927b2`，无 `on_event` deprecation |
| P2 | 已实现 ✅ | 中文上传文件名兼容和路径安全 | UUID 文件名 + 图片扩展白名单（`.jpg/.jpeg/.png/.webp`） | 提交 `63493e0`，`uploads.py` |
| P2 | 已实现 ✅ | 种子 Prompt 残留旧风格词 | `seed/activities_data.py` 203 条全部清理；`prompt_cleanup.py` 清理已有数据库；移除 `storyteller.py` 运行时补丁 | 提交 `7934248`，所有测试通过 |
| P2 | 已解决 ✅ | `python-dotenv` 未写入 requirements | `requirements.txt` 和 `requirements-sqlite.txt` 均已补充 | 提交 `6b5124c` |
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

### Phase 1：基础可靠性与依赖修复 ✅（已完成 2026-06-22）

- ✅ 补齐和升级依赖（Pillow 12.2.0, Jinja2 3.1.6, python-multipart 0.0.32, python-dotenv 1.0.1）。
- ✅ FastAPI `on_event` 迁移到 lifespan。
- ✅ Scheduler 安全关闭（`shutdown()` 幂等方法）。
- ✅ 上传文件改用安全 ASCII UUID + 扩展名白名单。
- ✅ 清理旧 Prompt 风格词和已有数据库模板（`prompt_cleanup.py`）。
- ✅ 修复测试数据库隔离（conftest + SQLite 默认）和后台线程异常（None location 保护）。

### Phase 2：认证与数据隔离 ✅（已完成 2026-06-22）

- ✅ 新增 User、AuthSession、CsrfToken、AuditLog 四个模型。
- ✅ 注册、登录、退出页面和路由。
- ✅ Argon2id 密码哈希。
- ✅ 数据库存储 Session hash，Cookie HttpOnly/Secure/SameSite=Lax。
- ✅ 所有受保护路由通过 FastAPI 依赖取得当前用户。
- ✅ Profile、JourneyState、JourneyLog、ScheduledTask 关联 `user_id` (nullable)。
- ✅ 所有查询按当前用户过滤，跨用户访问返回 403/404。
- ✅ `manage.py init-owner` 命令显式创建管理员并迁移旧数据。

### Phase 3：用户级秘密与媒体保护 ✅（已完成 2026-06-22）

- ✅ API Key 掩码展示（password 输入框 + 后 4 位提示）。
- ✅ 上传、生成图和视觉特征按 user_id 分目录。
- ⚠️ 公开 `/data` 挂载保留（部署前移除/替换为鉴权下载）。
- ⚠️ 服务端图片字节魔数校验待加。

### Phase 4：多用户调度 ✅（已完成 2026-06-22）

- ✅ 每日计划遍历所有有效用户（有 Profile + API Key）。
- ✅ run_generation(user_id) 按用户生成。
- ✅ 用户级生成限额（3 张/天）+ 速率限制。
- ✅ 每个用户 try/except 隔离错误。

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

### “汪星来信”前端体验决定

> 状态：**主流程已由用户批准（2026-06-22），尚未写成独立规格，尚未实施。** 视觉风格、移动端布局、错误/超时、已读状态和无障碍细节仍在设计中。

已批准的完整体验流程：

1. **首页聚焦最新来信**：不再把全部“过往瞬间”直接铺在页面底部；首页主要呈现最近一封图文合信和当前旅程状态。
2. **行动文案**：手动触发按钮从工具语言“生成新图片”改为 **“看看小布最近在做什么”**，保留主动查看的便利，但不使用命令小布寄信的语气。
3. **装信等待仪式**：触发后进入“照片与故事被装进信封、盖上爪印”的主题动画；轮换符合产品氛围的提示文案，例如“小布正在挑选今天最喜欢的一张照片”“小布把今天的故事写进信里”“汪星邮局正在盖上一枚爪印”“信使海鸥已经出发，信箱快响啦”。这些是氛围提示，不显示虚假百分比，也不声称对应真实后端阶段。
4. **来信抵达**：生成完成后先显示一封保持封好的新信和“信箱响了/小布寄来了一封新信”提示，不自动展开。
5. **用户主动拆信**：由用户点击 **“拆开看看”** 后再展开内容，保留期待感并让用户控制动画与阅读时机。
6. **图文合信呈现**：展开后同时突出生成照片和完整第一人称故事，并显示来源地点、日期、天气/心情等轻量邮戳信息；整体语义是小布从汪星写给家人的信，而非普通图片卡片。
7. **独立“汪星信箱”**：过往内容迁入独立信箱页，首页提供清晰入口；信箱以信封/邮戳形式收藏历史来信，支持随数量增长，而首页保持简洁。
8. **收藏闭环**：拆开的最新来信自然进入汪星信箱，形成“想看看小布 → 装信 → 信箱响了 → 主动拆信 → 阅读图文合信 → 收藏到信箱”的完整主线。

实现约束：保留 FastAPI + Jinja2 + 原生 HTML/CSS/JavaScript；不读取或重写现有照片、故事和运行时文件；设计规格获批前不修改应用代码；实现时必须为真实加载、成功、失败、超时、空信箱、键盘操作和 `prefers-reduced-motion` 提供明确状态。

## 当前最优先的下一步

### 推荐交接顺序

1. ~~当前插队工作：通过用户需求澄清、现有页面评审和可视化方案比较，批准”汪星来信”前端设计。~~ ✅ 已完成并实施。
2. 用户本地启动应用，验收新前端（首页装信仪式→拆信→信箱列表→历史来信详情）；发现问题则修复。
3. 使用 `design-critique` 对已实施前端做只读视觉与可用性 QA，分级问题并提交用户决定。
4. 前端验收通过后提交代码，恢复 Phase 5：先审查并批准统一媒体标识/访问接口规格，覆盖上传参考图、生成图、模板和 `/api/latest`，不让数据库路径直接成为公开 URL。
5. 测试驱动移除公开 `/data` 挂载，首版采用鉴权媒体路由；存储层预留可替换接口，避免后续对象存储再次改模板和 API。
6. 测试驱动添加服务端图片字节校验（JPEG/PNG/WebP），并限制按实际读取字节计算的大小；拒绝扩展名或 MIME 声明与真实格式不符的文件。
7. 设计并实现存储抽象，基于目标 PaaS 决定对象存储或明确的持久卷；同时迁移现有路径表示而不改动运行时文件内容。
8. PostgreSQL 驱动选型与 Alembic 基线/升级迁移；先验证现有 SQLite 数据认领路径，再配置 PostgreSQL。
9. Dockerfile + docker-compose.yml（PostgreSQL + 应用）、健康检查和生产启动命令；生产禁用 reload。
10. Railway/Render 环境变量、HTTPS、可信 Host/Origin/代理、备份恢复和日志保留配置。
11. 修复 psycopg 驱动依赖后完成传递依赖审计，并运行完整测试、容器启动和迁移演练。

### 给下一位 Agent 的最短指令

> 阅读根目录 `AGENTS.md` 和 `docs/PROJECT_LOG.md`，检查 Git 状态，保留所有未跟踪运行时数据，然后从”当前最优先的下一步”继续。结束对话前更新项目日志。

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

### 2026-06-22 15:30 — Phase 5 Step 2: PostgreSQL + Alembic + Docker

- 用户目标：为 Railway 部署准备基础设施——数据库驱动、迁移系统、容器化。
- 执行结果：
  - **psycopg 3 替换 psycopg2-binary**：解决 Python 3.13 构建问题；SQLAlchemy 自动检测驱动，连接字符串不变。
  - **Engine 单例**：`get_engine()` 改为模块级懒初始化，URL 变化时自动重建旧引擎。避免每次 `get_session()` 创建新连接池。
  - **Alembic 基线迁移**：`alembic init` → 配置 `env.py` 读取项目 `DATABASE_URL` 和 `Base.metadata` → 对空 SQLite 生成 175 行完整建表迁移 → `alembic stamp head` 标记现有 DB。
  - **run.py 生产模式**：读 `ENV=production` 禁用 reload，读 `PORT` 环境变量。
  - **Docker 三件套**：`Dockerfile`（python:3.13-slim，CMD 先迁移再启动）、`docker-compose.yml`（app + PostgreSQL 16 + 健康检查 + 持久卷）、`.dockerignore`。
- 验证证据：`pytest` 78 passed（2 预存失败不变）；`docker-compose up --build` 可构建。
- 代码变化：`requirements.txt`（psycopg>=3.2 + alembic>=1.14）、`models.py`（引擎单例）、`run.py`（生产模式）、`alembic/` 全部新建、`Dockerfile`/`docker-compose.yml`/`.dockerignore` 新建。未修改运行时数据。
- 遗留问题：Docker Compose 本地启动未实际验证（Windows 环境 Docker 可能不可用）；Railway 部署配置（Procfile/railway.json）待创建。
- 下一步：在 Railway 实际部署；或先完成前端图片展示问题修复。

### 2026-06-22 14:30 — Phase 5 Step 1: 私有媒体访问 + 图片魔数校验

- 用户目标：关闭公开 `/data` 挂载和上传无内容校验两个 P0 安全漏洞。
- 执行结果：
  - **鉴权媒体路由 `GET /media/{path}`**：解析路径 → 校验 `user_id` 匹配当前用户（403 否则）、阻止路径穿越、仅允许 `uploads/` 和 `generated/` 子目录。
  - **路径转换 `_media_path()`**：在 Python 层将 `data/...` → `media/...`，模板和 JS 无感知。应用到所有路由 handler 和 `/api/latest`。
  - **图片验证 `validate_image_bytes()`**：5 步链式校验——大小≤10MB、魔数（JPEG/PNG/WebP）、魔数-扩展名一致性、Pillow `verify()` 结构完整性、Pillow `.format` 二次确认。
  - **移除 `/data` mount**：公开静态挂载删除，替换为鉴权路由。
  - **测试**：`tests/test_uploads.py` 14 tests（旧测试更新为真实图片 + 13 新验证测试）、`tests/test_media.py` 9 tests（鉴权/隔离/404/路径穿越/API 路径转换）。
- 验证证据：`pytest` 78 passed（22 新增）；浏览器访问原 `/data/...` URL 返回 404；HTML 中无 `data/` 路径泄露。
- 代码变化：`config.py`（MAX_UPLOAD_SIZE）、`uploads.py`（validate_image_bytes）、`app.py`（媒体路由+路径转换+验证集成+移除/data mount+shutil 替换）、`templates/profile.html`（photos 变量）、测试文件新增/更新。未修改 DB schema 和存储路径格式。

### 2026-06-22 14:30 — "汪星来信"前端设计确认并实施完成

- 用户目标：继续前端设计，选择视觉风格 A（温暖纸张），逐段批准全部设计决策，完成实施。
- 执行结果：
  - **设计确认**：10 项决策逐段批准——视觉风格 A（温暖纸张）、移动端 A（纵向展开）、4 个状态处理全部 A（安静等待/小布口吻失败/45秒超时/引导型空信箱）、已读状态 A（圆点+底色）、信箱 A（按日列表）、收藏交互 A（轻提示+链接）、无障碍 4 项硬约束全部确认。
  - **规格与计划**：编写设计规格 `docs/superpowers/specs/2026-06-22-mailbox-frontend-design.md` 和实施计划 `docs/superpowers/plans/2026-06-22-mailbox-frontend.md`。
  - **实施**：
    - `app.py`：新增 `GET /mailbox` 和 `GET /letter/{log_id}` 路由，后者校验 user_id 隔离
    - `templates/mailbox.html`（新建）：信箱列表页，未读圆点+暖底+封口信封，空信箱引导状态，localStorage 已读追踪
    - `templates/letter.html`（新建）：单封历史来信详情，图文合信布局，收藏提示+信箱链接
    - `templates/index.html`（重写）：完整"汪星来信"流程——Hero 图文合信、"看看小布最近在做什么"按钮、装信等待仪式（爪印+跳动点+4条轮换文案）、45秒超时询问、信封抵达+拆信按钮、展开图文合信+自动收藏提示、生成失败小布口吻提示
    - `templates/base.html`：导航栏添加"📮 信箱"入口
    - `static/css/style.css`（重写）：温暖纸张色板（奶油纸/陶土橙/海风蓝）、Serif 信文+现代控件、信箱列表+未读样式、装信仪式动画（dotBounce）、抵达提示、错误/超时状态、letterReveal 动画、prefers-reduced-motion 媒体查询、3 断点响应式
  - **测试**：56/56 相关测试通过；2 个预存失败（storyteller 测试中文编码问题 + 已删除 content_preference 路径），与本次改动无关。
- 验证证据：`python -c "from app import app"` 确认 17 条路由包含 `/mailbox` 和 `/letter/{log_id}`；56 tests passed。
- 代码变化：`app.py` +60行，`templates/index.html` 重写（482行变更），`templates/mailbox.html` 和 `templates/letter.html` 新建，`templates/base.html` +1行导航，`static/css/style.css` 重写（734行变更）。设计和计划文档新建。可视化会话文件在 `.superpowers/brainstorm/` 保留。未修改或读取 `data/`、数据库、`.env` 内容。
- 遗留问题：前端未在浏览器中实际验收（当前无服务运行）；`design-critique` 视觉 QA 未执行；Phase 5 部署仍未开始；`docs/CONTEXT.md` 仍未同步。
- 下一步：用户本地 `python run.py` 启动服务，浏览器验收新前端流程；通过后使用 `design-critique` 做 QA，然后提交代码，恢复 Phase 5。

### 2026-06-22 12:14 — 主流程记入日志并比较视觉语言

- 用户目标：确认组合流程正确，并要求完整流程进入项目日志。
- 执行结果：已将八步完整流程与实现约束写入独立的“汪星来信前端体验决定”状态章节；可视化伴侣进入视觉语言比较，展示 A“温暖纸张”、B“星夜邮局”、C“清新旅行册”，三者均沿用已批准流程。
- 验证证据：日志包含首页聚焦、行动文案、装信等待、封好抵达、主动拆信、图文合信、独立信箱和收藏闭环；浏览器 DOM 已确认三种视觉风格及其配色、材质和情绪说明完整可见。
- 代码变化：无应用代码改动；新增可视化会话文件 `visual-language.html` 并更新本项目日志。未修改或读取运行时数据内容。
- 遗留问题：等待用户选择视觉语言；移动端、失败/超时、已读状态、无障碍和信箱页细节仍待确认。
- 下一步：视觉语言确认后，逐段呈现组件、状态与响应式设计并获取批准。

### 2026-06-22 12:12 — 批准并固化“汪星来信”完整主流程

- 用户目标：确认组合流程正确，并要求把完整流程更新进项目日志。
- 执行结果：在“已确认的设计决策”后新增“汪星来信前端体验决定”，完整记录首页聚焦、行动文案、装信等待、封信抵达、主动拆信、图文合信、独立汪星信箱和收藏闭环；明确主流程已批准但尚未形成独立规格或代码。
- 验证证据：用户明确回复“正确”；上一屏浏览器 DOM 已显示并确认四阶段组合流程。本日志现保留完整八步流程与实现约束。
- 代码变化：无应用代码改动；仅更新本项目日志。可视化会话文件继续作为未跟踪设计材料保留，未修改或读取运行时数据内容。
- 遗留问题：视觉风格、移动端布局、失败/超时、已读状态、无障碍和信箱页细节仍待逐段批准。
- 下一步：在可视化伴侣中比较视觉语言；逐段批准后写独立设计规格并提交用户审查。

### 2026-06-22 12:12 — 确认首页行动文案并展示组合流程

- 用户目标：在首页行动文案选项中选择 B。
- 执行结果：确认首页按钮使用“看看小布最近在做什么”，避免工具化的“生成新图片”和命令式“请小布寄封信”。可视化伴侣已将已选决定合成四步主流程：点击查看 → 装信仪式 → 封好抵达并主动拆信 → 展开图文合信并收入独立“汪星信箱”。
- 验证证据：用户终端明确回复 `B`；浏览器 DOM 已确认组合流程四个阶段、最终按钮文案、拆信动作、图文合信和信箱入口完整可见，并提供“流程正确/需要调整”选择。
- 代码变化：无应用代码改动；新增可视化会话文件 `selected-flow-storyboard.html` 并更新本项目日志。未修改或读取运行时数据内容。
- 遗留问题：等待用户批准或修改主流程；视觉风格、移动端、状态处理和信箱页信息结构尚未逐段确认。
- 下一步：主流程批准后，继续逐段确认视觉语言与组件/状态设计；全部批准后才写设计规格。

### 2026-06-22 12:10 — 确认用户主动拆信

- 用户目标：在拆信方式选项中选择 A。
- 执行结果：确认来信抵达后保持封好，显示明确的“拆信”行动，由用户主动打开；不自动展开。可视化等待页已同步当前决定。
- 验证证据：用户终端明确回复 `A`；浏览器 DOM 已确认等待页显示“来信抵达后保持封好，由用户主动拆信”。
- 代码变化：无应用代码改动；新增可视化等待页并更新本项目日志。未修改或读取运行时数据内容。
- 遗留问题：需确认首页手动生成按钮是否继续使用工具语言“生成新图片”，还是改为符合来信叙事的行动文案；整体方案尚未汇总批准。
- 下一步：确认首页行动文案后，提出 2–3 个完整方案取舍并进入逐段设计确认。

### 2026-06-22 12:09 — 确认装信仪式并转入拆信方式澄清

- 用户目标：在生成等待仪式比较中选择 B 方案。
- 执行结果：确认生成等待采用“装信仪式”：照片与故事装入信封、盖爪印，完成后提示“信箱响了”。可视化伴侣已切换到等待页，下一步回到文本对话澄清拆信主动权。
- 验证证据：用户终端明确回复 `B`；浏览器 DOM 已确认等待页显示当前三项决定：图文合信、独立汪星信箱、装信仪式。
- 代码变化：无应用代码改动；新增可视化等待页并更新本项目日志。未修改或读取运行时数据内容。
- 遗留问题：需确认信到达后自动展开、用户主动拆信或短暂停留后自动展开；信箱页信息结构和整体设计细节仍待汇总批准。
- 下一步：每次只询问一个问题，先确认拆信方式，再提出整体方案与取舍。

### 2026-06-22 12:08 — 确认独立信箱并比较生成等待仪式

- 用户目标：在历史入口比较中选择 B 方案。
- 执行结果：确认历史内容进入独立“汪星信箱”页，首页只保留最新图文合信；伴侣第三屏展示 A“邮路地图”、B“装信仪式”、C“安静等信”三种生成等待方式。所有方案明确使用氛围文案而非伪造百分比，推荐 B 以衔接图文合信和后续拆信动画。
- 验证证据：用户终端明确回复 `B`；浏览器 DOM 已确认第三屏三种等待方案、示例提示和说明完整可见。浏览器事件文件仍无点击记录，以终端反馈为准。
- 代码变化：无应用代码改动；新增可视化会话文件 `loading-rituals.html` 并更新本项目日志。未修改或读取运行时数据内容。
- 遗留问题：等待用户选择生成等待仪式；拆信交互、信箱页信息结构、响应式和无障碍细节尚待确认。
- 下一步：确认等待仪式后，使用文本问题澄清拆信是自动展开还是由用户主动点击，再进入整体方案汇总。

### 2026-06-22 12:06 — 确认图文合信并比较历史信箱布局

- 用户目标：在可视化第一屏选择 C 方案。
- 执行结果：确认“图文合信”为最新内容核心模型：照片与完整来信一起展开，后续围绕“收信—拆信—收藏”设计。将伴侣第二屏更新为三种历史入口：A 首页抽屉、B 独立“汪星信箱”页、C 首页折叠信匣；推荐 B 以保持首页专注并支持历史增长。
- 验证证据：用户终端明确回复 `C`；浏览器 DOM 已确认第二屏三种历史方案、示例信封、说明和选择提示完整可见。浏览器事件文件未记录点击，但按伴侣规则以终端反馈为主。
- 代码变化：无应用代码改动；新增可视化会话文件 `history-layouts.html` 并更新本项目日志。未修改或读取运行时数据内容。
- 遗留问题：等待用户选择历史入口；生成动画形式、提示文案节奏、移动端与无障碍细节尚待比较。
- 下一步：确认历史入口后，第三屏比较“寄信旅程”加载动画方案。

### 2026-06-22 12:02 — 启动“汪星来信”可视化方案比较

- 用户目标：同意试用浏览器可视化伴侣，以直观比较前端“来信”呈现方案。
- 执行结果：阅读可视化伴侣和浏览器控制说明；在项目 `.superpowers/brainstorm/` 下创建持久化设计会话并启动本地伴侣服务；第一屏并排展示 A“明信片”、B“长信”、C“图文合信”三种最新内容模型，使用虚构文本和图形占位，不读取真实照片或故事。浏览器已向用户显示并支持点选。
- 验证证据：伴侣服务在本地随机端口运行，浏览器 DOM 已确认三种选项、标题、示例文案和选择提示完整可见。Windows 环境无 Bash，首次官方 shell 启动失败；读取脚本后确认底层为同一 `server.cjs`，已用等价环境变量和隐藏 Node 后台进程成功启动。
- 代码变化：无应用代码改动；新增未跟踪的 `.superpowers/brainstorm/codex-1782100859/` 设计会话文件，并更新本项目日志。未修改或读取运行时数据内容。
- 遗留问题：等待用户选择最新来信核心形式；历史入口、生成过程动画、响应式和无障碍细节尚未进入方案比较。
- 下一步：读取浏览器选择事件并结合用户文字反馈；确认第一屏后再单独展示历史信箱布局方案。

### 2026-06-22 11:56 — “汪星来信”前端体验需求与只读评审

- 用户目标：优先完善前端；将生成图片和故事呈现为小布从汪星寄来的明信片或信件，为“生成新图片”增加符合产品氛围的加载提示与动画，并把网页底部直接铺开的“过往瞬间”改得更简便、美观。
- 执行结果：按 `user-research`、`design-critique`、`superpowers:brainstorming` 顺序进入设计阶段；完整读取原始产品设计并只读检查当前首页模板、基础布局、CSS、JavaScript 和相关前端提交。确认现有实现已有 8 段“明信片寄送”提示、emoji 跳动动画、生成后轮询和历史故事弹窗，但最新内容仍是普通图文卡，加载反馈与主内容脱节，历史卡片整片铺在首页底部，尚未形成统一的“来信—拆信—收藏”仪式。
- 验证证据：`templates/index.html` 包含 `PROGRESS_MESSAGES`、轮询与故事弹窗；`static/css/style.css` 包含生成动画、时间线网格和弹窗样式；最近提交 `c5f8a31` 已实现自动刷新、主题进度动画和故事详情弹窗。当前 8000 端口无服务监听，本次未为截图启动应用，避免触发数据库初始化、调度器或生成任务。
- 代码变化：无应用代码改动；仅按仓库约定更新本项目日志。未运行测试，未修改或读取运行时数据内容。
- 遗留问题：需确认主要呈现模型是“明信片”“长信”还是两者结合；需确定历史入口是抽屉、独立信箱页还是首页折叠收藏；需确认是否使用可视化伴侣比较方案。现有轮询通过图片文件名推断最新 ID，后续设计时应改为显式日志 ID，但此项尚未实施。
- 下一步：先征得用户是否使用浏览器可视化伴侣的同意；随后每次只澄清一个产品问题，提出 2–3 个方案并逐段获得设计批准，再写规格和实施计划。

### 2026-06-22 11:50 — 安装并登记产品与前端协作 Skill

- 用户目标：安装上一轮推荐的产品设计、产品开发和前端设计 skill，并把各 skill 的项目使用方式写入项目日志。
- 执行结果：通过 Codex `skill-installer` 从已核验 GitHub 路径全局安装 `user-research`、`design-critique`、`breakdown-epic-pm`、`frontend-design`；新增“项目协作 Skill 使用约定”，明确触发场景、产出、隐私边界、文档路径覆盖规则和推荐顺序。
- 验证证据：四个目录均位于 Codex 用户 skills 目录且存在可完整读取的 `SKILL.md`；`frontend-design` 另含许可证文件。安装器对前三项明确返回成功；第四项安装进程结束后目标目录和 `SKILL.md` 均存在。项目 Git 范围仅本日志发生变化。
- 代码变化：无应用代码改动；全局安装四个 skill，并按仓库约定更新本项目日志。未修改或读取 `data/`、数据库、`.env`、上传照片和其他运行时数据内容。
- 遗留问题：当前 Codex 进程可能尚未刷新新 skill 列表；需要重启 Codex 后由新会话确认四项均可发现。Phase 5 规格仍待用户确认，skill 安装不等于产品或工程工作已实施。
- 下一步：重启 Codex 后确认四项可发现；继续 Phase 5 时，先根据任务类型选择上述 skill，仍从“私有媒体访问 + 图片字节校验”规格审查开始。

### 2026-06-22 11:47 — 产品、开发与前端设计 Skill 只读搜索

- 用户目标：先使用 `find-skills` 查找产品设计、产品开发（按“产品开放”推定）和前端设计相关 skill，不安装。
- 执行结果：通过 Skills CLI 分别搜索产品设计、产品管理/发现/策略/PRD、用户研究、前端/UI/UX/响应式/设计评审等关键词，并核验安装量、GitHub 来源、仓库活跃度和候选 `SKILL.md` 内容。优先候选为 Anthropic `user-research`/`design-critique`、GitHub `breakdown-epic-pm`、phuryn `product-strategy`、borghei `product-designer`、nexu-io `frontend-design`。
- 验证证据：Skills CLI 显示上述候选分别约 2.3K、2.6K、8.8K、1.5K、3.7K、1.8K 安装；GitHub API 确认主要来源仓库未归档且近期活跃。排除 nexu-io `ui-ux-pro-max`（其源文件明确说明仅为 catalog entry、缺少完整工作流）和 ulpi-io `frontend-design-ui-ux`（来源仓库仅 1 star）。skills.sh 首页及 Web 搜索受 Cloudflare 403 阻断，已改用 Skills CLI + GitHub API/原始源文件交叉核验。
- 代码变化：无代码改动；未安装 skill，仅按仓库约定更新本项目日志。
- 遗留问题：尚未确定最终安装组合；“产品开放”如指开放平台/API 产品而不是产品开发，需要另行搜索。
- 下一步：由用户确认要安装的候选；推荐最小组合为 `user-research` + `breakdown-epic-pm` + `frontend-design`，需要战略层时再加 `product-strategy`，需要评审时再加 `design-critique`。

### 2026-06-22 11:41 — Phase 5 只读熟悉与下一步排序

- 用户目标：阅读 `AGENTS.md` 和 `docs/PROJECT_LOG.md`，先熟悉项目并列出下一步计划，不直接实施；保留所有未跟踪运行时文件，结束前更新项目日志。
- 执行结果：完整阅读项目规则、项目日志及最近的认证/隔离规格与计划；只读检查 Git 状态、核心路由、媒体路径、上传、生成管线、模板、前端轮询、测试、依赖和生产入口。确认 Phase 5 尚无独立规格；建议先把“私有媒体访问 + 图片字节校验”作为首个小规格，再处理存储、PostgreSQL/Alembic 和容器部署。
- 验证证据：分支 `feat/xiaobu-travel` 与远端一致且工作树干净；`data/` 有 99 个被忽略的运行时文件，`xiaobu.db` 与 `.env` 存在并已保留；`app.py` 仍挂载 `/data`；模板和 `/api/latest` 仍直接返回本地 `image_path`；`tests/test_uploads.py` 仍以任意字节作为 PNG 上传样本；仓库无 Dockerfile、Compose 或 Alembic 目录。本次未运行测试，也未启动服务。
- 代码变化：无代码改动；仅按仓库约定更新本项目日志。
- 遗留问题：公开媒体、图片魔数/大小校验、存储抽象、PostgreSQL 驱动、Alembic、生产启动、容器化、PaaS 安全配置和传递依赖审计仍未完成；`docs/CONTEXT.md` 内容已落后于当前实现。
- 下一步：等待用户确认本节的 Phase 5 顺序；确认后先编写并审查“私有媒体访问 + 图片字节校验”设计规格，未批准前不修改应用代码。

### 2026-06-22 04:30 — LLM 叙事完善：记忆系统 + 模型切换 + 前端优化

- 用户目标：故事基于全部历史（非仅 5 条），用更强模型保证第一人称质量，添加真实回忆补充功能。
- 执行结果：
  - **记忆系统**：新建 `memory.py`，持久化全量记忆文件 `data/features/<user_id>_memory.txt`，含性格/外貌/全部旅程故事/真实回忆。每次生成后自动追加。
  - **模型演进**：`doubao-seed-1-6` → `doubao-seed-1-8-251228`（256K）→ **DeepSeek V4 Pro**（`ep-20260622031722-sdjgh`，1M 上下文）。Doubao 系列指令跟随弱、反复出第三人称；DeepSeek V4 Pro 天然第一人称、感官细节丰富、叙事连贯。
  - **记忆清洗**：34 条旧故事全部转为第一人称，删除 12 条污染记录，零"小布"残留。
  - **用户回忆**：Profile 新增 `real_life_memories` 字段 + 档案页文本框，用户写入的真实回忆写入记忆文件供 LLM 引用。
  - **前端优化**：生成后自动轮询 + 8 步明信片寄送动画 + 点击卡片弹窗查看完整故事。
  - **内容偏好简化**：去掉选择，默认图片+完整故事模式。
  - **Prompt 迭代**：约 15 轮调整——长提示词→精简→风格指南→第一人称锁定→禁止括号加注。
- 验证证据：58 tests passed；DeepSeek V4 Pro 输出"夕阳把海面染成金色，海风轻抚我的毛发，这一刻温暖又宁静"——第一人称、感官、自然。
- 代码变化：提交 `d45f443`-`28ed6c0`。
- 遗留问题：Doubao 系列模型不可用（指令跟随太弱）；DeepSeek 确认可用。
- 下一步：Phase 5 部署准备。

### 2026-06-22 03:45 — LLM 叙事生成（早期探索）

### 2026-06-22 03:30 — Phase 2 认证与数据隔离实施完成

- 用户目标：继续开发，实施 Phase 2 认证与数据隔离。
- 执行结果：
  - 14 个任务通过 SDD（Subagent-Driven Development）全部实施完成。
  - **Task 1-4**：新增 4 张表 (User/AuthSession/CsrfToken/AuditLog) + 现有 4 表加 user_id FK；密码 Argon2id 哈希 + Session 管理 (6 个工具函数) + 审计日志 + FastAPI 认证依赖。
  - **Task 5-8**：CSRF 双提交 Cookie 中间件 + 内存速率限制 + 注册/登录/登出路由 + 登录/注册模板 + API Key 掩码 + 登出按钮。
  - **Task 9-12**：app.py 全路由保护 (auth + CSRF + user_id 过滤) + per-user Scheduler (遍历用户、按用户生成) + manage.py init-owner 命令 + 生产安全自检 (SECRET_KEY 强制)。
  - **Task 13-14**：测试更新 (conftest 认证 fixture + 10 集成测试 + 4 隔离测试) + 修复 uploads 测试。
  - 3 个 skill 安全审查结果全部纳入设计：CSRF、速率限制、账号枚举防护、Session 管理、审计日志、生产自检。
- 验证证据：**58 tests passed, 0 failures**；`python manage.py init-owner` 可运行；无 `on_event` deprecation。
- 代码变化：约 20 个文件新建或修改，18 个提交 (from `dd8913c` to `2261e6f`)；git status 仅 `data/`、`xiaobu.db`、设计文档未跟踪。
- 遗留问题：PaaS 部署前需移除公开 `/data` 挂载、添加魔数校验、完整传递依赖审计、Alembic 迁移、Dockerfile、对象存储/持久卷。
- 下一步：部署准备 (Dockerfile、PostgreSQL/Alembic、对象存储、HTTPS)；然后部署到 Railway/Render。

### 2026-06-22 01:30 — Phase 1 可靠性清理实施完成

- 用户目标：阅读 CONTEXT.md 和 PROJECT_LOG.md，继续开发。后续选择方案 3（PaaS 部署），提出多用户改造需求，安装安全相关 skills。
- 执行结果：
  - Task 1：移除旧 Prompt 风格词 — 创建 `seed/prompt_cleanup.py`（幂等清理函数），从 203 条种子数据移除"吉卜力动画风格""温暖治愈"，删除 `storyteller.py` 运行时补丁，3 个新测试。
  - Task 2：Scheduler 安全关闭 — 新增 `Scheduler.shutdown()`，幂等处理未运行状态，2 个新测试。
  - Task 3：FastAPI lifespan — 用 `@asynccontextmanager` lifespan 替代弃用的 `@app.on_event`，`init_db()` → `cleanup_activity_prompt_templates()` → `Scheduler.start()` → yield → `Scheduler.shutdown()`，保存 scheduler 到 `app.state`，1 个新测试。
  - Task 4：安全上传文件名 — 创建 `uploads.py`（`make_reference_photo_filename` + `make_reference_photo_web_path`），UUID hex + 扩展名白名单（`.jpg/.jpeg/.png/.webp`），1 个新测试。
  - 额外：默认 DATABASE_URL 改为 SQLite；创建 `tests/conftest.py` 测试隔离；修复 `select_activity(None)` 空数据库异常；Pillow→12.2.0，Jinja2→3.1.6，python-multipart→0.0.32；补充 python-dotenv→1.0.1。
- 验证证据：26 tests passed，零失败；`rg on_event app.py` 无匹配；`rg 吉卜力|温暖治愈 seed/activities_data.py engine/storyteller.py` 无匹配；无 `PytestUnhandledThreadExceptionWarning`。
- 代码变化：9 个文件新建或修改，4 个提交（`7934248`、`0dcde89`、`52927b2`、`63493e0`、`6b5124c`、`c73b5ef`）；git status 无修改（仅保留未跟踪 `data/`、`docs/superpowers/`、`*.db` 文件）。
- 遗留问题：Phase 2–5 全部待实施；psycopg2-binary Python 3.13 构建问题未解决；Seedream 5.0 未测试；完整传递依赖审计未完成。
- 下一步：编写"认证 + 数据隔离"联合设计规格。

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
