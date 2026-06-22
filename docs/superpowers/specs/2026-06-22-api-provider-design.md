# API 提供商选择功能 — 设计规格

- 日期：2026-06-22
- 状态：待审批

## 目标

支持用户在档案页选择 API 提供商（火山引擎 / 云雾 API），填入对应的 API Key，后端据此自动切换生图模型、故事 API 端点和请求格式。

## 用户故事

1. 用户打开档案页，看到"API 提供商"下拉框，选择"火山引擎"或"云雾 API"。
2. 用户填入对应提供商的 API Key，保存。
3. 点击"看看小布最近在做什么"后，后端使用用户选择的提供商生成图片和故事。

## 提供商映射

| 字段 | 火山引擎 (volcano) | 云雾 API (yunwu) |
|------|-------------------|-----------------|
| 生图模型 | `doubao-seedream-4-5-251128` | `gpt-image-2` |
| 生图端点 | `https://ark.cn-beijing.volces.com/api/v3/images/generations` | `https://yunwu.ai/v1/images/generations` |
| 生图格式 | 火山引擎原生格式 | OpenAI 兼容格式 |
| 故事模型 | `ep-20260622031722-sdjgh` (DeepSeek-V4-Pro) | `DeepSeek-V4-Pro` |
| 故事端点 | `https://ark.cn-beijing.volces.com/api/v3/chat/completions` | `https://yunwu.ai/v1/chat/completions` |
| 故事格式 | 火山引擎原生格式 | OpenAI 兼容格式 (Chat Completions) |

## 数据模型变更

`models.py` — Profile 新增字段：

```python
api_provider = Column(String(20), default="volcano")  # "volcano" or "yunwu"
```

`image_api_key` 字段保持不变，作为唯一的 API Key 存储。`text_api_key` 保留但标记为 deprecated，不再在 UI 中展示。

## 前端变更

`templates/profile.html` — 档案页新增下拉框：

```
API 提供商：[火山引擎 ▾] [云雾 API ▾]
API Key：  [••••••••••••••••••] （已有字段，名称改为"API Key"）
```

选中不同提供商时，提示文字动态切换（火山引擎 → "去火山引擎控制台创建 API Key"，云雾 → "去 yunwu.ai 获取 API Key"）。

## 后端变更

### 1. `app.py` — Profile 保存

接收新表单字段 `api_provider`，保存到 `profile.api_provider`。

### 2. `engine/image_gen.py` — 新增 YunwuImageGenerator

```python
class YunwuImageGenerator(ImageGenerator):
    """OpenAI-compatible image generation via yunwu.ai. Uses gpt-image-2."""
    API_URL = "https://yunwu.ai/v1/images/generations"

    def generate(self, prompt: str, reference_photos: list[str]) -> str:
        # OpenAI Images API format
        # gpt-image-2 supports reference images via the 'image' parameter
        ...
```

### 3. `engine/storyteller.py` — 新增 yunwu 故事端点

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

Storyteller 根据传入的 `api_provider` 参数选择对应的 URL 和 model。

### 4. `scheduler.py` — 传递 provider

`run_generation()` 从 `profile.api_provider` 读取提供商类型，传递给 Storyteller 和 ImageGenerator。

## 兼容性

- 现有 Profile 的 `api_provider` 默认为 `"volcano"`，行为与之前完全一致。
- `text_api_key` 字段保留在数据库中但不显示。生成故事时，优先使用 `image_api_key`（两个提供商都用同一个 Key）。
- 如果用户之前填了 `text_api_key`，迁移时不删除，只是后续不再使用。

## 不做

- 不同时支持多个提供商（一次只能选一个）
- 不自动探测 API 类型
- 不修改 `config.py` 的全局 `IMAGE_API_TYPE`（用户级配置优先）
- 不删除 `text_api_key` 数据库列（向后兼容）
- gpt-image-2 的参考图传参方式先以 OpenAI 标准格式实现，如果遇到参数名差异再做调整

## 测试

- Profile 保存后 `api_provider` 正确落库
- volcano 提供商走 Seedream + 火山 Ark 端点
- yunwu 提供商走 gpt-image-2 + yunwu.ai Chat Completions 端点
- 现有测试不受影响（默认 volcano）
