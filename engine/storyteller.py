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

# ── Wangxing World Residents ──
# These are injected into the system prompt for rich social context
WANGXING_WORLD = (
    "汪星是一个温暖广袤的宠物世界，分成海滨区、原野区、森林区、山地区、小镇区五大区域，"
    "每个区域都住着许多友善的动物居民——"
    "海滨区有冲浪高手拉布拉多阿浪、开贝壳小店的老海龟龟爷爷、灯塔守塔人柯基灯灯、"
    "每天在码头等信的柴犬邮递员小邮、在礁石上唱歌的白鲸圆圆；"
    "原野区有花田里的蝴蝶犬花花、薰衣草田里养蜜蜂的棕熊蜜叔、麦田里拉小提琴的边牧麦麦；"
    "森林区有树洞里开图书馆的猫头鹰咕教授、会做蘑菇汤的松鼠松果儿、"
    "吊桥上荡秋千的小熊猫滚滚、浆果丛里酿果酒的刺猬球球；"
    "山地区有泡温泉的雪橇犬雪球、在山涧里吹竹笛的白兔笛笛、"
    "石头小屋里做手工饼干的柯基大厨饼饼；"
    "小镇区有开咖啡馆的橘猫拿铁、面包房的比格犬面团师傅、"
    "狗狗公园里每天组局的哈士奇跑跑、冰淇淋车旁讲故事的老金毛爷爷。"
    "每个居民都有自己的小故事和日常，旅行的狗狗路过时可以和他们互动。"
)

# Action & composition variety for image prompts
ACTIONS = [
    # ── social & playful ──
    "正和一只拉布拉多在浅滩比赛谁跑得快，水花四溅，两只狗的耳朵都在飞",
    "叼着飞盘跑向一只边牧，对方跳起来凌空接住，配合默契",
    "和一只柯基面对面趴着，鼻子对鼻子，尾巴各自在身后画圈",
    "正从一只橘猫爪子里接过一小块饼干，动作很轻，像在交换礼物",
    "追着一只柴犬在草地上绕圈跑，两只狗都累得吐舌头，但谁也不肯先停",
    "正把一颗松果用鼻子推给一只松鼠，对方抱着松果开心地蹦了三下",
    "趴在老海龟旁边，歪头听它讲贝壳湾的古老故事，眼神认真极了",
    "和一群狗狗在沙滩上围坐成一圈，中间放着一颗椰子，像在开茶话会",
    "正在教一只刚来汪星的小奶狗用爪子挖沙坑，小奶狗学得很认真",
    "靠在一只金毛爷爷旁边打盹，阳光暖融融的，两只狗的呼吸同步起伏",
    "和海鸥邮差面对面站着，从它嘴里接过一封贝壳信，尾巴摇了三下表示感谢",
    "正和一只白鲸在浅水里互相泼水，白鲸喷出一道小水柱，狗兴奋地蹦起来",
    # ── solo adventures ──
    "叼着一根比身体长两倍的浮木从海里拖上岸，像完成了一项重大任务",
    "正用前爪在沙滩上画图案，已经画好了一朵歪歪扭扭的花和一颗圆圆的太阳",
    "站在礁石最高处，海风吹得毛发向后飘扬，像船头的雕像一样威风",
    "四脚朝天在开满野花的山坡上打滚，花瓣粘了一身，耳朵里也夹着一片",
    "在溪水中央的石头上站稳，低头看水里的游鱼，鼻尖离水面只差一点点",
    "正用爪子小心翼翼拨开一片大叶子，发现下面藏着一窝彩色的蘑菇",
    "趴在木栈桥边缘，一只爪子伸下去试图碰海面，差一点点就能摸到",
    "正从一个小山坡上滑下来，屁股坐着当滑板，耳朵飞起来，表情又紧张又兴奋",
    # ── discovery & wonder ──
    "蹲在一棵大树下仰头看，树上有一只猫头鹰正低头看回来，两个在对视",
    "正用鼻子拱开一扇半掩的木头门，里面透出暖黄色的灯光和饼干的香味",
    "站在瀑布旁边，水雾打在脸上凉丝丝的，伸出一只爪子试图接住水帘",
    "在晨雾里发现一座小木桥，桥下溪水叮咚，站在桥中央看得入神",
    "夜色中趴在草地上看萤火虫，一只萤火虫落在鼻尖上，整个脸被照成淡绿色",
    "在松果堆里打滚，松果粘在毛上怎么甩都甩不掉，表情又好气又好笑",
    "遇到一只刺猬，正学对方把自己团成一个球，但肚子太大团不起来",
]
STALE_ACTIONS = ACTIONS  # keep old name working until references updated

