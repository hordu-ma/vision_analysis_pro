# 开发进度记录

Vision Analysis Pro 项目开发进度跟踪，按时间顺序记录每日开发成果。

---

## 📊 项目概览

**当前状态**：工程闭环已成型；在真实环境样本暂不可得前，当前交付焦点切换为试点系统封装与完整预演；当前执行入口为根目录 `tasks.md`
**最后更新**：2026-05-07
**后端测试**：218 passed, 44 skipped（当前轻量环境；缺少 legacy `runs/train/exp/weights/best.pt`、`models/best.onnx`、`data/images/*` 或可选本地模型产物时跳过对应测试）
**前端测试**：90 passed（vitest）
**代码质量**：ruff 全绿，ESLint 全绿，前端 build 与 3 条 browser E2E 通过；工作台与设备页产品化视觉提升已完成

---

## 🎯 里程碑完成状态

| 里程碑 | 状态 | 完成时间 |
|--------|------|----------|
| M1: MVP 闭环打通 | ✅ 完成 | Week 1-2 |
| M2: 性能与可视化 | ✅ 完成 | Week 3-4 |
| M3: 边缘 Agent | ✅ 完成 | Week 5 |
| M4: 生产化与运营 | 🚧 进行中 | CI/Docker/metrics/report 持久化已落地，文档和质量基线继续收敛 |

## 🗓️ 2026-05-07：试点系统封装与完整预演 ✅

### 核心成果

- ✅ 将主账本当前焦点调整为 **Trial System Packaging and Rehearsal**：先把系统封装为可部署、可演示、可采集真实样本的输电塔巡检试点系统，再在现场数据到位后扩充样本并训练多类模型。
- ✅ 明确 6 步顺序：系统封装、当前模型能力接入、真实数据采集入口、人工复核与标注准备、完整试点预演、现场数据到位后的 `prototype_v0_2` 训练与替换。
- ✅ 完成 `stub` 模式 API 预演：health、live、metrics、单图上传、两图批量任务均通过。
- ✅ 完成上报与报告链路预演：设备 metadata、`POST /api/v1/report`、人工复核、模板摘要、CSV 导出、批次列表、设备列表和告警摘要均通过。
- ✅ 完成 Stage A ONNX readiness 检查：`models/stage_a_crack/best.onnx` 可加载，使用有效 JPEG 样本可完成真实模型路径推理。
- ✅ 完成 Edge Agent ONNX 上报预演：Stage A crack 样本检测到 1 个目标并上报到 API，成功上报 1 批次。
- ✅ 提交前质量门禁通过：后端 ruff/pytest、前端 lint/test/build 和 browser E2E 全部通过。

### 当前验证

- ✅ `docker compose config`
- ✅ `REPORT_STORE_DB_PATH=/tmp/vision-analysis-pro-trial.db INFERENCE_ENGINE=stub API_RELOAD=false uv run uvicorn vision_analysis_pro.web.api.main:app --host 127.0.0.1 --port 8000`
- ✅ `curl` 验证 `/api/v1/health`、`/api/v1/health/live`、`/api/v1/metrics`
- ✅ `curl -F file=@data/samples/web_rust_bolt.jpg http://127.0.0.1:8000/api/v1/inference/image?visualize=true`
- ✅ `curl -F files=@... http://127.0.0.1:8000/api/v1/inference/images/tasks?visualize=false`
- ✅ `curl` 验证 report intake、review、summary、CSV export、batch list、device list、alert summary
- ✅ `REPORT_STORE_DB_PATH=/tmp/vision-analysis-pro-trial-onnx.db INFERENCE_ENGINE=onnx ONNX_MODEL_PATH=models/stage_a_crack/best.onnx ... --port 8001`
- ✅ `uv run python examples/run_edge_agent.py --engine onnx --model-path models/stage_a_crack/best.onnx --confidence 0.1 ...`
- ✅ `uv run ruff check .`
- ✅ `uv run pytest`：218 passed, 44 skipped
- ✅ `cd web && npm run lint`
- ✅ `cd web && npm run test -- --run`：90 passed
- ✅ `cd web && npm run build`
- ✅ `cd web && npm run test:e2e`：3 passed（本机先执行过一次 `cd web && npx playwright install chromium` 补齐浏览器）

