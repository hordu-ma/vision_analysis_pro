# Vision Analysis Pro tasks.md

Harness Engineering task ledger for the current project direction.

Last updated: 2026-05-07

## Operating Rules

- Keep exactly one active delivery focus at a time. The current active focus is **Trial System Packaging and Rehearsal** (在真实环境样本暂不可得前，优先把系统封装成可部署、可演示、可采集真实样本的输电塔巡检试点系统；多类塔材模型继续保留为实验模型，不作为当前默认部署能力).
- Every task must include scope, acceptance criteria, validation commands, artifacts, and rollback notes.
- Data, model weights, run outputs, and private credentials stay out of git. Commit scripts, configs, tests, docs, and small reproducibility metadata only.
- `data/data.yaml` remains the legacy five-class target. Stage A uses `data/stage_a_crack/data.yaml` and must not overwrite the five-class config.
- DeepLab, Transformer trend modeling, and MQTT are not on the critical path unless a task below explicitly promotes them.

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
- `scripts/prepare_public_surrogate_crack_dataset.py` now supports SDNET2018 + RDD2022 as public surrogate inputs while real pilot media is still unavailable.
- `scripts/validate_pilot_inbox.py` now validates the local real-pilot handoff inbox before HE-007 real-pilot training.
- HE-007 real-pilot rerun remains the model-comparison step once reviewed positive pilot crack labels exist.

### Stage C Engineering Pilot

Goal:
- Wire the selected model into API, frontend, Edge Agent, reporting, and deployment runbooks for an end-to-end pilot.

Exit criteria:
- Browser E2E and Edge Agent reporting steady-state tests pass.
- Pilot deployment runbook is complete.
- Rollback path to `stub` remains documented for link testing; model rollback uses the previous local YOLO/ONNX artifact.

### Multiclass Tower Defect Prototype

Goal:
- Use the user's local tower-defect image set to build a small, inspectable prototype loop for deformation, tower corrosion, loose bolts, and bolt rust.
- Prioritize data organization, annotation readiness, YOLO-compatible labels, and end-to-end prototype wiring over crack-only model accuracy.

Inputs:
- Source images: `/home/liguoma/Downloads/锈蚀、松动、变形、腐蚀/`
- Local ignored inbox: `data/multiclass_inbox/`
- Proposed class mapping:
  - `0 deformation`
  - `1 tower_corrosion`
  - `2 loose_bolt`
  - `3 bolt_rust`

Exit criteria:
- Source images are copied into `data/multiclass_inbox/raw_images/`.
- `metadata/`, `classes.json`, `manifest.json`, and `annotation_queue.csv` exist locally.
- Human-reviewed YOLO bbox labels are created under `data/multiclass_inbox/reviewed_labels/`.
- A prototype dataset can be generated from the reviewed labels for YOLO smoke training.

Status:
- HE-015 completed the route pivot, local inbox preparation, and annotation queue generation.
- HE-016 converted the AI-assisted reviewed labels into a YOLO dataset and completed a 1-epoch smoke training run.
- HE-017 added local inference smoke verification; model loading and class-name propagation work, but current weights are not ready for ONNX/API/frontend demo because normal confidence thresholds return no detections.
- Model quality remains non-claimable until the labels are reviewed, target boxes are tightened, and the dataset grows beyond the current 24-image prototype set.

### Trial System Packaging and Rehearsal

Goal:
- Package the existing API, frontend, Edge Agent, reporting, review, export, and observability path into a deployable trial system before more real tower samples are available.
- Make the system useful as the real-data capture and review entry point once it reaches the field.

Current six-step order:
1. Package the trial system first: make the deployment, startup, demo, metrics, reporting, and rollback flow repeatable.
2. Use the currently available model surfaces without waiting for the multiclass model to mature: keep `stub` as the stable link-test default, Stage A ONNX as the real-model route demo, and keep the multiclass tower model experimental.
3. Turn the system into the real-data intake entry point: Edge Agent collection, batch upload, metadata, review status, and export should be ready before field access.
4. Keep the human review and labeling preparation loop ready: inbox rules, annotation queue, reviewed-label validation, and dataset generation stay ready for later real samples.
5. Run a full trial rehearsal with existing samples and `stub` / Stage A ONNX, validating the system path rather than claiming multiclass model accuracy.
6. After field access, expand samples, review labels, train `prototype_v0_2`, evaluate, export ONNX, replace the trial model, and rerun system regression.

