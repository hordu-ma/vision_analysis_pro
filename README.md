# Vision Analysis Pro

工程基础设施图像识别智能运维系统 - 面向无人机/边缘巡检的缺陷检测试点平台

## 项目简介

针对输电塔等工程基础设施，使用图像识别技术结合无人机巡检，识别自然灾害或长期服役导致的潜在安全隐患。当前项目已具备前后端、边缘 Agent、上报持久化、复核与导出等工程闭环；算法主线先以裂缝检测试点和目标检测闭环为主，五类缺陷模型需要在数据集与权重补齐后再作为正式能力启用。

### 当前路线决策（2026-04-22）

- **短期目标**：先交付裂缝检测试点闭环，使用 `stub` 做链路验证，使用 Stage A 自训练 YOLO/ONNX 做真实模型路径。
- **中期目标**：补齐真实数据集与评估报告后，再恢复五类缺陷 YOLO/ONNX 模型路线。
- **数据层**：已提供 OpenCV 视频帧读取与关键帧抽取工具，先使用固定间隔、场景变化和模糊过滤等可解释规则。
- **报告层**：已提供基于结构化检测结果的模板报告与版本化 LLM 报告契约，LLM 只作为解释与报告生成层，不参与检测判定。
- **前端层**：2026-04-22 完成工作台与设备页产品化视觉提升，保留 Element Plus 组件能力，但通过自有品牌、流程条、密度、色彩与组件皮肤降低默认样品感。
- **暂不作为当前主线**：DeepLab 语义分割、Transformer 趋势分析、LLM 自动结论判定。
- **最新执行结论**：2026-04-22 已复核本地 Stage B 代理数据集和 Stage A/Stage B 同集评估；未发现新的真实试点媒体或人工复核正样本，当前继续推荐 Stage A 作为部署模型。

### 核心特性

- 🚁 **无人机巡检**：支持图片上传、批量任务、边缘端视频/摄像头/RTSP 采集和关键帧抽取工具
- 🤖 **AI 检测**：Stub / YOLO / ONNX Runtime 推理
- 🔧 **边缘计算**：完整的边缘 Agent（采集/推理/上报/离线缓存）
- 🌐 **云端管理**：FastAPI 后端 + Vue3 前端（上传/批量任务/复跑/导出/复核/设备视图）+ 边缘上报接收
- 📝 **报告输出**：边缘批次模板摘要、版本化 LLM 报告上下文、人工复核与导出
- ⚡ **高性能**：ONNX 推理相比 YOLO 提升 7.25x（基准测试）

## 快速开始

### 环境要求

- Python >= 3.12，uv >= 0.9.8
- Node.js 20+（前端）
- 可选：CUDA >= 11.8（GPU 推理）

默认日志输出为结构化 JSON，可通过 `LOG_FORMAT=text` 切回传统文本日志。

### 后端（API + 模型）

```bash
# 克隆并安装
git clone <repository_url>
cd vision_analysis_pro
uv sync                      # 基础依赖
uv sync --extra dev          # 开发/测试
uv sync --extra onnx         # ONNX Runtime 支持

# 运行 API（开发）
uv run uvicorn vision_analysis_pro.web.api.main:app --reload
# 打开 http://localhost:8000 查看 OpenAPI

# 运行测试
uv run pytest
# 注：缺少 legacy runs/train/exp/weights/best.pt、models/best.onnx、
# data/images/* 或可选本地模型产物时，
# 对应模型/数据测试会按预期跳过
```

### 前端（web/）

```bash
cd web
npm install

# 开发预览
npm run dev

# 质量检查与测试
npm run lint
npm run test -- --run

# 生产构建与预览
npm run build
npm run preview

# 浏览器级端到端测试（自动启动前后端）
npm run test:e2e
```

### 边缘 Agent