### 口径说明

- 这次预演验证的是系统封装和现场试点链路，不是多类塔材模型精度。
- 当前多类塔材模型仍保持实验状态；在正常阈值下稳定检测前，不作为默认部署模型。
- 真实现场数据到位后，系统本身将作为采集、复核、导出和训练集沉淀入口。
- 预演中发现 `data/samples/web_rust_bolt.jpg` 实际是 HTML 文档伪装成 `.jpg`，`stub` 可通过但真实 ONNX 解码会失败；后续真实模型 smoke 应使用 `data/samples/web_rust_chain.jpg` 或 Stage A 数据集中的有效 JPEG。

## 🗓️ 2026-05-07：试点封装 1-4 交付化补齐 ✅

### 核心成果

- ✅ 补齐客户远程演示流程：部署机器不带到客户现场时，推荐屏幕共享远程演示；如客户需要自行访问，需提前准备 HTTPS/反代/CORS/API Key，不在会议中临时排障。
- ✅ 补齐当前模型能力使用规则：`stub` 做稳定流程演示，Stage A ONNX 做真实模型路径展示，多类塔材模型保持实验状态。
- ✅ 补齐真实数据采集入口 SOP：明确前端上传、Edge Agent 文件夹源、视频关键帧三条入口，以及现场 metadata 字段。
- ✅ 补齐人工复核与标注准备 SOP：明确 review 与 training annotation 的边界、reviewed labels 目录、预标注、数据集生成和 `prototype_v0_2` 训练门禁。

### 产物

- `docs/customer-remote-demo.md`
- `docs/field-data-intake-and-review.md`
- README、demo、deployment、progress 和主账本均已加入入口。

## 🗓️ 2026-04-30：多类塔材缺陷原型入口 ✅

### 核心成果

- ✅ 当前开发焦点从 crack-only HE-007 门禁切换为多类塔材缺陷原型。
- ✅ 明确 4 类原型映射：`deformation`、`tower_corrosion`、`loose_bolt`、`bolt_rust`。
- ✅ 新增 `scripts/prepare_multiclass_prototype_inbox.py`，用于整理 `/home/liguoma/Downloads/锈蚀、松动、变形、腐蚀/` 下的本地图片。
- ✅ 已生成本地 ignored inbox：`data/multiclass_inbox/raw_images/`、`metadata/`、`reviewed_labels/`、`annotation_queue.csv`、`classes.json` 和 `manifest.json`。
- ✅ 当前本地图片统计：24 张，其中 `deformation=4`、`tower_corrosion=5`、`loose_bolt=7`、`bolt_rust=8`。
- ✅ 新增 `docs/multiclass-tower-defect-prototype.md` 记录原型范围、类别映射、标注规则和训练前置条件。

### 当前验证

- ✅ `uv run python scripts/prepare_multiclass_prototype_inbox.py`
- ✅ `uv run ruff check scripts/prepare_multiclass_prototype_inbox.py tests/test_prepare_multiclass_prototype_inbox.py`
- ✅ `uv run pytest tests/test_prepare_multiclass_prototype_inbox.py -q`

### 口径说明

- 本次不提交原始图片、metadata 或标签数据；`data/` 仍保持 git ignored。
- 当前状态是 `ready_for_annotation=true`、`ready_for_training=false`。
- 下一步是人工 bbox 标注，标注完成后再生成 YOLO 数据集并训练原型模型。
- Stage A crack-only ONNX 保留为历史演示/链路模型，HE-007 真实裂缝试点版暂不作为当前原型阻塞条件。

## 🗓️ 2026-04-30：多类 YOLO 数据集与 smoke training ✅

### 核心成果