Status:
- HE-018 records the first full rehearsal under this packaging-first route.
- Sample expansion and multiclass retraining are intentionally deferred until the system can enter the real environment and collect representative data.

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

The best-practice path is not to build a four-model chain or block on more real samples immediately. Because real tower-environment data is unavailable before the system reaches the field, the project should first finish a deployable trial package:

1. Keep `stub` as the stable system-link test mode.
2. Keep Stage A ONNX as the real-model route demo.
3. Keep the current multiclass tower model experimental until it produces stable detections at normal thresholds.
4. Use the system itself to capture, review, export, and later convert real field data into training data.
5. Only after representative field samples and reviewed labels exist, train and promote the next multiclass model.

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
- Stage C browser E2E now covers single-image upload, completed batch task history, and report detail review save.
- Frontend pagination UI now drives report batch, task history, and device overview page offsets.
- HE-013 upgraded the frontend presentation layer: product shell, sidebar brand system, workflow rails, upload surface, Device Control header, HealthStatus controls, and global Element Plus skin overrides now read as a deliverable product rather than default component samples.
- Compose API builds now pin `uv` to the official PyPI simple index by default, with `COMPOSE_UV_DEFAULT_INDEX` as an override for internal mirrors.
- API metrics now use `prometheus_client.Counter/Histogram/Gauge`, while `/api/v1/metrics` keeps the Prometheus scrape contract and exposes request/inference histogram buckets.
- Audit logs now support `offset` pagination, `total`, and actor filtering in the API; the device page includes matching audit-log pagination controls.
- X-Trace-ID is now included in request completion/failure structured log records.
- Public surrogate crack-data support now includes `scripts/prepare_public_surrogate_crack_dataset.py`, which uses SDNET2018 negatives plus RDD2022 crack boxes to build a crack-only proxy dataset.
- HE-014 added a Pilot Inbox preflight validator for `data/pilot_inbox/`, covering raw image readability, reviewed label pairing, required handoff metadata, review fields, and reviewed positive crack-box gating before HE-007.
- HE-015 pivoted the active prototype path away from crack-only gating and prepared the 24-image multiclass tower-defect inbox from `/home/liguoma/Downloads/锈蚀、松动、变形、腐蚀/`.
- `scripts/prepare_multiclass_prototype_inbox.py` now writes the ignored local `data/multiclass_inbox/` structure, including `raw_images/`, `metadata/`, `reviewed_labels/`, `classes.json`, `manifest.json`, and `annotation_queue.csv`.
- HE-016 added `scripts/prepare_multiclass_tower_dataset.py`, generated local `data/multiclass_tower_defect/`, and completed a CPU 1-epoch YOLO smoke training run under `runs/multiclass_tower_defect/smoke_v0_1/`.
- HE-017 added `scripts/smoke_multiclass_tower_inference.py` and verified that `prototype_v0_1` loads with the expected 4-class mapping. At `conf=0.25` and `conf=0.05`, the test split returns zero detections; at `conf=0.001`, detections are noisy and biased toward `tower_corrosion` / `bolt_rust`, so ONNX/API/frontend integration is deliberately deferred.
- HE-018 accepted the packaging-first route: complete a full trial rehearsal before more real tower samples are available, then use the deployed system as the real-data capture and review entry point.
- HE-019 completed the first four packaging tasks as docs/SOP deliverables: remote customer demo flow, current model profile usage, field data intake, and review/labeling preparation.
- HE-020 corrected the customer-demo rule: `stub` is internal-only, while customer-facing detection results must use Stage A ONNX or Stage A YOLO with real images. Stage A YOLO and ONNX were both rechecked on the same real crack sample and returned one `crack` detection; multiclass tower YOLO remains experimental.
- HE-021 added the recommended soft-hardware trial bundle, procurement-control parameters, and package tiers in `docs/hardware-bundle.md`.
- Current backend baseline: `218 passed, 44 skipped`.
- Current frontend baseline: `90 passed`, lint, production build, and 3 Playwright E2E tests passing from the latest validation run.
- 2026-04-22 execution check: local `data/stage_b_pilot_crack` validates successfully; Stage A and Stage B proxy models were re-evaluated on the same Stage A val set and the recommendation remains **keep Stage A**.

## Accepted Tasks

### HE-021 Trial Hardware Bundle

Status: Done
Priority: P1
Owner: project maintainer

