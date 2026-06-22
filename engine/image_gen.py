import time
from abc import ABC, abstractmethod
from pathlib import Path
from config import settings
import httpx
from PIL import Image
import base64


class ImageGenerator(ABC):
    def __init__(self):
        self.api_key = None

    @abstractmethod
    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        """Generate an image. Returns the path to the saved image file."""
        ...

    def _get_api_key(self) -> str:
        return self.api_key or settings.IMAGE_API_KEY

    def _encode_ref_photos(self, paths: list[str]) -> list[str]:
        """Read local image files, resize to max 1024px, return base64 strings."""
        encoded = []
        for path in paths[:10]:
            try:
                filepath = Path(path)
                if not filepath.is_absolute():
                    filepath = Path.cwd() / filepath
                if filepath.exists():
                    img = Image.open(filepath)
                    img = img.convert("RGB")
                    # Resize to max 1024px on longest side for better character preservation
                    w, h = img.size
                    if max(w, h) > 1024:
                        ratio = 1024 / max(w, h)
                        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
                    # Save to bytes
                    import io
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=75)
                    encoded.append("data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8"))
            except Exception as e:
                print(f"  (skipped ref photo {path}: {e})")
                continue
        return encoded


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
        # Use Qwen Image model for better quality
        payload = {
            "model": "qwen-image-plus",
            "input": {"prompt": prompt},
            "parameters": {"size": "1024*1024"},
        }
        # Encode reference photos as base64 for character consistency
        if reference_photos:
            ref_imgs = self._encode_ref_photos(reference_photos)
            if ref_imgs:
                payload["input"]["ref_img"] = ref_imgs[0]

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
        img_resp = httpx.get(image_url, timeout=120)
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
        resp = httpx.post(self.API_URL, json=payload, headers=headers, timeout=300)
        resp.raise_for_status()
        data = resp.json()

        image_url = data["data"][0]["url"]
        img_resp = httpx.get(image_url, timeout=120)
        img_resp.raise_for_status()

        ts = int(time.time() * 1000)
        output_path = settings.GENERATED_DIR / f"xiaobu_{ts}.png"
        output_path.write_bytes(img_resp.content)
        return str(output_path)


class SeedreamGenerator(ImageGenerator):
    """Seedream 4.5 via Volcano Engine (火山引擎) — image-to-image mode for character consistency."""
    API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }

        # Image-to-image mode: use ref photos to preserve the dog, transform scene
        if reference_photos:
            ref_imgs = self._encode_ref_photos(reference_photos)
            # Put character-preservation at BOTH ends for maximum model attention
            char_guard = "保持参考图中这只狗的外观完全不变：品种、体型、毛色分布、耳朵形状、眼睛颜色和眼神、鼻子形状，所有细节严格一致。只改变背景环境和姿势动作。"
            payload = {
                "model": "doubao-seedream-4-5-251128",
                "prompt": f"{char_guard}\n\n{prompt}\n\n{char_guard}",
                "images": ref_imgs,
                "size": "2048x2048",
                "watermark": False,
                "response_format": "b64_json",
            }
        else:
            payload = {
                "model": "doubao-seedream-4-5-251128",
                "prompt": prompt,
                "size": "2048x2048",
                "watermark": False,
                "response_format": "b64_json",
            }

        resp = httpx.post(self.API_URL, json=payload, headers=headers, timeout=300)
        resp.raise_for_status()
        data = resp.json()

        # Extract image from response
        img_data = data["data"][0]["b64_json"]
        img_bytes = base64.b64decode(img_data)

        ts = int(time.time() * 1000)
        output_path = settings.GENERATED_DIR / f"xiaobu_{ts}.png"
        output_path.write_bytes(img_bytes)
        return str(output_path)


class YunwuImageGenerator(ImageGenerator):
    """OpenAI-compatible image generation via yunwu.ai. Uses gpt-image-2."""
    API_URL = "https://yunwu.ai/v1/images/generations"

    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "gpt-image-2",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json",
        }

        resp = httpx.post(self.API_URL, json=payload, headers=headers, timeout=300)
        resp.raise_for_status()
        data = resp.json()

        img_data = data["data"][0]["b64_json"]
        img_bytes = base64.b64decode(img_data)

        ts = int(time.time() * 1000)
        output_path = settings.GENERATED_DIR / f"xiaobu_{ts}.png"
        output_path.write_bytes(img_bytes)
        return str(output_path)


GENERATORS = {
    "tongyi": TongyiImageGenerator,
    "seedream": SeedreamGenerator,
    "openai": OpenAIImageGenerator,
    "yunwu": YunwuImageGenerator,
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