- ✅ 基于 `data/multiclass_inbox/reviewed_labels/` 生成本地 YOLO 数据集 `data/multiclass_tower_defect/`。
- ✅ 新增 `scripts/prepare_multiclass_tower_dataset.py`，覆盖多类标签校验、图片/标签配对、数据切分、`data.yaml` 和 `manifest.json` 生成。
- ✅ 新增 `tests/test_prepare_multiclass_tower_dataset.py`，覆盖数据集生成、缺失标签和非法类别。
- ✅ 当前数据集统计：24 张图片、24 个 bbox，train/val/test 为 16 / 4 / 4。
- ✅ 完成 1-epoch CPU smoke training，生成 `runs/multiclass_tower_defect/smoke_v0_1/weights/best.pt`。

### 当前验证

- ✅ `uv run python scripts/prepare_multiclass_tower_dataset.py`
- ✅ `uv run python scripts/prepare_multiclass_tower_dataset.py --validate-only`
- ✅ `uv run python scripts/train.py --data data/multiclass_tower_defect/data.yaml --model yolov8n.pt --epochs 1 --batch 4 --imgsz 320 --device cpu --workers 0 --project runs/multiclass_tower_defect --name smoke_v0_1 --exist-ok --patience 1`
- ✅ smoke metrics：mAP50 `0.0412`、mAP50-95 `0.0061`、precision `0.0039`、recall `0.7500`

### 口径说明

- 本次训练只证明多类原型数据链路和 YOLO 训练链路可运行，不代表模型质量。
- `data/multiclass_tower_defect/` 和 `runs/multiclass_tower_defect/` 均为 ignored 本地产物，不提交到 git。
- 下一步是使用 smoke 权重做一次本地推理验证，再决定是否导出 ONNX 并接入 API/前端。

## 🗓️ 2026-04-30：多类原型推理 smoke ✅

### 核心成果

- ✅ 新增 `scripts/smoke_multiclass_tower_inference.py`，可加载本地多类 YOLO 权重，校验 4 类映射，并输出 JSON 与预览图。
- ✅ 新增 `tests/test_smoke_multiclass_tower_inference.py`，覆盖类别映射校验。
- ✅ 已验证 `runs/multiclass_tower_defect/smoke_v0_1/weights/best.pt` 能加载并运行。
- ✅ 已额外训练 `runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt`，第 14 轮早停，mAP50 `0.0624`、mAP50-95 `0.0251`。
- ✅ 已用 `prototype_v0_1` 完成本地推理 smoke。

### 当前验证

- ✅ `uv run python scripts/smoke_multiclass_tower_inference.py --model runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt --conf 0.25 ...`：4 张 test 图，0 detections
- ✅ `uv run python scripts/smoke_multiclass_tower_inference.py --model runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt --conf 0.001 ...`：4 张 test 图，191 个低阈值候选，类别偏向 `tower_corrosion` / `bolt_rust`
- ✅ `uv run python scripts/smoke_multiclass_tower_inference.py --model runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt --images data/multiclass_tower_defect/images/train --conf 0.25 ...`：16 张 train 图，0 detections

### 口径说明

- 当前模型可以加载并推理，但正常展示阈值下没有稳定检测。
- 不导出 ONNX，不接入 API/前端。
- 下一步应改进数据和标注：收紧 bbox、补充每类近景正样本、允许多框标注，然后训练 `prototype_v0_2`。

## 🧭 当前路线决策（2026-04-19）

- 短期以 **裂缝检测试点** 为交付目标：`stub` 用于链路验证，Stage A 自训练 YOLO/ONNX 用于真实模型路径。
- 五类缺陷（crack/rust/deformation/spalling/corrosion）仍作为中期目标，但必须依赖真实数据集、训练权重和评估报告，不再在 README 中表述为已成熟能力。
- 数据层先使用 OpenCV 可解释规则抽取关键帧：固定间隔、场景变化阈值、模糊过滤；暂不引入复杂视频模型。
- 视觉识别主线保持 YOLO/ONNX 目标检测；DeepLab 语义分割仅在需要像素级裂缝面积/长度估计时作为后续 refinement。
- Transformer 趋势分析依赖连续批次与设备历史数据，后置到数据积累之后。
- LLM 只作为报告解释层，输入结构化检测结果、人工复核状态和设备元数据，不参与检测判定。

