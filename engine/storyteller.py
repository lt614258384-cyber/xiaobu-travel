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