COMPOSITIONS = [
    "抓拍风格，画面有轻微的自然动感模糊，像生活中真实按下快门的瞬间",
    "从狗的视角拍摄，低机位，世界显得又大又奇妙",
    "中距离平视，像蹲下来和狗对话的高度，亲切平等",
    "环境人像风格，狗在画面一侧，有大片美丽的风景作为留白",
    "特写局部——只拍爪子和地面的互动，或鼻子与花朵的近距离接触，含蓄温暖",
    "广角远景，一只小狗在大世界里，渺小但自在，充满故事感",
    "透过花丛或草丛间隙偷拍的感觉，前景虚化的花草形成天然画框",
    "正面中景，狗狗直视镜头，像是在和你分享它发现的新鲜事",
    "双狗构图——两个角色在画面中各占一侧，互动感强，像电影海报",
    "俯拍视角——从树梢或屋檐往下看，狗在下方仰头回望",
]

MOOD_LIGHTING = [
    "柔和温暖的午后阳光，画面有淡淡的金色光晕",
    "清晨薄雾中，光线柔和偏蓝，空气感强，露水未干",
    "黄昏时分，长影子，暖橙色光线洒满画面",
    "阴天柔和的散射光，色彩淡雅安静，像雨后的清新",
    "星光或月光下，画面偏蓝紫色调，静谧温柔",
    "透过树叶的斑驳光影洒在身上，明暗交错，生动自然",
    "雨后初晴，地面还湿漉漉的，水洼反射着蓝天白云",
    "傍晚蓝调时刻，天边有一抹粉橘色的晚霞，路灯刚刚亮起",
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
            f"核心规则：你写的一切都必须用第一人称\"我\"。你是{dog_name}本人，"
            f"正在写自己的旅行日记。绝对禁止使用\"{dog_name}\"、\"它\"、\"他\"、\"她\"来指代自己。"
            f"你是亲历者，不是旁观者。每句话都以\"我\"为主语。"
            f"\n\n"
            f"你是一只{breed_name}，正在汪星旅行。"
            f"{WANGXING_WORLD}"
            f"\n你会在旅途中自然地遇到这些居民，和他们打招呼、分享食物、听他们讲故事、结伴走一小段路。"
            f"互动不刻意——有时只是擦肩而过的一个微笑，有时是一次难忘的同行。"
            f"\n\n"
            f"用狗狗的感官写——闻到什么、听到什么、爪子踩到什么。"
            f"尾巴摇代表开心。100-200字。温暖、童趣、不煽情。"
            f"像给家人写明信片一样自然，不要说\"第几天\"或\"第几次\"，不要用括号加注。"
            f"每次写全新的地点和体验，用全新的感官细节——气味、声音、触感、光线。"
            f"每篇要有独特的具体意象，至少自然地遇到一位汪星居民。"
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
            f"\n\n现在，用\"我\"的第一人称写今天的旅行日记。记住：你是亲历者，每句话都用\"我\"开头。"
            f"重点描写新地方的具体细节——看到什么、听到什么、闻到什么、爪子踩到什么触感。"
            f"如果遇到其他动物，写成\"我\"和他们互动的场景，不要站在旁观者角度描述。"
            f"禁止出现\"{dog_name}\"这个词。禁止\"它\"来指自己。禁止第三人称叙述。"
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
                f"主角：{dog_desc}。所有格子中这只{dog_desc}的外貌特征保持完全一致。"
                f"地点：{location_name}。氛围：{atmosphere}。天气：{weather}。心情：{mood}。"
                f"重要：如果故事中提到其他动物（狗狗、猫咪、兔子、海鸥、松鼠等），必须在对应格子里画出来。至少2格要出现主角和其他动物互动的画面。"
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
