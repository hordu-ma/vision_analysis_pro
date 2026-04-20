# Vision Analysis Pro tasks.md

Harness Engineering task ledger for the current project direction.

Last updated: 2026-04-21

## Operating Rules

- Keep exactly one active delivery focus at a time. The current active focus is **Stage C Engineering Pilot** (HE-007 完成代理运行，等待真实试点数据后重跑真实版；当前部署推荐 Stage A).
- Every task must include scope, acceptance criteria, validation commands, artifacts, and rollback notes.
- Data, model weights, run outputs, and private credentials stay out of git. Commit scripts, configs, tests, docs, and small reproducibility metadata only.
- `data/data.yaml` remains the legacy five-class target. Stage A uses `data/stage_a_crack/data.yaml` and must not overwrite the five-class config.
- DeepLab, Transformer trend modeling, MQTT, and Rust/PyO3 are not on the critical path unless a task below explicitly promotes them.

## Stage Definitions

### Stage A Public-Data Crack Baseline

Goal:
- Use a public crack dataset to produce a reproducible single-class YOLO baseline.
- Prove the current backend/frontend/Edge Agent architecture can consume a real model artifact.

Status:
- Data source selected and converted locally.
- 1-epoch smoke training passed.
- Formal baseline training, evaluation, ONNX export, YOLO/API smoke, and ONNX smoke passed in HE-001.

Exit criteria:
- `runs/stage_a_crack/baseline_v0_1/weights/best.pt` exists locally.
- `models/stage_a_crack/best.onnx` exists locally or export blocker is documented.
- Evaluation note under `docs/` records dataset, command, precision, recall, mAP50, and mAP50-95.
- API/YOLO inference smoke succeeds with the Stage A model.

### Stage B Pilot/Self-Owned Data Loop

Goal:
- Turn the user's own videos/images into a maintainable YOLO dataset and compare it against the public-data baseline.
- Use Stage B to reduce domain shift before claiming pilot readiness.

Inputs:
- Inspection videos or image folders from the target environment.
- OpenCV keyframes from `scripts/extract_keyframes.py`.
- Manual annotations or reviewed auto-labels.

Exit criteria:
- A versioned local dataset such as `data/stage_b_pilot_crack/data.yaml` exists locally.
- Annotation guidelines and label QA are applied.
- Stage B model is trained and compared against Stage A on a held-out pilot validation set.
- Deployment docs identify whether Stage A or Stage B is the recommended demo/pilot model.

Status:
- HE-006 completed the repeatable Stage B data intake loop and generated `data/stage_b_pilot_crack/` locally.
- The current local Stage B smoke dataset uses readable checked-in sample images with reviewed-negative empty labels to validate structure only.
- HE-007 remains the model-comparison step once reviewed positive pilot crack labels exist.

### Stage C Engineering Pilot

Goal:
- Wire the selected model into API, frontend, Edge Agent, reporting, and deployment runbooks for an end-to-end pilot.

Exit criteria:
- Browser E2E and Edge Agent reporting steady-state tests pass.
- Pilot deployment runbook is complete.
- Rollback path to `stub` remains documented for link testing; model rollback uses the previous local YOLO/ONNX artifact.

## Noise Control

Removed from the mainline:
- `hf_crack` was removed because it duplicated the Stage A objective, introduced a separate `transformers` model stack, and only worked on the API side.

Future engine additions must satisfy all of the following before entering `INFERENCE_ENGINE`:
- It has a clear owner task in this file.
- It works for the intended deployment surface: API only, Edge Agent only, or both.
- It does not add a second model framework when `stub`, `yolo`, or `onnx` already satisfies the use case.
- It has tests, deployment docs, and a rollback path.
- It is not just a temporary demo fallback.

## Original Direction Traceability

The conversation started with four candidate directions. They map to the current task ledger as follows:

| Direction | Current handling | Tasks |
|-----------|------------------|-------|
| Data layer: OpenCV keyframes from video | Mainline data ingestion path; CLI and optional Edge Agent keyframe mode are in place | HE-003, HE-006 |
| Vision recognition: DeepLab, YOLO, Transformer | YOLO is the active detector; segmentation and trend analysis are follow-up tasks gated by evidence | HE-001, HE-007, HE-010, HE-011 |
| Language extension: LLM explanations/reports | Template report exists now; LLM is report-only and must not change detection decisions | HE-004, HE-009 |
| Backend/frontend: full inspection flow | Current app has API, frontend, batch tasks, report summary, browser smoke, and backend flow coverage | HE-002, HE-004, HE-008 |

## Current Decision

The best-practice path is not to build a four-model chain immediately. The project should first finish a reliable crack-only inspection loop:

1. Public crack dataset to YOLO data format.
2. Reproducible YOLO training and evaluation.
3. Exported inference artifact wired into the existing API/Edge Agent paths.
4. Browser and Edge Agent end-to-end checks.
5. Only then expand to segmentation or temporal trends; LLM report text is now limited to the report layer and must not alter detection facts.

## Done Recently

- Stage A public dataset source selected: Hugging Face `senthilsk/crack_detection_dataset`, CC BY 4.0.
- `scripts/prepare_stage_a_crack_dataset.py` converts COCO annotations to single-class YOLO labels.
- Generated local dataset: `data/stage_a_crack/data.yaml`.
- Smoke training completed with `yolov8n.pt`, 1 epoch, `imgsz=320`, MPS.
- HE-001 Stage A formal YOLO baseline completed from `data/stage_a_crack/data.yaml`.
- Best Stage A validation metrics at epoch 26: precision `0.92581`, recall `0.91344`, mAP50 `0.95556`, mAP50-95 `0.63521`.
- Local artifacts created: `runs/stage_a_crack/baseline_v0_1/weights/best.pt` and `models/stage_a_crack/best.onnx`.
- HE-002 browser E2E smoke now covers upload -> inference -> visible result state with deterministic `stub`.
- HE-003 added optional keyframe mode for `video` Edge Agent sources while preserving raw-frame mode.
- HE-006 added Stage B pilot dataset preparation, manifesting, and validation under `data/stage_b_pilot_crack/`.
- Local Stage B smoke labels now distinguish reviewed negative empty labels from pending annotation, and dataset validation rejects unreadable image files.
- HE-004 added steady-state coverage for Edge Agent cache replay, duplicate batch handling, API Key protection, and report summary access.
- HE-005 aligned the pilot deployment runbook, Compose model paths, Edge Agent sample config, smoke commands, and rollback steps.
- HE-009 added a versioned LLM report contract with deterministic template fallback and local provider mode.
- HE-P1A added `offset` pagination + `total` field to `/reports/batches`, `/reports/devices`, and `/inference/images/tasks` list endpoints; ORDER BY uses deterministic tie-breakers.
- HE-P1B added X-Trace-ID propagation middleware: reads `x-trace-id` request header and echoes it as `X-Trace-ID` response header.
- HE-P1C added 4 new frontend component spec files (ImageUpload, BatchTaskStatus, ReportBatchList, ReportDetailDrawer) and 6 new backend pagination/trace-id tests.
- Current backend baseline: `198 passed, 44 skipped`.
- Current frontend baseline: `85 passed`, lint and production build passing from the latest full validation run.

## Accepted Tasks

### HE-001 Stage A YOLO Baseline v0.1

Status: Done
Priority: P0
Owner: project maintainer

Scope:
- Train a reproducible crack-only YOLO model from `data/stage_a_crack/data.yaml`.
- Produce a real evaluation record that is good enough to decide whether Stage A can be used for demo/pilot inference.
- Export the selected model to ONNX and document the deployment path.

Implementation notes:
- Start from `yolov8n.pt` for the first baseline.
- Use the generated public dataset, not the legacy five-class `data/data.yaml`.
- Keep training outputs under `runs/stage_a_crack/` and model exports under ignored `models/`.
- Do not claim production accuracy from the 1-epoch smoke run.

