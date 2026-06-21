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
        base = activity.prompt_template.format(
            appearance=profile.appearance or "一只可爱的狗狗",
            weather=weather,
            mood=mood,
            atmosphere=atmosphere,
        )
        # Strip Ghibli/anime keywords from template (we append realistic style below)
        base = base.replace("吉卜力动画风格", "").replace("温暖治愈", "").replace("，吉卜力动画风格", "")
        # Realistic photography style
        base += ", photorealistic, hyperrealistic, 8k, detailed fur texture, natural lighting, professional pet portrait photography, shallow depth of field, warm and soft atmosphere"
        return base
