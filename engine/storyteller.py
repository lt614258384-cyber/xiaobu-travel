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
    # ── 社交互动 (social) ──
    "正和一只拉布拉多在浅滩比赛谁跑得快，水花四溅，两只狗的耳朵都在飞",
    "叼着飞盘跑向一只边牧，对方跳起来凌空接住，配合默契",
    "和一只柯基面对面趴着，鼻子对鼻子，尾巴各自在身后画圈",
    "正从一只橘猫爪子里接过一小块饼干，动作很轻，像在交换礼物",
    "追着一只柴犬在草地上绕圈跑，两只狗都累得吐舌头",
    "正把一颗松果用鼻子推给一只松鼠，对方抱着松果开心地蹦了三下",
    "趴在老海龟旁边，歪头听它讲贝壳湾的古老故事",
    "和一群狗狗在沙滩上围坐成一圈，中间放着一颗椰子，像在开茶话会",
    "正在教一只刚来汪星的小奶狗用爪子挖沙坑，小奶狗仰头看得认真",
    "靠在一只金毛老爷爷身边打盹，两条尾巴偶尔同步摇一下",
    "和海鸥邮差面对面站着，从它嘴里接过一封贝壳信",
    "正和一只白鲸在浅水里互相泼水，白鲸喷出一道小水柱",
    "帮一只短腿柯基把掉进水沟里的网球捞了回来，柯基开心地直转圈",
    "和一只哈士奇并排坐着看夕阳，哈士奇突然嚎了一嗓子，被逗得也跟着呜呜",
    "正在猫头鹰咕教授的树洞里借一本书，用爪子小心翼翼地翻页",
    "路过面包房门口，比格犬面团师傅从窗口递出来一块刚烤好的骨头饼干",
    "和一只小熊猫在吊桥上面对面僵住了——桥太窄，谁都不肯先退",
    "正在冰淇淋车旁听老金毛爷爷讲它年轻时环游汪星的故事",
    "遇到一只迷路的小兔子，陪它一起找到了回家的蘑菇小径",
    # ── 独自玩耍 (solo play) ──
    "正用前爪在沙滩上画画，已经画好一朵歪歪扭扭的花和一个圆圆的太阳",
    "叼着一根比身体长两倍的浮木从海里拖上岸，像完成了大工程",
    "四脚朝天在开满野花的山坡上打滚，花瓣粘了一身",
    "在草地上追自己的尾巴，转了十几圈后晕乎乎地趴下了",
    "正用爪子把一个松果当球踢，左一下右一下，自娱自乐",
    "从一个小山坡上屁股坐地滑下来，耳朵飞起，表情紧张又兴奋",
    "叼着玩具球跑向镜头，眼神亮晶晶的，像是要把球送给你",
    "在落叶堆里又跳又刨，落叶被扬得到处都是，像下了一场金色雨",
    "正对着水坑里的倒影歪头打量，偶尔用爪子碰一下水面，倒影碎成涟漪",
    "把一块石头当乌龟壳翻过来翻过去研究，鼻子凑得很近",
    # ── 美食时间 (food) ──
    "趴在野餐垫旁边，下巴搁在垫子边缘，眼巴巴看着篮子里的食物",
    "正低头专心吃一碗狗粮，耳朵微微抖动，尾巴慢慢地晃",
    "在草莓园里小心翼翼地用嘴唇摘了一颗草莓，汁水染红了嘴角",
    "正在啃一块巨大的骨头，两只前爪按住，表情超级满足",
    "坐在码头边，面前摆着半块三明治，海鸥在不远处虎视眈眈",
    "从树上用鼻子接住一颗掉下来的野果，嚼得咔嚓响",
    "偷偷从野餐篮里叼走了一块奶酪，躲在树后吃得鬼鬼祟祟",
    # ── 安静观察 (quiet) ──
    "低头嗅着一丛野花，鼻尖快要碰到花瓣，闭着眼睛很专注",
    "坐在礁石上看夕阳，背影小小的，面前是金色的大海",
    "趴在窗台上，下巴搁在窗框边缘，看外面的雨丝斜斜落下",
    "蹲在岸边，一只前爪伸进水里试探温度，小心翼翼",
    "站在开满野花的山坡上，风把毛吹得向后飘起，眯着眼迎风",
    "趴在一棵老树根旁，前爪交叠，安静地听风吹树叶的声音",
    "坐在木码头边沿，四只爪子并排垂在木板外，看着远处的渔船",
    "清晨趴在挂着露珠的草地上，鼻尖贴着草尖，一动不动地看一只蜗牛爬过",
    # ── 探险发现 (discovery) ──
    "正用鼻子拱开一扇半掩的木头门，里面透出暖黄灯光和饼干香",
    "从灌木丛里探出半个脑袋，鼻子上沾着一片叶子，浑然不觉",
    "小心翼翼踩过一串石头过小溪，爪子张开保持平衡，尾巴僵直",
    "站在一棵开花的树下，花瓣正落下来，有一片停在鼻尖上",
    "爬上一块大石头站在最高处环顾，像一个小小的探险家",
    "站在瀑布旁边，水雾打在脸上，伸出一只爪子试图接水帘",
    "在晨雾里发现一座小木桥，桥下溪水叮咚，站在桥中央看得出神",
    "遇到一只刺猬，正学对方团成球，但肚子太大团不起来",
    # ── 天气互动 (weather) ──
    "在雨里欢快地蹦跳，故意踩进每个水坑，水花溅得到处都是",
    "趴在雪地里印出一个完美的小狗形状的雪坑，站起来回头看自己的作品",
    "正追着一片被风吹跑的落叶，跳起来扑空了好几次",
    "大热天把肚皮贴在冰凉的石板上降温，舌头伸得老长",
    "在彩虹下仰头看着，一只爪子举起来，像是想去够那道彩色的光",
    "风大得把耳朵吹翻过来，用爪子按下去又翻上来，反复好几次",
    # ── 运动高手 (athletic) ──
    "正在沙滩上冲刺，身后扬起一道沙雾，四肢腾空，表情专注",
    "跳过一根横在地上的原木，前爪已经过去了，后爪正在空中",
    "在浅水区游泳，只有脑袋露出水面，耳朵像两个小浮漂",
    "正试着用鼻子顶一个球保持平衡，走了三步后球滚掉了",
    "从一块礁石跳到另一块礁石，跳得不高但姿态认真",
    # ── 搞笑瞬间 (silly) ──
    "打喷嚏打到整个脸皱成一团，前爪抬起来捂住了自己的鼻子",
    "被自己的尾巴吓了一跳，回头盯着尾巴看了很久",
    "正试图挤进一个明显太小的纸箱，半个身子在外面，表情倔强",
    "刚睡醒，一边脸上还印着爪印形状的压痕，眼神迷离",
    "对着镜子里的自己歪头、举爪、叫了一声，然后绕到镜子后面找人",
    # ── 暮色温馨 (twilight) ──
    "夜色中趴在草地上看萤火虫，一只落在鼻尖上，脸被照成淡绿色",
    "在篝火旁缩成一团，火光在眼睛里跳动，旁边放着一根烤棉花糖的树枝",
    "月光下站在沙滩上，影子拉得长长的，海浪泛着银色的光",
    "傍晚时分趴在家门口，路灯刚亮，等待什么的样子",
    "深夜在帐篷里探出半个脑袋看星空，耳朵竖得笔直",
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