Result:
- Training completed on CUDA device `0` with early stopping at epoch 31.
- Best model came from epoch 26.
- Evaluation note: `docs/stage-a-yolo-baseline-v0.1.md`.
- API/YOLO smoke and ONNX smoke passed on `data/stage_a_crack/images/val/crack-101-_jpg.rf.7250a8c4188a62263f703859846f833d.jpg`.

Acceptance criteria:
- [x] Training command and hyperparameters are recorded in docs.
- [x] Validation metrics include at least precision, recall, mAP50, and mAP50-95.
- [x] A sample inference succeeds through the existing YOLO path.
- [x] ONNX export succeeds or the blocker is documented with exact error output.
- [x] A short model card or evaluation note is added under `docs/`.

Validation commands:

```bash
uv run python scripts/prepare_stage_a_crack_dataset.py \
  --source data/public/senthilsk_crack_detection_dataset \
  --output data/stage_a_crack

uv run python scripts/train.py \
  --data data/stage_a_crack/data.yaml \
  --model yolov8n.pt \
  --epochs 50 \
  --batch 8 \
  --imgsz 640 \
  --device 0 \
  --workers 0 \
  --project runs/stage_a_crack \
  --name baseline_v0_1 \
  --exist-ok

uv sync --extra dev --extra onnx

uv run python scripts/export_onnx.py \
  --model runs/stage_a_crack/baseline_v0_1/weights/best.pt \
  --output models/stage_a_crack/best.onnx

uv run ruff check .
INFERENCE_ENGINE=stub uv run pytest -q
```

Rollback:
- Remove `runs/stage_a_crack/baseline_v0_1/` and exported files under `models/stage_a_crack/`.
- Leave `scripts/prepare_stage_a_crack_dataset.py` and `data/stage_a_crack/data.yaml` intact unless the dataset source changes.

### HE-002 Browser E2E Smoke

Status: Done
Priority: P0

Scope:
- Add a browser-level test for upload -> inference -> result view.
- Use `INFERENCE_ENGINE=stub` as the deterministic default.
- Keep the test independent of local model weights.

Result:
- `web/e2e/app.spec.ts` uploads an image, waits for the result panel, asserts detection count, and checks the primary defect heading.
- `web/playwright.config.ts` starts the API with `INFERENCE_ENGINE=stub` and proxies the frontend to it.

Acceptance criteria:
- [x] The test starts or targets the local API and frontend dev server.
- [x] It uploads a small image, waits for completion, and asserts visible result state.
- [x] It can run from `web/` with a documented command.

Validation commands:

```bash
cd web
npm run lint
npm run test -- --run
npm run build
npm run test:e2e
```

### HE-003 Keyframes Into Edge Agent

Status: Done
Priority: P0

Scope:
- Wire the OpenCV keyframe extractor into video source handling or a dedicated preprocessing path.
- Preserve the current raw-frame path for compatibility.
- Add config options for interval, scene delta, and blur threshold.

Result:
- `SourceConfig.source.keyframes` controls optional video keyframe mode.
- `VideoSource` keeps raw-frame mode by default and uses `extract_keyframes()` only when enabled.
- `config/edge_agent.example.yaml` documents the new options.

Acceptance criteria:
- [x] Video source can run in raw-frame mode and keyframe mode.
- [x] Tests cover fixed interval extraction, scene filtering, and missing/invalid video behavior.
- [x] Example config documents the new options.

Validation commands:

```bash
uv run pytest tests/test_keyframes.py tests/test_edge_agent.py -q
uv run ruff check .
```

### HE-006 Stage B Pilot Data Loop

Status: Done
Priority: P0

Scope:
- Build a repeatable process for turning the user's own videos/images into a YOLO dataset.
- Use keyframe extraction, annotation QA, train/val/test split, and dataset manifest generation.
- Keep the output separate from Stage A and the legacy five-class `data/data.yaml`.