## 🗓️ 2026-04-26：Pilot Inbox 前置校验 ✅

### 核心成果

- ✅ 新增 `scripts/validate_pilot_inbox.py`，把真实样本交接清单落成 HE-007 前置校验命令。
- ✅ 默认校验 `data/pilot_inbox/raw_images`、`data/pilot_inbox/reviewed_labels` 和 `data/pilot_inbox/metadata`。
- ✅ 覆盖图像可读性、孤儿标签、必填媒体元数据、人工复核字段、YOLO crack-only 标签格式、pending 样本、reviewed negative 和 reviewed positive crack box 统计。
- ✅ 默认要求至少存在一个 reviewed positive crack box；`--allow-no-positive` 仅用于真实标签到位前的结构演练。
- ✅ 新增 `tests/test_validate_pilot_inbox.py`，覆盖正样本就绪、缺失 metadata、无正样本门禁、结构演练和 manifest metadata 输入。

### 当前验证

- ✅ `uv run ruff check scripts/validate_pilot_inbox.py tests/test_validate_pilot_inbox.py`
- ✅ `uv run pytest tests/test_validate_pilot_inbox.py tests/test_prepare_stage_b_dataset.py -q`：11 passed

### 口径说明

- 本次不引入新模型、不切换部署模型、不提交真实 pilot 媒体。
- HE-007 真实试点版仍以 reviewed positive pilot crack labels 为触发条件。

## 🗓️ 2026-04-22：前端产品化视觉提升 ✅

### 核心成果

- ✅ 保留 Vue 3 + Element Plus 组件体系，但通过自有视觉系统降低默认样品感。
- ✅ `App.vue` 增强为深色操作侧栏 + 品牌标识 + telemetry + 导航状态 + 顶部流程状态的产品外壳。
- ✅ `style.css` 统一产品色彩、字体、圆角、阴影，并覆盖 Element Plus 的按钮、输入、单选、表格、卡片、空状态和告警样式。
- ✅ `WorkspacePage.vue` 增加巡检交付流程条，首屏更像任务工作台而不是组件堆叠。
- ✅ `DeviceManagementView.vue` 增加 Edge/API/Review 信号链路，设备页更贴近运维控制台。
- ✅ `ImageUpload.vue` 上传区升级为定制检测发起面板；`HealthStatus.vue` 控件改为方角产品控件，减少默认图标/按钮感。
- ✅ 使用 Playwright 预览桌面工作台、设备页和移动工作台截图，未发现明显文字重叠或布局挤压。

### 当前验证

- ✅ `cd web && npm run lint`
- ✅ `cd web && npm run test -- --run`：90 passed
- ✅ `cd web && npm run build`
- ✅ Playwright screenshot 预览：桌面工作台、桌面设备页和移动工作台均已检查；截图作为本地临时预览产物，不纳入仓库。

### 口径说明

- 本次是前端表现层提升，不改变 API、路由、组件事件或数据契约。
- 截图文件仅用于本地预览，不纳入 git 提交。

## 🗓️ 2026-04-22：HE-007 代理路径复核与文档对齐 ✅

### 核心结论

- ✅ 已检查本地数据与模型产物：Stage A YOLO/ONNX、Stage B 代理模型与 `data/stage_b_pilot_crack/` 均存在。
- ✅ 未发现新的真实试点媒体目录或人工复核正样本标签；真实试点版 HE-007 仍未触发。
- ✅ `data/stage_b_pilot_crack/` 校验通过，确认当前本地 Stage B 是 Stage A 测试集自动标注代理数据。
- ✅ Stage A 与 Stage B 代理模型在同一 Stage A val 集（462 张图像）上完成 CPU 复核评估，指标复现，结论仍为 **保留 Stage A 作为部署模型**。
- ✅ 对齐 `AGENTS.md`、`README.md`、`tasks.md`、`docs/development-plan.md`、`docs/stage-b-model-comparison.md`、`docs/stage-b-pilot-data.md`、`docs/demo.md` 与 `docs/e2e-test-results.md`，统一下一步门禁与测试基线口径。

