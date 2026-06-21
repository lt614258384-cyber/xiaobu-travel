# 小布的旅行 (Xiaobu's Travel) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an MVP web app that uses AI image generation to create and display a narrative "Xiaobu in Wang Star" photo timeline, driven by a template-based state machine with scheduled daily generation.

**Architecture:** FastAPI monolith with Jinja2 server-side templates, SQLAlchemy ORM over PostgreSQL, APScheduler for timed generation, and an adapter-pattern image generation layer. The narrative engine uses a state machine over a 60-location world map with personality-weighted movement and template-driven story selection.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL, APScheduler, Pillow, Jinja2, HTML/CSS/JS (no bundler)

## Global Constraints

- No manual trigger — only scheduled auto-generation
- Zero LLM dependency — pure template + state machine
- All templates stored in database, not hardcoded
- Image API behind adapter interface — swappable
- Max 10 reference photos for image generation
- PostgreSQL as database
- Local filesystem storage for uploads and generated images

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `data/` directory structure

**Interfaces:**
- Produces: `config.py` → `Settings` dataclass with `DATABASE_URL`, `IMAGE_API_KEY`, `IMAGE_API_TYPE`, `UPLOAD_DIR`, `GENERATED_DIR`, `MAX_REFERENCE_PHOTOS`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.35
psycopg2-binary==2.9.9
apscheduler==3.10.4
pillow==10.4.0
jinja2==3.1.4
python-multipart==0.0.12
httpx==0.27.0
pytest==8.3.0
```

- [ ] **Step 2: Create config.py**

```python
import os
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost:5432/xiaobu")
    IMAGE_API_KEY: str = os.getenv("IMAGE_API_KEY", "")
    IMAGE_API_TYPE: str = os.getenv("IMAGE_API_TYPE", "tongyi")
    UPLOAD_DIR: Path = field(default_factory=lambda: Path("data/uploads"))
    GENERATED_DIR: Path = field(default_factory=lambda: Path("data/generated"))
    MAX_REFERENCE_PHOTOS: int = 10
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")

    def __post_init__(self):
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.GENERATED_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
```

- [ ] **Step 3: Verify**

Run: `python -c "from config import settings; print(settings.DATABASE_URL)"`
Expected: Prints `postgresql://localhost:5432/xiaobu`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt config.py
git commit -m "feat: add project scaffolding and config"
```

---

### Task 2: Database Models

**Files:**
- Create: `models.py`

**Interfaces:**
- Consumes: `config.settings`
- Produces: `Profile`, `JourneyState`, `JourneyLog`, `Region`, `Location`, `Activity`, `ScheduledTask` SQLAlchemy models + `init_db()`, `get_session()`

- [ ] **Step 1: Write models.py**

```python
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, relationship, Session
from config import settings

Base = declarative_base()

class Profile(Base):
    __tablename__ = "profile"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, default="小布")
    breed = Column(String(100), default="")
    age = Column(Integer, default=0)
    appearance = Column(Text, default="")
    personality_tags = Column(JSON, default=list)
    interests = Column(JSON, default=list)
    habits = Column(Text, default="")
    content_preference = Column(String(20), default="caption")
    reference_photos = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Region(Base):
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")


class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    atmosphere = Column(Text, default="")
    adjacent_locations = Column(JSON, default=list)
    region = relationship("Region")
    activities = relationship("Activity", back_populates="location")


class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    name = Column(String(100), nullable=False)
    prompt_template = Column(Text, default="")
    captions = Column(JSON, default=list)
    stories = Column(JSON, default=list)
    location = relationship("Location", back_populates="activities")


class JourneyState(Base):
    __tablename__ = "journey_state"
    id = Column(Integer, primary_key=True)
    current_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    mood = Column(String(50), default="开心")
    day_number = Column(Integer, default=1)
    weather_today = Column(String(50), default="晴")
    last_activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JourneyLog(Base):
    __tablename__ = "journey_log"
    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    story_text = Column(Text, default="")
    image_path = Column(String(500), default="")
    weather = Column(String(50), default="晴")
    mood = Column(String(50), default="开心")
    generated_at = Column(DateTime, default=datetime.utcnow)


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"
    id = Column(Integer, primary_key=True)
    scheduled_at = Column(DateTime, nullable=False)
    executed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")
    retry_count = Column(Integer, default=0)
    journey_log_id = Column(Integer, ForeignKey("journey_log.id"), nullable=True)


def get_engine():
    return create_engine(settings.DATABASE_URL)


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)


def get_session():
    engine = get_engine()
    return Session(engine)
```

- [ ] **Step 2: Test model definitions**

Run: `python -c "from models import Base; print('Tables:', [t for t in Base.metadata.tables.keys()])"`
Expected: `Tables: ['profile', 'regions', 'locations', 'activities', 'journey_state', 'journey_log', 'scheduled_tasks']`

- [ ] **Step 3: Commit**

```bash
git add models.py
git commit -m "feat: add SQLAlchemy data models"
```

---

### Task 3: Database Init & Seed Framework

**Files:**
- Create: `seed/__init__.py`
- Create: `seed/locations_data.py`
- Create: `seed/activities_data.py`
- Create: `seed/generate_seed.py`

**Interfaces:**
- Consumes: `models.py`
- Produces: Populated database with 5 regions, 60 locations, ~250 activities, ~1200+ templates

- [ ] **Step 1: Create seed/locations_data.py**

```python
"""
60 locations across 5 regions with adjacency and atmosphere definitions.
"""

