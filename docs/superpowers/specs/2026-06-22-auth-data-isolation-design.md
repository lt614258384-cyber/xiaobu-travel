# 小布的旅行：认证与数据隔离设计规格

> 状态：草稿，待审查
> 日期：2026-06-22
> 依赖：Phase 1 可靠性清理已完成

## 目标

将单用户本地应用改造为多用户 Web 服务。每位用户注册、登录、建立小布档案、查看独立时间线，且数据严格隔离。不改动图片生成引擎，不改动叙事系统，不新增推送功能。

## 范围

- 新增 `User`、`AuthSession`、`CsrfToken`、`AuditLog` 四张表
- 现有 `Profile`、`JourneyState`、`JourneyLog`、`ScheduledTask` 四张表加 `user_id` 非空外键
- 注册 / 登录 / 登出路由和页面
- Cookie-based Session 认证（数据库存储不透明随机 token 的 SHA256 hash）
- Argon2id 密码哈希
- CSRF 双提交 Cookie 保护所有状态修改路由
- 数据库级速率限制
- 账号枚举防护
- 审计日志
- 生产环境启动安全自检
- 旧数据迁移命令 `python manage.py init-owner`
- 按用户隔离上传和生成图片目录

### 非目标

- 密码重置、邮箱验证、OAuth 登录（首版不做）
- Alembic 迁移（本轮不引入）
- 对象存储迁移（继续本地磁盘 + 按 user_id 分目录）
- PostgreSQL 切换（继续 SQLite，生产部署时再切）
- 推送通知
- 角色/权限系统（只有管理员与普通用户两层）

---

## 架构

### 新增与修改的模型（共 11 张表）

```
+-----------+       +------------------+
|   User    |       |   AuthSession    |
+-----------+       +------------------+
| id (PK)   |<──────| user_id (FK)     |
| email     |       | token_hash (SHA256)|
| password  |       | expires_at       |
| pet_name  |       | remember_me (bool)|
| is_admin  |       | user_agent (text)|
| created   |       | created_at       |
+-----------+       +------------------+
       |
       | 1:1
       v
+-----------+       +------------------+       +------------------+
|  Profile  |       |  JourneyState    |       |   JourneyLog     |
| (已有+改) |       |  (已有+改)       |       |   (已有+改)      |
+-----------+       +------------------+       +------------------+
| +user_id  |       | +user_id (FK)    |       | +user_id (FK)    |
| ...原字段 |       | ...原字段        |       | ...原字段        |
+-----------+       +------------------+       +------------------+

+------------+      +-------------------+
| CsrfToken  |      |    AuditLog       |
+------------+      +-------------------+
| id (PK)    |      | id (PK)           |
| session_id |      | user_id (FK,可空)  |
| token_hash |      | event             |
| created_at |      | ip_address        |
| expires_at |      | user_agent        |
+------------+      | details (JSON)    |
                    | created_at        |
+-------------------+                    +-------------------+
|   ScheduledTask   |
|   (已有+改)       |
+-------------------+
| +user_id (FK)     |
| ...原字段         |
+-------------------+
```

### 路由结构

```
认证（无需登录）
GET  /register          → 注册页面
POST /register          → 处理注册
GET  /login             → 登录页面
POST /login             → 处理登录
POST /logout            → 登出

受保护路由（需登录）
GET  /                  → 首页时间线
GET  /profile           → 档案页面
POST /profile           → 保存档案 + 上传照片
POST /generate          → 手动触发图片生成

管理命令（命令行）
python manage.py init-owner --email <...> --password <...>
    → 创建管理员账号，将现有旧数据的 user_id 全部指向该账号
```

### 认证中间件依赖链

```
请求 → 从 Cookie 提取 session_token
     → SHA256(session_token) = token_hash
     → 在 AuthSession 表中查找 token_hash
         ├── 未找到或已过期 → 清除无效 Cookie → 302 /login
         └── 找到且有效
             ├── 检查是否需要续期（expires_at - now < 24h 且 remember_me=True）
             │   └── 生成新 session_token，更新 AuthSession
             ├── 将 current_user 注入 request.state
             └── 继续处理路由
```

### Session 安全模型

```
浏览器 Cookie                          数据库 AuthSession
─────────────────────────────────────────────────────────────
session_token: 64-char random hex      token_hash: SHA256(session_token)
  HttpOnly: true                       expires_at: timezone-aware datetime
  Secure: true                         remember_me: bool
  SameSite: Lax                        user_id: FK → User
  Path: /                              user_agent: text
  Cookie name: __Host-sid               created_at: datetime
  Max-Age: 604800 (7天) 或 Session
```

### CSRF 保护（双提交模式）

```
浏览器                                         服务端
────────────────────────────────────────────────────
csrf_token (明文字符串)  ←─── Set-Cookie 首次渲染    csrf_token 存在 CsrfToken 表
                         在 Cookie 和 HTML <form>
                         隐藏域中同时发送

POST /profile            请求中同时携带：
  Cookie: csrf_token=X   ←─── 比对 Cookie 中的 X
  body: _csrf_token=X    ←─── 和表单中的 X
                             不一致 → 403
```

