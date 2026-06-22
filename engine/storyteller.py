import random
import httpx
from models import Activity, Profile


STORY_CONFIGS = {
    "volcano": {
        "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "model": "ep-20260622031722-sdjgh",
    },
    "yunwu": {
        "url": "https://yunwu.ai/v1/chat/completions",
        "model": "deepseek-v4-pro",
    },
}

# Action & composition variety for image prompts
# Mix of candid lifestyle shots, playful moments, and quiet observations
ACTIONS = [
    # Playing & active
    "正在追逐一只蝴蝶，前爪扑空，尾巴兴奋地摇成模糊的影子",
    "和一只小螃蟹在沙滩上玩捉迷藏，鼻子凑近沙洞，好奇地嗅着",
    "叼着一根比身体还长的树枝，得意地小跑着，耳朵一颠一颠",
    "在浅水里蹦跳着追自己的倒影，水花四溅，阳光在水珠里碎成彩虹",
    "正用爪子刨沙坑，沙粒飞溅，已经挖出一个浅浅的窝，耳朵沾着沙",
    "叼着玩具球跑向镜头，眼神亮晶晶的，像是要把球送给你",
    "和海鸥面对面站着，互相歪头打量对方，保持着一个礼貌的距离",
    "在草地上打滚，四脚朝天扭来扭去，露出肚皮，表情陶醉",
    # Quiet & observant
    "低头嗅着一丛野花，鼻尖快要碰到花瓣，闭着眼睛很专注的样子",
    "坐在礁石上看夕阳，背影小小的，面前是金色的大海，海风吹动毛发",
    "趴在草地上的野餐垫旁边，下巴搁在垫子边缘，眼巴巴看着篮子里的食物",
    "蹲在岸边，一只前爪伸进水里试探温度，小心翼翼地",
    "倚靠在另一只大狗身边打盹，呼吸均匀，毛贴着对方的毛，很安心的样子",
    "坐在码头木板上，旁边放着一顶小草帽和半块饼干，像是在等待什么",
    "站在开满野花的山坡上，风把毛吹得向后飘起，眯着眼迎着风",
    # Exploration & curiosity
    "从灌木丛里探出半个脑袋，鼻子上沾着一片叶子，浑然不觉",
    "小心翼翼踩过一串石头过小溪，爪子张开保持平衡，尾巴紧张地僵住",
    "站在一棵开花的树下，花瓣正落下来，仰头看着，有一片停在鼻尖上",
    "用鼻子拱开一扇虚掩的木栅栏门，半个身子已经挤进去了",
    "在沙滩上留下一串梅花形脚印，边走边回头看脚印，像在检查自己的作品",
    "爬上一块大石头，站在最高处环顾四周，像一个小小的探险家",
]
STALE_ACTIONS = ACTIONS  # keep old name working until references updated

COMPOSITIONS = [
    "抓拍风格，画面有轻微的自然动感模糊，像生活中真实按下快门的瞬间",
    "从狗的视角拍摄，低机位，世界显得又大又奇妙",
    "中距离平视，像蹲下来和狗对话的高度，亲切平等",
    "环境人像风格，狗在画面一侧，周围是大片美丽的风景",
    "特写局部——只拍爪子和沙地或花瓣的互动，含蓄而温暖",
    "广角远景，一只小狗在大世界里，渺小但自在",
    "透过花丛或草丛间隙偷拍的感觉，前景虚化的花草形成天然画框",
    "正面中景，狗狗直视镜头，像是在和你分享它发现的新鲜事",
]

MOOD_LIGHTING = [
    "柔和温暖的午后阳光，画面有淡淡的金色光晕",
    "清晨薄雾中，光线柔和偏蓝，空气感强，露水未干",
    "黄昏时分，长影子，暖橙色光线洒满画面",
    "阴天柔和的散射光，色彩淡雅安静，像雨后的清新",
    "星光或月光下，画面偏蓝紫色调，静谧温柔",
    "透过树叶的斑驳光影洒在狗身上，明暗交错，生动自然",
]