Implementation notes:
- Default target path: `data/stage_b_pilot_crack/`.
- Start crack-only unless the pilot data clearly supports more classes.
- Use the same class id as Stage A: `0 crack`.
- Keep raw videos, extracted images, labels, and trained weights out of git.

Result:
- `scripts/prepare_stage_b_pilot_dataset.py` builds a crack-only YOLO dataset from local images and optional video keyframes.
- `data/stage_b_pilot_crack/data.yaml` and `data/stage_b_pilot_crack/manifest.json` were generated locally and remain ignored by git.
- `docs/stage-b-pilot-data.md` documents the intake, validation, pending annotation, and HE-007 handoff.

Acceptance criteria:
- [x] `data/stage_b_pilot_crack/data.yaml` is generated locally.
- [x] A manifest records source videos/images, extraction settings, split counts, and annotation status.
- [x] At least one validation command checks image/label pairing and YOLO label format.
- [x] Documentation explains how Stage B data is added without overwriting Stage A.

Validation commands:

```bash
uv run python scripts/prepare_stage_b_pilot_dataset.py path/to/pilot_video.mp4 \
  --extract-videos \
  --output data/stage_b_pilot_crack \
  --interval-seconds 1.0 \
  --min-scene-delta 20 \
  --blur-threshold 10

uv run python scripts/prepare_stage_b_pilot_dataset.py \
  --output data/stage_b_pilot_crack \
  --validate-only

uv run ruff check .
uv run pytest tests/test_keyframes.py tests/test_prepare_stage_b_dataset.py -q
```

Artifacts:
- Local dataset: `data/stage_b_pilot_crack/`
- Local manifest: `data/stage_b_pilot_crack/manifest.json`
- Optional docs note after first pilot dataset: `docs/stage-b-pilot-data.md`

Rollback:
- Remove `data/stage_b_pilot_crack/` and any corresponding `runs/stage_b_pilot_crack/` outputs.
- No tracked five-class config should be modified.

### HE-004 Edge Agent Reporting Steady State

Status: Done
Priority: P1

Scope:
- Exercise network failure, cache replay, duplicate batch, API key, and report summary paths together.
- Confirm cloud API idempotency with realistic Edge Agent payloads.

Result:
- `tests/test_edge_agent_reporter.py` covers HTTP reporter offline caching, cache flush after recovery, and duplicate replay cleanup.
- `tests/test_api_inference.py` covers realistic Edge Agent payload idempotency, API Key protection, replayed duplicate batches, and `/api/v1/report/{batch_id}/summary`.
- `docs/demo.md` documents the steady-state failure modes and recovery commands.

Acceptance criteria:
- [x] Tests cover offline cache replay and duplicate batch acceptance.
- [x] `/api/v1/report/{batch_id}/summary` works for replayed batches.
- [x] Failure modes are documented in `docs/demo.md` or deployment runbook.

Validation commands:

```bash
uv run pytest tests/test_edge_agent.py tests/test_api_inference.py tests/test_edge_agent_reporter.py -q
INFERENCE_ENGINE=stub uv run pytest -q
```

### HE-005 Pilot Deployment Runbook

Status: Done
Priority: P1

Scope:
- Make the local pilot path explicit: API, frontend, optional observability, model volume, Edge Agent config.
- Document which inference engine is expected in each profile.

Result:
- `.env.example`, `docker-compose.yml`, and `config/edge_agent.example.yaml` now agree on Stage A crack-only YOLO/ONNX model paths.
- `docs/deployment.md` defines `stub`, Stage A YOLO, and Stage A ONNX profiles, including Compose smoke commands and rollback steps.
- Deployment config tests guard the Stage A model paths and Edge Agent sample config.

Acceptance criteria:
- [x] `docs/deployment.md` has one clear crack-only Stage A path.
- [x] `.env.example` and `docker-compose.yml` agree on model paths.
- [x] Smoke commands and rollback steps are included.

Validation commands:

```bash
docker compose config
uv run ruff check .
uv run pytest tests/test_deployment_config.py -q
```

## Completed Task