```bash
# 使用配置文件启动
edge-agent -c config/edge_agent.example.yaml

# 使用命令行参数
python examples/run_edge_agent.py --source-type folder --source-path data/images/test

# 使用环境变量
EDGE_AGENT_SOURCE_TYPE=folder \
EDGE_AGENT_SOURCE_PATH=data/images/test \
EDGE_AGENT_INFERENCE_MODEL_PATH=models/stage_a_crack/best.onnx \
edge-agent
```

默认上报地址为 `http://localhost:8000/api/v1/report`，API 会接收 Edge Agent 的批量推理结果、按 `batch_id` 幂等持久化，并返回接收确认。配置 `CLOUD_API_KEY` 后，上报请求需要携带 `Authorization: Bearer <key>` 或 `X-API-Key: <key>`。

### 完整巡检流程

当前稳定主路径是：在前端或 API 上传单张/批量图片，创建批量任务并执行推理，查看带框可视化结果；Edge Agent 或外部巡检批次上报到 `POST /api/v1/report` 后，云端持久化批次，人工在报告详情中复核单帧结果，再通过 `GET /api/v1/report/{batch_id}/summary` 生成模板摘要或配置化 LLM 报告文本，并按需导出任务 CSV/JSON/ZIP 或报告 CSV。

恢复路径是：批量任务失败时先查看任务详情，整体失败可调用 retry，部分失败可调用 retry-failed，已完成任务可 rerun；Edge Agent 网络故障时先进入本地 SQLite 缓存，云端恢复后按 FIFO 回放，同一 `batch_id` 的重复上报返回 `duplicate` 且不会重复累计检测数。需要鉴权的环境统一使用 `Authorization: Bearer <key>` 或 `X-API-Key: <key>`。

报告默认使用确定性模板。设置 `REPORT_GENERATION_MODE=llm`、`REPORT_LLM_PROVIDER=local` 后，summary 响应会返回 `generated_by=llm`、`prompt_version`、`output_schema_version` 和完整 `llm_context`；该模式只生成报告文本，不改写检测标签、置信度、bbox、复核状态或设备元数据。

### 关键帧抽取

```bash
uv run python scripts/extract_keyframes.py path/to/video.mp4 \
  --output-dir data/keyframes \
  --interval-seconds 1.0 \
  --min-scene-delta 20 \
  --blur-threshold 10
```

该工具使用 OpenCV 读取视频，按固定间隔、场景变化和清晰度规则抽取关键帧。它是当前数据层的最小稳定实现，后续可接入 Edge Agent 或标注工作流。

### 阶段 A 公开裂缝数据集

当前阶段 A 不覆盖原有五分类 `data/data.yaml`，而是生成独立的单类裂缝 YOLO 数据集：

```bash
uv run python scripts/prepare_stage_a_crack_dataset.py \
  --download \
  --source data/public/senthilsk_crack_detection_dataset \
  --output data/stage_a_crack

uv run python scripts/train.py \
  --data data/stage_a_crack/data.yaml \
  --model yolov8n.pt \
  --epochs 1 \
  --batch 8 \
  --imgsz 320 \
  --device mps \
  --workers 0 \
  --project runs/stage_a_crack \
  --name smoke \
  --exist-ok
```

默认数据源为 Hugging Face `senthilsk/crack_detection_dataset`，许可证为 CC BY 4.0，原始标注为 COCO 格式。准备脚本会将 `crack`、`stairstep_crack`、`cracked` 映射为目标类 `0 crack`，并保留少量空标签负样本用于降低误报风险。
非 Apple Silicon 环境可将 `--device mps` 改为 `--device cpu` 或 CUDA 设备号。

### 阶段 B 公开代理数据（SDNET2018 + RDD2022）

当手头还没有真实试点图片/视频时，可先用公开数据继续推进 crack-only 开发验证，但这条路径**只算 public surrogate，不等同真实试点数据**。

- SDNET2018（官方页）：<https://digitalcommons.usu.edu/all_datasets/48/>
- RDD2022（官方 DOI / Figshare）：<https://doi.org/10.6084/m9.figshare.21431547>

