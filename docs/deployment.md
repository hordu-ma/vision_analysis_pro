# Vision Analysis Pro 部署说明（最小可部署版）

本文档提供 `Vision Analysis Pro` 的试点部署说明，目标是让你可以在本地或单机环境中快速启动 API、前端、可选观测栈和 Edge Agent 上报链路，并与当前“系统封装优先”的试点路线保持一致。

当前前提是：真实输电塔环境样本在系统进入现场前暂不可得。因此部署优先级是先交付可运行、可演示、可采集真实样本的试点系统；样本扩充、人工复核标注和 `prototype_v0_2` 训练放在现场数据回流之后。

客户远程演示流程见 `docs/customer-remote-demo.md`。现场数据采集、metadata、人工复核、标注交接和后续训练准备见 `docs/field-data-intake-and-review.md`。软硬一体试点包和控标参数见 `docs/hardware-bundle.md`。

## 1. 适用范围

当前文档覆盖：

- 后端 API 服务部署
- 前端静态站点部署
- 边缘 Agent 上报接收端
- 可选 Prometheus/Grafana 本地观测栈
- 模型文件准备
- 环境变量配置
- 本地直接运行
- Docker Compose 统一部署
- smoke 验证与回滚步骤

当前文档**不覆盖**：

- Kubernetes 部署
- 多实例负载均衡
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

当前试点模型路径约定：

- Stage A YOLO：`runs/stage_a_crack/baseline_v0_1/weights/best.pt`
- Stage A ONNX：`models/stage_a_crack/best.onnx`
- Stage A 数据集：`data/stage_a_crack/data.yaml`

默认 Compose profile 使用 `INFERENCE_ENGINE=stub`，用于不依赖模型文件的内部链路验证。客户正式演示或真实模型 smoke 应切换到 `onnx` 或 `yolo`，并先确认上面的 Stage A 模型文件已存在，或通过环境变量覆盖为其他已验证模型路径。

当前多类塔材模型仍是实验模型：它可以用于离线训练/推理 smoke，但在正常阈值下没有稳定检测前，不建议作为试点部署默认模型，也不建议导出为默认 ONNX。

---

## 4. 环境变量

后端 API 当前主要依赖以下环境变量：

### 推理相关

- `INFERENCE_ENGINE`
  - 可选值：`yolo`、`onnx`、`stub`
  - 试点部署默认值：`stub`

- `YOLO_MODEL_PATH`
  - YOLO 模型路径
  - 试点路径：`runs/stage_a_crack/baseline_v0_1/weights/best.pt`
  - Compose 容器路径：`/app/runs/stage_a_crack/baseline_v0_1/weights/best.pt`

- `ONNX_MODEL_PATH`
  - ONNX 模型路径
  - 试点路径：`models/stage_a_crack/best.onnx`
  - Compose 容器路径：`/app/models/stage_a_crack/best.onnx`

### API 运行相关

- `API_HOST`
  - 默认值：`0.0.0.0`

- `API_PORT`
  - 默认值：`8000`

- `API_RELOAD`
  - 开发模式自动重载
  - 默认值：`true`
  - 生产环境建议：`false`

- `CORS_ALLOW_ORIGINS`
  - 允许访问 API 的前端来源，使用逗号分隔
  - 示例：`http://localhost:4173,https://vision.example.com`

- `LOG_FORMAT`
  - 日志格式，可选 `json` 或 `text`
  - 默认值：`json`

### 边缘上报相关

- `EDGE_AGENT_REPORTER_URL`
  - Edge Agent 上报地址
  - 默认值：`http://localhost:8000/api/v1/report`

- `REPORT_STORE_DB_PATH`
  - API 侧保存 Edge Agent 上报批次的 SQLite 路径
  - 默认值：`data/reports.db`

- `CLOUD_API_KEY`
  - API 侧上报鉴权密钥；为空时不启用鉴权
  - 启用后请求需携带 `Authorization: Bearer <key>` 或 `X-API-Key: <key>`