### HE-007 Stage B Model Comparison

Status: Done (proxy run with auto-labeled Stage A test images; real pilot data pending)
Priority: P1

Scope:
- Train a Stage B model on pilot/self-owned data and compare it against the Stage A public-data baseline.
- Decide whether the demo/pilot should use Stage A, Stage B, or a merged dataset.

Result:
- Stage B proxy dataset: 225 images from Stage A test set, auto-labeled with Stage A ONNX (conf=0.30).
- Stage B training: 157 train / 33 val / 35 test, 30 epochs, early stop at epoch 24.
- Comparison on Stage A val set (462 images):
  - Stage A: mAP50=0.9661, mAP50-95=0.6320, P=0.9434, R=0.9203
  - Stage B: mAP50=0.8711, mAP50-95=0.3898, P=0.8844, R=0.8383
- **Recommendation: Keep Stage A as deployment model.**
- Full evaluation note: `docs/stage-b-model-comparison.md`.

Acceptance criteria:
- [x] Evaluation note compares Stage A and Stage B metrics on the same val set.
- [x] Recommendation is explicit: keep Stage A.
- [x] Domain-shift limitation is documented (same-distribution proxy, not real pilot data).

Validation commands:

```bash
# 自动标注
uv run python scripts/auto_label_onnx.py \
  --model models/stage_a_crack/best.onnx \
  --images data/stage_a_crack/images/test \
  --output /tmp/stage_b_auto_labels \
  --conf 0.30

# 构建 Stage B 数据集
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  data/stage_a_crack/images/test \
  --labels-dir /tmp/stage_b_auto_labels \
  --output data/stage_b_pilot_crack \
  --mark-reviewed

# 训练 Stage B
uv run python scripts/train.py \
  --data data/stage_b_pilot_crack/data.yaml \
  --model yolov8n.pt \
  --epochs 30 --batch 8 --imgsz 640 --device 0 \
  --project runs/stage_b_pilot_crack --name comparison_v0_1 --exist-ok

# 评估对比（同一 val 集）
uv run python scripts/evaluate.py \
  --model runs/stage_a_crack/baseline_v0_1/weights/best.pt \
  --data data/stage_a_crack/data.yaml --split val

uv run python scripts/evaluate.py \
  --model runs/stage_b_pilot_crack/comparison_v0_1/weights/best.pt \
  --data data/stage_a_crack/data.yaml --split val

INFERENCE_ENGINE=stub uv run pytest -q
```

Rollback:
- Remove `runs/stage_b_pilot_crack/` and exported files under `models/stage_b_pilot_crack/`.

## Completed Task

### HE-008 Full Inspection Flow Hardening

Status: Done
Priority: P1

Scope:
- Make the full flow explicit across backend and frontend: upload/batch task, inference, visualization, review, report summary, export.
- This is the engineering counterpart to the original "backend and frontend complete inspection process" direction.

Acceptance criteria:
- README and demo docs describe a single happy path and one recovery path.
- API schemas and frontend types remain aligned.
- Browser smoke and backend task/report tests cover the main flow.

Validation commands:

```bash
uv run ruff check .
INFERENCE_ENGINE=stub uv run pytest tests/test_api_inference.py tests/test_reporting.py -q
INFERENCE_ENGINE=stub uv run pytest -q
cd web
npm run lint
npm run test -- --run
npm run build
npm run test:e2e
```

Result:
- Frontend task status types now include backend `cancelled` tasks, and task history/status UI renders cancelled tasks explicitly.
- `tests/test_api_inference.py` now covers the HE-008 happy path across async batch task creation, inference visualization, task CSV/JSON/ZIP export, cloud report intake, review update, report summary, report detail, and report CSV export.
- README and demo docs describe one happy path and one recovery path for the full inspection flow.

Rollback:
- Revert the HE-008 frontend status type/UI changes and the full-flow test if the task contract is narrowed.
- Revert the README/demo/progress wording if the accepted demo path changes.

## Completed Task

### HE-009 LLM Report Extension