### 当前验证

- ✅ `uv run python scripts/prepare_stage_b_pilot_dataset.py --output data/stage_b_pilot_crack --validate-only`
- ✅ `uv run python scripts/evaluate.py --model runs/stage_a_crack/baseline_v0_1/weights/best.pt --data data/stage_a_crack/data.yaml --split val --device cpu --batch 8`
  - Stage A：mAP50=0.9661，mAP50-95=0.6320，P=0.9434，R=0.9203
- ✅ `uv run python scripts/evaluate.py --model runs/stage_b_pilot_crack/comparison_v0_1/weights/best.pt --data data/stage_a_crack/data.yaml --split val --device cpu --batch 8`
  - Stage B 代理：mAP50=0.8711，mAP50-95=0.3898，P=0.8844，R=0.8383

### 口径说明

- “完成 1-5”中真实数据收集与人工复核无法由仓库自动生成；本次完成的是可验证的现有代理数据校验、同集模型评估复核和文档对齐。
- 下一步仍是获取 reviewed positive pilot crack labels 后重跑 HE-007 真实试点版；在此之前不切换部署模型、不宣称真实试点精度。

## 🗓️ 2026-04-21：公开代理数据入口（SDNET2018 + RDD2022）✅

### 核心成果

- ✅ 新增 `src/vision_analysis_pro/core/crack_yolo_dataset.py`，抽出 crack-only YOLO 数据集共享校验与 `data.yaml` 写入逻辑。
- ✅ 新增 `scripts/prepare_public_surrogate_crack_dataset.py`，支持把 `SDNET2018` 与 `RDD2022` 接入当前 crack-only 代理数据流程。
- ✅ `SDNET2018` 默认纳入 `NonCrack` 负样本；如提供 `--sdnet2018-crack-auto-label-model`，可对 `Crack` 图像做 ONNX 代理预标。
- ✅ `RDD2022` 支持读取官方 Pascal VOC XML，并把 `D00` / `D10` / `D20` 自动映射到单类 `0 crack`；非裂缝病害图像按负样本保留。
- ✅ 新增 `tests/test_prepare_public_surrogate_dataset.py`，并将后端轻量基线提升到 `204 passed, 44 skipped`。

### 当前验证

- ✅ `uv run ruff check .`
- ✅ `uv run pytest`：204 passed, 44 skipped
- ✅ `cd web && npm run lint`
- ✅ `cd web && npm run test -- --run`：90 passed
- ✅ `cd web && npm run build`

### 口径说明

- 这条路径用于 **public surrogate / 公开代理验证**，不是“真实试点数据”。
- 真实试点版 HE-007 仍必须等待 reviewed positive pilot crack labels 到位后重跑。

---

## 🗓️ 2026-04-21：Compose 下载阻塞修复、Prometheus 指标升级、审计日志分页 ✅

### 核心成果

- ✅ `Dockerfile`、`docker-compose.yml` 和 `.env.example` 增加可覆盖的 `UV_DEFAULT_INDEX` / `COMPOSE_UV_DEFAULT_INDEX`，默认显式使用 `https://pypi.org/simple`。
- ✅ `pyproject.toml` 显式声明 `prometheus-client` 依赖，并锁定 `uv` 默认索引为官方 PyPI，Compose 构建已越过原先不可达镜像导致的 `uv sync` 超时点。
- ✅ `app.state.metrics` 已替换为基于 `prometheus_client.Counter/Histogram/Gauge` 的封装，`/api/v1/metrics` 继续兼容 Prometheus scrape，并新增请求/推理耗时 histogram 分桶。
- ✅ 审计日志接口升级为列表响应：支持 `offset`、`total` 和 `actor` 过滤；前端设备页补齐审计日志分页控件。
- ✅ 新增后端分页/分桶测试与前端 `AuditLogList.spec.ts`，轻量基线提升到后端 `202 passed, 44 skipped`、前端 `90 passed`。

