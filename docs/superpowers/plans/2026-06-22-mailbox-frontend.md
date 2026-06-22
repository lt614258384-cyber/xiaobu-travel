# 小布的旅行："汪星来信"前端实施计划

> 日期：2026-06-22
> 依赖：设计规格 `docs/superpowers/specs/2026-06-22-mailbox-frontend-design.md` 已批准

## 实施顺序

### Task 1：新增后端路由 + 测试
- `GET /mailbox` → 返回信箱页，传入按时间倒序的 JourneyLog 列表
- `GET /letter/<log_id>` → 返回单封历史来信详情，校验 user_id
- 3 个新测试（路由可访问、跨用户隔离、空信箱）

### Task 2：信箱页模板 + CSS
- 新建 `templates/mailbox.html`：页头 + 按日列表 + 空状态 + 加载更多
- CSS：温暖纸张色板变量、信箱列表样式、未读圆点+底色、响应式

### Task 3：首页改造（模板 + CSS + JS）
- 修改 `templates/index.html`：Hero 卡片、等待仪式、抵达提示、拆信交互
- JS：替换现有 PROGRESS_MESSAGES 为装信轮询+拆信流程
- CSS：Hero 卡片、等待动画、拆信状态

### Task 4：图文合信复用片段
- 可选抽取 `_letter_card.html`，首页和信箱详情共用

### Task 5：无障碍收尾
- prefers-reduced-motion 媒体查询
- aria 标签补全
- 键盘焦点管理

### Task 6：全量测试 + 视觉 QA
- 确保 58 个现有测试仍通过
- 使用 `design-critique` 做只读评审

## 验证标准

- [ ] `GET /mailbox` 返回 200，包含当前用户来信列表
- [ ] `GET /letter/<id>` 返回 200（本人）/ 404（他人）
- [ ] 空信箱显示引导状态
- [ ] 首页按钮文案为"看看小布最近在做什么"
- [ ] 点击生成后显示装信等待动画
- [ ] 58 个现有测试保持通过