REGIONS = [
    {
        "name": "海滨区",
        "description": "一望无际的大海，金色的沙滩，浪花拍打着海岸，海鸥在天空盘旋",
        "locations": [
            ("彩虹桥", "连接汪星与人类世界的梦幻桥梁，七彩的桥身横跨天际", "彩虹横跨天空，云朵环绕，晨曦微光"),
            ("阳光沙滩", "柔软的金色沙滩，温暖的阳光洒在海面上", "金色沙滩，碧蓝海水，棕榈树摇曳"),
            ("贝壳湾", "遍布五彩贝壳的宁静小海湾", "彩色贝壳点缀沙滩，清澈浅滩，珊瑚碎片"),
            ("灯塔礁", "礁石上矗立着古老的白色灯塔", "白色灯塔，礁石海岸，海天一色"),
            ("落日码头", "延伸入海的木质码头，是看日落的最佳地点", "夕阳染红海面，木质栈桥，渔船停泊"),
            ("海风悬崖", "陡峭的海崖，海风拂面，视野开阔", "悬崖峭壁，海风劲吹，俯瞰大海"),
            ("珊瑚浅滩", "浅海中珊瑚丛生，小鱼穿梭其间", "彩色珊瑚，清澈见底的海水，热带鱼群"),
            ("美人鱼湾", "传说中有美人鱼出没的神秘海湾", "神秘蓝光，礁石拱门，波光粼粼"),
            ("沙滩排球场", "狗狗们最喜欢在这里打沙滩排球", "沙滩球场，彩色排球，欢快热闹"),
            ("冲浪者海滩", "浪花翻涌，汪星冲浪高手聚集地", "白色浪花，冲浪板，阳光灿烂"),
            ("海边露营地", "沙滩边的露营地，晚上可以看星星", "帐篷篝火，星空，海风轻拂"),
            ("海鸥灯塔", "成群海鸥栖息在灯塔周围", "海鸥飞舞，灯塔钟声，晨雾朦胧"),
        ]
    },
    {
        "name": "原野区",
        "description": "广袤的原野，四季花开的草原，金色麦田在风中起伏",
        "locations": [
            ("花海草原", "无边无际的花海，各种颜色的花竞相开放", "彩色花海，蝴蝶飞舞，蓝天白云"),
            ("薰衣草田", "紫色的薰衣草花田，空气中弥漫着淡淡香气", "紫色花田，蜜蜂穿梭，浪漫梦幻"),
            ("金色麦田", "成熟的金色麦田在风中掀起层层波浪", "金色麦浪，稻草人守望，温暖阳光"),
            ("蒲公英丘陵", "长满蒲公英的绿色丘陵，风一吹漫天飞舞", "蒲公英飞舞，绿色丘陵，轻柔微风"),
            ("樱花坡道", "春天樱花盛开的坡道，花瓣如雨飘落", "粉色樱花雨，石板小径，春日暖阳"),
            ("蝴蝶谷", "成千上万只蝴蝶聚集的山谷", "蝴蝶群舞，野花遍地，幽静山谷"),
            ("蜂蜜农场", "勤劳的蜜蜂在这里酿造甜甜的蜂蜜", "蜂箱排列，蜜蜂忙碌，甜香四溢"),
            ("草莓采摘园", "红彤彤的草莓挂满枝头", "鲜红草莓，绿色藤蔓，果香扑鼻"),
            ("风吹麦浪", "广阔麦田中一座小木屋，风过时麦浪如海", "麦浪翻涌，小木屋，风车转动"),
            ("三叶草草原", "遍地三叶草，偶尔能找到四叶草", "翠绿三叶草，幸运四叶草，柔软草地"),
            ("水果庄园", "各种果树硕果累累的大庄园", "果树成行，果实累累，果香浓郁"),
            ("稻草人农场", "稻草人守护的农场，有各种可爱的动物", "稻草人微笑，菜园整齐，小动物出没"),
        ]
    },
    {
        "name": "山地区",
        "description": "连绵起伏的山脉，云海翻涌，山峰耸立，溪流潺潺",
        "locations": [
            ("云朵山", "山顶常年被云朵环绕，可以摸到云彩", "云海翻涌，山顶微光，柔软云朵"),
            ("星空峰", "夜晚可以看到最璀璨的星空", "银河横跨，流星划过，静谧夜空"),
            ("枫叶岭", "秋天满山枫叶变红，如火焰般绚烂", "红色枫叶，落叶铺径，秋高气爽"),
            ("温泉山谷", "山谷中有天然温泉，蒸汽袅袅", "温泉蒸汽，山谷幽静，暖意融融"),
            ("竹林小径", "穿过竹林的小径，竹子沙沙作响", "翠绿竹林，光影斑驳，竹叶飘落"),
            ("松果林", "高大的松树挂满松果，松鼠在树上跳跃", "松树参天，松果遍地，松针柔软"),
            ("回声峡谷", "对着峡谷喊话会有回声传来", "峡谷幽深，回声缭绕，岩壁陡峭"),
            ("瀑布溪", "清澈的瀑布从山涧飞流直下", "瀑布飞溅，彩虹水雾，溪流潺潺"),
            ("彩虹山涧", "雨后山涧间经常出现彩虹", "彩虹横跨山涧，水珠晶莹，翠绿山色"),
            ("石头小屋", "山间石头砌成的小屋，温暖舒适", "石头壁炉，炊烟袅袅，温馨小屋"),
            ("云端瞭望台", "建在山顶的瞭望台，可以俯瞰整个汪星", "云朵环绕，全景视野，日出壮观"),
            ("幽兰谷", "山谷中兰花静静开放，幽香四溢", "兰花盛放，清幽山谷，薄雾轻笼"),
        ]
    },
    {
        "name": "森林区",
        "description": "神秘而生机勃勃的大森林，高大的树木遮天蔽日，各种小动物在此安家",
        "locations": [
            ("森林探险", "未知的森林深处，充满了冒险和惊喜", "密林光影，未知小径，冒险氛围"),
            ("蘑菇村", "各种彩色蘑菇组成的小村落", "彩色蘑菇屋，小精灵出没，童话氛围"),
            ("树洞图书馆", "大树洞里有汪星最大的图书馆", "树洞书架，温暖灯光，书香弥漫"),
            ("萤火虫森林", "夜晚萤火虫点亮整片森林", "萤火虫光点，夜色朦胧，梦幻森林"),
            ("橡果广场", "巨大的橡树下，是森林居民的聚会广场", "巨大橡树，橡果散落，林间空地"),
            ("树懒吊桥", "树与树之间有绳索吊桥相连", "吊桥摇荡，树冠漫步，森林全景"),
            ("松鼠果园", "松鼠们种植的果园，果实满满", "松鼠忙碌，果树枝头，果实累累"),
            ("藤蔓迷宫", "藤蔓交织形成的天然迷宫", "藤蔓缠绕，绿色迷宫，探险趣味"),
            ("迷雾森林", "清晨薄雾笼罩的神秘森林", "薄雾弥漫，晨光穿透，朦胧神秘"),
            ("巨人树屋", "建在巨树上的大型树屋群落", "树屋错落，木梯盘旋，树冠生活"),
            ("浆果丛林", "各种浆果挂满枝头的丛林中", "浆果彩色，果香四溢，小动物觅食"),
            ("森林音乐厅", "森林中央由树木围成的天然音乐厅", "鸟鸣乐章，树荫环绕，自然舞台"),
        ]
    },
    {
        "name": "小镇区",
        "description": "温馨热闹的汪星小镇，有各种店铺和友好的邻居",
        "locations": [
            ("汪星小镇", "小镇的中心，是所有狗狗的家", "温馨街道，彩色房屋，邻里和睦"),
            ("美食街", "各种美食应有尽有的街道", "美食飘香，餐厅林立，热闹非凡"),
            ("中央公园", "小镇中心的大公园，有大片草坪和喷泉", "草坪翠绿，喷泉水花，悠闲时光"),
            ("喷泉广场", "小镇的标志性喷泉广场", "喷泉水柱，鸽子飞舞，阳光水雾"),
            ("狗狗咖啡馆", "狗狗们聚会聊天的温馨咖啡馆", "咖啡香气，舒适沙发，骨头饼干"),
            ("玩具商店", "各种狗狗玩具应有尽有", "玩具琳琅，彩色球球，飞盘墙"),
            ("面包工坊", "烤面包的香味飘满整条街", "新鲜面包，面粉飘香，温暖烤箱"),
            ("冰淇淋车", "小镇最受欢迎的冰淇淋车", "彩色冰淇淋，华夫筒，夏日清凉"),
            ("周末集市", "每周末开放的热闹集市", "摊位林立，新鲜果蔬，热闹交易"),
            ("电影院", "播放经典狗狗电影的小影院", "爆米花香，大银幕，舒适座椅"),
            ("书店角落", "安静的书店，有柔软的靠垫", "书架满墙，温暖灯光，安静角落"),
            ("友谊桥", "桥上有锁满了友谊锁的栏杆", "友谊锁闪亮，小桥流水，温馨祝福"),
        ]
    },
]

# Cross-region connections
CROSS_REGION_CONNECTIONS = [
    ("阳光沙滩", "花海草原"),
    ("海风悬崖", "蒲公英丘陵"),
    ("落日码头", "汪星小镇"),
    ("海边露营地", "周末集市"),
    ("蝴蝶谷", "森林探险"),
    ("樱花坡道", "蘑菇村"),
    ("水果庄园", "松鼠果园"),
    ("金色麦田", "云朵山"),
    ("三叶草草原", "温泉山谷"),
    ("竹林小径", "萤火虫森林"),
    ("松果林", "橡果广场"),
    ("瀑布溪", "迷雾森林"),
    ("巨人树屋", "汪星小镇"),
    ("森林音乐厅", "中央公园"),
    ("美食街", "石头小屋"),
    ("友谊桥", "星空峰"),
]
```

- [ ] **Step 2: Create seed/activities_data.py**

```python
"""
Activity and story template definitions for all 60 locations.
Each location has 3-5 activities, each with prompt_template, captions, and stories.
Templates use {appearance}, {weather}, {atmosphere}, {mood} as variables.
"""

