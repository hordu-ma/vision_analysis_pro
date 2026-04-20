# 开发进度记录

Vision Analysis Pro 项目开发进度跟踪，按时间顺序记录每日开发成果。

---

## 📊 项目概览

**当前状态**：工程闭环已成型；短期路线收敛为裂缝检测试点 + 目标检测主线；当前执行入口为根目录 `tasks.md`
**最后更新**：2026-04-20
**后端测试**：184 passed, 43 skipped（当前轻量环境；缺少 `runs/train/exp/weights/best.pt`、`models/best.onnx` 与 `data/images/*` 时跳过对应测试）
**前端测试**：53 passed（vitest）
**代码质量**：ruff 全绿，ESLint 全绿，前端 build 通过

---

## 🎯 里程碑完成状态

| 里程碑 | 状态 | 完成时间 |
|--------|------|----------|
| M1: MVP 闭环打通 | ✅ 完成 | Week 1-2 |
| M2: 性能与可视化 | ✅ 完成 | Week 3-4 |
| M3: 边缘 Agent | ✅ 完成 | Week 5 |
| M4: 生产化与运营 | 🚧 进行中 | CI/Docker/metrics/report 持久化已落地，文档和质量基线继续收敛 |

## 🧭 当前路线决策（2026-04-19）

- 短期以 **裂缝检测试点** 为交付目标：`stub` 用于链路验证，Stage A 自训练 YOLO/ONNX 用于真实模型路径。
- 五类缺陷（crack/rust/deformation/spalling/corrosion）仍作为中期目标，但必须依赖真实数据集、训练权重和评估报告，不再在 README 中表述为已成熟能力。
- 数据层先使用 OpenCV 可解释规则抽取关键帧：固定间隔、场景变化阈值、模糊过滤；暂不引入复杂视频模型。
- 视觉识别主线保持 YOLO/ONNX 目标检测；DeepLab 语义分割仅在需要像素级裂缝面积/长度估计时作为后续 refinement。
- Transformer 趋势分析依赖连续批次与设备历史数据，后置到数据积累之后。
- LLM 只作为报告解释层，输入结构化检测结果、人工复核状态和设备元数据，不参与检测判定。

## 🗓️ 2026-04-19：路线收敛、关键帧与模板报告 ✅

### 核心成果

- ✅ 修复本地质量基线：ruff、pytest、前端 lint/test/build 重新对齐
- ✅ 修复 YOLO 权重缺失时 E2E/训练产物测试未跳过的问题
- ✅ 统一默认 YOLO 路径口径为 `runs/train/exp/weights/best.pt`
- ✅ `.gitignore` 忽略本地模型目录，避免误提交本地模型权重
- ✅ 新增 OpenCV 关键帧抽取模块与 CLI：固定间隔、场景变化、模糊过滤、可选落盘
- ✅ 新增边缘上报批次模板报告接口：`GET /api/v1/report/{batch_id}/summary`
- ✅ 前端 API 类型与服务层补充模板报告读取能力
- ✅ 下线 `hf_crack` 临时参考引擎，主线推理引擎收敛为 `stub` / `yolo` / `onnx`

### 当前验证

- ✅ `uv run ruff check .`
- ✅ `INFERENCE_ENGINE=stub uv run pytest -q`：184 passed, 43 skipped
- ✅ `cd web && npm run lint`
- ✅ `cd web && npm run test -- --run`：53 passed
- ✅ `cd web && npm run build`

---

## 🗓️ 2026-04-19：阶段 A 公开裂缝数据集 ✅

### 核心成果

- ✅ 选定可直接下载的公开数据源：Hugging Face `senthilsk/crack_detection_dataset`，Roboflow 导出，CC BY 4.0，COCO 标注
- ✅ 新增 `scripts/prepare_stage_a_crack_dataset.py`，将 COCO 标注转换为 YOLO 单类 `0 crack`
- ✅ 输出独立数据集 `data/stage_a_crack/data.yaml`，不覆盖五分类 `data/data.yaml`
- ✅ 默认保留 `crack`、`stairstep_crack`、`cracked` 为正样本，并保留少量空标签负样本
- ✅ `.gitignore` 忽略 `runs/`，避免本地训练权重和图表误提交