### 当前验证

- ✅ `uv run ruff check .`
- ✅ `uv run pytest`：202 passed, 44 skipped
- ✅ `cd web && npm run lint`
- ✅ `cd web && npm run test -- --run`：90 passed
- ✅ `cd web && npm run build`
- ✅ `docker compose config`
- ✅ `docker compose --progress plain build api`：已越过原 `uv` 镜像超时阶段，当前冷缓存构建主要耗时在 `torch` / `nvidia-*` 大体积依赖下载

---

## 🗓️ 2026-04-21：Stage C E2E、分页 UI 与 trace_id 日志 ✅

### 核心成果

- ✅ Playwright E2E 从 1 条扩展到 3 条：单图上传、批量任务历史打开、上报批次打开并保存复核。
- ✅ 前端接入列表分页 UI：历史批次、最近任务、设备概览均支持上一页/下一页。
- ✅ `ReportBatchList` 单测补充分页事件覆盖；前端 Vitest 基线提升到 86 passed。
- ✅ `X-Trace-ID` 不仅回显响应头，也进入 `request_completed` / `request_failed` 结构化日志字段。
- ✅ 修复前端 `ImageUpload.spec.ts` 在生产 build 类型检查中的 `wrapper.vm` 类型断言问题。

### 当前验证

- ✅ `uv run ruff check .`
- ✅ `uv run pytest tests/test_api_inference.py -q`
- ✅ `cd web && npm run lint`
- ✅ `cd web && npm run test -- --run`：86 passed
- ✅ `cd web && npm run build`
- ✅ `cd web && npm run test:e2e`：3 passed

---

## 🗓️ 2026-04-21：Pilot Deployment Runbook 演练 ✅

### 核心成果

- ✅ `docker compose config` 通过，确认默认 profile 为 `INFERENCE_ENGINE=stub`，Stage A ONNX/Yolo 路径与示例配置一致。
- ✅ Web 容器镜像构建通过。
- ⚠️ API 容器镜像构建阻塞于外部 Python 包源下载超时，失败依赖为 `nvidia-nvjitlink-cu12==12.8.93` 与 `nvidia-nvshmem-cu12==3.3.20`；判断为首次容器构建的网络/依赖下载 blocker，不是 Compose 配置错误。
- ✅ 用本地直接运行完成替代 smoke：stub 回滚链路、Stage A ONNX health/ready/metrics/inference、Edge Agent ONNX 检测并上报到云端 API。
- ✅ 演练记录、blocker、重跑命令和回滚结论已回填 `docs/deployment.md`。

### 当前验证

- ✅ `docker compose config`
- ✅ `docker compose up --build -d`：Web build 通过；API build 因外部依赖下载超时阻塞
- ✅ `INFERENCE_ENGINE=stub ... uv run uvicorn ...`：health 与 inference smoke 通过
- ✅ `INFERENCE_ENGINE=onnx ONNX_MODEL_PATH=models/stage_a_crack/best.onnx ... uv run uvicorn ...`：health/ready/metrics/inference smoke 通过
- ✅ `examples/run_edge_agent.py --engine onnx --confidence 0.1 ...`：1 帧、1 条检测、HTTP 上报 `202 Accepted`

---

## 🗓️ 2026-04-21：HE-007 Stage B 模型对比（代理运行）✅

### 核心成果

- ✅ 新增 `scripts/auto_label_onnx.py`：用 ONNX 模型批量生成 YOLO 格式自动标注
- ✅ 用 Stage A 测试集（225 张）自动标注后构建 Stage B 代理数据集（157 train / 33 val / 35 test）
- ✅ 训练 Stage B 模型：yolov8n.pt 起点，30 epoch，早停于第 24 epoch
- ✅ 在同一 Stage A val 集（462 张）对比两个模型：
  - Stage A：mAP50=0.966，mAP50-95=0.632，P=0.943，R=0.920
  - Stage B：mAP50=0.871，mAP50-95=0.390，P=0.884，R=0.838