def generate_activities():
    """Return activities dict keyed by location name."""
    activities = {}

    # --- 海滨区 ---
    activities["彩虹桥"] = [
        {
            "name": "看日出",
            "prompt_template": "{appearance} 站在彩虹桥上眺望日出的方向，{weather}的早晨，{atmosphere}，吉卜力动画风格，温暖治愈",
            "captions": [
                "今天小布起了个大早，在彩虹桥上看到了最美的日出 🌅",
                "彩虹桥的日出永远看不腻，小布趴在桥边看了好久～",
                "清晨第一缕阳光洒在彩虹桥上，小布觉得好幸福 ❤️",
            ],
            "stories": [
                "今天天还没亮，小布就醒了。它沿着彩虹桥一路小跑到桥中央，选了个最好的位置趴下。太阳慢慢从海平面升起，把云朵染成了橘子色。小布摇了摇尾巴——这是它在汪星最喜欢的时间，虽然很想念远方的家人，但彩虹桥的日出能让它觉得一切都会好的。",
                "清晨的彩虹桥格外安静，小布是最早到的。当第一缕阳光穿过云层照在它身上时，小布闭上眼睛，感受着温暖。它想，如果家人也能看到这一幕就好了。",
            ],
        },
        {
            "name": "和朋友们打招呼",
            "prompt_template": "{appearance} 在彩虹桥上和新来的汪星朋友们打招呼，{weather}的天空下，{atmosphere}，吉卜力动画风格",
            "captions": [
                "今天彩虹桥来了新朋友，小布热情地上去打招呼 👋",
                "小布在桥头迎接新来的小伙伴，尾巴摇得像螺旋桨～",
            ],
            "stories": [
                "今天彩虹桥格外热闹，又有新朋友来到了汪星。小布作为彩虹桥的老居民，主动跑过去迎接。它带着新朋友在桥上走了一圈，介绍了哪里看日出最美、哪里的云朵最软。新朋友本来有点紧张，但在小布的热情感染下，很快就放松了。",
            ],
        },
        {
            "name": "在桥上奔跑",
            "prompt_template": "{appearance} 在彩虹桥上欢快地奔跑，{weather}，{atmosphere}，风吹动毛发，吉卜力动画风格",
            "captions": [
                "小布今天精力充沛，在彩虹桥上来回跑了好几趟 🏃",
                "彩虹桥上有一道模糊的身影——那是小布在撒欢跑！",
            ],
            "stories": [
                "小布今天心情特别好，一大早就开始在彩虹桥上撒欢。它从桥的这头跑到那头，又从那头跑回来，四条小短腿倒腾得飞快。跑累了就趴在桥边喘气，看着云朵从脚下飘过，然后又站起来继续跑——汪星的日子就是这么自由自在。",
            ],
        },
        {
            "name": "眺望人间",
            "prompt_template": "{appearance} 趴在彩虹桥边，向下眺望远方的家，{weather}，{atmosphere}，深情而温柔，吉卜力动画风格",
            "captions": [
                "小布趴在桥边，往家的方向看了好久 🏠",
                "小布说它不怕远，因为看得见家的方向 ⭐",
            ],
            "stories": [
                "有时候小布会安静地趴在彩虹桥栏杆上，把头伸出去，往下面看好久好久。它知道那个方向有它最爱的家人。虽然看不太清楚，但它能感觉到。今天{weather}，能见度很好，小布觉得自己好像看到了家里窗户透出的灯光。它轻轻哼了一声，像是在说：我在这里很好，你们也要好好的。",
            ],
        },
    ]

    activities["阳光沙滩"] = [
        {
            "name": "追浪花",
            "prompt_template": "{appearance} 在沙滩上追逐白色的浪花，{weather}，{atmosphere}，浪花拍打沙滩，吉卜力动画风格",
            "captions": [
                "小布和浪花玩了一下午，每次浪退就追、浪来就逃 😂",
                "追浪花是沙滩上最好玩的游戏，没有之一！",
                "看小布和浪花斗智斗勇，太可爱了～",
            ],
            "stories": [
                "阳光沙滩上，小布正在进行它最喜欢的活动——追浪花。它的策略是：等浪退到最远的时候冲过去，然后在下一波浪来之前赶紧往回跑。但今天有几次判断失误，被浪花轻轻拍到了屁股，小布假装生气地对着大海叫了两声，然后又乐此不疲地继续了。",
            ],
        },
        {
            "name": "挖沙坑",
            "prompt_template": "{appearance} 在沙滩上认真地挖沙坑，{weather}，{atmosphere}，沙子飞溅，吉卜力动画风格",
            "captions": [
                "小布今天挖了一个超大的沙坑，差点把自己埋进去 🕳️",
                "沙滩工程队队长小布正在施工中，请勿打扰～",
            ],
            "stories": [
                "小布今天在沙滩上挖了一个巨大无比的坑。它刨沙子的速度惊人，沙子向身后飞出去老远。旁边的狗狗们都来看热闹，说小布是不是想挖通到地球另一边的汪星。小布不理它们，继续埋头苦干，直到坑快有自己两个大了才满意地趴在里面一个完美的沙坑沙发！",
            ],
        },
        {
            "name": "晒太阳",
            "prompt_template": "{appearance} 懒洋洋地躺在沙滩上晒太阳，{weather}，{atmosphere}，温暖的阳光洒在身上，吉卜力动画风格",
            "captions": [
                "小布摊成了一张毛茸茸的煎饼，舒服得不想动 ☀️",
                "今日活动：晒太阳。任务完成度：100%",
            ],
            "stories": [
                "今天的阳光太好了，小布找了个最舒服的位置，直接趴在沙滩上摊成了一张狗饼。海风轻轻吹过，阳光暖洋洋地照在肚皮上，小布幸福地叹了口气，眼睛慢慢眯了起来。旁边有狗狗叫它去玩，小布只是摇了摇尾巴表示收到了但不想动。",
            ],
        },
        {
            "name": "捡贝壳",
            "prompt_template": "{appearance} 在沙滩上仔细寻找美丽的贝壳，{weather}，{atmosphere}，沙滩上散落着五彩贝壳，吉卜力动画风格",
            "captions": [
                "小布发现了一枚闪闪发光的贝壳！🐚",
                "今天是满载而归的一天～小布的贝壳收藏又增加了",
            ],
            "stories": [
                "小布在沙滩上慢慢走着，鼻子凑近地面仔细嗅着。突然它停下了，用爪子轻轻拨开沙子——一枚泛着珍珠光泽的粉色贝壳露了出来！小布兴奋地摇着尾巴，小心翼翼地把贝壳叼起来。这是它贝壳收藏里最漂亮的一枚了，它决定存起来，等下次家人来汪星的时候送给他们。",
            ],
        },
    ]

    # NOTE: For the full plan, the remaining 58 locations follow the same pattern.
    # Each location gets 3-5 activities with appropriate Chinese story content.
    # The complete activities_data.py will be ~2500-3500 lines covering:
    # - 60 locations × ~4 activities = ~250 activities
    # - Each with 3-5 captions and 3-5 stories = ~1200+ each
    #
    # Full content is generated during implementation in the actual file.

    return activities
```

- [ ] **Step 3: Create seed/generate_seed.py**

```python
"""Seed the database with all locations, activities, and templates."""
from models import get_session, Region, Location, Activity, init_db
from seed.locations_data import REGIONS, CROSS_REGION_CONNECTIONS
from seed.activities_data import generate_activities


def seed():
    init_db()
    session = get_session()

    if session.query(Region).count() > 0:
        print("Database already seeded. Skipping.")
        session.close()
        return

    location_map = {}
    for region_data in REGIONS:
        region = Region(name=region_data["name"], description=region_data["description"])
        session.add(region)
        session.flush()

        loc_names = [l[0] for l in region_data["locations"]]
        for i, (name, desc, atmosphere) in enumerate(region_data["locations"]):
            adj_names = []
            if i > 0:
                adj_names.append(loc_names[i - 1])
            if i < len(loc_names) - 1:
                adj_names.append(loc_names[i + 1])

            loc = Location(
                region_id=region.id,
                name=name,
                description=desc,
                atmosphere=atmosphere,
                adjacent_locations=adj_names,  # resolved to IDs below
            )
            session.add(loc)
            session.flush()
            location_map[name] = loc

    # Resolve adjacent names to IDs
    for region_data in REGIONS:
        loc_names = [l[0] for l in region_data["locations"]]
        for i, (name, desc, atmosphere) in enumerate(region_data["locations"]):
            adj_ids = []
            if i > 0:
                adj_ids.append(location_map[loc_names[i - 1]].id)
            if i < len(loc_names) - 1:
                adj_ids.append(location_map[loc_names[i + 1]].id)
            location_map[name].adjacent_locations = adj_ids

    # Add cross-region connections
    for from_name, to_name in CROSS_REGION_CONNECTIONS:
        if from_name in location_map and to_name in location_map:
            fl, tl = location_map[from_name], location_map[to_name]
            adj = list(fl.adjacent_locations or [])
            if tl.id not in adj:
                adj.append(tl.id)
                fl.adjacent_locations = adj
            adj2 = list(tl.adjacent_locations or [])
            if fl.id not in adj2:
                adj2.append(fl.id)
                tl.adjacent_locations = adj2

    session.flush()

    # Create activities
    all_activities = generate_activities()
    for loc_name, acts in all_activities.items():
        loc = location_map.get(loc_name)
        if not loc:
            continue
        for act_data in acts:
            activity = Activity(
                location_id=loc.id,
                name=act_data["name"],
                prompt_template=act_data["prompt_template"],
                captions=act_data["captions"],
                stories=act_data["stories"],
            )
            session.add(activity)

    session.commit()
    print(f"Seeded: {session.query(Region).count()} regions, "
          f"{session.query(Location).count()} locations, "
          f"{session.query(Activity).count()} activities")
    session.close()


if __name__ == "__main__":
    seed()