Scope:
- Define the minimum hardware package for selling Vision Analysis Pro as a soft-hardware trial kit.
- Keep drones outside the minimum package and place them in an optional higher-tier UAV package.
- Provide procurement-control parameters that avoid locking to one brand while preserving user experience consistency.
- Link the hardware bundle from README, deployment docs, progress, and this ledger.

Acceptance criteria:
- [x] Standard Trial Kit hardware modules are documented.
- [x] Edge AI box capability parameters are documented.
- [x] Operator terminal, network, power, storage, and delivery accessories are documented.
- [x] Optional Field Collection Kit and UAV Inspection Kit tiers are documented.
- [x] Sales wording and avoided claims are documented.
- [x] Integration with current ONNX/Yolo/stub software profiles is documented.

Artifacts:
- `docs/hardware-bundle.md`
- Updated `README.md`
- Updated `docs/deployment.md`
- Updated `docs/progress.md`
- Updated `tasks.md`

Validation commands:

```bash
git diff --check
uv run ruff check .
```

Rollback:
- Revert this documentation-only package definition if the commercial packaging strategy changes.

### HE-020 Real Model Demo Rule and Profile Status

Status: Done
Priority: P0
Owner: project maintainer

Scope:
- Correct the customer-demo rule so `stub` is internal-only and customer-facing detection results use a real model profile.
- Confirm current YOLO and ONNX completion with direct model smoke tests.
- Document the current boundary between Stage A crack-only models and the multiclass tower prototype.
- Align README, demo, deployment, progress, and customer demo docs.

Acceptance criteria:
- [x] Stage A YOLO loads and detects `crack` on a real Stage A validation sample.
- [x] Stage A ONNX loads and detects `crack` on the same real Stage A validation sample.
- [x] Multiclass tower YOLO prototype status is documented as experimental.
- [x] Customer demo docs say `stub` must not be used as the main customer-facing detection source.
- [x] `docs/model-profile-status.md` records profile status and commands.

Result:
- Stage A YOLO smoke:
  - model: `runs/stage_a_crack/baseline_v0_1/weights/best.pt`
  - sample: `data/stage_a_crack/images/val/crack-1455-_jpg.rf.d78b0366a48c54f31295522b24dcf2f0.jpg`
  - detection: `1 crack`, confidence `0.425392`
- Stage A ONNX smoke:
  - model: `models/stage_a_crack/best.onnx`
  - sample: same as YOLO smoke
  - detection: `1 crack`, confidence `0.425472`
- Multiclass tower YOLO smoke:
  - model: `runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt`
  - sample: `data/multiclass_tower_defect/images/test/bolt_rust_004.jpg`
  - detection at `conf=0.25`: `0`

Validation commands:

```bash
uv run python - <<'PY'
from pathlib import Path
from vision_analysis_pro.core.inference import YOLOInferenceEngine, ONNXInferenceEngine

sample = next(Path("data/stage_a_crack/images/val").glob("*.jpg"))
for engine in [
    YOLOInferenceEngine("runs/stage_a_crack/baseline_v0_1/weights/best.pt"),
    ONNXInferenceEngine("models/stage_a_crack/best.onnx"),
]:
    print(engine.__class__.__name__, engine.predict(sample, conf=0.1, iou=0.5))
PY
```

Rollback:
- Revert the documentation changes if the customer-demo policy changes.
- Do not change model artifacts in this task.

### HE-019 Trial Packaging Steps 1-4

Status: Done
Priority: P0
Owner: project maintainer

Scope:
- Complete step 1: system trial packaging for remote customer demonstration when the deployment machine is not brought to the customer site.
- Complete step 2: document current model usage rules: `stub` for stable flow, Stage A ONNX for real-model route, multiclass tower model as experimental.
- Complete step 3: define the system as the field-data intake entry point with upload, Edge Agent reporting, metadata, review, and export.
- Complete step 4: define the human review, annotation handoff, and later dataset-generation SOP.
- Align README, demo, deployment, progress, and this ledger.

Acceptance criteria:
- [x] Customer remote demo flow is documented.
- [x] Access modes, pre-demo checks, demo script, fallback plan, and customer follow-up are documented.
- [x] Current model profile rules are documented without claiming multiclass production accuracy.
- [x] Field data intake paths and required metadata are documented.
- [x] Review status, annotation handoff, prelabeling, dataset generation, and training gate are documented.
- [x] README and existing demo/deployment/progress docs link to the new SOPs.