- ✅ 评估报告：`docs/stage-b-model-comparison.md`
- ✅ **决策：当前保留 Stage A 作为部署模型**

### 局限说明

Stage B 使用同分布代理数据（Stage A 测试集），无法体现跨域泛化。
有真实巡检图片后，用 Stage A ONNX 预标注 → 人工复核 → 重跑对比，结果更有指导意义。

### 当前验证

- ✅ `uv run ruff check .`
- ✅ `uv run pytest -q`：198 passed, 44 skipped

---

## 🗓️ 2026-04-21：API 分页、X-Trace-ID、前端组件测试（P1/P2）✅

### 核心成果

- ✅ 后端列表接口支持 `offset` 分页：`/reports/batches`、`/reports/devices`、`/inference/images/tasks`
- ✅ 响应增加 `total` 字段（`int | None`，向后兼容）；ORDER BY 添加确定性 tie-breaker（`batch_id DESC`/`task_id DESC`）
- ✅ 中间件透传 `X-Trace-ID`：请求携带时在响应头回显，不自动生成
- ✅ 新增 6 个后端分页 & trace-id 测试（pagination_offset × 3 + invalid_offset + trace_id_echoed + trace_id_absent）
- ✅ 新增 4 个前端组件 spec 文件：`ImageUpload.spec.ts`（7 tests）、`BatchTaskStatus.spec.ts`（11 tests）、`ReportBatchList.spec.ts`（7 tests）、`ReportDetailDrawer.spec.ts`（6 tests）
- ✅ 前端服务层 `api.ts` 所有列表方法支持 `offset` 参数

### 当前验证

- ✅ `uv run ruff check .`
- ✅ `uv run pytest -q`：198 passed, 44 skipped
- ✅ `cd web && npm run lint`
- ✅ `cd web && npm run test -- --run`：85 passed

---

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
- ✅ `INFERENCE_ENGINE=stub uv run pytest -q`：192 passed, 44 skipped
- ✅ `cd web && npm run lint`
- ✅ `cd web && npm run test -- --run`：53 passed
- ✅ `cd web && npm run build`
- ✅ `cd web && npm run test:e2e`：1 passed

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
├── tests/                          # 测试 (当前轻量基线 218 passed, 44 skipped) ✅
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
uv run python scripts/export_onnx.py \
  --model runs/stage_a_crack/baseline_v0_1/weights/best.pt \
  --output models/stage_a_crack/best.onnx
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

## 最新进展：HE-002 / HE-003 / HE-006 / HE-004 / HE-005 主线推进

2026-04-20 继续完成浏览器 smoke、Edge Agent 关键帧接入、Stage B 数据闭环、Edge Agent 上报稳态覆盖和试点部署 runbook。

- HE-002：`web/e2e/app.spec.ts` 已覆盖上传图片、触发推理、展示结果区、检测数量和首要缺陷。
- HE-003：`VideoSource` 默认保留逐帧读取；启用 `source.keyframes.enabled` 后复用 OpenCV keyframe extractor 读取关键帧。
- HE-003：`config/edge_agent.example.yaml` 增加 `source.keyframes` 示例配置。
- HE-006：新增 `scripts/prepare_stage_b_pilot_dataset.py`，可从本地图片或视频关键帧生成 crack-only YOLO 数据集。
- HE-006：本地生成 `data/stage_b_pilot_crack/data.yaml` 和 `manifest.json`，该目录仍被 git 忽略。
- HE-006：新增 `docs/stage-b-pilot-data.md`，说明 Stage B 数据进入、标注状态、校验和 HE-007 交接。
- HE-004：新增 API 集成回归，覆盖 API Key、首次上报、缓存回放后的 duplicate 响应和 replayed batch 的模板摘要。
- HE-004：确认 `tests/test_edge_agent_reporter.py` 覆盖断网缓存、服务恢复后 flush，以及 duplicate 回放清理。
- HE-004：`docs/demo.md` 增加 Edge Agent 上报稳态与故障恢复说明。
- HE-005：`docs/deployment.md` 收敛为 `stub`、Stage A YOLO、Stage A ONNX 三个试点 profile。
- HE-005：`.env.example`、`docker-compose.yml` 与 `config/edge_agent.example.yaml` 对齐到 Stage A crack-only 模型路径。
- HE-005：补充部署配置测试，守住 Compose 和 Edge Agent 示例的模型路径。

