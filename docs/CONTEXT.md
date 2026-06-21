# 小布的旅行 — 项目上下文

## 项目概述

"小布的旅行"是一个 AI 驱动的"旅行青蛙"式陪伴应用。用户养的金毛犬"小布"因病去世，通过这个项目生成小布在汪星的生活照片，带来陪伴慰藉。

- **仓库**：https://github.com/lt614258384-cyber/xiaobu-travel （分支 `feat/xiaobu-travel`）
- **本地路径**：`d:\Xiaobu's travel\`
- **Python 3.13**，Windows 11

## 核心功能

- **档案页** `/profile`：填写小布信息、上传 8 张参考照片、填写外貌描述、粘贴 API Key
- **首页** `/`：时间线展示生成的汪星照片，Hero 卡片 + 历史瀑布流
- **一键生成**：首页 "✨ 生成新照片" 按钮，手动触发
- **定时生成**：每天 00:01 自动规划 1-3 个随机时间触发（需要服务运行中）
- **叙事系统**：状态机驱动，60 个汪星地点 + 203 个活动 + 1000+ 文案模板

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI + Jinja2 |
| 数据库 | SQLite（开发）/ PostgreSQL |
| ORM | SQLAlchemy |
| 定时任务 | APScheduler |
| 前端 | 纯 HTML/CSS/JS（无构建工具） |
| 图片生成 | 火山引擎 Seedream 4.5 |
| 视觉分析 | 火山引擎 Doubao 1.5 Vision Pro |

## 当前模型配置

- **生图模型**：`doubao-seedream-4-5-251128`（Seedream 4.5，2048x2048）
- **视觉模型**：`doubao-1-5-vision-pro-32k-250115`（分析小布照片提取特征，只调一次已缓存）
- **API 端点**：火山引擎 `https://ark.cn-beijing.volces.com/api/v3/`
- **API Key**：存在 Profile 表的 `image_api_key` 字段（网页档案页输入）
- **图片风格**：半写实手绘水彩插画风，彩铅+透明水彩，温暖治愈，儿童绘本感
- **代码中可切换的模型**：tongyi（通义万相）、seedream、openai、fake

## 图片生成流程

1. 用户点击"生成新照片"或定时触发
2. 读取 JourneyState（当前地点 + 心情 + 天气）
3. 状态机选择下一个相邻地点 + 随机活动
4. **视觉分析**（仅首次）：Doubao Vision 分析 3 张参考照片，提取详细特征描述，缓存到 `data/xiaobu_features.txt`
5. 将特征描述 + 地点 + 活动 + 天气 → 组装 Prompt（英文 + 中文混合）
6. 参考照片 base64 编码后传入 Seedream（图生图模式）
7. 生成图片保存到 `data/generated/`
8. 更新旅程状态（新地点、新心情、天数+1）

## 项目结构

```
xiaobu/
├── app.py              # FastAPI 入口 + 路由
├── config.py           # 配置（加载 .env）
├── models.py           # 7 张表：Profile, JourneyState, JourneyLog, Region, Location, Activity, ScheduledTask
├── scheduler.py        # APScheduler + 生成管线（含视觉分析）
├── run.py              # uvicorn 启动脚本
├── engine/
│   ├── state_machine.py   # 状态机：选地点、选活动、天气、心情
│   ├── storyteller.py     # 文案模板 + Prompt 组装
│   └── image_gen.py       # 图片 API 适配器（Seedream/Tongyi/OpenAI/Fake）
├── templates/
│   ├── base.html / index.html / profile.html
├── static/
│   ├── css/style.css / js/app.js
├── seed/               # 60 地点 + 203 活动初始数据
├── data/
│   ├── uploads/        # 用户上传的小布照片
│   ├── generated/      # AI 生成的照片
│   └── xiaobu_features.txt  # 视觉模型缓存的狗特征描述
└── tests/              # 19 个测试
```

## 启动方式

```bash
cd "d:\Xiaobu's travel"
export DATABASE_URL="sqlite:///xiaobu.db"
export IMAGE_API_TYPE="seedream"
python run.py
# 打开 http://localhost:8000
```

> 需要火山引擎 API Key（在网页 /profile 输入）。如无 Key，设 `IMAGE_API_TYPE=fake` 用测试模式（产橙色方块）。

## 已知问题 & 未来方向

1. **角色一致性不够**——Seedream 参考图机制无法精确复刻小布五官。讨论了 LoRA 方案（Replicate 付费、Civitai 免费、Colab 免费）但未执行
2. **图片格式**——Windows 反斜杠路径已转为 `/`，但 `data/uploads/` 下照片文件名含中文可能有编码问题
3. **数据库**——当前 SQLite，生产需要切 PostgreSQL
4. **FastAPI startup**——用了已弃用的 `@app.on_event("startup")`，应改为 lifespan
5. **推送通知**——MVP 无推送，用户需主动打开网页查看
6. **Seedream 5.0**——模型列表里有 `doubao-seedream-5-0-260128`，未测试
7. **种子数据 Prompt 模板**——203 个活动的 `prompt_template` 仍含"吉卜力动画风格"，compose_prompt 中用字符串替换去掉了，但不优雅

## 关键设计决策

- 无手动触发 → 后来加了"生成新照片"按钮（用户主动要求）
- 零 LLM 依赖 → 叙事用模板状态机
- 模板存数据库 → 方便扩展
- 图片 API 可切换 → 适配器模式
- 无推送通知 → MVP 阶段网页查看
- 参考照片上限 10 张 → 图生图用全部，视觉分析取前 3 张
