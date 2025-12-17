# 端到端 Demo 演示指南

本文档演示如何在本地环境运行完整的推理服务，并获取带可视化的检测结果。

---

## 📋 前置要求

- **Python 3.12+**（推荐使用 `uv` 管理环境）
- **操作系统**：macOS / Linux / Windows

---

## 🚀 快速开始

### 1. 克隆仓库并进入目录

```bash
git clone <repository-url>
cd vision_analysis_pro
```

### 2. 安装依赖

使用 `uv` 安装（推荐）：

```bash
# 安装基础依赖
uv sync

# 安装开发依赖（可选，用于测试）
uv sync --extra dev
```

或使用 pip：

```bash
pip install -e .
```

### 3. 启动 API 服务

```bash
uv run uvicorn vision_analysis_pro.web.api.main:app --reload
```

服务将在 `http://127.0.0.1:8000` 启动。

**验证服务**：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

预期输出：

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "model_loaded": false
}
```

---

## 🎯 Demo 演示

### 场景 1：基础推理（返回 JSON 检测结果）

**准备测试图片**（或使用任意图片）：

```bash
# 创建一个简单的测试图片
python3 -c "import cv2; import numpy as np; img = np.zeros((640,480,3), dtype=np.uint8); img[:] = (200,200,200); cv2.imwrite('test_image.jpg', img)"
```

**发送推理请求**：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/inference/image" \
  -F "file=@test_image.jpg" \
  -H "Content-Type: multipart/form-data"
```

**预期响应**：

```json
{
  "filename": "test_image.jpg",
  "detections": [
    {
      "label": "crack",
      "confidence": 0.95,
      "bbox": [100.0, 150.0, 300.0, 400.0]
    },
    {
      "label": "rust",
      "confidence": 0.88,
      "bbox": [450.0, 200.0, 550.0, 350.0]
    },
    {
      "label": "deformation",
      "confidence": 0.72,
      "bbox": [200.0, 300.0, 350.0, 450.0]
    }
  ],
  "metadata": {
    "engine": "StubInferenceEngine"
  },
  "visualization": null
}
```

---

### 场景 2：带可视化的推理（返回 base64 图像）

**发送带可视化的请求**：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/inference/image?visualize=true" \
  -F "file=@test_image.jpg" \
  -H "Content-Type: multipart/form-data" \
  -o response.json
```

**查看响应**：

```bash
cat response.json | jq .
```

响应中 `visualization` 字段包含 base64 编码的可视化图像：

```json
{
  "filename": "test_image.jpg",
  "detections": [...],
  "metadata": {...},
  "visualization": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**提取并保存可视化图像**：

```bash
# 使用 jq 提取 base64 数据并解码保存为图片
cat response.json | jq -r '.visualization' | sed 's/^data:image\/jpeg;base64,//' | base64 -d > output_with_bbox.jpg

# 查看图片（macOS）
open output_with_bbox.jpg

# 或（Linux）
xdg-open output_with_bbox.jpg
```

---

### 场景 3：使用 Python 脚本调用 API

创建文件 `demo_request.py`（见 `examples/demo_request.py`）：

```python
import base64
from pathlib import Path

import httpx

API_URL = "http://127.0.0.1:8000/api/v1/inference/image"

# 上传图片并获取带可视化的结果
with open("test_image.jpg", "rb") as f:
    files = {"file": ("test_image.jpg", f, "image/jpeg")}
    response = httpx.post(f"{API_URL}?visualize=true", files=files)

data = response.json()

print(f"检测到 {len(data['detections'])} 个目标：")
for det in data["detections"]:
    print(f"  - {det['label']}: {det['confidence']:.2f} at {det['bbox']}")

# 保存可视化图像
if data.get("visualization"):
    base64_data = data["visualization"].split(",")[1]
    img_bytes = base64.b64decode(base64_data)
    Path("output_visualization.jpg").write_bytes(img_bytes)
    print("✅ 可视化图像已保存到 output_visualization.jpg")
```

**运行脚本**：

```bash
uv run python demo_request.py
```

---

## 🔍 API 文档

启动服务后，访问交互式 API 文档：

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

---

## ⚠️ 当前限制（MVP 阶段）

1. **模型状态**：当前使用 `StubInferenceEngine`，返回固定的检测结果（不依赖真实 YOLO 模型）
2. **文件限制**：
   - 最大文件大小：10MB
   - 支持格式：JPEG, PNG, JPG, WebP
3. **检测结果**：固定返回 3 个检测框（crack, rust, deformation）

---

## 🧪 运行测试

```bash
# 运行所有测试
uv run pytest tests/ -v

# 运行 API 测试
uv run pytest tests/test_api_inference.py -v

# 运行可视化测试
uv run pytest tests/test_visualization.py -v
```

预期：21 个测试全部通过 ✅

---

## 🐛 常见问题

### 问题 1: `ModuleNotFoundError: No module named 'vision_analysis_pro'`

**解决方案**：

```bash
# 方案 1：使用 PYTHONPATH
PYTHONPATH=src uv run uvicorn vision_analysis_pro.web.api.main:app --reload

# 方案 2：安装包到环境
uv pip install -e .
```

### 问题 2: 端口 8000 被占用

**解决方案**：

```bash
# 使用其他端口
uv run uvicorn vision_analysis_pro.web.api.main:app --reload --port 8001
```

### 问题 3: `httpx` 模块缺失（运行测试时）

**解决方案**：

```bash
uv sync --extra dev
```

---

## 📝 下一步开发

- [ ] Day 6-7：数据准备（类目定义、标注规范、data.yaml）
- [ ] Day 8-9：YOLO 训练与导出
- [ ] Day 10：集成真实推理引擎（替换 StubInferenceEngine）

---

## 📞 反馈

如遇到问题或有建议，请提交 Issue 或联系开发团队。
