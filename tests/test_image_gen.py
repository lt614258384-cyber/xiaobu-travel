from pathlib import Path
from engine.image_gen import ImageGenerator, FakeGenerator, get_image_generator


def test_fake_generator_creates_image():
    gen = FakeGenerator()
    result = gen.generate("a cute dog playing at the beach", [])
    assert Path(result).exists()
    assert "generated" in result
    from PIL import Image
    img = Image.open(result)
    assert img.size == (512, 512)


def test_get_image_generator_fake():
    gen = get_image_generator("fake")
    assert isinstance(gen, ImageGenerator)


def test_get_image_generator_unknown_raises():
    try:
        get_image_generator("nonexistent")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_prompt_template_substitution():
    template = "{appearance} playing at {location} on a {weather} day, {atmosphere}"
    prompt = template.format(
        appearance="A cream colored corgi",
        location="beach",
        weather="sunny",
        atmosphere="warm golden light"
    )
    assert "corgi" in prompt
    assert "beach" in prompt