Artifacts:
- `docs/customer-remote-demo.md`
- `docs/field-data-intake-and-review.md`
- Updated `README.md`
- Updated `docs/demo.md`
- Updated `docs/deployment.md`
- Updated `docs/progress.md`
- Updated `tasks.md`

Validation commands:

```bash
git diff --check
uv run ruff check .
```

Rollback:
- Revert the documentation changes in this task.
- Continue using HE-018 rehearsal commands and `INFERENCE_ENGINE=stub` as the stable fallback demo mode.

### HE-018 Trial System Packaging Rehearsal

Status: Done
Priority: P0
Owner: project maintainer

Scope:
- Record the six-step packaging-first route in this ledger.
- Run a full trial rehearsal with existing local samples and stable engines.
- Validate deployment configuration, API health, single-image upload, batch task, Edge Agent / report intake, human review, summary, export, metrics, and rollback readiness.
- Align README and deployment/demo/progress docs after rehearsal.

Acceptance criteria:
- [x] `docker compose config` passes.
- [x] API health/live/metrics endpoints respond in `stub` mode.
- [x] Single-image inference succeeds with a checked-in sample image.
- [x] Batch task reaches `completed`.
- [x] Edge/report intake accepts a batch.
- [x] Report review, summary, CSV export, batch list, device list, and alert summary respond.
- [x] Stage A ONNX readiness is checked if `models/stage_a_crack/best.onnx` exists.
- [x] Edge Agent runs with Stage A ONNX and reports one detected frame to the API.
- [x] Frontend lint/test/build and browser E2E pass.
- [x] Docs are aligned with the packaging-first route and latest rehearsal result.

Result:
- `docker compose config` passed.
- `stub` API rehearsal used `REPORT_STORE_DB_PATH=/tmp/vision-analysis-pro-trial.db` and validated health/live/metrics, single-image upload, and a two-image batch task.
- Manual report batch `trial-rehearsal-*` validated device metadata, report intake, frame review, template summary, CSV export, batch list, device list, and alert summary.
- Stage A ONNX readiness passed on port `8001`; inference on valid sample `data/samples/web_rust_chain.jpg` returned successfully with zero detections. The invalid checked-in sample `data/samples/web_rust_bolt.jpg` is an HTML document despite its `.jpg` suffix and should not be used for real-engine smoke.
- Edge Agent ran against `models/stage_a_crack/best.onnx` with a Stage A crack sample and reported one detected frame to the `stub` API receiver.
- Quality gates passed: `uv run ruff check .`, `uv run pytest`, `cd web && npm run lint`, `cd web && npm run test -- --run`, `cd web && npm run build`, and `cd web && npm run test:e2e`. Playwright Chromium had to be installed once with `cd web && npx playwright install chromium` before E2E could run on this machine.

Validation commands:

```bash
docker compose config

REPORT_STORE_DB_PATH=/tmp/vision-analysis-pro-trial.db \
INFERENCE_ENGINE=stub \
API_RELOAD=false \
uv run uvicorn vision_analysis_pro.web.api.main:app \
  --host 127.0.0.1 \
  --port 8000

cd web
npm run lint
npm run test -- --run
npm run build
npm run test:e2e
```

Rollback:
- Stop the rehearsal API/frontend processes.
- Remove temporary rehearsal stores under `/tmp/vision-analysis-pro-trial*.db`.
- Keep `INFERENCE_ENGINE=stub` as the safe fallback if ONNX/model paths are unavailable.

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
- 2026-04-22 CPU re-evaluation reproduced the same metrics and validated `data/stage_b_pilot_crack`.
- **Recommendation: Keep Stage A as deployment model.**
- Full evaluation note: `docs/stage-b-model-comparison.md`.
- Repository support now also includes a second public surrogate intake path (`SDNET2018 + RDD2022`) for non-real-pilot validation before self-owned media arrives.

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

### HE-012 Public Surrogate Crack Data Support

Status: Done
Priority: P1

Scope:
- Provide a reproducible fallback path when real pilot media is unavailable.
- Support SDNET2018 and RDD2022 as public surrogate sources without claiming real pilot readiness.
- Keep the workflow crack-only and compatible with the existing Stage B dataset/validation path.

