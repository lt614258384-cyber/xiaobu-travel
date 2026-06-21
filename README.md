# 🐾 小布的旅行 (Xiaobu's Travel)

AI 驱动的"旅行青蛙"式陪伴应用。设置档案后，系统每天不定时生成小布在汪星的照片和故事。

## 快速开始

### 环境要求
- Python 3.11+
- PostgreSQL 14+

### 安装

```bash
# 创建数据库
createdb xiaobu

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export DATABASE_URL="postgresql://localhost:5432/xiaobu"
export IMAGE_API_KEY="your-tongyi-api-key"
export IMAGE_API_TYPE="tongyi"  # 或用 "fake" 测试

# 初始化数据
python -m seed.generate_seed

# 启动
python run.py
# 打开 http://localhost:8000
```

### 使用
1. 访问 `/profile` 设置小布档案
2. 上传小布的照片
3. 系统每天随机时间自动生成照片
4. 回到首页查看小布最新动态

### 测试
```bash
IMAGE_API_TYPE=fake pytest tests/ -v
```

## 项目结构
```
xiaobu/
├── app.py / config.py / models.py
├── scheduler.py / run.py
├── engine/            # 状态机、文案、图片生成
├── templates/         # Jinja2 HTML 模板
├── static/            # CSS/JS
├── seed/              # 初始数据
└── tests/             # 测试
```