### 其他配置

项目中还存在 `Settings` 配置项，例如：

- `MODEL_PATH`
- `CONFIDENCE_THRESHOLD`
- `IOU_THRESHOLD`
- `CLOUD_API_URL`

如果你在生产环境中使用这些配置，建议统一通过环境变量注入，不要硬编码到代码中。

---

## 5. 本地直接部署

### 5.0 试点环境一键启动

如果你要快速拉起试点版环境，可直接执行：

```bash
bash scripts/bootstrap_trial.sh
```

脚本会自动：

- 复制 `.env.example` 到 `.env`（如果尚不存在）
- 创建 `data/`、`models/`、`runs/` 目录
- 执行 `docker compose up --build -d`
- 默认使用 `INFERENCE_ENGINE=stub` 启动，适合先验证 API、前端和上报链路

适合：

- 本地试点预演
- 客户现场快速启动
- 演示环境恢复

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

### 6.1 当前试点 profile

本地试点建议按以下顺序切换：

| Profile | 环境变量 | 用途 | 模型依赖 |
|---------|----------|------|----------|
| 内部链路 smoke | `INFERENCE_ENGINE=stub` | API、前端、Edge 上报、报告摘要联调；不用于客户检测结果展示 | 无 |
| Stage A YOLO | `INFERENCE_ENGINE=yolo` | 训练产物验证、真实模型 fallback | `runs/stage_a_crack/baseline_v0_1/weights/best.pt` |
| Stage A ONNX | `INFERENCE_ENGINE=onnx` + `COMPOSE_INSTALL_ONNX=true` | 客户演示优先真实模型路径、试点部署和边缘推理优先路径 | `models/stage_a_crack/best.onnx` |

2026-05-07 预演结果：

- `docker compose config` 通过。
- `stub` 模式 API health/live/metrics、单图上传、批量任务通过。
- report intake、人工复核、模板摘要、CSV 导出、批次列表、设备列表、告警摘要通过。
- Stage A ONNX readiness 通过；使用有效 JPEG 样本 `data/samples/web_rust_chain.jpg` 可完成 ONNX 推理请求。
- Edge Agent 使用 `models/stage_a_crack/best.onnx` 和 Stage A crack 样本完成 1 帧检测并成功上报。
- 注意：`data/samples/web_rust_bolt.jpg` 实际是 HTML 文档，不能用于真实引擎 smoke；真实模型 smoke 应使用有效 JPEG 或 Stage A 数据集样本。

2026-05-07 模型 profile 完成度复核见 `docs/model-profile-status.md`。结论：Stage A YOLO 和 Stage A ONNX 均可在真实裂缝样本上检出 `crack`；多类塔材 YOLO `prototype_v0_1` 在正常阈值仍不稳定，未完成 ONNX/API/前端部署。

### 6.2 Stage A YOLO 模型

如果你使用 YOLO 推理，请确保模型文件存在：

```text
runs/stage_a_crack/baseline_v0_1/weights/best.pt
```

启动前可设置：

```bash
export INFERENCE_ENGINE=yolo
export YOLO_MODEL_PATH=runs/stage_a_crack/baseline_v0_1/weights/best.pt
```

如果本地缺少该权重，请按 `docs/stage-a-yolo-baseline-v0.1.md` 中记录的训练命令重新生成。仓库历史中的 `runs/train/exp/weights/best.pt` 不再是当前试点主线。

### 6.3 Stage A ONNX 模型

如果你使用 ONNX 推理，请确保模型文件存在：

```text
models/stage_a_crack/best.onnx
```

启动前可设置：

```bash
export INFERENCE_ENGINE=onnx
export ONNX_MODEL_PATH=models/stage_a_crack/best.onnx
```

如需重新导出：