Result:
- `src/vision_analysis_pro/core/crack_yolo_dataset.py` centralizes crack-only YOLO dataset validation and `data.yaml` writing.
- `scripts/prepare_public_surrogate_crack_dataset.py` builds `data/stage_b_public_surrogate_crack/` from local SDNET2018 and RDD2022 downloads.
- SDNET2018 contributes reviewed negative `NonCrack` images by default; optional Stage A ONNX auto-labeling can turn `Crack` images into proxy positives.
- RDD2022 Pascal VOC XML is converted into crack-only YOLO labels by mapping `D00` / `D10` / `D20` to class `0 crack`.
- Documentation now marks this path as public surrogate / proxy, not real pilot evidence.

Acceptance criteria:
- [x] Repository provides one documented command to prepare a crack-only public surrogate dataset from SDNET2018 and RDD2022.
- [x] Tests cover SDNET2018 negative intake and RDD2022 crack XML conversion.
- [x] Documentation explains the proxy/public-surrogate limitation explicitly.

Validation commands:

```bash
uv run ruff check .
uv run pytest tests/test_prepare_stage_b_dataset.py tests/test_prepare_public_surrogate_dataset.py tests/test_deployment_config.py -q
uv run pytest

cd web
npm run lint
npm run test -- --run
npm run build
```

Rollback:
- Remove `data/stage_b_public_surrogate_crack/` and any related local downloads under `data/public/`.
- Keep the real-pilot Stage B path and Stage A baseline intact.

## Completed Task

### HE-014 Pilot Inbox Preflight

Status: Done
Priority: P1

Scope:
- Turn the real-pilot handoff checklist into an executable validation step before HE-007.
- Validate local-only `data/pilot_inbox/` structure without committing pilot media, labels, or metadata.
- Block HE-007 training when no reviewed positive crack boxes exist.

Result:
- `scripts/validate_pilot_inbox.py` validates `raw_images/`, `reviewed_labels/`, and `metadata/` under `data/pilot_inbox/` by default.
- The validator checks readable images, orphan labels, required media metadata (`asset_id`, `device_id`, `site_name`, `capture_time`, `source_type`), label review metadata (`reviewer`, `review_rule_version`), YOLO crack-only label format, pending images, reviewed negatives, and reviewed positive box counts.
- Metadata can be provided as per-image JSON files, a mapping JSON file, or a JSON file with an `items` list.
- The default mode exits non-zero if reviewed positive crack boxes are absent; `--allow-no-positive` is available for structure-only rehearsal before labels arrive.
- `tests/test_validate_pilot_inbox.py` covers positive readiness, missing metadata, no-positive gating, structure-only mode, and metadata manifest input.

Acceptance criteria:
- [x] One command can determine whether `data/pilot_inbox/` is ready for HE-007 real-pilot training.
- [x] The command reports total images, labeled images, pending images, reviewed positives, reviewed negatives, metadata count, and readiness.
- [x] Missing metadata or missing reviewed positive boxes prevents accidental Stage B training.

Validation commands:

```bash
uv run ruff check scripts/validate_pilot_inbox.py tests/test_validate_pilot_inbox.py
uv run pytest tests/test_validate_pilot_inbox.py tests/test_prepare_stage_b_dataset.py -q
```

Rollback:
- Remove `scripts/validate_pilot_inbox.py` and `tests/test_validate_pilot_inbox.py`; keep HE-006/HE-007 dataset preparation unchanged.

## Completed Task

### HE-017 Multiclass Prototype Inference Smoke

Status: Done
Priority: P0

Scope:
- Run local inference smoke against the multiclass prototype weights.
- Verify that the YOLO engine loads the model and exposes the expected 4-class mapping.
- Produce ignored JSON and preview artifacts for inspection.
- Decide whether the model is ready for ONNX export and API/frontend wiring.

Result:
- Added `scripts/smoke_multiclass_tower_inference.py`.
- Added tests in `tests/test_smoke_multiclass_tower_inference.py`.
- Verified `runs/multiclass_tower_defect/smoke_v0_1/weights/best.pt` loads and runs.
- Trained a slightly longer local `prototype_v0_1` run:
  - output: `runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt`
  - stopped at epoch 14 by early stopping
  - mAP50 `0.0624`, mAP50-95 `0.0251`, precision `0.0020`, recall `0.2500`
- Inference smoke results for `prototype_v0_1`:
  - test split at `conf=0.25`: 4 images, 0 detections
  - test split at `conf=0.05`: 4 images, 0 detections
  - test split at `conf=0.001`: 4 images, 191 noisy detections, biased toward `tower_corrosion` and `bolt_rust`
  - train split at `conf=0.25`: 16 images, 0 detections
  - train split at `conf=0.01`: 16 images, 114 noisy detections