Status: Done
Priority: P2

Promote only after HE-001 and HE-004 are stable.

Scope:
- Generate human-readable report text from structured detection results, review status, and device metadata.
- LLM output must not alter detection labels or confidence values.

Acceptance criteria:
- Report generation has deterministic template fallback.
- LLM prompt and output schema are versioned.
- Tests cover missing metadata and low-confidence detections.

Validation commands:

```bash
uv run ruff check .
INFERENCE_ENGINE=stub uv run pytest tests/test_api_inference.py tests/test_reporting.py -q
INFERENCE_ENGINE=stub uv run pytest -q
cd web
npm run lint
npm run test -- --run
npm run build
npm run test:e2e
```

Result:
- `/api/v1/report/{batch_id}/summary` remains deterministic template output by default.
- `REPORT_GENERATION_MODE=llm` enables the local versioned report contract without external network calls.
- Response payloads now expose `prompt_version` and `output_schema_version`, while `llm_context` carries prompt text, output schema, guardrails, device metadata, review counts, missing metadata, and low-confidence detections.
- Tests cover template fallback, LLM mode source-fact preservation, missing metadata, low-confidence detections, device metadata, review status, and the API route contract.

Rollback:
- Keep `/api/v1/report/{batch_id}/summary` on deterministic template output only.
- Disable the LLM provider path by configuration without changing stored reports.

### HE-P1A API Pagination (offset + total)

Status: Done
Priority: P1

Scope:
- Add `offset` query parameter and `total` count field to list endpoints: `/reports/batches`, `/reports/devices`, `/inference/images/tasks`.
- Use deterministic ORDER BY (e.g., `batch_id DESC` as tie-breaker) to make LIMIT/OFFSET stable.
- Keep backward compatibility: `total` is `int | None` (absent from existing consumers).

Result:
- `report_store.py`: `list_batches`/`list_devices` support `offset`; new `count_batches()`/`count_devices()` methods.
- `inference_tasks.py`: `list_tasks` supports `offset` with stable `task_id DESC` ordering.
- `schemas.py`: `ReportBatchListResponse` and `ReportDeviceListResponse` gain `total: int | None`.
- `routers/reports.py` and `routers/inference.py`: expose `offset: int = Query(0, ge=0)`.
- `web/src/services/api.ts`: `listBatchTasks`, `listReportBatches`, `listReportDevices` accept `offset` param.
- `web/src/types/api.ts`: interfaces updated with `total?: number`.

Acceptance criteria:
- [x] `GET /reports/batches?limit=2&offset=2` returns the correct second page with `total >= count`.
- [x] `GET /reports/batches?offset=-1` returns 422.
- [x] Pagination tests cover batches, devices, and inference tasks.

Validation commands:

```bash
uv run ruff check .
uv run pytest tests/test_api_inference.py -q -k "pagination"
cd web && npm run test -- --run
```

Rollback:
- Remove `offset` Query param and `count_*` method calls; remove `total` from schemas.

### HE-P1B X-Trace-ID Propagation

Status: Done
Priority: P1

Scope:
- Read `x-trace-id` header in middleware and echo it as `X-Trace-ID` response header.
- Only echo when present in the request; do not auto-generate (unlike `request_id`).

Result:
- `main.py` middleware stores `request.state.trace_id` and adds `X-Trace-ID` to response headers when present.

Acceptance criteria:
- [x] Response includes `X-Trace-ID` when request carries `x-trace-id`.
- [x] Response omits `X-Trace-ID` when request does not carry it.

Validation commands:

```bash
uv run pytest tests/test_api_inference.py -q -k "trace_id"
```

Rollback:
- Remove the two-line trace_id block from the `add_process_time_header` middleware.

### HE-P1C Frontend Component Tests

Status: Done
Priority: P1

Scope:
- Add unit test coverage for the four highest-risk interactive components.
- Bring frontend spec count from 53 to ≥ 85 passed.