仓库新增 `scripts/prepare_public_surrogate_crack_dataset.py`，用于把两套数据接进当前 Stage B 代理流程：

```bash
uv run python scripts/prepare_public_surrogate_crack_dataset.py \
  --sdnet2018-source data/public/SDNET2018 \
  --rdd2022-source data/public/RDD2022 \
  --output data/stage_b_public_surrogate_crack
```

默认行为：

- `SDNET2018`：纳入 `NonCrack` 负样本；`Crack` 图像默认跳过，避免把分类正样本误当作检测框 ground truth。
- `RDD2022`：读取 Pascal VOC XML，自动把 `D00` / `D10` / `D20` 映射到单类 `0 crack`；仅含非裂缝病害的图像作为负样本保留。

如果本地已有 Stage A ONNX 权重，也可以把 SDNET2018 的 `Crack` 图像作为代理正样本自动预标：

```bash
uv run python scripts/prepare_public_surrogate_crack_dataset.py \
  --sdnet2018-source data/public/SDNET2018 \
  --sdnet2018-crack-auto-label-model models/stage_a_crack/best.onnx \
  --rdd2022-source data/public/RDD2022 \
  --output data/stage_b_public_surrogate_crack
```

生成后可继续走当前 crack-only YOLO 流程；但文档和结论必须明确标记为“公开代理验证”，不能写成真实试点已完成。

## 工程化与部署

### 持续集成（CI）

仓库已补充最小 CI 流水线，覆盖以下检查：

- 后端：`uv run ruff check .`、`uv run pytest`
- 前端：`npm run lint`（只检查）、`npm run test -- --run`、`npm run build`

建议在每次提交前，本地至少执行与改动面对应的最小检查。

### Docker 部署（API）

项目提供最小 API 服务镜像构建能力，推荐通过环境变量注入运行参数。

#### 构建镜像

```bash
docker build -t vision-analysis-pro:latest .

# 如需在容器内使用 ONNX Runtime
docker build --build-arg INSTALL_ONNX=true -t vision-analysis-pro:onnx .
```

#### 运行容器

```bash
docker run --rm -p 8000:8000 \
  -e INFERENCE_ENGINE=stub \
  -e API_HOST=0.0.0.0 \
  -e API_PORT=8000 \
  vision-analysis-pro:latest
```

启动后可访问：

- OpenAPI: `http://localhost:8000/docs`
- 健康检查: `http://localhost:8000/api/v1/health`

### Docker Compose（前后端统一部署）

仓库现在提供最小 `docker-compose.yml`，可直接同时启动 API 与前端静态站点：

```bash
cp .env.example .env
docker compose up --build
```

默认访问地址：

- 前端：`http://localhost:4173`
- 后端 API：`http://localhost:8000`

如需启用 ONNX 容器构建，可在 `.env` 中设置 `COMPOSE_INSTALL_ONNX=true`。
如需覆盖默认 Python 包源，可在 `.env` 中设置 `COMPOSE_UV_DEFAULT_INDEX=<your-simple-index-url>`；默认使用 `https://pypi.org/simple`，避免首次构建卡在不可达镜像。首次冷启动仍可能因 `torch` / `nvidia-*` 大体积依赖下载而耗时较长。

### 试点环境一键启动

仓库新增 `scripts/bootstrap_trial.sh`，用于快速完成试点版环境准备：

```bash
bash scripts/bootstrap_trial.sh
```

该脚本会：

- 自动补齐 `.env`
- 创建 `data/`、`models/`、`runs/` 目录
- 直接启动 `docker compose up --build -d`

适合本地演示、试点交付预演和客户现场快速启动。

### 本地监控栈（Prometheus + Grafana）

仓库额外提供一个可叠加的监控编排文件：`docker-compose.observability.yml`。

启动业务服务和监控栈：

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.observability.yml up --build
```

默认访问地址：

- Prometheus：`http://localhost:9090`
- Grafana：`http://localhost:3000`