### 数据集统计

- train：2263 images，2461 crack objects，94 backgrounds
- val：462 images，439 crack objects，25 backgrounds
- test：225 images，215 crack objects，11 backgrounds

### 当前验证

- ✅ `uv run pytest tests/test_prepare_stage_a_dataset.py -q`：1 passed
- ✅ 手动校验 `data/stage_a_crack` 图像/标签一一匹配，且 YOLO 标注 class_id 均为 0
- ✅ YOLO smoke training：`uv run python scripts/train.py --data data/stage_a_crack/data.yaml --model yolov8n.pt --epochs 1 --batch 8 --imgsz 320 --device mps --workers 0 --project runs/stage_a_crack --name smoke --exist-ok`
- ✅ smoke 结果：mAP50 0.8165，mAP50-95 0.4258，Precision 0.7212，Recall 0.8072

---

## 🗓️ Week 1: API 基础与 Stub 实现（Day 1-5）

### Day 1: 对齐契约 ✅

- ✅ 定义 `DetectionBox` schema：bbox 格式 `[x1, y1, x2, y2]` 像素坐标
- ✅ 定义 `ErrorResponse` schema：统一错误响应结构
- ✅ OpenAPI 文档完整示例

### Day 2: Stub 推理引擎 ✅

- ✅ 实现 `StubInferenceEngine` 三种模式（normal/empty/error）
- ✅ 6 个单元测试全部通过
- ✅ 无需真实模型即可演示 API

### Day 3: API 上传闭环 ✅

- ✅ 实现文件上传校验（大小限制、MIME 类型、空文件）
- ✅ 完善错误处理与响应
- ✅ 14 个测试用例全部通过

### Day 4: 可视化能力 ✅

- ✅ 实现 `draw_detections()` 函数绘制检测框
- ✅ API 支持 `?visualize=true` 参数
- ✅ 返回 base64 Data URI 格式图像

### Day 5: Demo Day ✅

- ✅ 创建 `demo_request.py` 演示脚本
- ✅ 端到端验证（创建图像 → 推理 → 保存可视化）

---

## 🗓️ Week 2: 数据准备与真实模型集成（Day 6-10）

### Day 6: 类目与标注规范 ✅

- ✅ 确定 5 类缺陷标注类目（crack/rust/deformation/spalling/corrosion）
- ✅ 制定标注口径与指导原则
- ✅ 创建标注文档 `annotation_guidelines.md`

### Day 7: 数据目录与样例 ✅

- ✅ 建立 YOLO 数据集目录结构
- ✅ 创建 `data.yaml` 配置文件
- ✅ 准备数据目录与样例库规划

### Day 8: 训练脚本 ✅

- ✅ 实现 `scripts/train.py` 训练脚本
- ✅ 支持 YOLOv8n 模型训练
- ✅ 完成首次模型训练

### Day 9: YOLO 推理引擎 ✅

- ✅ 实现 `YOLOInferenceEngine` 真实推理引擎
- ✅ API 依赖注入支持引擎切换
- ✅ 58 个测试用例全部通过

### Day 10: 回归与收敛 ✅

- ✅ 补齐边界条件与异常路径测试
- ✅ 端到端集成测试
- ✅ 质量检查全绿（78 passed, 2 skipped）

---

## 🗓️ Week 3: 前端 Web MVP

### 前端基础搭建 ✅

- ✅ Vue3 + TypeScript 前端（Vite）
- ✅ 基础页面（上传 → 推理 → 展示）
- ✅ Element Plus 组件库集成
- ✅ ESLint/TS 类型检查全绿
- ✅ vitest 单元测试通过

### 组件实现 ✅