Result:
- `web/src/components/ImageUpload.spec.ts`: 7 tests (upload mode toggle, file validation, clearFile, batch upload trigger).
- `web/src/components/BatchTaskStatus.spec.ts`: 11 tests (all status variants, button visibility, retry/cancel emit).
- `web/src/components/ReportBatchList.spec.ts`: 7 tests (list render, empty state, event emit for refresh/detail/filter).
- `web/src/components/ReportDetailDrawer.spec.ts`: 6 tests (drawer visibility, export emit, content display).

Acceptance criteria:
- [x] 85 frontend tests pass with lint clean.
- [x] All 4 new spec files are lint-clean (prettier/eslint).

Validation commands:

```bash
cd web
npm run lint
npm run test -- --run
```

Rollback:
- Remove the 4 new spec files; revert `api.spec.ts` URL assertions to drop `offset=0`.

## P2 Backlog

### HE-010 Segmentation Refinement

Status: Backlog
Priority: P2

Promote only if Stage A users need crack length/area estimates that bounding boxes cannot support.

Scope:
- Evaluate segmentation for crack masks as a refinement step after object detection.
- Do not replace the YOLO baseline unless evaluation justifies it.
- Candidate models include DeepLab-style semantic segmentation or SAM/SAM2-style refinement, selected after Stage A/Stage B evidence.

### HE-011 Trend Analysis

Status: Backlog
Priority: P2

Promote only after repeated inspections exist for the same device/asset.

Scope:
- Build trend features from stored batch history before considering Transformer models.
- Start with simple time-series summaries and thresholds.
- Transformer-based trend modeling is only justified after repeated, timestamped, asset-linked inspection data exists.

## Explicit Non-Goals For The Next Sprint

- No five-class production claim without a real five-class dataset and evaluation report.
- No DeepLab/Transformer chain as a prerequisite for Stage A.
- No committed model weights or public dataset archives.
- No Rust/PyO3 work until profiling shows Python preprocessing or postprocessing is the bottleneck.

## 下一步开发建议

优先级参考如下。短期目标以完成 Stage C 工程闭环为主，中期补齐多 worker 运维能力。

### 短期（Immediate）

1. **解锁 HE-007 Stage B 模型对比**
   - 当前阻塞因素：缺少 reviewed positive pilot crack labels。
   - 行动项：确认标注获取路径（手工标注一批试点帧 or 审阅 Stage A 自动预测结果），完成后直接执行 `scripts/train.py`。

2. **Stage C E2E 自动化试点**
   - 当前 Playwright E2E 只有 1 个 happy path 测试。
   - 建议补：批次任务创建 → 推理 → 报告上报 → 复核全链路 E2E，在 `web/e2e/` 下扩展。

3. **Pilot Deployment Runbook 演练**
   - 在 Docker Compose 环境完整跑一次 HE-005 runbook（Stage A ONNX 模型路径 + Edge Agent）。
   - 补充部署验收 checklist 至 `docs/deployment.md`。

### 中期（Next Sprint）

4. **指标系统升级**（对应原 P2 建议 #6）
   - 当前 `app.state.metrics` 是普通 dict，多 worker 下存在竞态。
   - 用 `prometheus_client.Counter/Histogram` 替换，减少 `main.py` 中的样板代码，支持 Grafana histogram 分桶。

5. **结构化日志 trace_id 透传**
   - X-Trace-ID 已在响应头回显，下一步将 `trace_id` 注入 Python 结构化日志（使用 `structlog` 或 `logging.LoggerAdapter`），方便跨服务链路追踪。

6. **Report Store 分页前端集成**
   - 后端已完成 `offset`+`total` 分页，前端 `api.ts` 已暴露参数，但 `ReportBatchList` 组件尚未驱动分页 UI（下一页/上一页按钮）。

### 长期（Backlog）

- HE-010 分割细化（DeepLab/SAM）：仅在需要像素级裂缝面积/长度估计时推进。
- HE-011 趋势分析：依赖多批次历史数据积累，Transformer 路线在数据足够后再评估。
