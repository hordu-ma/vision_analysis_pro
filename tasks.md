# Vision Analysis Pro tasks.md

Harness Engineering task ledger for the current project direction.

Last updated: 2026-04-19

## Operating Rules

- Keep exactly one active delivery focus at a time. The current focus is **Stage A crack-only YOLO baseline**.
- Every task must include scope, acceptance criteria, validation commands, artifacts, and rollback notes.
- Data, model weights, run outputs, and private credentials stay out of git. Commit scripts, configs, tests, docs, and small reproducibility metadata only.
- `data/data.yaml` remains the legacy five-class target. Stage A uses `data/stage_a_crack/data.yaml` and must not overwrite the five-class config.
- DeepLab, Transformer trend modeling, MQTT, Rust/PyO3, and LLM report generation are not on the critical path unless a task below explicitly promotes them.

## Current Decision

The best-practice path is not to build a four-model chain immediately. The project should first finish a reliable crack-only inspection loop:

1. Public crack dataset to YOLO data format.
2. Reproducible YOLO training and evaluation.
3. Exported inference artifact wired into the existing API/Edge Agent paths.
4. Browser and Edge Agent end-to-end checks.
5. Only then expand to segmentation, temporal trends, or LLM reports.

## Done Recently

- Stage A public dataset source selected: Hugging Face `senthilsk/crack_detection_dataset`, CC BY 4.0.
- `scripts/prepare_stage_a_crack_dataset.py` converts COCO annotations to single-class YOLO labels.
- Generated local dataset: `data/stage_a_crack/data.yaml`.
- Smoke training completed with `yolov8n.pt`, 1 epoch, `imgsz=320`, MPS.
- Current backend baseline: `175 passed, 43 skipped`.
- Current frontend baseline: `53 passed`, lint and production build passing from the latest full validation run.

## Active Task

### HE-001 Stage A YOLO Baseline v0.1

Status: Next
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

Acceptance criteria:
- Training command and hyperparameters are recorded in docs.
- Validation metrics include at least precision, recall, mAP50, and mAP50-95.
- A sample inference succeeds through the existing YOLO path.
- ONNX export succeeds or the blocker is documented with exact error output.
- A short model card or evaluation note is added under `docs/`.

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
  --device mps \
  --workers 0 \
  --project runs/stage_a_crack \
  --name baseline_v0_1 \
  --exist-ok

uv run python scripts/export_onnx.py \
  --model runs/stage_a_crack/baseline_v0_1/weights/best.pt \
  --output models/stage_a_crack/best.onnx

uv run ruff check .
INFERENCE_ENGINE=stub uv run pytest -q
```

Rollback:
- Remove `runs/stage_a_crack/baseline_v0_1/` and exported files under `models/stage_a_crack/`.
- Leave `scripts/prepare_stage_a_crack_dataset.py` and `data/stage_a_crack/data.yaml` intact unless the dataset source changes.

## P0 Queue

### HE-002 Browser E2E Smoke

Status: Planned
Priority: P0

Scope:
- Add a browser-level test for upload -> inference -> result view.
- Use `INFERENCE_ENGINE=stub` as the deterministic default.
- Keep the test independent of local model weights.

Acceptance criteria:
- The test starts or targets the local API and frontend dev server.
- It uploads a small image, waits for completion, and asserts visible result state.
- It can run from `web/` with a documented command.

Validation commands:

```bash
cd web
npm run lint
npm run test -- --run
npm run build
npm run test:e2e
```

### HE-003 Keyframes Into Edge Agent

Status: Planned
Priority: P0

Scope:
- Wire the OpenCV keyframe extractor into video source handling or a dedicated preprocessing path.
- Preserve the current raw-frame path for compatibility.
- Add config options for interval, scene delta, and blur threshold.

Acceptance criteria:
- Video source can run in raw-frame mode and keyframe mode.
- Tests cover fixed interval extraction, scene filtering, and missing/invalid video behavior.
- Example config documents the new options.

Validation commands:

```bash
uv run pytest tests/test_keyframes.py tests/test_edge_agent.py -q
uv run ruff check .
```

## P1 Queue

### HE-004 Edge Agent Reporting Steady State

Status: Planned
Priority: P1

Scope:
- Exercise network failure, cache replay, duplicate batch, API key, and report summary paths together.
- Confirm cloud API idempotency with realistic Edge Agent payloads.

Acceptance criteria:
- Tests cover offline cache replay and duplicate batch acceptance.
- `/api/v1/report/{batch_id}/summary` works for replayed batches.
- Failure modes are documented in `docs/demo.md` or deployment runbook.

Validation commands:

```bash
uv run pytest tests/test_edge_agent.py tests/test_api_inference.py -q
INFERENCE_ENGINE=stub uv run pytest -q
```

### HE-005 Pilot Deployment Runbook

Status: Planned
Priority: P1

Scope:
- Make the local pilot path explicit: API, frontend, optional observability, model volume, Edge Agent config.
- Document which inference engine is expected in each profile.

Acceptance criteria:
- `docs/deployment.md` has one clear crack-only Stage A path.
- `.env.example` and `docker-compose.yml` agree on model paths.
- Smoke commands and rollback steps are included.

Validation commands:

```bash
docker compose config
uv run ruff check .
```

## P2 Backlog

### HE-006 LLM Report Extension

Status: Backlog
Priority: P2

Promote only after HE-001 and HE-004 are stable.

Scope:
- Generate human-readable report text from structured detection results, review status, and device metadata.
- LLM output must not alter detection labels or confidence values.

Acceptance criteria:
- Report generation has deterministic template fallback.
- LLM prompt and output schema are versioned.
- Tests cover missing metadata and low-confidence detections.

### HE-007 Segmentation Refinement

Status: Backlog
Priority: P2

Promote only if Stage A users need crack length/area estimates that bounding boxes cannot support.

Scope:
- Evaluate segmentation for crack masks as a refinement step after object detection.
- Do not replace the YOLO baseline unless evaluation justifies it.

### HE-008 Trend Analysis

Status: Backlog
Priority: P2

Promote only after repeated inspections exist for the same device/asset.

Scope:
- Build trend features from stored batch history before considering Transformer models.
- Start with simple time-series summaries and thresholds.

## Explicit Non-Goals For The Next Sprint

- No five-class production claim without a real five-class dataset and evaluation report.
- No DeepLab/Transformer chain as a prerequisite for Stage A.
- No committed model weights or public dataset archives.
- No Rust/PyO3 work until profiling shows Python preprocessing or postprocessing is the bottleneck.
