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
        # Add quality/style keywords for better generation
        base += ", high quality, 4k, detailed fur, soft warm lighting, Studio Ghibli animation style, cute pet photography"
        return base