```bash
uv run python scripts/export_onnx.py \
  --model runs/stage_a_crack/baseline_v0_1/weights/best.pt \
  --output models/stage_a_crack/best.onnx
```

### 6.4 Stub 模式

如果你只是验证 API 链路，不依赖真实模型，可以使用：

```bash
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
  -e YOLO_MODEL_PATH=/app/runs/stage_a_crack/baseline_v0_1/weights/best.pt \
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
  -e ONNX_MODEL_PATH=/app/models/stage_a_crack/best.onnx \
  -e API_HOST=0.0.0.0 \
  -e API_PORT=8000 \
  -e API_RELOAD=false \
  -v ./models:/app/models \
  vision-analysis-pro:onnx
```

## 7.5 Docker Compose 统一部署

仓库根目录已提供 `docker-compose.yml`，用于同时启动：

- `api`：FastAPI 后端
- `web`：前端静态站点（Nginx 托管，并将 `/api` 反向代理到后端）

最小使用方式：

```bash
cp .env.example .env
docker compose up --build
```

默认访问地址：

- 前端：`http://localhost:4173`
- 后端：`http://localhost:8000`

常用变量：

- `WEB_PORT`：前端对外端口，默认 `4173`
- `COMPOSE_INSTALL_ONNX`：是否在 API 镜像中安装 ONNX 依赖，默认 `false`
- `INFERENCE_ENGINE`：默认 `stub`；真实模型 profile 使用 `yolo` 或 `onnx`
- `YOLO_MODEL_PATH`：默认 `/app/runs/stage_a_crack/baseline_v0_1/weights/best.pt`
- `ONNX_MODEL_PATH`：默认 `/app/models/stage_a_crack/best.onnx`
- `CORS_ALLOW_ORIGINS`：生产前端来源白名单
- `LOG_FORMAT`：日志输出格式，默认 `json`

## 7.6 本地监控栈（Prometheus + Grafana）

仓库新增 `docker-compose.observability.yml`，用于在本地最小部署之上叠加：

- `prometheus`：抓取 `api:8000/api/v1/metrics`
- `grafana`：自动预置 Prometheus 数据源与基础仪表盘

启动方式：

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.observability.yml up --build
```

默认访问地址：

- 前端：`http://localhost:4173`
- API：`http://localhost:8000`
- Prometheus：`http://localhost:9090`
- Grafana：`http://localhost:3000`

预置内容：

- Prometheus 抓取配置：`config/monitoring/prometheus/prometheus.yml`
- Grafana 数据源：`config/monitoring/grafana/provisioning/datasources/datasources.yml`
- Grafana 仪表盘：`config/monitoring/grafana/dashboards/vision-api-overview.json`
- 告警规则：`config/prometheus_alert_rules.example.yml`

Grafana 默认管理员凭据来自 `.env`：

- `GRAFANA_ADMIN_USER`
- `GRAFANA_ADMIN_PASSWORD`

这种方式适合本地调试、演示和试点环境预演；如果进入正式生产，可再将 Prometheus/Grafana 拆分为独立运维服务。

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

仓库新增的 `web/Dockerfile` 已内置这一约定：容器内由 Nginx 托管前端静态资源，并将 `/api` 转发到 compose 中的 `api` 服务。

---

## 9. 部署后验证

建议至少执行以下验证：

### 9.1 健康检查

```/dev/null/bash.sh#L1-1
curl http://localhost:8000/api/v1/health
```

预期返回类似：

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "model_loaded": true,
  "engine": "StubInferenceEngine"
}
```

如果 `INFERENCE_ENGINE=yolo` 或 `INFERENCE_ENGINE=onnx`，`engine` 会分别变为真实推理引擎名称。

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
- `GET /api/v1/report/{batch_id}`

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

预期返回 `202 Accepted`，并包含 `batch_id`、`result_count`、`total_detections` 与 `request_id`。首次接收返回 `status=accepted`；重复 `batch_id` 返回 `status=duplicate`，不会重复累加结果/检测数量指标。

查询已保存批次：

```bash
curl "http://localhost:8000/api/v1/report/edge-agent-001-smoke"
```

如果配置了 `CLOUD_API_KEY`，上报与查询请求都需要携带密钥，例如：

```bash
curl -X POST "http://localhost:8000/api/v1/report" \
  -H "Authorization: Bearer ${CLOUD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "edge-agent-001",
    "batch_id": "edge-agent-001-secure-smoke",
    "report_time": 1700000000.0,
    "results": []
  }'