Grafana 默认账号密码来自 `.env`：

- 用户名：`GRAFANA_ADMIN_USER`
- 密码：`GRAFANA_ADMIN_PASSWORD`

首次启动后会自动预置：

- Prometheus 数据源
- `Vision API Overview` 仪表盘
- `config/prometheus_alert_rules.example.yml` 告警规则

#### 挂载模型文件运行

如果你要使用 YOLO 或 ONNX 推理，而不是 `stub`，需要把模型文件挂载进容器，并传入对应环境变量。例如：

```bash
docker run --rm -p 8000:8000 \
  -e INFERENCE_ENGINE=onnx \
  -e ONNX_MODEL_PATH=/app/models/stage_a_crack/best.onnx \
  -v ./models:/app/models \
  vision-analysis-pro:onnx
```

### 部署建议

- 开发环境优先使用 `INFERENCE_ENGINE=stub` 验证 API 与前端链路
- 真实模型路径统一使用 `INFERENCE_ENGINE=yolo` 或 `INFERENCE_ENGINE=onnx`
- Stage A 自训练模型路径已验收；本地权重位于 `runs/stage_a_crack/baseline_v0_1/weights/best.pt`，ONNX 位于 `models/stage_a_crack/best.onnx`
- API 与 Edge Agent 的部署口径保持一致：`stub` 用于链路测试，`yolo` 用于训练/实验，`onnx` 用于部署/边缘推理
- 生产环境通过 `CORS_ALLOW_ORIGINS` 明确限制前端域名，避免使用通配符
- 模型文件、数据目录、日志目录建议通过挂载卷管理
- 密钥类配置统一通过环境变量注入，不要写入镜像
- 告警规则示例见 `config/prometheus_alert_rules.example.yml`
- 本地监控栈使用 `docker-compose.observability.yml` 叠加启动，不影响最小部署路径

## 项目结构

```
vision_analysis_pro/
├── src/vision_analysis_pro/
│   ├── core/
│   │   ├── inference/          # 推理引擎（stub/yolo/onnx）
│   │   └── preprocessing/      # 预处理、可视化、关键帧抽取
│   ├── web/api/                # FastAPI 路由与依赖
│   └── edge_agent/             # 边缘 Agent 完整实现
│       ├── sources/            # 数据源（视频/图像/摄像头/RTSP）
│       ├── reporters/          # 上报器（HTTP + 离线缓存）
│       ├── agent.py            # Agent 主程序
│       ├── config.py           # 配置管理（YAML + ENV）
│       └── models.py           # 数据模型
├── scripts/                    # 训练/验证/评估/导出/基准测试/关键帧/公开数据准备脚本
├── config/                     # 配置文件示例
├── data/                       # YOLO 数据集与 data.yaml
├── models/                     # 训练/导出模型产物
├── web/                        # 前端（Vue3 + Vite + TS）
├── tests/                      # Python 测试（当前轻量基线 204 passed, 44 skipped）
├── docs/                       # 计划与进度文档
├── tasks.md                    # 当前 Harness Engineering 任务台账
├── pyproject.toml              # Python 依赖与工具链
└── ruff.toml                   # ruff 配置
```

## 开发指南

### AI 协作入口

- 仓库级协作规范：`AGENTS.md`
- GitHub Copilot 项目指令：`.github/copilot-instructions.md`
- 常用任务 prompt：
  - `.github/prompts/plan-visionAnalysisPro.prompt.md`
  - `.github/prompts/implement-change.prompt.md`
  - `.github/prompts/debug-failure.prompt.md`
  - `.github/prompts/repo-health-check.prompt.md`

### 代码规范

- Python：`uv run ruff check .`；格式化 `uv run ruff format .`
- 前端：`npm run lint`（ESLint 只检查）；自动修复使用 `npm run lint:fix`
- 浏览器级端到端：`cd web && npm run test:e2e`