- ✅ `ImageUpload` - 图片上传组件
- ✅ `DetectionResult` - 检测结果展示
- ✅ `HealthStatus` - 服务状态显示
- ✅ API 服务层封装

---

## 🗓️ Week 4: ONNX 导出与性能优化

### ONNX 支持 ✅

- ✅ 实现 `scripts/export_onnx.py` 导出脚本
- ✅ 实现 `ONNXInferenceEngine` 推理引擎
- ✅ 完整的预处理/后处理/NMS 实现
- ✅ 22 个 ONNX 引擎测试全部通过

### 性能基准 ✅

- ✅ 实现 `scripts/benchmark.py` 基准测试脚本
- ✅ ONNX 相比 YOLO 提升 **7.25x**（33.36ms → 4.60ms）
- ✅ 生成基准报告 `docs/benchmark-report.md`

### 前端 UX 优化 ✅

- ✅ API 错误处理（axios 拦截器、ApiError 类）
- ✅ 上传进度条
- ✅ 健康状态自动刷新与重试
- ✅ 前端测试更新（28 tests）

---

## 🗓️ Week 5: 边缘 Agent 核心功能 ✅

**完成时间**：2025-12-24

### 核心成果

实现了完整的边缘 Agent 系统，支持多数据源采集、推理和结果上报。

### 数据模型 (`models.py`) ✅

- ✅ `FrameData` - 帧数据封装
- ✅ `Detection` - 单个检测结果
- ✅ `InferenceResult` - 推理结果
- ✅ `ReportPayload` - 上报数据载荷
- ✅ `CacheEntry` - 缓存条目
- ✅ `SourceType` / `ReportStatus` 枚举

### 配置管理 (`config.py`) ✅

- ✅ `EdgeAgentConfig` - 主配置类
- ✅ `SourceConfig` - 数据源配置
- ✅ `InferenceConfig` - 推理配置
- ✅ `ReporterConfig` - 上报器配置
- ✅ `CacheConfig` - 缓存配置
- ✅ 支持 **YAML + 环境变量**，优先级：ENV > YAML > 默认值
- ✅ 配置验证功能

### 数据源模块 (`sources/`) ✅

- ✅ `BaseSource` - 抽象基类，支持迭代器协议
- ✅ `VideoSource` - 本地视频文件（MP4/AVI/MKV 等）
- ✅ `FolderSource` - 图像文件夹（JPG/PNG/BMP 等）
- ✅ `CameraSource` - 摄像头/RTSP 流
- ✅ `create_source()` - 工厂函数
- ✅ FPS 限制、跳帧、循环播放支持

### 上报器模块 (`reporters/`) ✅

- ✅ `BaseReporter` - 抽象基类
- ✅ `HTTPReporter` - HTTP 上报器
  - ✅ 指数退避重试策略
  - ✅ 同步/异步上报接口
  - ✅ 健康检查
- ✅ `CacheManager` - SQLite 离线缓存
  - ✅ 自动创建数据库
  - ✅ 线程安全读写
  - ✅ 过期/溢出清理
- ✅ `create_reporter()` - 工厂函数

### Agent 主类 (`agent.py`) ✅

- ✅ 完整的 **采集 → 推理 → 上报** 循环
- ✅ 支持 ONNX / YOLO 推理引擎
- ✅ 后台线程处理上报队列
- ✅ 批量上报（按数量或时间间隔）
- ✅ 优雅关闭（SIGINT/SIGTERM 信号处理）
- ✅ 运行统计（帧数、检测数、上报数、FPS）
- ✅ CLI 入口点 `edge-agent`

### 配置与示例 ✅

- ✅ `config/edge_agent.example.yaml` - 示例配置文件
- ✅ `examples/run_edge_agent.py` - 使用示例脚本

### 单元测试 ✅

- ✅ 38 个边缘 Agent 测试全部通过
- ✅ 覆盖数据模型、配置、缓存、数据源

### 质量指标

- ✅ 当时测试通过率：141 passed, 25 skipped（历史轻量环境）
- ✅ 代码质量：ruff 0 错误
- ✅ 类型注解：完整

