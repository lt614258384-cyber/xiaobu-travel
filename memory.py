"""小布的汪星记忆管理 —— 累积所有旅程故事和人格，为 LLM 叙事提供完整上下文。"""

from pathlib import Path
from models import Profile


MEMORY_DIR = Path("data/features")


def get_memory_path(user_id: int) -> Path:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_DIR / f"{user_id}_memory.txt"


def build_memory(profile: Profile, features: str, all_stories: list[str]) -> str:
    """构建小布的完整记忆上下文，供 LLM 使用。"""
    dog_name = profile.name or "小布"
    personality = ", ".join(profile.personality_tags) if profile.personality_tags else "温柔、忠诚"
    interests = ", ".join(profile.interests) if profile.interests else "探索新地方"
    habits = profile.habits or "喜欢在阳光下打盹"
    appearance = features or profile.appearance or "一只可爱的狗狗"

    real_memories = profile.real_life_memories or ""

    parts = [
        f"# {dog_name}的汪星记忆",
        "",
        "## 我是谁",
        f"我是{dog_name}，{appearance}",
        f"我的性格：{personality}。",
        f"我喜欢：{interests}。",
        f"我的习惯：{habits}。",
    ]

    if real_memories.strip():
        parts += [
            "",
            "## 我还在家时（家人写下的真实回忆）",
            "以下是我还在家人身边时的真实故事和回忆。汪星的故事中要自然地延续这些记忆——"
            "比如去过的真实地方、喜欢的真实玩具、和家人做过的真实事情。",
            real_memories.strip(),
        ]

    parts += [
        "",
        "## 我的汪星旅程",
    ]

    if not all_stories:
        parts.append("（今天是我来到汪星的第一天，一切才刚刚开始。）")
    else:
        for i, story in enumerate(all_stories, 1):
            # Trim excessive length for older stories to save context
            if i < len(all_stories) - 10 and len(story) > 120:
                story = story[:120] + "…"
            parts.append(f"### 第{i}天")
            parts.append(story)
            parts.append("")

    return "\n".join(parts)


def save_memory(user_id: int, profile: Profile, features: str, all_stories: list[str]) -> Path:
    """持久化记忆文件到磁盘。"""
    content = build_memory(profile, features, all_stories)
    path = get_memory_path(user_id)
    path.write_text(content, encoding="utf-8")
    return path


def load_memory_context(user_id: int) -> str:
    """加载记忆文件内容作为 LLM 上下文。不存在则返回空字符串。"""
    path = get_memory_path(user_id)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""