Decision:
- Do not export ONNX yet.
- Do not wire this model into the API/frontend demo yet.
- Next prototype step is data/label improvement, not deployment integration.

Acceptance criteria:
- [x] A repeatable inference smoke command exists.
- [x] The script validates the expected 4-class mapping before inference.
- [x] JSON and preview outputs are written under ignored local data directories.
- [x] The docs record that current weights are not demo-ready.

Validation commands:

```bash
uv run python scripts/smoke_multiclass_tower_inference.py \
  --model runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt \
  --conf 0.25 \
  --output data/multiclass_tower_defect/inference_smoke/prototype_v0_1_conf025.json \
  --preview-dir data/multiclass_tower_defect/inference_smoke/prototype_v0_1_previews_conf025

uv run python scripts/smoke_multiclass_tower_inference.py \
  --model runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt \
  --conf 0.001 \
  --output data/multiclass_tower_defect/inference_smoke/prototype_v0_1_conf0001.json \
  --preview-dir data/multiclass_tower_defect/inference_smoke/prototype_v0_1_previews_conf0001

uv run ruff check scripts/smoke_multiclass_tower_inference.py tests/test_smoke_multiclass_tower_inference.py
uv run pytest tests/test_smoke_multiclass_tower_inference.py -q
```

Rollback:
- Remove `scripts/smoke_multiclass_tower_inference.py` and `tests/test_smoke_multiclass_tower_inference.py`.
- Remove ignored local `data/multiclass_tower_defect/inference_smoke/` if the smoke output format changes.

## Completed Task

### HE-016 Multiclass Tower Dataset and Smoke Training

Status: Done
Priority: P0

Scope:
- Convert AI-assisted reviewed labels from `data/multiclass_inbox/` into a YOLO dataset.
- Validate image/label pairing, class IDs, bbox ranges, and split directories.
- Run a minimum smoke training pass to prove the multiclass prototype training path works.

Result:
- Added `scripts/prepare_multiclass_tower_dataset.py`.
- Added tests in `tests/test_prepare_multiclass_tower_dataset.py`.
- Generated ignored local dataset `data/multiclass_tower_defect/`:
  - total images: 24
  - total boxes: 24
  - train/val/test: 16 / 4 / 4
  - class boxes: `deformation=4`, `tower_corrosion=5`, `loose_bolt=7`, `bolt_rust=8`
- Completed 1-epoch CPU smoke training:
  - command uses `yolov8n.pt`, `imgsz=320`, `batch=4`, `workers=0`
  - output: `runs/multiclass_tower_defect/smoke_v0_1/weights/best.pt`
  - smoke metrics: mAP50 `0.0412`, mAP50-95 `0.0061`, precision `0.0039`, recall `0.7500`

Acceptance criteria:
- [x] Reviewed local labels are transformed into a YOLO data directory.
- [x] `data.yaml` records the 4-class prototype mapping.
- [x] Dataset validation passes.
- [x] YOLO smoke training completes and writes a local model artifact.
- [x] Docs state that smoke metrics are not an accuracy claim.

Validation commands:

```bash
uv run python scripts/prepare_multiclass_tower_dataset.py
uv run python scripts/prepare_multiclass_tower_dataset.py --validate-only
uv run python scripts/train.py \
  --data data/multiclass_tower_defect/data.yaml \
  --model yolov8n.pt \
  --epochs 1 \
  --batch 4 \
  --imgsz 320 \
  --device cpu \
  --workers 0 \
  --project runs/multiclass_tower_defect \
  --name smoke_v0_1 \
  --exist-ok \
  --patience 1
uv run ruff check scripts/prepare_multiclass_tower_dataset.py tests/test_prepare_multiclass_tower_dataset.py
uv run pytest tests/test_prepare_multiclass_tower_dataset.py -q
```

Rollback:
- Remove `scripts/prepare_multiclass_tower_dataset.py` and `tests/test_prepare_multiclass_tower_dataset.py`.
- Remove ignored local `data/multiclass_tower_defect/` and `runs/multiclass_tower_defect/` if the prototype dataset definition changes.

## Completed Task

### HE-015 Multiclass Tower Defect Prototype Inbox

Status: Done
Priority: P0

