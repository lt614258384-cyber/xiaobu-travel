# API 提供商选择 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在档案页加入 API 提供商下拉选择（火山引擎 / 云雾 API），后端据此切换生图模型和 API 格式。

**Architecture:** Profile 模型新增 `api_provider` 字段；前端加下拉框；`image_gen.py` 新增 OpenAI 兼容的 `YunwuImageGenerator`；`storyteller.py` 新增 yunwu.ai Chat Completions 端点；`scheduler.py` 根据 provider 分发。

**Tech Stack:** Python 3.13, FastAPI + Jinja2, SQLAlchemy ORM, httpx

## Global Constraints

- 保持 FastAPI + Jinja2 + 原生 HTML/CSS/JS 技术栈
- 现有用户默认 `api_provider="volcano"`，行为不变
- `text_api_key` 字段保留但前端不再展示
- 不修改 `config.py` 全局 `IMAGE_API_TYPE`
- 测试驱动：先写失败测试，再写实现

---

### Task 1: Profile 模型新增 `api_provider` 字段

**Files:**
- Modify: `models.py:11-28`
- Modify: `app.py:147-175` (profile save 接收新字段)
- Test: `tests/test_integration.py`

**Interfaces:**
- Produces: `Profile.api_provider` — Column(String(20), default="volcano")
- Produces: `POST /profile` 接收 `api_provider: str = Form("volcano")`

- [ ] **Step 1: 添加模型字段**

```python
# models.py — Profile class, after text_api_key line
api_provider = Column(String(20), default="volcano")  # "volcano" or "yunwu"
```

- [ ] **Step 2: 更新 `app.py` 接收 api_provider 表单字段**

找到 profile 保存路由（约第 147 行），添加 `api_provider` 参数：

```python
# app.py — 在 profile save 路由参数中添加
api_provider: str = Form("volcano"),
```

保存：

```python
# app.py — 在 profile.image_api_key = image_api_key 之后添加
profile.api_provider = api_provider
```

- [ ] **Step 3: 写测试**

```python
# tests/test_integration.py — 在 test_profile_save_succeeds_when_authenticated 附近新增

def test_profile_save_with_yunwu_provider(authenticated_client):
    """Profile save should persist api_provider=yunwu."""
    client, user_id, csrf_token = authenticated_client
    resp = client.post("/profile", data={
        "_csrf_token": csrf_token,
        "name": "小布",
        "api_provider": "yunwu",
        "image_api_key": "sk-test-key",
    })
    assert resp.status_code == 303

    from models import get_session, Profile
    sess = get_session()
    profile = sess.query(Profile).filter_by(user_id=user_id).first()
    assert profile.api_provider == "yunwu"
    sess.close()
```

- [ ] **Step 4: 运行测试验证**

```bash
python -m pytest tests/test_integration.py::test_profile_save_with_yunwu_provider -v
```

Expected: PASS

- [ ] **Step 5: 运行全部测试确保无回归**

```bash
python -m pytest tests/ -v
```

Expected: 所有之前通过的测试仍然通过。

- [ ] **Step 6: 提交**

```bash
git add models.py app.py tests/test_integration.py
git commit -m "feat: add api_provider field to Profile model

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: 档案页添加提供商下拉框

**Files:**
- Modify: `templates/profile.html:45-55`

**Interfaces:**
- Consumes: `Profile.api_provider` (from Task 1)
- Produces: 表单字段 `name="api_provider"` 提交到 `POST /profile`

- [ ] **Step 1: 添加下拉框 HTML**

将 `templates/profile.html` 中"图片生成 API Key"段落替换为：

```html
            <label>API 提供商</label>
            <select name="api_provider" id="api_provider" style="width:100%;padding:12px;margin-bottom:16px;border:2px solid #d4a574;border-radius:8px;font-size:16px;">
              <option value="volcano" {% if profile and profile.api_provider == 'volcano' %}selected{% endif %}>火山引擎</option>
              <option value="yunwu" {% if profile and profile.api_provider == 'yunwu' %}selected{% endif %}>云雾 API</option>
            </select>

            <label>API Key</label>
            <input type="password" name="image_api_key" id="image_api_key"
                   value="{{ profile.image_api_key if profile else '' }}"
                   placeholder="粘贴 API Key">
            {% if profile and profile.image_api_key %}
              <small>已保存（末尾：****{{ profile.image_api_key[-4:] }}）</small>
            {% endif %}
            <small class="api-hint" id="api-hint-volcano" {% if profile and profile.api_provider == 'yunwu' %}style="display:none"{% endif %}>
                去 <a href="https://console.volcengine.com/" target="_blank">火山引擎控制台</a> 创建 API Key，粘贴到这里即可
            </small>
            <small class="api-hint" id="api-hint-yunwu" {% if not profile or profile.api_provider != 'yunwu' %}style="display:none"{% endif %}>
                去 <a href="https://yunwu.ai" target="_blank">yunwu.ai</a> 获取 API Key，粘贴到这里即可
            </small>
