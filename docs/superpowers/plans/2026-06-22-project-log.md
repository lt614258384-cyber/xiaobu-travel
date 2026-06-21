# Cross-Agent Project Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a canonical project log and repository-level Agent instructions so every future project conversation leaves an accurate, secret-free handoff.

**Architecture:** `docs/PROJECT_LOG.md` is the living single source of truth for current state and append-only session history. Root `AGENTS.md` is the discovery layer that requires every Agent to read and update the log while preserving verified status and confidential data boundaries.

**Tech Stack:** Markdown, Git, PowerShell validation commands

---

## File map

- Create `AGENTS.md`: mandatory read/update/confidentiality rules for all Agents.
- Create `docs/PROJECT_LOG.md`: detailed current state, risks, roadmap, decisions, next step, and session history.

### Task 1: Add repository-level Agent instructions

**Files:**
- Create: `AGENTS.md`

- [ ] **Step 1: Confirm the file is absent**

Run: `Test-Path -LiteralPath AGENTS.md`

Expected: `False`.

- [ ] **Step 2: Create the mandatory protocol**

Create `AGENTS.md` with these exact requirements:

```markdown
# Repository Agent Instructions

## Required project context

Before inspecting, planning, editing, testing, committing, or reporting:

1. Read `docs/PROJECT_LOG.md` completely.
2. Read the active specification and implementation plan linked from the log.
3. Check the current Git branch and working tree; preserve user and other Agent changes.

## Required log update

Before ending every project-related conversation, update `docs/PROJECT_LOG.md`.

- Record the user's goal, checks or changes, verification evidence, remaining work, and next action.
- If no code changed, explicitly record `无代码改动` and retain the investigation or decision.
- Update current status and dated history whenever state changes.
- Use Asia/Hong_Kong date and time.
- Never mark planned or unverified work as completed.

## Confidentiality

Never record passwords, API keys, session tokens, cookies, real email addresses, `.env` contents, private photos, database records, or visual-feature cache contents. Record only a secret's purpose, storage location, and required protection.

## Handoff quality

- Keep `docs/PROJECT_LOG.md` as the only canonical status document.
- Preserve important decisions and append session records in reverse chronological order.
- Link relevant files, commits, specs, plans, and test commands.
```

- [ ] **Step 3: Verify the instruction contract**

Run: `rg -n "PROJECT_LOG|Before ending every project-related conversation|无代码改动|Never mark|Confidentiality|Asia/Hong_Kong" AGENTS.md`

Expected: every required concept appears.

### Task 2: Create and populate the project log

**Files:**
- Create: `docs/PROJECT_LOG.md`

- [ ] **Step 1: Confirm the file is absent**

Run: `Test-Path -LiteralPath docs/PROJECT_LOG.md`

Expected: `False`.

- [ ] **Step 2: Create the canonical sections**

Use these exact headings:

```markdown
# 小布的旅行：项目日志与 Agent 交接
## 日志元数据
## Agent 更新协议
## 项目目标
## 当前产品与架构
## 当前状态摘要
## 已完成并验证
## 当前问题与安全隐患
## 多用户与部署路线图
## 已确认的设计决策
## 当前最优先的下一步
## 重要文件索引
## 会话与开发记录（倒序）
```

At the top, state that all Agents must read and update the log and must not record real secrets or personal data.

- [ ] **Step 3: Fill verified project identity and architecture**

Include:

```markdown
- 仓库：`D:\Xiaobu's travel`；分支：`feat/xiaobu-travel`
- Python 3.13；Windows 11
- FastAPI + Jinja2 SSR + SQLAlchemy + SQLite + APScheduler
- 火山引擎 Seedream 4.5 图生图与视觉分析
- 当前无 User 表；Profile、JourneyState、JourneyLog、ScheduledTask 无 user_id
- 图片位于本地 `data/`，且当前由 `/data` 公开挂载
- 当前是单用户本地应用，不满足公网多用户安全要求
```

- [ ] **Step 4: Record verified status without overstating plans**

State that the MVP functions and `docs/CONTEXT.md` exist. State that reliability cleanup has committed design and plan documents but no implementation. State that multi-user architecture decisions are approved but not implemented. State that the Better Auth security skill is installed but must be discovered and read in each applicable session.

- [ ] **Step 5: Create the risk register**

Use columns `优先级 / 状态 / 问题 / 证据 / 解决方向` and include:

```markdown
| P0 | 未解决 | 无认证和用户隔离 | 路由公开并查询全局数据 | 认证与 user_id 隔离同批上线 |
| P0 | 未解决 | API Key 明文存储并回填网页 | Profile 与 profile.html | 加密、掩码、主人专属访问 |
| P0 | 未解决 | `/generate` 可匿名触发付费生成 | POST 路由无保护 | 登录、CSRF、限速、配额、审计 |
| P0 | 未解决 | 上传和媒体暴露 | 无服务端大小/魔数校验，公开 `/data` | 图片白名单与私有媒体访问 |
| P0 | 未解决 | 生产依赖有公开漏洞 | Pillow、Jinja2、python-multipart 版本过旧 | 升级并重新审计 |
| P1 | 未解决 | 无 CSRF、限速和安全审计 | 所有 POST 缺少控制 | Session Token、Origin、限速、审计 |
| P1 | 未解决 | 默认 SECRET_KEY 可预测 | config.py 开发默认值 | 生产拒绝默认或低熵秘密 |
| P1 | 未解决 | 调度器和生成目录全局共享 | Scheduler 查询全局数据 | 绑定 user_id 并隔离失败 |
| P1 | 未解决 | PaaS 本地磁盘不保证持久 | data/uploads、data/generated | 对象存储或持久卷 |
| P2 | 已规划未实施 | lifespan、中文文件名、旧 Prompt 风格词 | 已提交可靠性规格和计划 | 按计划测试驱动实施 |
```

- [ ] **Step 6: Record roadmap, decisions, next action, and links**

Roadmap order:

1. 基础可靠性与依赖修复。
2. User、数据库 Session、注册/登录/退出、CSRF、限速和 user_id 隔离原子上线。
3. 上传、生成文件和 API Key 的用户级保护。
4. 多用户调度、幂等、配额和失败隔离。
5. PostgreSQL、对象存储、Docker、Railway/Render。

Record approved decisions: database-backed opaque Session; no first-release email verification/reset; explicit legacy owner creation; per-user API Key; auth and tenant isolation cannot be deployed separately.

Set the next action to implementing `docs/superpowers/plans/2026-06-22-reliability-cleanup.md`, then writing the combined auth-and-isolation spec. Link `docs/CONTEXT.md`, all 2026-06-22 specs, and both 2026-06-22 plans.

- [ ] **Step 7: Add initial reverse-chronological records for 2026-06-22**

Add separate entries for:

1. Project-log design approval.
2. Security audit completed with `无代码改动`, critical findings, and the incomplete transitive dependency audit caused by the Python 3.13 psycopg2 build issue.
3. Better Auth security skill found, source-checked, installed, and requiring restart/discovery.
4. Multi-user target clarified and key architecture choices approved.
5. Reliability design and plan committed while implementation remains pending.

Every entry includes goal, result, evidence, remaining work, and next action.

### Task 3: Validate and commit the handoff system

**Files:**
- Verify: `AGENTS.md`
- Verify: `docs/PROJECT_LOG.md`

- [ ] **Step 1: Verify headings and discovery links**

Run:

```powershell
rg -n "项目目标|当前问题与安全隐患|当前最优先的下一步|会话与开发记录" docs/PROJECT_LOG.md
rg -n "docs/PROJECT_LOG.md" AGENTS.md
```

Expected: all log headings exist and `AGENTS.md` points to the log.

- [ ] **Step 2: Scan for secret-value patterns**

Run: `rg -n "sk-[A-Za-z0-9_-]{16,}|Bearer [A-Za-z0-9._-]{16,}|session_token=[A-Za-z0-9._-]{16,}" AGENTS.md docs/PROJECT_LOG.md`

Expected: no matches.

- [ ] **Step 3: Verify status consistency**

Run: `rg -n "已规划未实施|未解决|尚未实施|无代码改动|下一步" docs/PROJECT_LOG.md`

Expected: reliability and multi-user code remain pending; the audit is complete but changed no code.

- [ ] **Step 4: Check formatting and scope**

Run:

```powershell
git diff --check -- AGENTS.md docs/PROJECT_LOG.md
git status --short -- AGENTS.md docs/PROJECT_LOG.md
```

Expected: no whitespace errors and exactly two new files before staging.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md docs/PROJECT_LOG.md
git commit -m "docs: add cross-agent project log"
```