Scope:
- Pivot the current prototype away from crack-only HE-007 gating.
- Use the local Downloads image set as the immediate prototype data source.
- Define the 4-class prototype mapping.
- Prepare an ignored local inbox with metadata and an annotation queue.

Class mapping:

| ID | Class | Source folder |
|----|-------|---------------|
| 0 | `deformation` | `变形` |
| 1 | `tower_corrosion` | `塔材腐蚀` |
| 2 | `loose_bolt` | `螺栓松动` |
| 3 | `bolt_rust` | `螺栓锈蚀` |

Result:
- Added `scripts/prepare_multiclass_prototype_inbox.py`.
- Added tests in `tests/test_prepare_multiclass_prototype_inbox.py`.
- Prepared local ignored inbox `data/multiclass_inbox/` from 24 source images:
  - `deformation`: 4
  - `tower_corrosion`: 5
  - `loose_bolt`: 7
  - `bolt_rust`: 8
- Generated `annotation_queue.csv` for manual bbox annotation.

Acceptance criteria:
- [x] Current task ledger names the multiclass prototype as the active focus.
- [x] Class mapping is explicit and separate from the historical crack-only dataset.
- [x] Local image inbox is prepared without committing raw data.
- [x] Annotation checklist is generated before training.
- [x] Tests cover metadata, queue generation, and unreadable-image rejection.

Validation commands:

```bash
uv run python scripts/prepare_multiclass_prototype_inbox.py
uv run ruff check scripts/prepare_multiclass_prototype_inbox.py tests/test_prepare_multiclass_prototype_inbox.py
uv run pytest tests/test_prepare_multiclass_prototype_inbox.py -q
```

Rollback:
- Remove `scripts/prepare_multiclass_prototype_inbox.py` and `tests/test_prepare_multiclass_prototype_inbox.py`.
- Remove ignored local `data/multiclass_inbox/` if the prototype data source changes.

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
- Bring frontend spec count from 53 to the current 90-test baseline.

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

### HE-013 Frontend Product Polish

Status: Done
Priority: P1

Scope:
- Reduce Element Plus default/sample feel while preserving the current Vue + Element Plus implementation.
- Improve the customer-facing product shell, workspace first screen, device management first screen, upload surface, health controls, and shared component skin.
- Keep API contracts, component events, and existing tests unchanged.

Result:
- `web/src/App.vue` now has a branded dark operation rail, custom mark, telemetry block, refined nav states, topbar process indicator, and stronger status chips.
- `web/src/style.css` defines a product-specific palette, typography, Element Plus primary color tokens, button/input/radio/table/card/alert/empty overrides, and less generic radius/shadow treatment.
- `WorkspacePage.vue` and `DeviceManagementView.vue` now expose workflow/signal rails so the first screen reads as an inspection operations product.
- `ImageUpload.vue` and `HealthStatus.vue` now use custom surfaces and controls instead of stock Element Plus visual defaults.
- Desktop and mobile Playwright screenshots were reviewed for layout, text fit, and visible overlap.

Acceptance criteria:
- [x] Workspace and Device pages no longer rely on raw Element Plus default appearance as the main visual identity.
- [x] Existing frontend tests remain green.
- [x] Production build succeeds.
- [x] Browser screenshots show the revised UI at desktop and mobile widths.

Validation commands:

```bash
cd web
npm run lint
npm run test -- --run
npm run build
```

Rollback:
- Revert the HE-013 changes in `web/src/App.vue`, `web/src/style.css`, `web/src/views/WorkspacePage.vue`, `web/src/components/DeviceManagementView.vue`, `web/src/components/ImageUpload.vue`, and `web/src/components/HealthStatus.vue`.

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
- No native acceleration work in the current stage; keep the implementation on the existing Python + YOLO/ONNX path.

## 后续开发分支

当前优先级已切换为基于 24 张本地塔材缺陷图片的多类缺陷原型。crack-only HE-007 真实试点版暂不作为当前阻塞门禁；它保留为后续如果重新回到裂缝专项路线时的历史分支。2026-04-30 已补齐 `data/multiclass_inbox/` 本地整理、类别映射和标注清单；下一步是人工 bbox 标注，标注完成后再生成 YOLO 数据集并训练原型模型。

### 当前分支：多类塔材缺陷原型

1. **人工 bbox 标注**
   - 输入清单：`data/multiclass_inbox/annotation_queue.csv`
   - 图像目录：`data/multiclass_inbox/raw_images/`
   - 标签输出：`data/multiclass_inbox/reviewed_labels/`
   - 标签格式：YOLO bbox，每行 `<class_id> <x_center> <y_center> <width> <height>`，坐标归一化到 0-1。