```

### 9.5 试点 smoke 与回滚

最小试点 smoke：

```bash
cp .env.example .env
docker compose config
docker compose up --build -d

curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/metrics
curl -X POST "http://localhost:8000/api/v1/report" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "edge-agent-001",
    "batch_id": "edge-agent-001-smoke",
    "report_time": 1700000000.0,
    "results": []
  }'
curl "http://localhost:8000/api/v1/report/edge-agent-001-smoke/summary"
```

Stage A ONNX profile smoke：

```bash
test -f models/stage_a_crack/best.onnx
INFERENCE_ENGINE=onnx \
ONNX_MODEL_PATH=/app/models/stage_a_crack/best.onnx \
COMPOSE_INSTALL_ONNX=true \
docker compose up --build -d api

curl http://localhost:8000/api/v1/health
```

回滚步骤：

```bash
# 链路优先回滚：不用模型，恢复 API、前端和上报链路
INFERENCE_ENGINE=stub docker compose up -d api

# 模型文件回滚：恢复上一版本地模型后重启 API
cp models/stage_a_crack/previous.onnx models/stage_a_crack/best.onnx
INFERENCE_ENGINE=onnx \
ONNX_MODEL_PATH=/app/models/stage_a_crack/best.onnx \
docker compose up -d api

# 完整停止
docker compose down
```

如果回滚到 `stub`，前端和 Edge Agent 上报链路仍可 smoke；真实检测结果只在切回 `yolo` 或 `onnx` 且模型文件有效后恢复。

### 9.6 指标与告警

当前 `metrics` 端点已包含以下新增指标：

- `vision_api_request_status_total{method,path,status_code}`
- `vision_api_request_duration_ms_sum|count|last`
- `vision_api_inference_duration_ms_sum|count|last`
- `vision_api_inference_detections_total`
- `vision_api_inference_visualizations_total`
- `vision_api_inference_input_bytes_total`
- `vision_api_report_duplicates_total`
- `vision_api_report_not_found_total`
- `vision_api_health_ready_failures_total`

Prometheus 告警规则示例见：

- `config/prometheus_alert_rules.example.yml`

本地最小监控栈默认会直接挂载该规则文件，无需额外复制。

如果你已经接入 Prometheus，可直接把示例规则拷贝到规则目录后再按阈值微调。

---

## 10. 常见问题

### 10.0 试点部署演练记录（2026-04-21）

本次按当前 Stage C 试点路径执行了部署演练，结论如下：

#### 前置条件

- `docker compose config`：通过，Compose 默认 profile 为 `INFERENCE_ENGINE=stub`。
- Stage A YOLO 权重存在：`runs/stage_a_crack/baseline_v0_1/weights/best.pt`。
- Stage A ONNX 权重存在：`models/stage_a_crack/best.onnx`。
- Edge Agent 示例配置已指向 Stage A ONNX：`config/edge_agent.example.yaml`。

#### Docker Compose 演练结果

- Web 镜像构建：通过。
- API 镜像构建：已通过显式默认索引修复原先的 Python 包源超时阻塞。
- 处理方式：
  - `Dockerfile` 增加 `ARG/ENV UV_DEFAULT_INDEX`。
  - `docker-compose.yml` 透传 `COMPOSE_UV_DEFAULT_INDEX`，默认值为 `https://pypi.org/simple`。
  - `pyproject.toml` 显式锁定 `uv` 默认索引为官方 PyPI，并增加 `prometheus-client` 依赖。
