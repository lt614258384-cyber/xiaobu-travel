import random
import httpx
from models import Activity, Profile


STORY_MODEL = "deepseek-v4-pro"
STORY_API_URL = "https://api.deepseek.com/v1/chat/completions"


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
            f"你是{dog_name}。你就是{dog_name}本人。没有另一个叫{dog_name}的角色。"
            f"你是一只金毛犬，正在汪星旅行。汪星是宠物离世后的温暖世界。"
            f"用第一人称\"我\"写旅行日记。用狗狗的感官——闻到什么、听到什么、"
            f"爪子踩到什么。尾巴摇代表开心。100-200字。温暖、童趣、不煽情。"
        )

        # Full memory — model has 256K context, plenty of room
        memory_section = ""
        if memory_context:
            memory_section = (
                f"以下是你从来到汪星至今的全部记忆。今天的故事请基于这些经历——"
                f"自然地提及去过的地方、交到的朋友、做过的事，让故事有连续性。\n\n"
                f"{memory_context}\n\n"
            )
        else:
            memory_section = "这是你来到汪星的第一天，一切刚刚开始。\n\n"

        user_message = (
            f"{memory_section}"
            f"今天你来到了{location_name}，正在{activity_name}。"
            f"天气{weather}，心情{mood}。{atmosphere}"
            f"\n\n用\"我\"的第一人称，写一段今天的旅行日记。你就是小布，小布就是你。\n"
            f"用\"我\"写今天的旅行日记（第{all_stories_count + 1}天）。不要出现\"小布\"。"
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