2. **标注完成后的原型训练**
   - ✅ 已生成 `data/multiclass_tower_defect/data.yaml`。
   - ✅ 已使用 `yolov8n.pt` 完成 1-epoch smoke training。
   - 当前产物证明数据与训练链路可运行；本地推理 smoke 已证明当前权重还不适合导出 ONNX 或接入 API/前端。

3. **下一步：数据/标注改进**
   - 收紧过大的 bbox，优先把目标框改为缺陷局部而不是整段塔材。
   - 每类补充更多正样本，优先补齐 `deformation` 和 `tower_corrosion` 的近景局部图。
   - 为每张图补充多个缺陷框，而不是每张只标一个主框。
   - 重新生成数据集并训练 `prototype_v0_2` 后，再重复 HE-017 推理 smoke。

3. **原型验收口径**
   - 每类至少有可读图片和人工复核标签。
   - 模型可以完成一次本地图像推理。
   - 前端能展示多类缺陷检测结果。

### 历史分支 A：真实裂缝试点标签到位

1. **HE-007 Stage B 模型对比（真实试点版）**
   - 触发条件：已有 reviewed positive pilot crack labels。
   - 行动项：确认标注来源与数据切分，使用 `scripts/train.py` 训练自有数据模型，并与 Stage A 公共数据模型在同一试点验证集上对比。
   - 验收标准：输出训练命令、评估指标、同集对比结论，并更新 `docs/stage-b-model-comparison.md`。

### 历史分支 B：真实裂缝试点标签暂未到位

1. **指标系统升级** ✅ 已完成
   - `app.state.metrics` 已替换为基于 `prometheus_client.Counter/Histogram/Gauge` 的封装。
   - `/api/v1/metrics` 继续兼容 Prometheus scrape，并新增请求/推理耗时 histogram 分桶。
   - 验证：`uv run pytest`、`tests/test_api_inference.py` 指标回归与 deployment config 回归均已覆盖。

2. **审计日志分页与筛选增强** ✅ 已完成
   - `/reports/audit-logs` 已支持 `offset`、`total` 和 `actor` 过滤。
   - 前端设备页已补齐审计日志分页控件与服务层类型。

3. **真实样本到位前的可执行工作**
   - 保持 Stage A ONNX 为当前部署模型，不切换到 Stage B 代理模型。
   - 使用 `scripts/validate_pilot_inbox.py` 校验数据接收目录、命名规范、标注交接字段和 reviewed positive crack boxes，确保真实图片/视频到位后可直接进入 `scripts/prepare_stage_b_pilot_dataset.py`。
   - 使用 `SDNET2018 + RDD2022` public surrogate 数据做非真实试点验证，所有结论必须标记为公开代理验证。
   - 继续演练 API、前端、Edge Agent 上报、离线缓存、复核、导出和回滚路径，确保交付链路稳定。
   - 记录现场需要补充的信息：设备/杆塔/线路标识、拍摄时间、拍摄角度、是否有裂缝正样本、人工复核人和复核规则。

4. **用户演示前准备**
   - 明确演示模式：客户正式演示使用 Stage A ONNX；必要时回退 Stage A YOLO；`stub` 只用于内部链路自检或故障说明，不能作为客户检测结果来源。没有 reviewed positive pilot crack labels 时不宣称真实试点精度。
   - 准备 3-5 张演示图片和 1 个 Edge Agent 上报样例，覆盖单图检测、批量任务、上报批次、人工复核、报告摘要和导出。
   - 演示前确认 `models/stage_a_crack/best.onnx` 是否存在；若缺失或 ready 失败，切回 `INFERENCE_ENGINE=stub` 演示链路。
   - 演练启动、健康检查、前端访问、Edge Agent 上报和回滚命令，确保 API、前端、设备页、审计日志和导出路径可重复。
   - 演示前运行最小质量门禁：`uv run ruff check .`、`uv run pytest`、`cd web && npm run lint && npm run test -- --run && npm run build && npm run test:e2e`。

### 长期（Backlog）

- HE-010 分割细化（DeepLab/SAM）：仅在需要像素级裂缝面积/长度估计时推进。
- HE-011 趋势分析：依赖多批次历史数据积累，Transformer 路线在数据足够后再评估。
