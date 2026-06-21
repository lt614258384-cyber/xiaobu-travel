import time
from abc import ABC, abstractmethod
from pathlib import Path
from config import settings
import httpx
from PIL import Image


class ImageGenerator(ABC):
    def __init__(self):
        self.api_key = None

    @abstractmethod
    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        """Generate an image. Returns the path to the saved image file."""
        ...

    def _get_api_key(self) -> str:
        return self.api_key or settings.IMAGE_API_KEY


class FakeGenerator(ImageGenerator):
    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        img = Image.new("RGB", (512, 512), color=(255, 200, 150))
        ts = int(time.time() * 1000)
        output = settings.GENERATED_DIR / f"xiaobu_{ts}.png"
        img.save(output)
        return str(output)


class TongyiImageGenerator(ImageGenerator):
    API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
    TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"

    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        payload = {
            "model": "wanx-v1",
            "input": {"prompt": prompt},
            "parameters": {"size": "1024*1024", "n": 1},
        }
        if reference_photos:
            payload["input"]["ref_img"] = reference_photos[0]

        # Submit async task
        resp = httpx.post(self.API_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        task_id = data["output"]["task_id"]

        # Poll for completion
        for _ in range(60):  # Max 5 minutes
            time.sleep(5)
            task_resp = httpx.get(
                self.TASK_URL.format(task_id=task_id),
                headers={"Authorization": f"Bearer {self._get_api_key()}"},
                timeout=30,
            )
            task_resp.raise_for_status()
            task_data = task_resp.json()
            status = task_data["output"]["task_status"]
            if status == "SUCCEEDED":
                image_url = task_data["output"]["results"][0]["url"]
                break
            elif status == "FAILED":
                raise RuntimeError(f"Image generation failed: {task_data.get('output', {}).get('message', 'unknown')}")
        else:
            raise TimeoutError("Image generation timed out after 5 minutes")

        # Download result
        img_resp = httpx.get(image_url, timeout=60)
        img_resp.raise_for_status()

        ts = int(time.time() * 1000)
        output_path = settings.GENERATED_DIR / f"xiaobu_{ts}.png"
        output_path.write_bytes(img_resp.content)
        return str(output_path)


class OpenAIImageGenerator(ImageGenerator):
    API_URL = "https://api.openai.com/v1/images/generations"

    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
        }
        resp = httpx.post(self.API_URL, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        image_url = data["data"][0]["url"]
        img_resp = httpx.get(image_url, timeout=60)
        img_resp.raise_for_status()

        ts = int(time.time() * 1000)
        output_path = settings.GENERATED_DIR / f"xiaobu_{ts}.png"
        output_path.write_bytes(img_resp.content)
        return str(output_path)


GENERATORS = {
    "tongyi": TongyiImageGenerator,
    "openai": OpenAIImageGenerator,
    "fake": FakeGenerator,
}


def get_image_generator(api_type: str = None, api_key: str = None) -> ImageGenerator:
    api_type = api_type or settings.IMAGE_API_TYPE
    cls = GENERATORS.get(api_type)
    if cls is None:
        raise ValueError(f"Unknown image API type: {api_type}. Available: {list(GENERATORS.keys())}")
    gen = cls()
    if api_key:
        gen.api_key = api_key
    return gen