---

## 🗓️ 2026-04-18：文档对齐、AI Harness 与边缘上报闭环 ✅

### 核心成果

- ✅ 补齐云端 `POST /api/v1/report` 接收端，Edge Agent 默认上报 URL 可直接闭环
- ✅ 上报响应包含 `batch_id`、结果数量、检测数量和 `request_id`
- ✅ `/api/v1/metrics` 增加边缘上报计数器
- ✅ 补充 API 测试，使用 Edge Agent `ReportPayload.to_dict()` 验证真实契约
- ✅ 对齐 README、部署/Demo、进度、前端文档与当前命令
- ✅ 优化 Codex / GitHub Copilot CLI 协作指令与 prompt
- ✅ 前端 `lint` 改为只检查，自动修复改用 `lint:fix`
- ✅ 清理 Ruff 配置，`ruff.toml` 作为唯一 Ruff 配置入口

## 🗓️ 2026-04-18：生产化硬化修复 ✅

### 核心成果

- ✅ 修复 `api-server` 控制台入口，支持 `--host`、`--port`、`--reload/--no-reload` 与 `--log-level`
- ✅ 修复 Edge Agent `YAML + ENV` 配置合并逻辑，确保只用显式环境变量覆盖 YAML
- ✅ Dockerfile 增加 `INSTALL_ONNX` 构建参数，ONNX 容器运行说明与镜像依赖保持一致
- ✅ 补充部署/配置回归测试：API CLI、Docker ONNX 构建参数、Edge Agent 配置优先级
- ✅ 当时轻量后端基线更新为 `141 passed, 25 skipped`

## 🗓️ 2026-04-18：边缘上报持久化与鉴权 ✅

### 核心成果

- ✅ API 侧使用 SQLite 保存 Edge Agent 上报批次，默认路径 `data/reports.db`
- ✅ `POST /api/v1/report` 按 `batch_id` 幂等处理重复上报，重复批次不会重复累加结果/检测数量指标
- ✅ 新增 `GET /api/v1/report/{batch_id}` 查询已保存批次
- ✅ 支持可选 `CLOUD_API_KEY` 鉴权，兼容 `Authorization: Bearer <key>` 与 `X-API-Key`
- ✅ 补充持久化、重复批次、鉴权与缺失批次回归测试

### 相关文件结构

```
src/vision_analysis_pro/edge_agent/
├── __init__.py              # 模块导出
├── agent.py                 # Agent 主类 + CLI
├── config.py                # 配置管理
├── models.py                # 数据模型
├── sources/
│   ├── __init__.py          # 工厂函数
│   ├── base.py              # 数据源基类
│   ├── video.py             # 视频文件源
│   ├── folder.py            # 图像文件夹源
│   └── camera.py            # 摄像头/RTSP 源
└── reporters/
    ├── __init__.py          # 工厂函数
    ├── base.py              # 上报器基类
    ├── http.py              # HTTP 上报器
    └── cache.py             # 离线缓存管理

config/
└── edge_agent.example.yaml  # 示例配置文件

examples/
└── run_edge_agent.py        # 使用示例脚本

tests/
├── test_edge_agent.py       # 单元测试 (40 tests)
└── test_deployment_config.py # 部署配置回归测试 (3 tests)
```

---

## 📈 项目统计

### 代码指标

- **后端代码行数**：~6000+ 行（含注释）
- **测试代码行数**：~4000+ 行
- **文件数量**：80+ 个
- **测试文件**：16 个

### 测试覆盖

| 模块 | 测试数 | 状态 |
|------|--------|------|
| API/上报 | 26 | ✅ |
| Stub 引擎 | 6 | ✅ |
| YOLO 引擎 | 9 | ✅ |
| ONNX 引擎 | 22 | ✅ |
| 可视化 | 8 | ✅ |
| 边界案例 | 11 | ✅ |
| E2E 集成 | 11 | ✅ |
| 训练脚本 | 9 | ✅ |
| 关键帧抽取 | 4 | ✅ |
| 模板报告 | 2 | ✅ |
| 边缘 Agent | 40 | ✅ |
| 部署配置 | 3 | ✅ |
| 前端组件/服务 | 53 | ✅ |