class Storyteller:
    def compose_story(
        self,
        activity: Activity,
        profile: Profile,
        weather: str = "",
        mood: str = "",
        features: str = "",
        memory_context: str = "",
        all_stories_count: int = 0,
        api_key: str = "",
        api_provider: str = "volcano",
    ) -> str:
        # Try LLM story generation if API key is available
        if api_key:
            try:
                story = self._generate_story_llm(
                    activity=activity,
                    profile=profile,
                    weather=weather,
                    mood=mood,
                    features=features,
                    memory_context=memory_context,
                    all_stories_count=all_stories_count,
                    api_key=api_key,
                    api_provider=api_provider,
                )
                if story:
                    return story
            except Exception as e:
                print(f"LLM story generation failed, falling back to template: {e}")

        # Fall back to template-based story
        pool = activity.stories or activity.captions or []
        if not pool:
            return ""
        return random.choice(pool)

    def _generate_story_llm(
        self,
        activity: Activity,
        profile: Profile,
        weather: str,
        mood: str,
        features: str,
        memory_context: str,
        all_stories_count: int,
        api_key: str,
        api_provider: str = "volcano",
    ) -> str:
        dog_name = profile.name or "小布"
        dog_desc = features if features else (profile.appearance or f"一只可爱的{profile.breed or '狗狗'}")
        # Extract breed from features (e.g. "1. 品种：金毛寻回犬。" → "金毛寻回犬")
        breed_name = profile.breed or "狗狗"
        if features and "品种" in features:
            for line in features.split("\n"):
                if "品种" in line:
                    breed_name = line.split("：")[-1].split("。")[0].strip() or breed_name
                    break
        location_name = activity.location.name if activity.location else "一个美丽的地方"
        atmosphere = activity.location.atmosphere if activity.location else ""
        activity_name = activity.name

        system_prompt = (
            f"你是{dog_name}。你就是{dog_name}本人。没有另一个叫{dog_name}的角色。"
            f"你是一只{breed_name}，正在汪星旅行。汪星是宠物离世后的温暖世界。"
            f"用第一人称\"我\"写旅行日记——所有叙述必须用\"我\"，严禁用\"{dog_name}\"或任何第三人称指代自己。"
            f"用狗狗的感官——闻到什么、听到什么、"
            f"爪子踩到什么。尾巴摇代表开心。100-200字。温暖、童趣、不煽情。"
            f"像给家人写明信片一样自然，不要说\"第几天\"或\"第几次\"，不要用括号加注。"
            f"每次写新的地点和新的体验，用全新的感官细节——气味、声音、触感、光线。"
            f"不要反复提到胡萝卜饼、寄居蟹、摇尾巴。每篇要有独特的具体意象。"
        )

        # Memory as light seasoning, not main ingredient
        memory_section = ""
        if memory_context:
            memory_section = (
                f"以下是你的过往经历，仅供参考——你可以在合适时自然地带到一笔"
                f"（比如\"像上次在贝壳湾那样\"），但今天的重点是全新的体验。\n\n"
                f"{memory_context}\n\n"
            )
        else:
            memory_section = "这是你刚来到汪星，一切才刚刚开始。\n\n"

        user_message = (
            f"{memory_section}"
            f"今天你来到了{location_name}，正在{activity_name}。"
            f"天气{weather}，心情{mood}。{atmosphere}"
            f"\n\n写一段今天的旅行日记。严格用第一人称\"我\"叙述。"
            f"重点描写今天这个新地方的具体细节——看到了什么特别的、听到了什么声音、"
            f"闻到了什么气味、爪子底下是什么触感。"
            f"禁止出现\"{dog_name}\"这个词。禁止使用第三人称。"
        )

        config = STORY_CONFIGS.get(api_provider, STORY_CONFIGS["volcano"])

        resp = httpx.post(
            config["url"],
            json={
                "model": config["model"],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 400,
                "temperature": 0.9,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )

        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            # Remove common artifacts
            for prefix in ["《", "【", "\"", '"', "'", "'"]:
                if content.startswith(prefix):
                    content = content[1:]
            for suffix in ["》", "】", "\"", '"', "'", "'"]:
                if content.endswith(suffix):
                    content = content[:-1]
            return content if len(content) >= 20 else ""
        else:
            print(f"LLM API error: {resp.status_code} {resp.text[:200]}")
            return ""

    def compose_prompt(self, activity: Activity, profile: Profile, weather: str, mood: str, features: str = "", story_text: str = "") -> str:
        atmosphere = activity.location.atmosphere if activity.location else ""
        location_name = activity.location.name if activity.location else "一个新的地方"

        dog_desc = features if features else (profile.appearance or f"一只可爱的{profile.breed or '狗狗'}")
        # Extract breed from features for image prompt
        breed_name = profile.breed or ""
        if features and "品种" in features:
            for line in features.split("\n"):
                if "品种" in line:
                    breed_name = line.split("：")[-1].split("。")[0].strip() or breed_name
                    break
        if breed_name and breed_name not in dog_desc:
            dog_desc = f"{breed_name}。{dog_desc}"

        # ── Multi-panel comic strip when story is available ──
        if story_text:
            prompt = (
                f"创建一张3行×2列的照片拼贴网格，共6个方形格子，用极细的白色线条分隔。"
                f"每一格都是从以下旅行故事中提取的1个关键场景，从左到右、从上到下按时间顺序排列，串联起来像一部微型连环画。"
                f"\n\n"
                f"角色：{dog_desc}。所有格子中这只{dog_desc}的外貌特征保持完全一致。"
                f"地点：{location_name}。氛围：{atmosphere}。天气：{weather}。心情：{mood}。"
                f"\n\n"
                f"旅行故事（请从中提取6个关键时刻，每格1个）：\n{story_text[:500]}"
                f"\n\n"
                f"温暖治愈的旅行摄影风格。低饱和暖色调，柔和自然光，清新蓝绿与金黄配色。"
                f"背景细节丰富但柔和。画面如同旅行明信片拼贴。"
                f"避免：3D渲染感、塑料质感、高饱和、变形、模糊、不同品种的狗、文字气泡或字幕。"
            )
            return prompt

        # ── Fallback: single image when no story ──
        action = random.choice(ACTIONS)
        composition = random.choice(COMPOSITIONS)
        lighting = random.choice(MOOD_LIGHTING)

        base = (
            f"{dog_desc}。"
            f"地点：{location_name}。正在：{activity.name}。"
            f"天气：{weather}。氛围：{atmosphere}。"
            f"动作与姿态：{action}。"
            f"构图：{composition}。"
            f"光线：{lighting}。"
            ", 温暖治愈的旅行摄影风格"
            ", 狗狗保持参考图中的品种、毛色、体型、耳朵形状、五官特征完全相同"
            ", 毛发层次分明自然，面部特征清晰可辨"
            ", 低饱和暖色调，柔和自然光，清新蓝绿与金黄配色"
            ", 背景细节丰富但柔和虚化，画面精致如同旅行明信片"
            ", 避免：3D渲染感、塑料质感、高饱和、锐利阴影、僵硬姿势"
            ", 避免：面部变形、模糊、文字、水印、不同品种的狗"
        )
        return base
