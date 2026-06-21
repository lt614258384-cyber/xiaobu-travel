import random
import httpx
from models import Activity, Profile


STORY_MODEL = "doubao-seed-1-6"
STORY_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"


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
        if profile.content_preference == "image_only":
            return ""

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
        if profile.content_preference == "story":
            pool = activity.stories or activity.captions or []
        else:
            pool = activity.captions or activity.stories or []
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
            f"你是{dog_name}——一只{dog_desc}的金毛犬，正在汪星旅行。"
            f"汪星是一个温暖、治愈、美好的平行世界，所有离世的宠物都在这里快乐地生活。"
            f"\n\n"
            f"【写作风格——必须严格遵循】\n"
            f"1. 始终用\"我\"的第一人称。小布就是\"我\"，\"我\"就是小布。\n"
            f"2. 用狗狗的感官写：闻到的气味、听到的声音、爪子踩到的触感、阳光照在毛上的温度。\n"
            f"3. 尾巴是情绪的指针——开心就摇、好奇就竖、放松就垂。每次写都带一次尾巴的动作。\n"
            f"4. 鼻子是探索世界的器官——\"我用鼻子碰了碰\"\"我闻到了\"\"鼻子抽了抽\"。\n"
            f"5. 汪星居民是其他狗狗——萨摩耶阿姨、柯基姐姐、金毛叔叔，用狗格化的称呼。\n"
            f"6. 自然地引用记忆中去过的地方、做过的事——像真的记得昨天的经历。\n"
            f"7. 用儿童绘本般的比喻——\"晚霞像蜂蜜\"\"钟声会拐弯\"\"云朵像棉花糖\"，天真但不幼稚。\n"
            f"8. 短句为主，有呼吸节奏。100-250字。\n"
            f"9. 可以写心理活动——\"要写什么呀？\"\"等下要不要去...\"，像真的在思考。\n"
            f"10. 结尾偶尔轻描淡写地提到家里的味道或阳光，克制地想念，不煽情。\n"
            f"\n"
            f"【禁止】\n"
            f"- 不要用\"主人\"这个词，用\"家人\"。\n"
            f"- 不要用第三人称\"小布\"来叙述。\n"
            f"- 不要长篇煽情、过度悲伤。\n"
            f"- 不要写标题、引号包裹全文、前缀后缀。\n"
            f"- 不要用\"今天是一个美好的日子\"这类空洞开头。\n"
            f"\n"
            f"【真实回忆】\n"
            f"如果记忆中有'我还在家时'的段落，请自然融入——家人提过的玩具、去过的地方、做过的事，让汪星和真实生活有温暖的连接。"
        )

        # Build prompt with full memory as context
        memory_section = ""
        if memory_context:
            memory_section = (
                f"以下是你从来到汪星至今的全部记忆。"
                f"今天的故事必须基于这些经历——可以自然提及去过的地方、交到的朋友、做过的事、"
                f"曾经的感受。不需要每条都提，但要让人感觉今天的故事和过往是连续的、真实的。"
                f"\n\n{memory_context}\n\n"
            )
        else:
            memory_section = "这是你来到汪星的第一天，一切刚刚开始。\n\n"

        user_message = (
            f"{memory_section}"
            f"今天你来到了{location_name}，正在{activity_name}。"
            f"天气{weather}，心情{mood}。{atmosphere}"
            f"\n\n请用\"我\"写一段今天的旅行日记（第{all_stories_count + 1}天）。"
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

    def compose_prompt(self, activity: Activity, profile: Profile, weather: str, mood: str, features: str = "") -> str:
        atmosphere = activity.location.atmosphere if activity.location else ""

        # Use vision-extracted features if available, otherwise fall back to appearance
        dog_desc = features if features else (profile.appearance or "一只可爱的狗狗")

        # Prompt with vision-extracted detailed features
        base = (
            f"{dog_desc}。"
            f"让它出现在{activity.location.name if activity.location else '一个新的地方'}里{activity.name}，"
            f"天气{weather}，{atmosphere}"
        )
        # Warm healing semi-realistic watercolor illustration style
        base += (
            ", warm healing semi-realistic hand-drawn watercolor illustration"
            ", delicate colored pencil line art with transparent watercolor and light gouache"
            ", natural paper texture and subtle brush grain"
            ", keep the dog's exact breed, fur color, body shape, facial features from the reference image"
            ", fluffy layered fur, gentle cute expression, facial features realistic and recognizable"
            ", soft Japanese animation influenced beautification, no exaggerated anime eyes"
            ", low saturation warm tones, soft natural lighting"
            ", fresh blue-green and golden-yellow palette"
            ", summer sunlight atmosphere, cozy companionship feel"
            ", detailed but soft-edged background"
            ", elegant children's picture book style, travel watercolor aesthetic"
            ", clean, airy, gentle, emotional"
            ", avoid: photorealism, 3D render, oily skin, thick comic lines, exaggerated big eyes"
            ", avoid: plastic texture, harsh saturation, sharp shadows, stiff poses"
            ", avoid: deformed face, extra fingers, blurry face, text, watermark, different dog breed"
        )
        return base