### 性能基准

| 引擎 | 平均延迟 (ms) | P95 (ms) | FPS | 加速比 |
|------|--------------|----------|-----|--------|
| YOLO | 33.36 | 34.78 | 29.97 | 1.0x |
| ONNX | 4.60 | 5.38 | 217.24 | **7.25x** |

*测试环境：Apple M4, 640x640 图像, 30 次迭代*

---

## 📁 完整目录结构

```
vision_analysis_pro/
├── src/vision_analysis_pro/
│   ├── core/
│   │   ├── inference/              # 推理引擎
│   │   │   ├── base.py             # 抽象基类
│   │   │   ├── stub_engine.py      # Stub 引擎
│   │   │   ├── python_engine.py    # Python 引擎
│   │   │   ├── yolo_engine.py      # YOLO 引擎 ✅
│   │   │   └── onnx_engine.py      # ONNX 引擎 ✅
│   │   └── preprocessing/
│   │       ├── transforms.py       # 图像预处理
│   │       └── visualization.py    # 可视化工具 ✅
│   ├── web/api/                    # FastAPI 应用
│   │   ├── main.py                 # 主应用
│   │   ├── schemas.py              # API Schema
│   │   ├── report_store.py         # Edge Agent 上报持久化
│   │   ├── deps.py                 # 依赖注入
│   │   └── routers/
│   │       ├── inference.py        # 推理路由
│   │       └── reports.py          # 上报路由
│   └── edge_agent/                 # 边缘 Agent ✅
│       ├── agent.py                # 主程序
│       ├── config.py               # 配置管理
│       ├── models.py               # 数据模型
│       ├── sources/                # 数据源
│       │   ├── base.py
│       │   ├── video.py
│       │   ├── folder.py
│       │   └── camera.py
│       └── reporters/              # 上报器
│           ├── base.py
│           ├── http.py
│           └── cache.py
├── web/                            # 前端 Vue3 应用 ✅
│   └── src/
│       ├── components/
│       ├── services/
│       └── App.vue
├── scripts/                        # 脚本
│   ├── train.py                    # 训练脚本 ✅
│   ├── export_onnx.py              # ONNX 导出 ✅
│   ├── benchmark.py                # 性能基准 ✅
│   ├── extract_keyframes.py        # 关键帧抽取 ✅
│   └── prepare_stage_a_crack_dataset.py # 阶段 A 公开裂缝数据集准备 ✅
├── config/
│   └── edge_agent.example.yaml     # Agent 配置示例 ✅
├── data/                           # 数据集
├── models/                         # 模型文件
│   └── .gitkeep                    # 本地模型缓存目录，权重不提交
├── tests/                          # 测试 (当前轻量基线 184 passed, 43 skipped) ✅
├── docs/                           # 文档
├── examples/                       # 示例脚本
└── tasks.md                        # 当前 Harness Engineering 任务台账
```

---

## 🚀 快速开始

### 环境准备

```bash
# 安装依赖
uv sync
uv sync --extra onnx     # ONNX 支持
uv sync --extra dev      # 开发依赖
```

### 运行 API

```bash
uv run uvicorn vision_analysis_pro.web.api.main:app --reload
```

### 运行边缘 Agent

```bash
# 使用配置文件
edge-agent -c config/edge_agent.example.yaml

# 使用命令行参数
python examples/run_edge_agent.py --source-type folder --source-path data/images/test

# 使用环境变量
EDGE_AGENT_SOURCE_TYPE=folder EDGE_AGENT_SOURCE_PATH=data/images/test edge-agent
```

### 运行测试

