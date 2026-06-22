import random
import httpx
from models import Activity, Profile


STORY_MODEL = "ep-20260622031722-sdjgh"
STORY_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# Action & composition variety for image prompts
ACTIONS = [
    "奔跑着，耳朵飞起来，四肢腾空",
    "趴在地上，前爪交叠，下巴搁在爪子上，眼神温柔",
    "侧身坐着，头微微歪着看向远方",
    "低头轻轻嗅一朵花或一片叶子",
    "仰头望着天空或树梢，阳光打在脸上",
    "背对镜头，坐看远方的风景，只留下背影和轮廓",
    "半身侧面，正在向前迈步，动态自然",
    "蹲坐着，一只前爪抬起，像在打招呼或指东西",
    "蜷缩着打盹，身体团成一团",
    "正低头喝水或吃东西，专注而安静",
    "后腿站立，前爪搭在某物上，探头张望",
    "在水边踩水，爪子轻轻拨动水面",
    "从门后或树后探出半个身子，露出期待的表情",
    "趴在窗台或栏杆上，下巴搁在边缘，望向远方",
]

COMPOSITIONS = [
    "中景构图，狗占画面主体约一半，环境清晰可见",
    "全景构图，狗较小，突出广阔的环境和氛围",
    "近景构图，狗的面部和上半身占大部分画面，突出表情",
    "低角度仰拍，从狗的视角看世界",
    "三分法构图，狗在画面一侧，留出大片环境空间",
    "狗狗在最前方，虚化的背景中有温暖的细节",
]

MOOD_LIGHTING = [
    "柔和温暖的午后阳光，画面有淡淡的金色光晕",
    "清晨薄雾中，光线柔和偏蓝，空气感强",
    "黄昏时分，长影子，暖橙色光线洒满画面",
    "阴天柔和的散射光，色彩淡雅安静",
    "星光或月光下，画面偏蓝紫色调，静谧",
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
    ) -> str:
        dog_name = profile.name or "小布"
        dog_desc = features if features else (profile.appearance or "一只可爱的金毛犬")
        location_name = activity.location.name if activity.location else "一个美丽的地方"
        atmosphere = activity.location.atmosphere if activity.location else ""
        activity_name = activity.name

        system_prompt = (
            f"你是{dog_name}。你就是{dog_name}本人。没有另一个叫{dog_name}的角色。"
            f"你是一只金毛犬，正在汪星旅行。汪星是宠物离世后的温暖世界。"
            f"用第一人称\"我\"写旅行日记。用狗狗的感官——闻到什么、听到什么、"
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
            f"\n\n用\"我\"的第一人称，写一段今天的旅行日记。你就是小布，小布就是你。"
            f"重点描写今天这个新地方的具体细节——看到了什么特别的、听到了什么声音、"
            f"闻到了什么气味、爪子底下是什么触感。不要出现\"小布\"。"
        )

        resp = httpx.post(
            STORY_API_URL,
            json={
                "model": STORY_MODEL,
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
            timeout=20,
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

        dog_desc = features if features else (profile.appearance or "一只可爱的狗狗")

        # Pick random action, composition, and lighting for variety
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
        )

        # If story is available, extract visual cues
        if story_text:
            base += (
                f"故事中提到这些画面元素，请自然地融入画面：{story_text[:200]}。"
            )

        base += (
            ", warm healing semi-realistic hand-drawn watercolor illustration"
            ", delicate colored pencil line art with transparent watercolor and light gouache"
            ", natural paper texture and subtle brush grain"
            ", keep the dog's exact breed, fur color, body shape, facial features from the reference image"
            ", fluffy layered fur, facial features realistic and recognizable"
            ", low saturation warm tones, soft natural lighting"
            ", fresh blue-green and golden-yellow palette"
            ", detailed but soft-edged background"
            ", elegant children's picture book style, travel watercolor aesthetic"
            ", avoid: photorealism, 3D render, oily skin, thick comic lines, exaggerated anime eyes"
            ", avoid: plastic texture, harsh saturation, sharp shadows, stiff poses, standing still facing camera"
            ", avoid: deformed face, extra fingers, blurry face, text, watermark, different dog breed"
        )
        return base