- 当前冷缓存构建会继续下载 `ultralytics -> torch -> nvidia-*` 大体积依赖，因此**可能较慢，但不再卡在不可达镜像**。

当前处理方式：

- 使用默认官方索引直接构建，或按环境覆盖：

```bash
docker compose up --build -d

# 如需使用企业内网 simple index
COMPOSE_UV_DEFAULT_INDEX=https://your.mirror/simple docker compose up --build -d
```

可选后续优化：

- 评估 API 镜像是否需要 CPU-only Torch 依赖源或分层预缓存策略。
- 将进一步的冷缓存提速独立为部署工程任务，避免在试点 smoke 中临时改动依赖锁定策略。

#### 本地直接运行替代 smoke

在修复包源阻塞之前，本次曾用本地直接运行完成同一业务链路验证；以下记录保留为替代 smoke 参考。

#### Stage B 代理模型复核（2026-04-22）

本次复核没有发现新的真实试点媒体或 reviewed positive pilot crack labels，因此未触发真实试点版 HE-007，也不切换部署模型。

执行结果：

- `data/stage_b_pilot_crack/` 校验通过，确认当前本地 Stage B 数据仍为 Stage A 测试集自动标注代理数据。
- Stage A 与 Stage B 代理模型在同一 Stage A val 集上复核评估，指标与 `docs/stage-b-model-comparison.md` 一致。
- 当前部署推荐仍为 Stage A ONNX：`models/stage_a_crack/best.onnx`；链路 smoke 仍可使用 `INFERENCE_ENGINE=stub`。
- 真实样本到位前，部署演练应聚焦 Stage A ONNX、stub 回滚、Edge Agent 上报、离线缓存、人工复核、报告摘要和导出链路；样本交接字段与 Day-1 HE-007 命令见 `docs/stage-b-pilot-data.md`。

复核命令：

```bash
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  --output data/stage_b_pilot_crack \
  --validate-only

uv run python scripts/evaluate.py \
  --model runs/stage_a_crack/baseline_v0_1/weights/best.pt \
  --data data/stage_a_crack/data.yaml \
  --split val \
  --device cpu \
  --batch 8

uv run python scripts/evaluate.py \
  --model runs/stage_b_pilot_crack/comparison_v0_1/weights/best.pt \
  --data data/stage_a_crack/data.yaml \
  --split val \
  --device cpu \
  --batch 8
```

Stub 回滚 smoke：

```bash
INFERENCE_ENGINE=stub API_RELOAD=false \
  uv run uvicorn vision_analysis_pro.web.api.main:app --host 127.0.0.1 --port 8000

curl http://127.0.0.1:8000/api/v1/health
curl -X POST "http://127.0.0.1:8000/api/v1/inference/image" \
  -F "file=@data/samples/autocrops/train_batch2_r3_c2.jpg;type=image/jpeg"
```

结果：

- `/api/v1/health` 返回 `StubInferenceEngine`。
- `/api/v1/inference/image` 返回 3 条 stub detections。
- `stub` 模式下 `/api/v1/health/ready` 返回 degraded/503；这是因为 stub 不加载真实模型，适合链路 smoke，不作为真实模型就绪信号。

Stage A ONNX smoke：

```bash
INFERENCE_ENGINE=onnx ONNX_MODEL_PATH=models/stage_a_crack/best.onnx API_RELOAD=false \
  uv run uvicorn vision_analysis_pro.web.api.main:app --host 127.0.0.1 --port 8001

curl http://127.0.0.1:8001/api/v1/health
curl -i http://127.0.0.1:8001/api/v1/health/ready
curl http://127.0.0.1:8001/api/v1/metrics
curl -X POST "http://127.0.0.1:8001/api/v1/inference/image" \
  -F "file=@data/samples/autocrops/train_batch2_r3_c2.jpg;type=image/jpeg"
```

