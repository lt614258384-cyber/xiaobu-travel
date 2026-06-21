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
        recent_stories: list[str] | None = None,
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
                    recent_stories=recent_stories or [],
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
        recent_stories: list[str],
        api_key: str,
    ) -> str:
        dog_name = profile.name or "小布"
        dog_desc = features if features else (profile.appearance or "一只可爱的金毛犬")
        personality = ", ".join(profile.personality_tags) if profile.personality_tags else "温柔、忠诚、好奇"
        location_name = activity.location.name if activity.location else "一个美丽的地方"
        atmosphere = activity.location.atmosphere if activity.location else ""
        activity_name = activity.name

        # Build conversation history context
        history_context = ""
        if recent_stories:
            history_context = "最近几天小布的经历：\n"
            for i, story in enumerate(recent_stories[-5:], 1):
                history_context += f"第{i}天：{story}\n"
            history_context += "\n请保持故事与之前的经历有自然的延续感，可以提及之前去过的地方或做过的事。\n"

        system_prompt = (
            f"你是小布——一只{dog_desc}的金毛犬，正在汪星旅行。"
            f"小布的性格：{personality}。"
            f"汪星是一个温暖、治愈、美好的平行世界，所有离世的宠物都在这里快乐地生活。"
            f"请以小布的视角，用第一人称或温暖第三人称，写一段100-200字的旅行日记片段。"
            f"要有画面感、呼吸感，像真的狗狗在体验这个世界——闻到什么、感受到什么、想到什么。"
            f"语言自然、温柔、有童趣，不要太煽情，不要用'主人'这个词。"
            f"偶尔可以提到'想念家里的味道'但不要过度悲伤，整体基调是温暖开心的。"
            f"只返回故事正文，不要加标题、引号、前缀或后缀说明。"
        )

        user_message = (
            f"今天小布来到了{location_name}，正在{activity_name}。"
            f"天气{weather}，小布心情{mood}。{atmosphere}"
            f"\n\n{history_context}"
            f"请写一段今天的旅行日记。"
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
