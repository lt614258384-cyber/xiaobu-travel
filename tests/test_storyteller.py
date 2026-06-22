from unittest.mock import MagicMock
from engine.storyteller import Storyteller


class TestStoryteller:
    def setup_method(self):
        self.storyteller = Storyteller()

    def test_compose_story_caption_preference(self):
        profile = MagicMock()
        profile.content_preference = "caption"
        activity = MagicMock()
        activity.captions = ["短句1", "短句2"]
        activity.stories = ["长故事"]
        for _ in range(20):
            assert self.storyteller.compose_story(activity, profile) in activity.captions

    def test_compose_story_story_preference(self):
        profile = MagicMock()
        profile.content_preference = "story"
        activity = MagicMock()
        activity.captions = ["短句"]
        activity.stories = ["一个温暖的长故事"]
        for _ in range(20):
            assert self.storyteller.compose_story(activity, profile) in activity.stories

    def test_compose_story_image_only_returns_empty(self):
        profile = MagicMock()
        profile.content_preference = "image_only"
        activity = MagicMock()
        activity.captions = ["测试"]
        assert self.storyteller.compose_story(activity, profile) == ""

    def test_compose_prompt_substitutes_all(self):
        profile = MagicMock()
        profile.breed = "柯基"
        profile.appearance = "A cream colored corgi with big ears"
        activity = MagicMock()
        activity.prompt_template = "{appearance} at the beach, {weather} day, feeling {mood}, {atmosphere}"
        prompt = self.storyteller.compose_prompt(activity, profile, "晴", "开心")
        assert "cream colored corgi" in prompt
