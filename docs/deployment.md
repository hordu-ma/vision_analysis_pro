# Vision Analysis Pro 部署说明（最小可部署版）

本文档提供 `Vision Analysis Pro` 的最小部署说明，目标是让你可以在本地或单机环境中快速启动后端 API，并与当前 Dockerfile、CI 和边缘 Agent 上报约定保持一致。

## 1. 适用范围

当前文档覆盖：

- 后端 API 服务部署
- 边缘 Agent 上报接收端
- 模型文件准备
- 环境变量配置
- 本地直接运行
- Docker 镜像运行约定

当前文档**不覆盖**：

- Kubernetes 部署
- 多实例负载均衡
- 前端静态站点独立部署
- 边缘 Agent 大规模集群管理

---

## 2. 环境要求

### 后端运行环境

- Python `>= 3.12`
- `uv >= 0.9.8`

### 可选依赖

- Node.js `20+`：如果你需要本地运行前端
- CUDA `>= 11.8`：如果你计划使用 GPU 推理
- ONNX Runtime 相关依赖：如果你计划使用 ONNX 推理

---

## 3. 目录与关键文件约定

项目关键目录如下：

- `src/vision_analysis_pro/web/api/`：FastAPI 应用
- `src/vision_analysis_pro/core/`：推理与预处理
- `models/`：模型文件目录
- `config/`：配置示例
- `web/`：前端项目

常见模型路径约定：

- YOLO：`runs/train/exp/weights/best.pt`
- ONNX：`models/best.onnx`

如果你使用自定义模型路径，请通过环境变量覆盖。

---

## 4. 环境变量

后端 API 当前主要依赖以下环境变量：

### 推理相关

- `INFERENCE_ENGINE`
  - 可选值：`yolo`、`onnx`、`stub`
  - 默认值：`yolo`

- `YOLO_MODEL_PATH`
  - YOLO 模型路径
  - 默认值：`runs/train/exp/weights/best.pt`

- `ONNX_MODEL_PATH`
  - ONNX 模型路径
  - 默认值：`models/best.onnx`

### API 运行相关

- `API_HOST`
  - 默认值：`0.0.0.0`

- `API_PORT`
  - 默认值：`8000`

- `API_RELOAD`
  - 开发模式自动重载
  - 默认值：`true`
  - 生产环境建议：`false`

### 边缘上报相关

- `EDGE_AGENT_REPORTER_URL`
  - Edge Agent 上报地址
  - 默认值：`http://localhost:8000/api/v1/report`

### 其他配置

项目中还存在 `Settings` 配置项，例如：

- `MODEL_PATH`
- `CONFIDENCE_THRESHOLD`
- `IOU_THRESHOLD`
- `CLOUD_API_URL`
- `CLOUD_API_KEY`

如果你在生产环境中使用这些配置，建议统一通过环境变量注入，不要硬编码到代码中。

---

## 5. 本地直接部署

## 5.1 安装依赖

基础依赖：

```/dev/null/bash.sh#L1-3
uv sync
uv sync --extra dev
uv sync --extra onnx
```

说明：

- `uv sync`：安装基础依赖
- `uv sync --extra dev`：安装开发/测试依赖
- `uv sync --extra onnx`：安装 ONNX Runtime 相关依赖

如果你只使用 YOLO 推理，可以不安装 `onnx` 扩展。

## 5.2 启动 API

开发模式：

```/dev/null/bash.sh#L1-1
uv run uvicorn vision_analysis_pro.web.api.main:app --host 0.0.0.0 --port 8000 --reload
```

生产建议模式：

```/dev/null/bash.sh#L1-1
uv run uvicorn vision_analysis_pro.web.api.main:app --host 0.0.0.0 --port 8000
```

启动后可访问：

- OpenAPI 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/v1/health`
- 存活检查：`http://localhost:8000/api/v1/health/live`
- 就绪检查：`http://localhost:8000/api/v1/health/ready`
- 指标端点：`http://localhost:8000/api/v1/metrics`

---

## 6. 模型文件准备

### 6.1 YOLO 模型

如果你使用 YOLO 推理，请确保模型文件存在，例如：

```/dev/null/text.txt#L1-1
runs/train/exp/weights/best.pt
```

启动前可设置：

```/dev/null/bash.sh#L1-2
export INFERENCE_ENGINE=yolo
export YOLO_MODEL_PATH=runs/train/exp/weights/best.pt
```

### 6.2 ONNX 模型

如果你使用 ONNX 推理，请确保模型文件存在，例如：

```/dev/null/text.txt#L1-1
models/best.onnx
```

启动前可设置：

```/dev/null/bash.sh#L1-2
export INFERENCE_ENGINE=onnx
export ONNX_MODEL_PATH=models/best.onnx
```

### 6.3 Stub 模式

如果你只是验证 API 链路，不依赖真实模型，可以使用：

```/dev/null/bash.sh#L1-1
export INFERENCE_ENGINE=stub
```

这种模式适合：

- 本地联调
- 前后端接口验证
- CI 中的轻量 smoke 场景

---

## 7. Docker 部署约定

当前项目的最小容器化目标是：

- 构建 API 服务镜像
- 通过环境变量注入运行参数
- 通过挂载卷提供模型文件

构建基础镜像：

```/dev/null/bash.sh#L1-1
docker build -t vision-analysis-pro:latest .
```

如果容器内要使用 ONNX Runtime，构建时启用 ONNX 依赖：

```/dev/null/bash.sh#L1-1
docker build --build-arg INSTALL_ONNX=true -t vision-analysis-pro:onnx .
```