### 数据隔离规则

所有受保护路由通过 FastAPI 依赖注入获取 `current_user`，所有数据库查询必须过滤 `user_id`：

```
Profile.query().filter_by(user_id=current_user.id).first()
JourneyState.query().filter_by(user_id=current_user.id).first()
JourneyLog.query().filter_by(user_id=current_user.id).order_by(...).all()
ScheduledTask.query().filter_by(user_id=current_user.id).all()
```

跨用户访问任何资源返回 **404**（不泄漏"该用户是否存在"），而非 403。

文件存储隔离：
```
data/uploads/<user_id>/ref_<uuid>.jpg     ← 上传的参考照片
data/generated/<user_id>/xiaobu_<ts>.png   ← AI 生成的照片
data/features/<user_id>_features.txt       ← 视觉特征缓存
```

---

## 安全设计（基于 3 个 Skill 审查）

### 1. 密码存储

| 参数 | 值 |
|------|-----|
| 算法 | Argon2id |
| time_cost | 3 |
| memory_cost | 65536 (64 MiB) |
| parallelism | 4 |
| hash_len | 32 |
| salt_len | 16 |

使用 `argon2-cffi` 库。不自行实现比较逻辑，只使用 `PasswordHasher.verify()`。

### 2. Cookie 安全

| 属性 | 值 | 理由 |
|------|-----|------|
| `HttpOnly` | true | 防止 JavaScript 读取 session token |
| `Secure` | true（生产） | 仅 HTTPS 传输 |
| `SameSite` | Lax | 阻止跨站 POST 但允许正常链接跳转 |
| `Path` | / | 全站可用 |
| `Name` | `__Host-sid` | Cookie Prefix 强制 Secure + Path=/ |
| session_token | 64 字符 hex | 192 位熵，抵御暴力枚举 |

### 3. CSRF 保护

- 使用双提交 Cookie 模式（适合纯 SSR 应用）
- 每个 session 对应一个 `CsrfToken`，有效期 24 小时
- CSRF token 出现在：Cookie（HttpOnly=False）+ 隐藏表单字段
- 所有 POST/PUT/DELETE 路由校验两个值是否一致
- Sign out 时清除 CSRF token

### 4. 速率限制

| 端点 | 窗口 | 最大次数 | 存储 |
|------|------|----------|------|
| POST /register | 1 分钟 | 5/IP | 数据库表 |
| POST /login | 1 分钟 | 5/IP | 数据库表 |
| POST /generate | 1 天 | 3/用户 | 数据库表 |

超过限制返回 `429 Too Many Requests`，带 `Retry-After` 响应头。同一区间内触发 3 次限制则记录审计日志。

### 5. 账号枚举防护

- 注册和登录始终返回相同错误信息："邮箱或密码错误"
- 注册时即使邮箱已存在，也返回"注册成功，请检查邮箱"（首版无邮件发送则直接跳转登录页）
- 密码比对耗时用固定时间比较（Argon2id `verify()` 已内置）
- 不通过 response body 或 header 泄漏用户是否存在

### 6. Session 管理

- 登录成功创建新 session（旧 session 不自动清除，允许用户多设备登录）
- Session 续期：距过期 < 24 小时且 `remember_me=True` 时自动续 7 天
- 登出：仅删除当前 session（单设备登出），`session_token` 和 `csrf_token` 同行删除
- 修改密码：删除所有该用户的 session（全设备强制登出）
- 新建 session 记录审计日志

### 7. 审计日志

`AuditLog` 表记录以下事件：

| 事件 | 级别 | 记录内容 |
|------|------|----------|
| `user.registered` | INFO | email, ip, user_agent |
| `user.login_success` | INFO | user_id, ip, user_agent |
| `user.login_failed` | WARN | email, ip, reason |
| `user.password_changed` | WARN | user_id, ip |
| `session.created` | DEBUG | user_id, user_agent |
| `session.revoked` | DEBUG | user_id |
| `session.all_revoked` | WARN | user_id, reason（如改密码） |
| `rate_limit.exceeded` | WARN | ip, endpoint, count |
| `csrf.invalid` | WARN | ip, endpoint |
| `generate.requested` | INFO | user_id |
| `generate.completed` | INFO | user_id, journey_log_id |

### 8. 生产环境启动自检

`lifespan` 在 `yield` 前执行以下检查（生产环境跳过，开发环境仅警告）：

| 检查项 | 生产（`ENV=production` 或 Railway/Render 默认） | 开发 |
|--------|---------------------------------------------------|------|
| SECRET_KEY ≠ "dev-secret-change-me" | **拒绝启动** | 警告 |
| SECRET_KEY 长度 ≥ 32 字符 | **拒绝启动** | 警告 |
| DATABASE_URL 为 sqlite | 警告 | 正常 |
| trusted_origin 已配置 | 警告 | 跳过 |
| HTTPS 是否启用 | 警告（本地 8000 正常） | 跳过 |

### 9. 文件上传安全

（继承 Phase 1 的 `uploads.py`，追加按 user_id 分目录）