```

- [ ] **Step 4: Verify seed framework**

Run: `python -c "from seed.locations_data import REGIONS; print(f'{len(REGIONS)} regions, {sum(len(r[\"locations\"]) for r in REGIONS)} locations')"`
Expected: `5 regions, 60 locations`

- [ ] **Step 5: Commit**

```bash
git add seed/
git commit -m "feat: add seed framework with location data and activity definitions"
```

---

### Task 4: Image Generator Adapter

**Files:**
- Create: `engine/__init__.py`
- Create: `engine/image_gen.py`
- Create: `tests/__init__.py`
- Create: `tests/test_image_gen.py`

**Interfaces:**
- Produces: `ImageGenerator` ABC with `generate(prompt, reference_photos) -> str`
- Produces: `TongyiImageGenerator`, `OpenAIImageGenerator`, `FakeGenerator`
- Produces: `get_image_generator(api_type=None) -> ImageGenerator`

- [ ] **Step 1: Write the test first**

Create: `tests/test_image_gen.py`

```python
from pathlib import Path
from engine.image_gen import ImageGenerator, FakeGenerator, get_image_generator


def test_fake_generator_creates_image():
    gen = FakeGenerator()
    result = gen.generate("a cute dog playing at the beach", [])
    assert Path(result).exists()
    assert "generated" in result
    from PIL import Image
    img = Image.open(result)
    assert img.size == (512, 512)


def test_get_image_generator_fake():
    gen = get_image_generator("fake")
    assert isinstance(gen, ImageGenerator)


def test_get_image_generator_unknown_raises():
    try:
        get_image_generator("nonexistent")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_prompt_template_substitution():
    template = "{appearance} playing at {location} on a {weather} day, {atmosphere}"
    prompt = template.format(
        appearance="A cream colored corgi",
        location="beach",
        weather="sunny",
        atmosphere="warm golden light"
    )
    assert "corgi" in prompt
    assert "beach" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_image_gen.py -v`
Expected: FAIL — `No module named 'engine.image_gen'`

- [ ] **Step 3: Write engine/image_gen.py**

```python
import time
from abc import ABC, abstractmethod
from pathlib import Path
from config import settings
import httpx
from PIL import Image


class ImageGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        """Generate an image. Returns the path to the saved image file."""
        ...


class FakeGenerator(ImageGenerator):
    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        img = Image.new("RGB", (512, 512), color=(255, 200, 150))
        ts = int(time.time() * 1000)
        output = settings.GENERATED_DIR / f"xiaobu_{ts}.png"
        img.save(output)
        return str(output)


