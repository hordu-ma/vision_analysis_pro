# 端到端 Demo 演示指南

本文档演示如何在本地环境运行完整的推理服务和边缘 Agent，并获取检测结果。

---

## 📋 前置要求

- **Python 3.12+**（推荐使用 `uv` 管理环境）
- **Node.js 20+**（前端开发）
- **操作系统**：macOS / Linux / Windows

---

## 🚀 快速开始

### 1. 克隆仓库并进入目录

```bash
git clone <repository-url>
cd vision_analysis_pro
```

### 2. 安装依赖

```bash
# 安装基础依赖
uv sync

# 安装 ONNX Runtime 支持（推荐，性能提升 7.25x）
uv sync --extra onnx

# 安装开发依赖（测试）
uv sync --extra dev
```

### 3. 启动 API 服务

```bash
# 默认：使用 YOLO 引擎
uv run uvicorn vision_analysis_pro.web.api.main:app --reload

# 使用 ONNX 引擎（更快）
INFERENCE_ENGINE=onnx uv run uvicorn vision_analysis_pro.web.api.main:app --reload

# 使用 Stub 引擎（固定输出，用于演示）
INFERENCE_ENGINE=stub uv run uvicorn vision_analysis_pro.web.api.main:app --reload
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
  "model_loaded": true,
  "engine": "YOLOInferenceEngine"
}
```

---

## 🎯 API 推理演示

### 场景 1：基础推理（返回 JSON 检测结果）

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
    }
  ],
  "metadata": {
    "engine": "YOLOInferenceEngine"
  },
  "visualization": null
}
```

### 场景 2：带可视化的推理

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/inference/image?visualize=true" \
  -F "file=@test_image.jpg" \
  -o response.json

# 提取并保存可视化图像
cat response.json | jq -r '.visualization' | sed 's/^data:image\/jpeg;base64,//' | base64 -d > output_with_bbox.jpg
```

### 场景 3：使用 Python 脚本

```bash
python examples/demo_request.py test_image.jpg
```

---

## 🤖 边缘 Agent 演示

边缘 Agent 支持从多种数据源采集图像，执行推理，并将结果上报到云端。

### 启动方式

#### 方式 1：使用配置文件

```bash
# 复制示例配置
cp config/edge_agent.example.yaml config/edge_agent.yaml

# 根据需要修改配置
vim config/edge_agent.yaml

# 启动 Agent
edge-agent -c config/edge_agent.yaml
```

#### 方式 2：使用命令行参数

```bash
python examples/run_edge_agent.py \
  --source-type folder \
  --source-path data/images/test \
  --engine onnx \
  --model-path models/best.onnx \
  --report-url http://localhost:8000/api/v1/report \
  --fps-limit 5
```

#### 方式 3：使用环境变量

```bash
EDGE_AGENT_DEVICE_ID=edge-001 \
EDGE_AGENT_SOURCE_TYPE=folder \
EDGE_AGENT_SOURCE_PATH=data/images/test \
EDGE_AGENT_INFERENCE_ENGINE=onnx \
EDGE_AGENT_INFERENCE_MODEL_PATH=models/best.onnx \
edge-agent
```

### 支持的数据源

| 类型 | 说明 | 示例配置 |
|------|------|----------|
| `folder` | 图像文件夹 | `path: /path/to/images` |
| `video` | 视频文件 | `path: /path/to/video.mp4` |
| `camera` | 本地摄像头 | `path: 0` (摄像头索引) |
| `rtsp` | RTSP 视频流 | `path: rtsp://user:pass@ip:554/stream` |

### 配置文件示例

```yaml
# config/edge_agent.yaml
device_id: "edge-agent-001"
log_level: "INFO"

source:
  type: folder
  path: data/images/test
  fps_limit: 5.0
  loop: false

inference:
  engine: onnx
  model_path: models/best.onnx
  confidence: 0.5
  iou: 0.5

reporter:
  type: http
  url: http://localhost:8000/api/v1/report
  timeout: 30.0
  retry_max: 3
  batch_size: 10
  batch_interval: 5.0

cache:
  enabled: true
  db_path: cache/edge_agent.db
  max_entries: 10000
  max_age_hours: 24.0
```

### 功能特性

- ✅ **多数据源**：视频、图像文件夹、摄像头、RTSP 流
- ✅ **高性能推理**：ONNX Runtime（7.25x 加速）
- ✅ **可靠上报**：指数退避重试
- ✅ **离线缓存**：网络不可用时本地缓存
- ✅ **优雅关闭**：Ctrl+C 安全退出
- ✅ **灵活配置**：YAML + 环境变量

---

## 🌐 前端演示

### 启动前端

```bash
cd web
npm install
npm run dev
```

访问 http://localhost:5173

### 功能

1. **图片上传**：拖拽或点击上传图片
2. **实时推理**：自动调用后端 API
3. **结果展示**：检测框、置信度、类别
4. **健康状态**：实时显示后端服务状态

---

## 🔍 API 文档

启动服务后，访问交互式 API 文档：

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

---

## 📊 性能基准

运行性能基准测试：

```bash
uv run python scripts/benchmark.py --iterations 30 --output docs/benchmark-report.md
```

**测试结果**（Apple M4）：

| 引擎 | 平均延迟 (ms) | P95 (ms) | FPS | 加速比 |
|------|--------------|----------|-----|--------|
| YOLO | 33.36 | 34.78 | 29.97 | 1.0x |
| ONNX | 4.60 | 5.38 | 217.24 | **7.25x** |

---

## 🧪 运行测试

```bash
# 全部后端测试
uv run pytest tests/ -v

# 边缘 Agent 测试
uv run pytest tests/test_edge_agent.py -v

# 前端测试
cd web && npm run test -- --run
```

**预期结果**：
- 后端：138 passed, 2 skipped ✅
- 前端：28 passed ✅

---

## ⚠️ 当前限制

1. **文件限制**：
   - 最大文件大小：10MB
   - 支持格式：JPEG, PNG, JPG, WebP

2. **边缘 Agent**：
   - MQTT 上报器尚未实现（使用 HTTP）
   - 批量推理尚未优化

3. **可视化**：
   - 当检测结果为空时不生成可视化图像

---

## 🐛 常见问题

### 问题 1: `ModuleNotFoundError: No module named 'vision_analysis_pro'`

```bash
# 方案 1：使用 PYTHONPATH
PYTHONPATH=src uv run uvicorn vision_analysis_pro.web.api.main:app --reload

# 方案 2：安装包到环境
uv pip install -e .
```

### 问题 2: ONNX 模型不存在

```bash
# 导出 ONNX 模型
uv run python scripts/export_onnx.py --output models/best.onnx
```

### 问题 3: 端口 8000 被占用

```bash
uv run uvicorn vision_analysis_pro.web.api.main:app --reload --port 8001
```

### 问题 4: 边缘 Agent 上报失败

检查：
1. 云端 API 是否启动
2. 上报 URL 是否正确
3. 查看离线缓存：`cache/edge_agent.db`

---

## 📞 反馈

如遇到问题或有建议，请提交 Issue 或联系开发团队。

---

**最后更新**：2025-12-24