- 扩展名白名单：`.jpg`、`.jpeg`、`.png`、`.webp`
- 文件名：UUID hex
- 最大文件大小：10 MB/张
- 最多参考照片：10 张/用户
- 上传后校验文件魔数（实际文件头必须匹配声称的类型）

### 10. API Key 安全

- API Key 在 Profile 表中**明文存储不变**（用户自备 Key，非服务端自有）
- 档案页用 `type="password"` 输入框，页面渲染时显示最后 4 位，其余掩码为 `****`
- 生成图片时从 Profile 读取 API Key，通过 HTTPS 传给火山引擎
- API Key 不出现在日志、审计记录、错误消息中

---

## 多用户调度

### 调度策略变更

| 当前（单用户） | 目标（多用户） |
|----------------|----------------|
| APScheduler 每天 00:01 只规划 1 个用户的 1~3 个任务 | APScheduler 每天 00:01 遍历所有用户，每人规划 1~3 个任务 |
| run_generation() 读第一条 Profile | run_generation(user_id) 只读该用户 Profile |
| 全局 Scheduler 单例 | Scheduler 单例 + per-user 参数 |

### 调度容错

- 每个用户的任务用 try/except 包裹，一个用户的错误不阻塞其他用户
- 任务执行前检查用户 Profile 是否完整（有 API Key 且状态有效）
- 不满足条件的用户跳过，记录审计日志

---

## 数据迁移策略

### `python manage.py init-owner` 命令

1. 验证邮箱格式和密码长度
2. 创建 User（Argon2id hash）
3. 查询数据库中所有 user_id 为空的记录（旧数据）
4. 将它们全部 batch update 为刚创建的 user_id
5. 打印：`创建管理员 xxx@example.com，迁移了 N 条旧记录`
6. 幂等：如果已有任何 user 存在，拒绝执行（提示改为使用 web 注册）

### 现有用户数据保留

- `xiaobu.db` 中的 `data/uploads/` 和 `data/generated/` 旧图片路径保留
- 旧图片移到 `data/uploads/<admin_user_id>/` 和 `data/generated/<admin_user_id>/`
- `data/xiaobu_features.txt` 移到 `data/features/<admin_user_id>_features.txt`

---

## 测试策略

### 新增测试文件

| 文件 | 覆盖内容 |
|------|----------|
| `tests/test_auth.py` | 注册成功/失败、登录成功/失败、登出、session 过期、邮箱重复 |
| `tests/test_csrf.py` | CSRF token 缺失/错误返回 403，正确 token 通过 |
| `tests/test_isolation.py` | 用户 A 不能访问用户 B 的数据（404），不能触发用户 B 的生成 |
| `tests/test_rate_limit.py` | 超出限制返回 429，Resetry-After 头存在 |
| `tests/test_security_checks.py` | SECRET_KEY 默认值被拒绝、Argon2id 验证正确 |
| `tests/test_audit.py` | 关键事件写入 AuditLog 表 |
| `tests/test_manage.py` | init-owner 创建管理员、迁移旧数据、拒绝重复执行 |

### 已有测试回归

- 现有 26 个测试全部保留
- 适配：集成测试在 `with TestClient(app)` 中先登录获取 cookie
- `conftest.py` 新增 `authenticated_client` fixture

---

## 文件变更清单

| 操作 | 文件 |
|------|------|
| **新增** | `models/user.py`（或直接加到 `models.py`） |
| **新增** | `middleware/auth.py` — 认证依赖 |
| **新增** | `middleware/csrf.py` — CSRF 令牌生成和校验 |
| **新增** | `middleware/rate_limit.py` — 速率限制 |
| **新增** | `middleware/audit.py` — 审计日志 |
| **新增** | `routers/auth.py` — 注册/登录/登出路由 |
| **新增** | `manage.py` — init-owner 命令 |
| **新增** | `templates/register.html` |
| **新增** | `templates/login.html` |
| **新增** | `tests/test_auth.py` |
| **新增** | `tests/test_csrf.py` |
| **新增** | `tests/test_isolation.py` |
| **新增** | `tests/test_rate_limit.py` |
| **新增** | `tests/test_security_checks.py` |
| **新增** | `tests/test_audit.py` |
| **新增** | `tests/test_manage.py` |
| **修改** | `models.py` — 加 user_id |
| **修改** | `app.py` — 路由注册、生命周期更新 |
| **修改** | `scheduler.py` — per-user 调度 |
| **修改** | `config.py` — SECRET_KEY 检查 |
| **修改** | `templates/base.html` — 登出链接 |
| **修改** | `templates/index.html` — 按用户渲染 |
| **修改** | `templates/profile.html` — API Key 掩码 |
| **修改** | `tests/conftest.py` — 新增认证 fixture |
| **修改** | `tests/test_integration.py` — 适配认证 |

---

## 依赖

### 新增 Python 依赖

```
argon2-cffi==24.1.0
```

### 已在 requirements.txt 中的依赖（不变）

```
fastapi==0.115.0
sqlalchemy==2.0.35
pillow==12.2.0
jinja2==3.1.6
python-multipart==0.0.32
python-dotenv==1.0.1
apscheduler==3.10.4
httpx==0.27.0
pytest==8.3.0
```