结果：

- `/api/v1/health` 返回 `model_loaded=true`，`engine=ONNXInferenceEngine`。
- `/api/v1/health/ready` 返回 `200 OK`，`status=ready`。
- `/api/v1/metrics` 返回 Prometheus 风格指标。
- ONNX 推理接口返回 `200 OK`，样例图未检出缺陷，接口链路正常。

Edge Agent ONNX 上报 smoke：

```bash
mkdir -p /tmp/vision-edge-smoke
cp data/stage_a_crack/images/val/crack-1455-_jpg.rf.d78b0366a48c54f31295522b24dcf2f0.jpg \
  /tmp/vision-edge-smoke/crack-smoke.jpg

timeout 30s uv run python examples/run_edge_agent.py \
  --device-id edge-agent-smoke-onnx-lowconf \
  --source-type folder \
  --source-path /tmp/vision-edge-smoke \
  --engine onnx \
  --model-path models/stage_a_crack/best.onnx \
  --confidence 0.1 \
  --report-url http://127.0.0.1:8001/api/v1/report \
  --batch-size 1 \
  --batch-interval 1 \
  --cache-path /tmp/vision-edge-smoke-cache-lowconf.db
```

结果：

- Edge Agent 处理 1 帧。
- ONNX 检测总数为 1。
- HTTP 上报返回 `202 Accepted`。
- `/api/v1/reports/batches?limit=5` 可查询到 `edge-agent-smoke-onnx-lowconf-*` 批次。

#### 回滚验证

从 ONNX profile 回到 `stub` 后，单图推理链路可用：

- `INFERENCE_ENGINE=stub`
- `/api/v1/health` 返回 `StubInferenceEngine`
- `/api/v1/inference/image` 返回固定 3 条检测结果

因此当前回滚路径可用于 API、前端和报告链路 smoke；真实模型 ready 检查仍应使用 `onnx` 或 `yolo` profile。

---

### 10.1 推理引擎噪音排查

当前主线只保留三类 API 推理引擎：

- `stub`：不加载模型，用于链路测试、CI smoke 和前后端联调。
- `yolo`：加载本地 `.pt` 权重，用于训练结果验证和实验。
- `onnx`：加载本地 `.onnx` 权重，用于部署和边缘推理。

如果后续出现新的 `INFERENCE_ENGINE` 取值，先检查它是否满足以下条件：

- 是否有 `tasks.md` 中的明确任务和验收标准。
- 是否同时说明 API 与 Edge Agent 的适用范围。
- 是否引入了新的模型框架或额外依赖。
- 是否只是临时 demo fallback。

不满足这些条件的引擎应保持在实验脚本或归档文档中，不进入主线配置、部署文档或默认环境变量。

### 10.2 健康检查返回 `model_loaded=false`

可能原因：

- 模型文件不存在
- 环境变量路径配置错误
- 当前使用的是 `stub` 模式

建议检查：

- `INFERENCE_ENGINE`
- `YOLO_MODEL_PATH`
- `ONNX_MODEL_PATH`

### 10.3 启动时报模型加载失败

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

### 10.4 前端页面无法访问后端

检查项：

- 后端是否监听在 `0.0.0.0:8000`
- 前端代理是否仍指向 `http://localhost:8000`
- 反向代理是否正确转发 `/api`

### 10.5 生产环境是否可以继续使用 `--reload`

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

1. 生产环境反向代理配置
2. 生产域名的 `CORS_ALLOW_ORIGINS` 收敛
3. 模型版本目录与 `previous.onnx` 回滚文件的发布约定
4. 集中日志采集与告警阈值调优

---

## 13. 维护约定

当以下内容发生变化时，应同步更新本文档：

- API 启动命令
- 环境变量名称
- 模型默认路径
- Docker 运行方式
- 前端代理或部署方式

保持部署文档与仓库实际命令一致，避免文档与实现漂移。