```

- [ ] **Step 2: 添加下拉切换 JS**

在 `profile.html` 的 `<script>` 块（或页面末尾）添加：

```html
<script>
document.getElementById('api_provider').addEventListener('change', function() {
    var v = this.value;
    document.getElementById('api-hint-volcano').style.display = (v === 'volcano') ? '' : 'none';
    document.getElementById('api-hint-yunwu').style.display = (v === 'yunwu') ? '' : 'none';
});
</script>
```

- [ ] **Step 3: 运行测试验证**

```bash
python -m pytest tests/test_integration.py -v -k "profile"
```

Expected: profile 相关测试全部 PASS

- [ ] **Step 4: 提交**

```bash
git add templates/profile.html
git commit -m "feat: add API provider dropdown to profile page

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: 新增 YunwuImageGenerator（OpenAI 兼容格式）

**Files:**
- Create: (修改现有) `engine/image_gen.py`
- Test: `tests/test_image_gen.py`

**Interfaces:**
- Consumes: `Profile.api_provider` (from Task 1)
- Produces: `YunwuImageGenerator.generate(prompt, reference_photos) -> str` (image path)
- Registers in: `GENERATORS["yunwu"] = YunwuImageGenerator`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_image_gen.py — 新增

def test_get_image_generator_yunwu():
    """get_image_generator should return YunwuImageGenerator for api_type=yunwu."""
    gen = get_image_generator(api_type="yunwu", api_key="sk-test")
    from engine.image_gen import YunwuImageGenerator
    assert isinstance(gen, YunwuImageGenerator)
    assert gen.api_key == "sk-test"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_image_gen.py::test_get_image_generator_yunwu -v