此前 Stage B 本地 smoke 使用 checked-in sample images 验证数据结构；当前本地 `data/stage_b_pilot_crack` 为 Stage A 测试集自动标注代理数据。在真实试点媒体到位前，仓库现已支持用 `SDNET2018 + RDD2022` 继续做 public surrogate 验证，但真实版 HE-007 仍必须等 reviewed pilot labels 后执行。

## 最新进展：HE-008 Full Inspection Flow Hardening

2026-04-20 完成完整巡检流程硬化。

- HE-008：前端 API 类型补齐 `cancelled` 任务状态，并在任务历史/当前任务状态视图中明确展示已取消任务。
- HE-008：新增后端全流程回归，覆盖批量任务创建、推理可视化、任务 CSV/JSON/ZIP 导出、Edge Agent 上报、人工复核、模板摘要、报告详情和报告 CSV 导出。
- HE-008：`README.md` 与 `docs/demo.md` 明确单一 happy path 和 recovery path，避免上传、批量任务、上报、复核、摘要与导出说明分散漂移。
- HE-008：浏览器 smoke 继续覆盖前端上传、推理结果展示、检测数量和首要缺陷展示。

## 最新进展：HE-009 LLM Report Extension

2026-04-20 完成 LLM 报告扩展的可测契约实现。

- HE-009：`/api/v1/report/{batch_id}/summary` 默认继续返回确定性模板报告，`REPORT_GENERATION_MODE=llm` 时启用本地确定性 LLM 报告契约。
- HE-009：summary 响应补充 `prompt_version`、`output_schema_version`，`llm_context` 固定包含 prompt、输出 schema、事实保护 guardrails、设备元数据、复核计数、缺失 metadata 与低置信度候选。
- HE-009：测试覆盖模板 fallback、LLM 模式源事实保护、缺失 metadata、低置信度 detections、设备元数据、人工复核状态和 API 路由契约。
- HE-009：`.env.example` 增加 `REPORT_GENERATION_MODE` 与 `REPORT_LLM_PROVIDER`，回滚只需切回 `template`。

## 📋 下一步计划

下一步开发计划以根目录 `tasks.md` 为准。当前只保留两条分支，按是否拿到 reviewed positive pilot crack labels 决策：

1. **分支 A：真实试点标签到位**。推进 HE-007 Stage B Model Comparison（真实试点版），用 reviewed pilot labels 训练自有数据模型，并与 Stage A 公共数据模型在同一试点验证集上对比。
2. **分支 B：真实试点标签暂未到位**。继续保持 Stage A 部署主线与证据门禁；样本到位前使用 `scripts/validate_pilot_inbox.py` 演练数据交接字段、预标注流程、复核规则、试点链路和 stub 回滚。
3. **公开代理补位（已完成）**。`SDNET2018 + RDD2022` 已接入 public surrogate 数据入口，可在没有真实试点媒体时继续做 crack-only 开发验证，但结论必须标记为非真实试点证据。

非关键路径：MQTT、DeepLab 和 Transformer 趋势分析均后置，除非 `tasks.md` 显式提升优先级。会话开头的四条方向已在 `tasks.md` 的 "Original Direction Traceability" 中映射到具体 HE 任务。

---

**文档维护者**：Vision Analysis Pro Team  
**最后更新**：2026-04-26
**下次更新**：HE-007 reviewed pilot labels 到位，或 public surrogate 数据被实际下载并完成一次重跑后