class TongyiImageGenerator(ImageGenerator):
    API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"

    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        headers = {
            "Authorization": f"Bearer {settings.IMAGE_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "wanx-v1",
            "input": {"prompt": prompt},
            "parameters": {"size": "1024*1024", "n": 1},
        }
        if reference_photos:
            payload["input"]["ref_img"] = reference_photos[0]

        resp = httpx.post(self.API_URL, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        image_url = data["output"]["results"][0]["url"]
        img_resp = httpx.get(image_url, timeout=60)
        img_resp.raise_for_status()

        ts = int(time.time() * 1000)
        output_path = settings.GENERATED_DIR / f"xiaobu_{ts}.png"
        output_path.write_bytes(img_resp.content)
        return str(output_path)


class OpenAIImageGenerator(ImageGenerator):
    API_URL = "https://api.openai.com/v1/images/generations"

    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        headers = {
            "Authorization": f"Bearer {settings.IMAGE_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
        }
        resp = httpx.post(self.API_URL, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        image_url = data["data"][0]["url"]
        img_resp = httpx.get(image_url, timeout=60)
        img_resp.raise_for_status()

        ts = int(time.time() * 1000)
        output_path = settings.GENERATED_DIR / f"xiaobu_{ts}.png"
        output_path.write_bytes(img_resp.content)
        return str(output_path)


GENERATORS = {
    "tongyi": TongyiImageGenerator,
    "openai": OpenAIImageGenerator,
    "fake": FakeGenerator,
}


def get_image_generator(api_type: str = None) -> ImageGenerator:
    api_type = api_type or settings.IMAGE_API_TYPE
    cls = GENERATORS.get(api_type)
    if cls is None:
        raise ValueError(f"Unknown image API type: {api_type}. Available: {list(GENERATORS.keys())}")
    return cls()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_image_gen.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/ engine/
git commit -m "feat: add image generator adapter with Tongyi, OpenAI, and fake backends"
```

---

### Task 5: State Machine Engine

**Files:**
- Create: `engine/state_machine.py`
- Create: `tests/test_state_machine.py`

**Interfaces:**
- Consumes: `models.Location`, `models.JourneyState`, `models.Profile`
- Produces: `StateMachine.select_next_location(state, profile) -> Location`
- Produces: `StateMachine.select_activity(location, profile) -> Activity`
- Produces: `StateMachine.roll_weather() -> str`
- Produces: `StateMachine.update_mood(current_mood, activity_name) -> str`

- [ ] **Step 1: Write tests**

Create: `tests/test_state_machine.py`

```python
from unittest.mock import MagicMock, patch
from engine.state_machine import StateMachine


class TestStateMachine:
    def setup_method(self):
        self.sm = StateMachine()

    def test_roll_weather_returns_valid(self):
        for _ in range(20):
            assert self.sm.roll_weather() in ["晴", "多云", "小雨", "彩虹"]

    def test_roll_weather_distribution(self):
        results = {"晴": 0, "多云": 0, "小雨": 0, "彩虹": 0}
        for _ in range(1000):
            results[self.sm.roll_weather()] += 1
        assert results["晴"] > 350
        assert results["多云"] > 200

    def test_select_next_location_from_adjacent(self):
        state = MagicMock()
        state.current_location_id = 1
        loc_a, loc_b, loc_c = MagicMock(), MagicMock(), MagicMock()
        loc_a.id, loc_a.adjacent_locations = 1, [2, 3]
        loc_b.id, loc_b.name = 2, "B"
        loc_c.id, loc_c.name = 3, "C"

        with patch("engine.state_machine.get_session") as mock_sess:
            mock_db = MagicMock()
            mock_sess.return_value = mock_db
            mock_db.get.side_effect = lambda m, id: {1: loc_a, 2: loc_b, 3: loc_c}[id]
            for _ in range(50):
                result = self.sm.select_next_location(state, None)
                assert result.id in [2, 3]

    def test_select_activity_from_pool(self):
        loc = MagicMock()
        act1, act2 = MagicMock(), MagicMock()
        act1.name, act2.name = "running", "sleeping"
        loc.activities = [act1, act2]
        results = set()
        for _ in range(50):
            results.add(self.sm.select_activity(loc, None).name)
        assert "running" in results and "sleeping" in results

    def test_update_mood_changes(self):
        moods = set()
        for _ in range(30):
            moods.add(self.sm.update_mood("开心", "exploring"))
        assert len(moods) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_state_machine.py -v`
Expected: FAIL

- [ ] **Step 3: Write engine/state_machine.py**

```python
import random
from models import get_session, Location, Activity, JourneyState, Profile


class StateMachine:
    WEATHER_WEIGHTS = [("晴", 50), ("多云", 30), ("小雨", 15), ("彩虹", 5)]
    MOODS = ["开心", "兴奋", "平静", "好奇", "不舍", "满足", "期待"]
    EXPLORATION_TAGS = {"好动", "爱探险", "好奇", "勇敢", "精力旺盛"}
    GOURMET_TAGS = {"贪吃", "爱吃", "美食家"}
    SOCIAL_TAGS = {"亲人", "爱社交", "友善", "热情"}
    COZY_TAGS = {"安静", "宅", "温柔", "胆小"}

    def roll_weather(self) -> str:
        options, weights = zip(*self.WEATHER_WEIGHTS)
        return random.choices(options, weights=weights, k=1)[0]

    def select_next_location(self, state: JourneyState, profile: Profile = None) -> Location:
        session = get_session()
        current_loc = session.get(Location, state.current_location_id)
        if not current_loc or not current_loc.adjacent_locations:
            session.close()
            return current_loc

        adj_ids = current_loc.adjacent_locations
        adj_locations = [session.get(Location, lid) for lid in adj_ids]
        adj_locations = [loc for loc in adj_locations if loc is not None]
        if not adj_locations:
            session.close()
            return current_loc

        weights = self._calculate_weights(adj_locations, profile)
        chosen = random.choices(adj_locations, weights=weights, k=1)[0]
        session.close()
        return chosen

    def _calculate_weights(self, locations: list[Location], profile: Profile = None) -> list[float]:
        weights = [1.0] * len(locations)
        if not profile or not profile.personality_tags:
            return weights
        tags = set(profile.personality_tags)
        for i, loc in enumerate(locations):
            region_name = loc.region.name if loc.region else ""
            if tags & self.EXPLORATION_TAGS and region_name in ["森林区", "山地区"]:
                weights[i] *= 1.5
            if tags & self.GOURMET_TAGS and ("美食" in loc.name or region_name == "小镇区"):
                weights[i] *= 1.5
            if tags & self.SOCIAL_TAGS and region_name in ["小镇区", "海滨区"]:
                weights[i] *= 1.3
            if tags & self.COZY_TAGS and region_name in ["原野区", "森林区"]:
                weights[i] *= 1.3
        return weights

    def select_activity(self, location: Location, profile: Profile = None) -> Activity:
        if not location.activities:
            return None
        return random.choice(list(location.activities))

    def update_mood(self, current_mood: str, activity_name: str) -> str:
        if random.random() < 0.7:
            return random.choice(["开心", "兴奋", "满足", "平静"])
        new_mood = random.choice(self.MOODS)
        while new_mood == current_mood and len(self.MOODS) > 1:
            new_mood = random.choice(self.MOODS)
        return new_mood
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_state_machine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/state_machine.py tests/test_state_machine.py
git commit -m "feat: add state machine for location/activity/weather/mood selection"
```

---

### Task 6: Storyteller Engine

**Files:**
- Create: `engine/storyteller.py`
- Create: `tests/test_storyteller.py`

**Interfaces:**
- Consumes: `models.Activity`, `models.Profile`
- Produces: `Storyteller.compose_story(activity, profile) -> str`
- Produces: `Storyteller.compose_prompt(activity, profile, weather, mood) -> str`

- [ ] **Step 1: Write tests**

Create: `tests/test_storyteller.py`

```python
from unittest.mock import MagicMock
from engine.storyteller import Storyteller


class TestStoryteller:
    def setup_method(self):
        self.storyteller = Storyteller()

    def test_compose_story_caption_preference(self):
        profile = MagicMock()
        profile.content_preference = "caption"
        activity = MagicMock()
        activity.captions = ["短句1", "短句2"]
        activity.stories = ["长故事"]
        for _ in range(20):
            assert self.storyteller.compose_story(activity, profile) in activity.captions

    def test_compose_story_story_preference(self):
        profile = MagicMock()
        profile.content_preference = "story"
        activity = MagicMock()
        activity.captions = ["短句"]
        activity.stories = ["一个温暖的长故事"]
        for _ in range(20):
            assert self.storyteller.compose_story(activity, profile) in activity.stories

    def test_compose_story_image_only_returns_empty(self):
        profile = MagicMock()
        profile.content_preference = "image_only"
        activity = MagicMock()
        activity.captions = ["测试"]
        assert self.storyteller.compose_story(activity, profile) == ""

    def test_compose_prompt_substitutes_all(self):
        profile = MagicMock()
        profile.appearance = "A cream colored corgi with big ears"
        activity = MagicMock()
        activity.prompt_template = "{appearance} at the beach, {weather} day, feeling {mood}, {atmosphere}"
        prompt = self.storyteller.compose_prompt(activity, profile, "晴", "开心")
        assert "cream colored corgi" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storyteller.py -v`
Expected: FAIL

- [ ] **Step 3: Write engine/storyteller.py**

```python
import random
from models import Activity, Profile


class Storyteller:
    def compose_story(self, activity: Activity, profile: Profile) -> str:
        if profile.content_preference == "image_only":
            return ""
        elif profile.content_preference == "story":
            pool = activity.stories or activity.captions or []
        else:
            pool = activity.captions or activity.stories or []
        if not pool:
            return ""
        return random.choice(pool)

    def compose_prompt(self, activity: Activity, profile: Profile, weather: str, mood: str) -> str:
        atmosphere = activity.location.atmosphere if activity.location else ""
        return activity.prompt_template.format(
            appearance=profile.appearance or "一只可爱的狗狗",
            weather=weather,
            mood=mood,
            atmosphere=atmosphere,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storyteller.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/storyteller.py tests/test_storyteller.py
git commit -m "feat: add storyteller for template-based story/prompt composition"
```

---

### Task 7: Scheduler

**Files:**
- Create: `scheduler.py`
- Create: `tests/test_scheduler.py`

**Interfaces:**
- Consumes: `engine.state_machine.StateMachine`, `engine.storyteller.Storyteller`, `engine.image_gen.get_image_generator`
- Produces: `Scheduler.start()` — starts APScheduler
- Produces: `Scheduler.plan_today()` — schedules 1-3 daily generation times
- Produces: `Scheduler.run_generation()` — full generation pipeline

- [ ] **Step 1: Write tests**

Create: `tests/test_scheduler.py`

```python
from datetime import datetime, time
from unittest.mock import MagicMock, patch
from scheduler import Scheduler


class TestScheduler:
    def test_generate_daily_times_count(self):
        for _ in range(50):
            times = Scheduler._generate_daily_times()
            assert 1 <= len(times) <= 3

    def test_generated_times_in_valid_hours(self):
        for _ in range(20):
            times = Scheduler._generate_daily_times()
            for t in times:
                valid = (6 <= t.hour <= 9) or (10 <= t.hour <= 12) or \
                        (14 <= t.hour <= 17) or (20 <= t.hour <= 22)
                assert valid, f"Hour {t.hour} invalid"

    def test_gap_at_least_4_hours(self):
        for _ in range(30):
            times = sorted(Scheduler._generate_daily_times())
            for i in range(len(times) - 1):
                gap = (datetime.combine(datetime.today(), times[i + 1]) -
                       datetime.combine(datetime.today(), times[i])).seconds / 3600
                assert gap >= 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scheduler.py -v`
Expected: FAIL

- [ ] **Step 3: Write scheduler.py**

```python
import random
from datetime import datetime, time, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from models import get_session, Profile, JourneyState, JourneyLog, Location, Activity, ScheduledTask
from engine.state_machine import StateMachine
from engine.storyteller import Storyteller
from engine.image_gen import get_image_generator


class Scheduler:
    TIME_SLOTS = [
        (6, 9, 30), (10, 12, 25), (14, 17, 30), (20, 22, 15),
    ]

    def __init__(self):
        self._aps = BackgroundScheduler()
        self.state_machine = StateMachine()
        self.storyteller = Storyteller()

    def start(self):
        self._aps.add_job(self.plan_today, trigger="cron", hour=0, minute=1, id="plan_today", replace_existing=True)
        self._aps.start()

    def plan_today(self):
        session = get_session()
        pending = session.query(ScheduledTask).filter_by(status="pending").all()
        for task in pending:
            task.status = "cancelled"
        session.commit()

        times = self._generate_daily_times()
        now = datetime.now()
        for t in times:
            scheduled_dt = datetime(now.year, now.month, now.day, t.hour, t.minute)
            task = ScheduledTask(scheduled_at=scheduled_dt, status="pending")
            session.add(task)
            session.flush()
            self._aps.add_job(self.run_generation, trigger="date", run_date=scheduled_dt, id=f"gen_{task.id}", replace_existing=True)
        session.commit()
        session.close()

    @staticmethod
    def _generate_daily_times() -> list[time]:
        num_events = random.choices([1, 2, 3], weights=[30, 50, 20], k=1)[0]
        for _ in range(100):
            chosen = []
            for _ in range(num_events):
                slot = random.choices(Scheduler.TIME_SLOTS, weights=[s[2] for s in Scheduler.TIME_SLOTS], k=1)[0]
                hour = random.randint(slot[0], slot[1] - 1)
                minute = random.randint(0, 59)
                chosen.append(time(hour, minute))
            chosen.sort()
            valid = True
            for i in range(len(chosen) - 1):
                gap = (datetime.combine(datetime.today(), chosen[i + 1]) -
                       datetime.combine(datetime.today(), chosen[i])).seconds / 3600
                if gap < 4:
                    valid = False
                    break
            if valid:
                return chosen
        return [time(10, 0)]

    def run_generation(self):
        session = get_session()
        try:
            profile = session.query(Profile).first()
            if not profile:
                session.close()
                return

            state = session.query(JourneyState).first()
            if not state:
                rainbow = session.query(Location).filter_by(name="彩虹桥").first()
                state = JourneyState(current_location_id=rainbow.id if rainbow else None)
                session.add(state)
                session.flush()

            weather = self.state_machine.roll_weather()
            next_location = self.state_machine.select_next_location(state, profile)
            activity = self.state_machine.select_activity(next_location, profile)
            if not activity:
                session.close()
                return

            prompt = self.storyteller.compose_prompt(activity, profile, weather, state.mood)
            image_gen = get_image_generator()
            image_path = image_gen.generate(prompt, profile.reference_photos or [])
            story = self.storyteller.compose_story(activity, profile)
            new_mood = self.state_machine.update_mood(state.mood, activity.name)

            log_entry = JourneyLog(
                location_id=next_location.id, activity_id=activity.id,
                story_text=story, image_path=image_path,
                weather=weather, mood=new_mood, generated_at=datetime.now(),
            )
            session.add(log_entry)
            session.flush()

            state.current_location_id = next_location.id
            state.mood = new_mood
            state.day_number += 1
            state.weather_today = weather
            state.last_activity_id = activity.id

            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_scheduler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scheduler.py tests/test_scheduler.py
git commit -m "feat: add scheduler with daily planning and generation pipeline"
```

---

### Task 8: Static Assets

**Files:**
- Create: `static/css/style.css`
- Create: `static/js/app.js`

**Interfaces:**
- Produces: Warm healing visual theme CSS
- Produces: Photo upload preview, drag-drop, tag selection JS

- [ ] **Step 1: Write static/css/style.css**

```css
:root {
    --color-warm-bg: #FFF8F0; --color-card-bg: #FFFFFF;
    --color-accent: #E8936B; --color-accent-dark: #D4785A;
    --color-text: #3D2C2A; --color-text-light: #8B7B78;
    --color-border: #F0E0D0; --shadow-card: 0 2px 16px rgba(0,0,0,0.06);
    --radius: 16px; --radius-sm: 8px; --max-width: 720px;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 16px; }
body { font-family: "PingFang SC","Microsoft YaHei",sans-serif; background: var(--color-warm-bg); color: var(--color-text); line-height: 1.6; }
.container { max-width: var(--max-width); margin: 0 auto; padding: 0 20px; }
.site-header { padding: 24px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--color-border); margin-bottom: 32px; }
.site-header h1 { font-size: 1.5rem; color: var(--color-accent); }
.site-header nav a { color: var(--color-text-light); text-decoration: none; margin-left: 20px; font-size: 0.95rem; }
.site-header nav a:hover { color: var(--color-accent); }

.status-bar { background: var(--color-card-bg); border-radius: var(--radius); padding: 20px 24px; box-shadow: var(--shadow-card); display: flex; justify-content: space-around; text-align: center; margin-bottom: 32px; }
.status-item .label { font-size: 0.8rem; color: var(--color-text-light); margin-bottom: 4px; }
.status-item .value { font-size: 1.1rem; font-weight: 500; }

.hero-card { background: var(--color-card-bg); border-radius: var(--radius); box-shadow: var(--shadow-card); overflow: hidden; margin-bottom: 32px; }
.hero-card img { width: 100%; max-height: 600px; object-fit: contain; background: #FAFAFA; display: block; }
.hero-card .story { padding: 20px 24px; font-size: 1.05rem; line-height: 1.8; }
.hero-card .meta { padding: 0 24px 16px; font-size: 0.85rem; color: var(--color-text-light); display: flex; gap: 16px; flex-wrap: wrap; }

.timeline-title { font-size: 1.2rem; font-weight: 600; margin-bottom: 16px; }
.timeline { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; margin-bottom: 48px; }
.timeline-card { background: var(--color-card-bg); border-radius: var(--radius-sm); box-shadow: var(--shadow-card); overflow: hidden; transition: transform 0.2s; }
.timeline-card:hover { transform: translateY(-4px); }
.timeline-card img { width: 100%; height: 180px; object-fit: cover; display: block; }
.timeline-card .info { padding: 12px 14px; }
.timeline-card .info .date { font-size: 0.8rem; color: var(--color-text-light); margin-bottom: 4px; }
.timeline-card .info .caption { font-size: 0.9rem; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

.form-page { background: var(--color-card-bg); border-radius: var(--radius); box-shadow: var(--shadow-card); padding: 32px; margin-bottom: 48px; }
.form-page h2 { font-size: 1.3rem; margin-bottom: 24px; color: var(--color-accent); }
.form-group { margin-bottom: 20px; }
.form-group label { display: block; font-weight: 500; margin-bottom: 6px; font-size: 0.95rem; }
.form-group input[type="text"], .form-group input[type="number"], .form-group textarea, .form-group select { width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: 0.95rem; background: #FAFAFA; transition: border-color 0.2s; font-family: inherit; }
.form-group input:focus, .form-group textarea:focus, .form-group select:focus { outline: none; border-color: var(--color-accent); }
.form-group textarea { min-height: 100px; resize: vertical; }

.tag-group { display: flex; flex-wrap: wrap; gap: 8px; }
.tag { padding: 6px 14px; border: 1px solid var(--color-border); border-radius: 20px; cursor: pointer; font-size: 0.9rem; transition: all 0.2s; user-select: none; }
.tag:hover { border-color: var(--color-accent); }
.tag.selected { background: var(--color-accent); color: white; border-color: var(--color-accent); }

.upload-zone { border: 2px dashed var(--color-border); border-radius: var(--radius); padding: 32px; text-align: center; cursor: pointer; transition: all 0.2s; background: #FAFAFA; }
.upload-zone:hover, .upload-zone.dragover { border-color: var(--color-accent); background: #FFF5F0; }
.upload-zone .hint { color: var(--color-text-light); font-size: 0.9rem; }
.photo-previews { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
.photo-preview { width: 80px; height: 80px; border-radius: var(--radius-sm); object-fit: cover; }
.photo-preview-wrapper { position: relative; }
.photo-preview-wrapper .remove { position: absolute; top: -6px; right: -6px; width: 22px; height: 22px; background: var(--color-accent); color: white; border-radius: 50%; border: none; cursor: pointer; font-size: 14px; line-height: 22px; text-align: center; }

.btn { display: inline-block; padding: 10px 24px; border: none; border-radius: 24px; font-size: 1rem; cursor: pointer; transition: all 0.2s; font-family: inherit; }
.btn-primary { background: var(--color-accent); color: white; }
.btn-primary:hover { background: var(--color-accent-dark); }
.btn-submit { width: 100%; padding: 12px; font-size: 1.05rem; margin-top: 16px; }

.empty-state { text-align: center; padding: 80px 20px; color: var(--color-text-light); }
.empty-state .icon { font-size: 3rem; margin-bottom: 16px; }
.empty-state p { font-size: 1.05rem; }

@media (max-width: 640px) {
    .status-bar { flex-wrap: wrap; gap: 12px; }
    .timeline { grid-template-columns: 1fr; }
    .hero-card img { max-height: 400px; }
}
```

- [ ] **Step 2: Write static/js/app.js**

```javascript
function initPhotoUpload() {
    const zone = document.getElementById("upload-zone");
    const input = document.getElementById("photo-input");
    const previews = document.getElementById("photo-previews");
    const maxPhotos = 10;
    let files = new DataTransfer();

    if (!zone || !input) return;
    zone.addEventListener("click", () => input.click());
    zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
    zone.addEventListener("drop", e => { e.preventDefault(); zone.classList.remove("dragover"); addFiles(e.dataTransfer.files); });
    input.addEventListener("change", () => { addFiles(input.files); input.value = ""; });

    function addFiles(newFiles) {
        for (const file of newFiles) {
            if (files.files.length >= maxPhotos) { alert(`最多上传${maxPhotos}张照片`); break; }
            if (!file.type.startsWith("image/")) continue;
            files.items.add(file);
        }
        renderPreviews();
    }
    function renderPreviews() {
        previews.innerHTML = "";
        for (let i = 0; i < files.files.length; i++) {
            const url = URL.createObjectURL(files.files[i]);
            const w = document.createElement("div");
            w.className = "photo-preview-wrapper";
            w.innerHTML = `<img src="${url}" class="photo-preview" alt="预览"><button class="remove" data-index="${i}" type="button">&times;</button>`;
            w.querySelector(".remove").addEventListener("click", () => {
                const nf = new DataTransfer();
                for (let j = 0; j < files.files.length; j++) if (j !== i) nf.items.add(files.files[j]);
                files = nf; renderPreviews();
            });
            previews.appendChild(w);
        }
        document.getElementById("photo-count").textContent = `${files.files.length}/${maxPhotos}`;
    }
}

function initTagGroups() {
    document.querySelectorAll(".tag-group").forEach(group => {
        group.addEventListener("click", e => {
            const tag = e.target.closest(".tag");
            if (!tag) return;
            if (group.dataset.multi !== "false") tag.classList.toggle("selected");
            else { group.querySelectorAll(".tag").forEach(t => t.classList.remove("selected")); tag.classList.add("selected"); }
            updateHiddenInput(group);
        });
    });
}

function updateHiddenInput(group) {
    const input = group.nextElementSibling;
    if (!input || !input.classList.contains("tag-value")) return;
    input.value = JSON.stringify(Array.from(group.querySelectorAll(".tag.selected")).map(t => t.textContent.trim()));
}

function initProfileForm() {
    const form = document.getElementById("profile-form");
    if (!form) return;
    form.addEventListener("submit", async e => {
        e.preventDefault();
        document.querySelectorAll(".tag-value").forEach(inp => {
            const selected = Array.from(inp.previousElementSibling.querySelectorAll(".tag.selected")).map(t => t.textContent.trim());
            inp.value = JSON.stringify(selected);
        });
        const fd = new FormData(form);
        const btn = form.querySelector(".btn-submit");
        btn.textContent = "保存中..."; btn.disabled = true;
        try {
            const resp = await fetch(form.action, { method: "POST", body: fd });
            if (resp.ok) window.location.href = "/";
            else { const err = await resp.json(); alert("保存失败: " + (err.detail || "未知错误")); }
        } catch (err) {
            alert("网络错误: " + err.message);
        } finally { btn.textContent = "保存"; btn.disabled = false; }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initPhotoUpload();
    initTagGroups();
    initProfileForm();
});
```

- [ ] **Step 3: Commit**

```bash
git add static/
git commit -m "feat: add static assets with warm healing theme and photo upload JS"
```

---

### Task 9: Base Template

**Files:**
- Create: `templates/base.html`

**Interfaces:**
- Produces: Jinja2 base layout with header nav and static asset links

- [ ] **Step 1: Write templates/base.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小布的旅行</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🐾</text></svg>">
</head>
<body>
    <header class="site-header">
        <h1>🐾 小布的旅行</h1>
        <nav>
            <a href="/">🏠 首页</a>
            <a href="/profile">⚙️ 档案</a>
        </nav>
    </header>
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    <script src="/static/js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify template compiles**

Run: `python -c "from jinja2 import Environment, FileSystemLoader; t = Environment(loader=FileSystemLoader('templates')).get_template('base.html'); print('OK')"`

- [ ] **Step 3: Commit**

```bash
git add templates/base.html
git commit -m "feat: add base HTML template"
```

---

### Task 10: Profile Page

**Files:**
- Create: `templates/profile.html`
- Create: `app.py` (initial with profile routes + static mounting)

**Interfaces:**
- Produces: GET `/profile` — form page
- Produces: POST `/profile` — save profile with photo uploads

- [ ] **Step 1: Write templates/profile.html**

```html
{% extends "base.html" %}
{% block content %}
<div class="form-page">
    <h2>📋 小布的档案</h2>
    <form id="profile-form" action="/profile" method="POST" enctype="multipart/form-data">
        <div class="form-group">
            <label>名字</label>
            <input type="text" name="name" value="{{ profile.name if profile else '小布' }}" required>
        </div>
        <div class="form-group">
            <label>品种</label>
            <input type="text" name="breed" value="{{ profile.breed if profile else '' }}" placeholder="例如：柯基">
        </div>
        <div class="form-group">
            <label>年龄（岁）</label>
            <input type="number" name="age" min="0" max="30" value="{{ profile.age if profile else 0 }}">
        </div>
        <div class="form-group">
            <label>外貌描述</label>
            <textarea name="appearance" placeholder="例如：奶油色短毛柯基，耳朵大而直立，背上有一块心形白斑...">{{ profile.appearance if profile else '' }}</textarea>
            <p style="font-size:0.8rem;color:var(--color-text-light);margin-top:4px;">越详细越好，AI 会根据描述生成小布在汪星的照片</p>
        </div>
        <div class="form-group">
            <label>性格标签（可多选）</label>
            <div class="tag-group" data-multi="true">
                {% for tag in ['活泼','亲人','贪吃','安静','勇敢','温柔','好奇','粘人','独立','精力旺盛','胆小','聪明'] %}
                <span class="tag {% if profile and tag in profile.personality_tags %}selected{% endif %}">{{ tag }}</span>
                {% endfor %}
            </div>
            <input type="hidden" name="personality_tags" class="tag-value" value='{{ profile.personality_tags | tojson if profile else "[]" }}'>
        </div>
        <div class="form-group">
            <label>兴趣爱好（可多选）</label>
            <div class="tag-group" data-multi="true">
                {% for tag in ['散步','追球','游泳','挖洞','晒太阳','结交新朋友','追尾巴','吃零食','坐车兜风','爬山','追鸟','打盹'] %}
                <span class="tag {% if profile and tag in profile.interests %}selected{% endif %}">{{ tag }}</span>
                {% endfor %}
            </div>
            <input type="hidden" name="interests" class="tag-value" value='{{ profile.interests | tojson if profile else "[]" }}'>
        </div>
        <div class="form-group">
            <label>生活习惯</label>
            <textarea name="habits" placeholder="例如：每天早上要出门散步，喜欢在沙发角落睡觉...">{{ profile.habits if profile else '' }}</textarea>
        </div>
        <div class="form-group">
            <label>内容偏好</label>
            <select name="content_preference">
                <option value="caption" {% if profile and profile.content_preference == 'caption' %}selected{% endif %}>🖼️ 图片 + 简短文字</option>
                <option value="story" {% if profile and profile.content_preference == 'story' %}selected{% endif %}>📖 图片 + 完整故事</option>
                <option value="image_only" {% if profile and profile.content_preference == 'image_only' %}selected{% endif %}>🖼️ 只要图片</option>
            </select>
        </div>
        <div class="form-group">
            <label>小布的照片（最多 10 张）</label>
            <div class="upload-zone" id="upload-zone">
                <p class="hint">📷 点击或拖拽上传照片</p>
                <p class="hint" style="font-size:0.8rem;" id="photo-count">0/10</p>
            </div>
            <input type="file" id="photo-input" accept="image/*" multiple style="display:none;">
            <div class="photo-previews" id="photo-previews">
                {% if profile and profile.reference_photos %}
                {% for photo in profile.reference_photos %}
                <div class="photo-preview-wrapper"><img src="/{{ photo }}" class="photo-preview" alt="小布"></div>
                {% endfor %}
                {% endif %}
            </div>
        </div>
        <button type="submit" class="btn btn-primary btn-submit">💾 保存档案</button>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 2: Write app.py**

```python
import json
import shutil
from pathlib import Path
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from models import get_session, Profile, init_db
from config import settings

app = FastAPI(title="小布的旅行")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")
templates = Jinja2Templates(directory="templates")


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    session = get_session()
    profile = session.query(Profile).first()
    session.close()
    return templates.TemplateResponse("profile.html", {"request": request, "profile": profile})


@app.post("/profile")
async def profile_save(
    request: Request,
    name: str = Form("小布"),
    breed: str = Form(""),
    age: int = Form(0),
    appearance: str = Form(""),
    personality_tags: str = Form("[]"),
    interests: str = Form("[]"),
    habits: str = Form(""),
    content_preference: str = Form("caption"),
    photos: list[UploadFile] = File([]),
):
    session = get_session()
    profile = session.query(Profile).first()
    if not profile:
        profile = Profile()
        session.add(profile)

    profile.name = name
    profile.breed = breed
    profile.age = age
    profile.appearance = appearance
    profile.personality_tags = json.loads(personality_tags) if personality_tags else []
    profile.interests = json.loads(interests) if interests else []
    profile.habits = habits
    profile.content_preference = content_preference

    existing = profile.reference_photos or []
    photo_paths = list(existing)
    for photo in photos:
        if photo.filename and photo.size > 0:
            if len(photo_paths) >= settings.MAX_REFERENCE_PHOTOS:
                break
            ext = Path(photo.filename).suffix or ".jpg"
            filename = f"ref_{name}_{len(photo_paths)}{ext}"
            filepath = settings.UPLOAD_DIR / filename
            with open(filepath, "wb") as f:
                shutil.copyfileobj(photo.file, f)
            photo_paths.append(str(filepath.relative_to(Path.cwd())))

    profile.reference_photos = photo_paths[:settings.MAX_REFERENCE_PHOTOS]
    session.commit()
    session.close()
    return RedirectResponse(url="/profile", status_code=303)
```

- [ ] **Step 3: Verify profile page renders**

Run:
```bash
python -c "
from fastapi.testclient import TestClient
from app import app
client = TestClient(app)
r = client.get('/profile')
assert r.status_code == 200 and '档案' in r.text
print('Profile page OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add templates/profile.html app.py
git commit -m "feat: add profile page with form, photo upload, and personality tags"
```

---

### Task 11: Index Page

**Files:**
- Create: `templates/index.html`
- Modify: `app.py` (add index route)

**Interfaces:**
- Consumes: `models.JourneyState`, `models.JourneyLog`, `models.Profile`, `models.Location`
- Produces: GET `/` — timeline with hero card and history

- [ ] **Step 1: Write templates/index.html**

```html
{% extends "base.html" %}
{% block content %}
{% if not logs %}
<div class="empty-state">
    <div class="icon">🐾</div>
    <p>小布的旅行即将开始...</p>
    <p style="font-size:0.9rem;color:var(--color-text-light);">先设置<a href="/profile">小布的档案</a>，然后小布就会从汪星发来照片啦</p>
</div>
{% else %}
<div class="status-bar">
    <div class="status-item"><div class="label">🐾 汪星第</div><div class="value">{{ state.day_number if state else 1 }} 天</div></div>
    <div class="status-item"><div class="label">📍 当前在</div><div class="value">{{ location.name if location else '彩虹桥' }}</div></div>
    <div class="status-item"><div class="label">🌤 今日天气</div><div class="value">{{ state.weather_today if state else '晴' }}</div></div>
    <div class="status-item"><div class="label">💭 心情</div><div class="value">{{ state.mood if state else '期待' }}</div></div>
</div>

{% set latest = logs[0] %}
<div class="hero-card">
    <img src="/{{ latest.image_path }}" alt="小布在{{ latest.location_name }}">
    {% if latest.story_text %}<div class="story">{{ latest.story_text }}</div>{% endif %}
    <div class="meta">
        <span>📍 {{ latest.location_name }}</span>
        <span>🌤 {{ latest.weather }}</span>
        <span>💭 {{ latest.mood }}</span>
        <span>{{ latest.generated_at.strftime('%m月%d日 %H:%M') }}</span>
    </div>
</div>

<div class="timeline-title">📸 过往瞬间</div>
<div class="timeline">
    {% for log in logs[1:] %}
    <div class="timeline-card">
        <img src="/{{ log.image_path }}" alt="小布在{{ log.location_name }}" loading="lazy">
        <div class="info">
            <div class="date">{{ log.generated_at.strftime('%m月%d日 %H:%M') }} · {{ log.location_name }}</div>
            {% if log.story_text %}<div class="caption">{{ log.story_text }}</div>{% endif %}
        </div>
    </div>
    {% endfor %}
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 2: Add index route to app.py**

Append to `app.py`:

```python
from models import JourneyState, JourneyLog, Location


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    session = get_session()
    state = session.query(JourneyState).first()
    logs = session.query(JourneyLog).order_by(JourneyLog.generated_at.desc()).all()

    location = None
    if state and state.current_location_id:
        location = session.query(Location).get(state.current_location_id)

    enriched = []
    for log in logs:
        loc_name = ""
        if log.location_id:
            loc = session.query(Location).get(log.location_id)
            loc_name = loc.name if loc else ""
        enriched.append({
            "id": log.id, "location_name": loc_name,
            "story_text": log.story_text, "image_path": log.image_path,
            "weather": log.weather, "mood": log.mood,
            "generated_at": log.generated_at,
        })

    session.close()
    return templates.TemplateResponse("index.html", {
        "request": request, "state": state, "location": location, "logs": enriched,
    })
```

- [ ] **Step 3: Verify index page renders**

Run:
```bash
python -c "
from fastapi.testclient import TestClient
from app import app
client = TestClient(app)
r = client.get('/')
assert r.status_code == 200 and '小布' in r.text
print('Index page OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add templates/index.html app.py
git commit -m "feat: add index page with hero card and history timeline"
```

---

### Task 12: App Startup & Entry Point

**Files:**
- Modify: `app.py` (add startup event)
- Create: `run.py`

- [ ] **Step 1: Add startup event to app.py**

Add to `app.py` imports and startup:

```python
from scheduler import Scheduler

@app.on_event("startup")
async def startup():
    init_db()
    scheduler = Scheduler()
    scheduler.start()
    print("🐾 小布的旅行开始啦！Scheduler started.")
```

- [ ] **Step 2: Create run.py**

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 3: Verify app starts**

```bash
timeout 5 python run.py 2>&1 || true
```

- [ ] **Step 4: Commit**

```bash
git add app.py run.py
git commit -m "feat: add startup event with DB init and scheduler, plus run.py"
```

---

### Task 13: Complete Seed Data (60 Locations)

**Files:**
- Modify: `seed/activities_data.py` — complete all 60 locations

- [ ] **Step 1: Complete activities_data.py for all 60 locations**

Extend the `generate_activities()` function to cover all 60 locations following the established pattern. Each location needs 3-5 activities, each with `prompt_template`, `captions` (3-5), and `stories` (3-5). Target: ~250 activities, ~1200+ captions, ~1200+ stories.

Template variables used throughout: `{appearance}`, `{weather}`, `{atmosphere}`, `{mood}`.

The full file is ~2500-3500 lines. Pattern reference (from Task 3):
```python
activities["地点名"] = [
    {
        "name": "活动名",
        "prompt_template": "{appearance} ... {weather} ... {atmosphere} ... 吉卜力动画风格，温暖治愈",
        "captions": ["短句1", "短句2", "短句3", "短句4"],
        "stories": ["故事1", "故事2", "故事3", "故事4"],
    },
    # ... 3-5 activities per location
]
```

Content guidelines per region:
- **海滨区**: beach/ocean activities (swimming, collecting shells, watching sunset, surfing, camping)
- **原野区**: meadow/flower activities (chasing butterflies, rolling in flowers, picnics, fruit picking)
- **山地区**: mountain activities (hiking, cloud watching, hot springs, echo calling, stargazing)
- **森林区**: forest activities (exploring, mushroom picking, reading in treehouse, swinging on vines)
- **小镇区**: town activities (cafe visits, shopping, market browsing, movie watching, bakery visits)

- [ ] **Step 2: Run seed and verify**

```bash
python -m seed.generate_seed
```
Expected: `Seeded: 5 regions, 60 locations, ~250 activities`

- [ ] **Step 3: Verify database integrity**

```bash
python -c "
from models import get_session, Location, Activity
s = get_session()
print(f'Locations: {s.query(Location).count()}')
print(f'Activities: {s.query(Activity).count()}')
# Check every location has activities
empty = s.query(Location).outerjoin(Activity).group_by(Location.id).having(s.func.count(Activity.id) == 0).all()
print(f'Locations without activities: {len(empty)}')
s.close()
"
```
Expected: 60 locations, ~250 activities, 0 locations without activities

- [ ] **Step 4: Commit**

```bash
git add seed/activities_data.py
git commit -m "feat: complete seed data for all 60 locations with activity and story templates"
```

---

### Task 14: Integration Tests

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration tests**

```python
from fastapi.testclient import TestClient
from app import app


def test_index_returns_200():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "小布的旅行" in resp.text


def test_profile_page_returns_200():
    client = TestClient(app)
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert "档案" in resp.text


def test_profile_save_works():
    client = TestClient(app)
    resp = client.post("/profile", data={
        "name": "小布",
        "breed": "柯基",
        "age": 3,
        "appearance": "一只奶油色柯基，大耳朵",
        "personality_tags": '["活泼","贪吃"]',
        "interests": '["追球","晒太阳"]',
        "habits": "每天早上要散步",
        "content_preference": "caption",
    })
    assert resp.status_code in [200, 303]
```

- [ ] **Step 2: Run integration tests**

```bash
IMAGE_API_TYPE=fake pytest tests/test_integration.py -v
```
Expected: PASS

- [ ] **Step 3: Run all tests**

```bash
IMAGE_API_TYPE=fake pytest tests/ -v
```
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration smoke tests"
```

---

### Task 15: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
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
├── engine/           # 状态机、文案、图片生成
├── templates/        # Jinja2 HTML 模板
├── static/           # CSS/JS
├── seed/             # 初始数据
└── tests/            # 测试
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup instructions"
```

---

## Implementation Order

Tasks should be executed sequentially (each depends on prior work):

1. Task 1 → Project scaffolding
2. Task 2 → Database models
3. Task 3 → Seed framework
4. Task 4 → Image generator
5. Task 5 → State machine
6. Task 6 → Storyteller
7. Task 7 → Scheduler
8. Task 8 → Static assets
9. Task 9 → Base template
10. Task 10 → Profile page
11. Task 11 → Index page
12. Task 12 → App startup wiring
13. Task 13 → Complete seed data
14. Task 14 → Integration tests
15. Task 15 → README