```bash
# 全部后端测试
uv run pytest

# 边缘 Agent 测试
uv run pytest tests/test_edge_agent.py -v

# 前端测试
cd web && npm run test -- --run
```

### 导出 ONNX 模型

```bash
uv run python scripts/export_onnx.py --output models/best.onnx
```

### 运行性能基准

```bash
uv run python scripts/benchmark.py --iterations 30 --output docs/benchmark-report.md
```

---

## 最新进展：HE-001 Stage A YOLO Baseline v0.1

2026-04-20 完成 Stage A crack-only YOLO 基线验收。

- 数据集：`data/stage_a_crack/data.yaml`，来自 Hugging Face `senthilsk/crack_detection_dataset`，单类 `crack`。
- 训练命令：`uv run python scripts/train.py --data data/stage_a_crack/data.yaml --model yolov8n.pt --epochs 50 --batch 8 --imgsz 640 --device 0 --workers 0 --project runs/stage_a_crack --name baseline_v0_1 --exist-ok`。
- 训练结果：EarlyStopping 于 31 epochs 结束，best epoch 为 26。
- best 验证指标：precision `0.92581`，recall `0.91344`，mAP50 `0.95556`，mAP50-95 `0.63521`。
- 本地产物：`runs/stage_a_crack/baseline_v0_1/weights/best.pt`，`models/stage_a_crack/best.onnx`。
- 评估记录：`docs/stage-a-yolo-baseline-v0.1.md`。
- 烟测：YOLO direct、FastAPI `/api/v1/inference/image`、ONNX direct 均通过。

Stage A 可用于真实 YOLO/ONNX 链路验证；是否可用于试点仍需 Stage B 自有数据闭环确认。

## 最新进展：HE-002 / HE-003 / HE-006 主线推进

2026-04-20 继续完成浏览器 smoke、Edge Agent 关键帧接入和 Stage B 数据闭环。

- HE-002：`web/e2e/app.spec.ts` 已覆盖上传图片、触发推理、展示结果区、检测数量和首要缺陷。
- HE-003：`VideoSource` 默认保留逐帧读取；启用 `source.keyframes.enabled` 后复用 OpenCV keyframe extractor 读取关键帧。
- HE-003：`config/edge_agent.example.yaml` 增加 `source.keyframes` 示例配置。
- HE-006：新增 `scripts/prepare_stage_b_pilot_dataset.py`，可从本地图片或视频关键帧生成 crack-only YOLO 数据集。
- HE-006：本地生成 `data/stage_b_pilot_crack/data.yaml` 和 `manifest.json`，该目录仍被 git 忽略。
- HE-006：新增 `docs/stage-b-pilot-data.md`，说明 Stage B 数据进入、标注状态、校验和 HE-007 交接。

当前 Stage B 本地 smoke 使用 checked-in sample images 生成 pending-annotation 空标签，只验证数据结构和流程；训练对比仍在 HE-007，必须等 reviewed pilot labels 后执行。

## 📋 下一步计划

下一步开发计划以根目录 `tasks.md` 为准。当前活跃队列：

1. **HE-004 Edge Agent Reporting Steady State**：覆盖离线缓存回放、重复 batch、API Key 与报告摘要。
2. **HE-005 Pilot Deployment Runbook**：明确试点部署、模型挂载、观测与回滚步骤。
3. **HE-007 Stage B Model Comparison**：训练自有数据模型，并与 Stage A 公共数据模型做同集对比。
4. **HE-008 Full Inspection Flow Hardening**：硬化上传/批量任务、推理、复核、报告摘要和导出链路。

非关键路径：MQTT、Rust/PyO3、DeepLab、Transformer 趋势分析、LLM 报告扩展均后置，除非 `tasks.md` 显式提升优先级。会话开头的四条方向已在 `tasks.md` 的 "Original Direction Traceability" 中映射到具体 HE 任务。

---

**文档维护者**：Vision Analysis Pro Team  
**最后更新**：2026-04-20
**下次更新**：完成 HE-004 Edge Agent Reporting Steady State 后