推荐运行约定：

### 7.1 端口映射

- 容器内端口：`8000`
- 宿主机端口：可按需映射，例如 `8000:8000`

### 7.2 模型挂载

建议将模型目录挂载到容器内，例如：

- 宿主机 `./models` 挂载到容器 `/app/models`
- 宿主机 `./runs` 挂载到容器 `/app/runs`

### 7.3 环境变量注入

至少注入：

- `INFERENCE_ENGINE`
- `YOLO_MODEL_PATH` 或 `ONNX_MODEL_PATH`
- `API_HOST=0.0.0.0`
- `API_PORT=8000`
- `API_RELOAD=false`

### 7.4 示例运行方式

YOLO 模式示例：

```/dev/null/bash.sh#L1-8
docker run --rm \
  -p 8000:8000 \
  -e INFERENCE_ENGINE=yolo \
  -e YOLO_MODEL_PATH=/app/runs/train/exp/weights/best.pt \
  -e API_HOST=0.0.0.0 \
  -e API_PORT=8000 \
  -e API_RELOAD=false \
  -v ./runs:/app/runs \
  vision-analysis-pro:latest
```

ONNX 模式示例：

```/dev/null/bash.sh#L1-8
docker run --rm \
  -p 8000:8000 \
  -e INFERENCE_ENGINE=onnx \
  -e ONNX_MODEL_PATH=/app/models/best.onnx \
  -e API_HOST=0.0.0.0 \
  -e API_PORT=8000 \
  -e API_RELOAD=false \
  -v ./models:/app/models \
  vision-analysis-pro:onnx
```

---

## 8. 前端联调说明

前端开发环境默认通过 Vite 代理访问后端：

- 前端开发地址：`http://localhost:5173`
- 后端 API 地址：`http://localhost:8000`

因此本地联调时，通常只需要先启动后端，再启动前端：

```/dev/null/bash.sh#L1-4
uv run uvicorn vision_analysis_pro.web.api.main:app --reload
cd web
npm install
npm run dev
```

如果你部署的是生产前端静态资源，请确保 `/api` 请求被反向代理到后端服务。

---

## 9. 部署后验证

建议至少执行以下验证：

### 9.1 健康检查

```/dev/null/bash.sh#L1-1
curl http://localhost:8000/api/v1/health
```

预期返回类似：

```/dev/null/json.json#L1-6
{
  "status": "healthy",
  "version": "0.1.0",
  "model_loaded": true,
  "engine": "YOLOInferenceEngine"
}
```

### 9.2 OpenAPI 页面

浏览器访问：

```/dev/null/text.txt#L1-1
http://localhost:8000/docs
```

### 9.3 图片推理接口

你可以通过前端页面上传图片，或直接调用接口验证：

- `POST /api/v1/inference/image`

如果使用真实模型，请确认模型路径存在且依赖已安装完整。

### 9.4 Edge Agent 上报接口

Edge Agent 默认向以下接口上报批量推理结果：

- `POST /api/v1/report`

最小验证请求：

```bash
curl -X POST "http://localhost:8000/api/v1/report" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "edge-agent-001",
    "batch_id": "edge-agent-001-smoke",
    "report_time": 1700000000.0,
    "results": []
  }'
```

预期返回 `202 Accepted`，并包含 `batch_id`、`result_count`、`total_detections` 与 `request_id`。

---

## 10. 常见问题

### 10.1 健康检查返回 `model_loaded=false`

可能原因：

- 模型文件不存在
- 环境变量路径配置错误
- 当前使用的是 `stub` 模式

建议检查：

- `INFERENCE_ENGINE`
- `YOLO_MODEL_PATH`
- `ONNX_MODEL_PATH`

### 10.2 启动时报模型加载失败

可能原因：

- 模型文件损坏
- 依赖未安装完整
- ONNX 模式下未安装 `onnxruntime`；Docker 运行时需使用 `--build-arg INSTALL_ONNX=true` 构建的镜像
- YOLO 模式下未安装 `ultralytics`

建议先确认：

```/dev/null/bash.sh#L1-3
uv sync
uv sync --extra dev
uv sync --extra onnx
```

### 10.3 前端页面无法访问后端

检查项：

- 后端是否监听在 `0.0.0.0:8000`
- 前端代理是否仍指向 `http://localhost:8000`
- 反向代理是否正确转发 `/api`

### 10.4 生产环境是否可以继续使用 `--reload`

不建议。  
生产环境应关闭自动重载，即：

```/dev/null/bash.sh#L1-1
uv run uvicorn vision_analysis_pro.web.api.main:app --host 0.0.0.0 --port 8000
```

---

## 11. 安全建议

生产部署时建议至少做到：

- 不要使用 `allow_origins=["*"]` 作为最终生产配置
- 不要硬编码任何密钥
- 使用环境变量注入 `CLOUD_API_KEY` 等敏感信息
- 模型文件与数据目录按最小权限挂载
- 区分开发与生产配置

---

## 12. 后续建议

当前最小部署完成后，建议继续推进：

1. `docker-compose` 示例
2. 生产环境反向代理配置
3. CORS allowlist 生产配置
4. metrics 告警示例与结构化日志采集
5. 前后端统一部署说明

---

## 13. 维护约定

当以下内容发生变化时，应同步更新本文档：

- API 启动命令
- 环境变量名称
- 模型默认路径
- Docker 运行方式
- 前端代理或部署方式

保持部署文档与仓库实际命令一致，避免文档与实现漂移。