```

Expected: FAIL (YunwuImageGenerator not defined)

- [ ] **Step 3: 实现 YunwuImageGenerator**

在 `engine/image_gen.py` 的 `GENERATORS` 定义之前添加：

```python
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
```

注册到 `GENERATORS`：

```python
GENERATORS = {
    "tongyi": TongyiImageGenerator,
    "seedream": SeedreamGenerator,
    "openai": OpenAIImageGenerator,
    "yunwu": YunwuImageGenerator,
    "fake": FakeGenerator,
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_image_gen.py::test_get_image_generator_yunwu -v
```

Expected: PASS

- [ ] **Step 5: 运行全部测试**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 6: 提交**

```bash
git add engine/image_gen.py tests/test_image_gen.py
git commit -m "feat: add YunwuImageGenerator with OpenAI-compatible format

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Storyteller 支持 yunwu.ai 端点

**Files:**
- Modify: `engine/storyteller.py:6-7, 128-143`

**Interfaces:**
- Consumes: `api_provider` parameter (from Task 1, passed via scheduler)
- Produces: `Storyteller.compose_story(..., api_provider="volcano")` — existing signature, new param

- [ ] **Step 1: 修改 Storyteller 支持多端点**

当前代码 (line 6-7):
```python
STORY_MODEL = "ep-20260622031722-sdjgh"
STORY_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
```

改为：

```python
STORY_CONFIGS = {
    "volcano": {
        "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "model": "ep-20260622031722-sdjgh",
    },
    "yunwu": {
        "url": "https://yunwu.ai/v1/chat/completions",
        "model": "DeepSeek-V4-Pro",
    },
}
```

在 `_generate_story_llm` 方法中（约 line 128-143），将硬编码的 URL 和 model 改为从配置读取：

```python
# _generate_story_llm 方法签名添加 api_provider 参数
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
    api_provider: str = "volcano",
) -> str:
```

方法体中：

```python
config = STORY_CONFIGS.get(api_provider, STORY_CONFIGS["volcano"])

resp = httpx.post(
    config["url"],
    json={
        "model": config["model"],
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
    timeout=60,
)
```

在 `compose_story` 方法中，将 `api_provider` 参数传递下去：

```python
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
    api_provider: str = "volcano",
) -> str:
```

LLM 调用处传递 `api_provider`：

```python
story = self._generate_story_llm(
    activity=activity,
    profile=profile,
    weather=weather,
    mood=mood,
    features=features,
    memory_context=memory_context,
    all_stories_count=all_stories_count,
    api_key=api_key,
    api_provider=api_provider,
)
```

- [ ] **Step 2: 编写测试**

```python
# tests/test_storyteller.py — 新增

def test_storyteller_has_yunwu_config():
    """STORY_CONFIGS should include yunwu entry."""
    from engine.storyteller import STORY_CONFIGS
    assert "yunwu" in STORY_CONFIGS
    assert STORY_CONFIGS["yunwu"]["model"] == "DeepSeek-V4-Pro"
    assert "yunwu.ai" in STORY_CONFIGS["yunwu"]["url"]
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/test_storyteller.py::test_storyteller_has_yunwu_config -v
```

Expected: PASS

- [ ] **Step 4: 运行全部测试**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 5: 提交**

```bash
git add engine/storyteller.py tests/test_storyteller.py
git commit -m "feat: add yunwu.ai endpoint to Storyteller

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Scheduler 根据 provider 分发

**Files:**
- Modify: `scheduler.py:342-434` (run_generation 方法)

**Interfaces:**
- Consumes: `Profile.api_provider` (from Task 1)
- Consumes: `YunwuImageGenerator` (from Task 3)
- Consumes: `Storyteller` with `api_provider` param (from Task 4)

- [ ] **Step 1: 修改 run_generation 读取 provider**

在 `run_generation` 方法中（约 line 342），读取 profile 后添加：

```python
provider = profile.api_provider or "volcano"
```

- [ ] **Step 2: 修改故事生成调用**

Line 381-387，添加 `api_provider` 参数：

```python
story = self.storyteller.compose_story(
    activity, profile,
    weather=weather, mood=state.mood, features=features,
    memory_context=memory_context,
    all_stories_count=len(all_stories),
    api_key=profile.text_api_key or profile.image_api_key or "",
    api_provider=provider,
)
```

- [ ] **Step 3: 修改图片生成调用**

Line 394-395，根据 provider 选择：

```python
if provider == "yunwu":
    api_type_for_image = "yunwu"
else:
    api_type_for_image = "seedream" if profile.image_api_key else None
image_gen = get_image_generator(api_type=api_type_for_image, api_key=profile.image_api_key)
```

- [ ] **Step 4: refill_buffer 同样修改**

`refill_buffer` 方法（约 line 270-290）中的故事和图片生成使用相同的 provider 逻辑（同上）。

- [ ] **Step 5: 运行测试**

```bash
python -m pytest tests/ -v
```

Expected: 所有测试 PASS（2 预存失败除外）

- [ ] **Step 6: 提交**

```bash
git add scheduler.py
git commit -m "feat: route generation through provider-specific models

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: 集成验证与部署

- [ ] **Step 1: 最终测试**

```bash
python -m pytest tests/ -v
```

Expected: 80 tests collected, 78 PASS (2 预存失败)

- [ ] **Step 2: 推送所有提交**

```bash
git push origin feat/xiaobu-travel
```

- [ ] **Step 3: 部署到服务器**

```bash
# 服务器端：
cd /home/ubuntu/xiaobu-travel
git fetch https://ghproxy.net/https://github.com/lt614258384-cyber/xiaobu-travel.git feat/xiaobu-travel
git reset --hard <latest-commit>
docker compose up -d --build
```

- [ ] **Step 4: 浏览器验收**

1. 登录 `http://49.233.183.173:8000/profile`
2. 选择"云雾 API"
3. 填入 yunwu.ai API Key
4. 保存
5. 点击"看看小布最近在做什么"
6. 确认生图调用的是 `gpt-image-2`，故事调用 `DeepSeek-V4-Pro`

- [ ] **Step 5: 更新项目日志**

在 `docs/PROJECT_LOG.md` 记录本次变更。