### 测试

- 后端：`uv run pytest`（当前本地轻量环境为 204 passed, 44 skipped；legacy `models/best.onnx`、`data/images/*` 或可选本地模型产物缺失时会跳过对应测试）
- 前端：`npm run test -- --run`（90 passed）

### 提交规范

遵循 Conventional Commits：`feat(core): ...`、`fix(api): ...`、`docs(web): ...`

## 技术栈

### Python 核心

- **AI 框架**：Ultralytics YOLO (PyTorch)
- **推理引擎**：ONNX Runtime（7.25x 加速）
- **图像处理**：OpenCV, NumPy
- **Web 框架**：FastAPI, Uvicorn
- **测试**：Pytest

### 前端

- **框架**：TypeScript + Vue3 + Vite
- **组件库**：Element Plus
- **测试**：Vitest + Vue Test Utils

### 边缘 Agent

- **数据源**：视频文件、图像文件夹、摄像头、RTSP 流
- **推理引擎**：ONNX Runtime / YOLO
- **上报**：HTTP（指数退避重试）
- **离线缓存**：SQLite
- **配置**：YAML + 环境变量

## 路线图

当前执行入口以根目录 [`tasks.md`](tasks.md) 为准；`docs/development-plan.md` 保留系统级计划，`docs/progress.md` 记录已完成进度。下一步开发不再从分散 TODO 列表推进，而是按 `tasks.md` 的 Harness Engineering 任务台账逐项验收。

### ✅ MVP 阶段（已完成）

- [x] YOLO 训练脚本与最小数据集
- [x] 推理引擎（Stub + YOLO + ONNX）
- [x] API 上传/可视化闭环
- [x] 前端 Web MVP（上传 → 推理 → 展示）
- [x] ONNX 导出与性能基准测试（7.25x 加速）
- [x] 前端 UX 优化（错误处理、上传进度、健康状态）
- [x] 前端产品化视觉提升（工作台、设备页、上传区、Element Plus 皮肤）

### ✅ 边缘 Agent 阶段（已完成）

- [x] 边缘 Agent 核心实现
  - [x] 多数据源支持（视频/图像/摄像头/RTSP）
  - [x] HTTP 上报（指数退避重试）
  - [x] SQLite 离线缓存
  - [x] YAML + ENV 配置
  - [x] 优雅关闭（信号处理）
- [x] 单元测试（40 tests）

### 📋 后续开发两项分支

- **分支 A：真实试点标签到位**。推进 HE-007 Stage B Model Comparison（真实试点版）：训练自有试点数据模型，并与 Stage A 公共数据模型在同一试点验证集上对比。
- **分支 B：真实试点标签暂未到位（已完成）**。指标系统已升级为 `prometheus_client.Counter/Histogram/Gauge`，`/api/v1/metrics` 已暴露 histogram 分桶；审计日志列表也已补齐 `offset` / `total` 与前端分页控件。
- **公开代理补位（新增）**。当真实试点媒体尚未到位时，可先用 `SDNET2018 + RDD2022` 通过 `scripts/prepare_public_surrogate_crack_dataset.py` 构建 public surrogate 数据集，继续做非真实试点开发验证。
- **当前门禁**。若没有 reviewed positive pilot crack labels，不切换部署模型、不宣称真实试点精度、不推进五分类/分割/趋势模型主线。

完整验收标准、验证命令和非目标参见 [`tasks.md`](tasks.md)。

## 性能基准

| 引擎 | 平均延迟 (ms) | P95 (ms) | FPS | 加速比 |
|------|--------------|----------|-----|--------|
| YOLO | 33.36 | 34.78 | 29.97 | 1.0x |
| ONNX | 4.60 | 5.38 | 217.24 | **7.25x** |

*测试环境：Apple M4, 640x640 图像, 30 次迭代*

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[MIT License](LICENSE)

## 联系方式

- 作者：Liguo Ma
- 邮箱：maliguo@outlook.com
