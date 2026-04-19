# Vision Analysis Pro tasks.md

Harness Engineering task ledger for the current project direction.

Last updated: 2026-04-20

## Operating Rules

- Keep exactly one active delivery focus at a time. The current active focus is **HE-002 / Browser E2E Smoke**; Stage B is already planned but starts after HE-001 acceptance.
- Every task must include scope, acceptance criteria, validation commands, artifacts, and rollback notes.
- Data, model weights, run outputs, and private credentials stay out of git. Commit scripts, configs, tests, docs, and small reproducibility metadata only.
- `data/data.yaml` remains the legacy five-class target. Stage A uses `data/stage_a_crack/data.yaml` and must not overwrite the five-class config.
- DeepLab, Transformer trend modeling, MQTT, Rust/PyO3, and LLM report generation are not on the critical path unless a task below explicitly promotes them.

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
| Data layer: OpenCV keyframes from video | Mainline data ingestion path; CLI exists, Edge Agent integration pending | HE-003, HE-006 |
| Vision recognition: DeepLab, YOLO, Transformer | YOLO is the active detector; segmentation and trend analysis are follow-up tasks gated by evidence | HE-001, HE-007, HE-010, HE-011 |
| Language extension: LLM explanations/reports | Template report exists now; LLM is report-only and must not change detection decisions | HE-004, HE-009 |
| Backend/frontend: full inspection flow | Current app already has API, frontend, batch tasks, report summary; browser/Edge steady-state checks remain | HE-002, HE-004, HE-008 |

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
- HE-001 Stage A formal YOLO baseline completed from `data/stage_a_crack/data.yaml`.
- Best Stage A validation metrics at epoch 26: precision `0.92581`, recall `0.91344`, mAP50 `0.95556`, mAP50-95 `0.63521`.
- Local artifacts created: `runs/stage_a_crack/baseline_v0_1/weights/best.pt` and `models/stage_a_crack/best.onnx`.
- Current backend baseline: `176 passed, 43 skipped`.
- Current frontend baseline: `53 passed`, lint and production build passing from the latest full validation run.

## Accepted Task

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

## Active Task

### HE-002 Browser E2E Smoke

Status: Next
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

## P0 Queue

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

### HE-006 Stage B Pilot Data Loop

Status: Planned
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

Acceptance criteria:
- `data/stage_b_pilot_crack/data.yaml` is generated locally.
- A manifest records source videos/images, extraction settings, split counts, and annotation status.
- At least one validation command checks image/label pairing and YOLO label format.
- Documentation explains how Stage B data is added without overwriting Stage A.

Validation commands:

```bash
uv run python scripts/extract_keyframes.py path/to/pilot_video.mp4 \
  --output-dir data/stage_b_pilot_crack/raw_keyframes \
  --interval-seconds 1.0 \
  --min-scene-delta 20 \
  --blur-threshold 10

uv run ruff check .
uv run pytest tests/test_keyframes.py -q
```

Artifacts:
- Local dataset: `data/stage_b_pilot_crack/`
- Local manifest: `data/stage_b_pilot_crack/manifest.json`
- Optional docs note after first pilot dataset: `docs/stage-b-pilot-data.md`

Rollback:
- Remove `data/stage_b_pilot_crack/` and any corresponding `runs/stage_b_pilot_crack/` outputs.
- No tracked five-class config should be modified.

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

### HE-007 Stage B Model Comparison

Status: Planned
Priority: P1

Scope:
- Train a Stage B model on pilot/self-owned data and compare it against the Stage A public-data baseline.
- Decide whether the demo/pilot should use Stage A, Stage B, or a merged dataset.

Acceptance criteria:
- Evaluation note compares Stage A and Stage B metrics on the same held-out pilot validation set.
- Recommendation is explicit: keep Stage A, switch to Stage B, or train merged v0.3.
- Any domain-shift issues are listed with examples.

Validation commands:

```bash
uv run python scripts/train.py \
  --data data/stage_b_pilot_crack/data.yaml \
  --model yolov8n.pt \
  --epochs 50 \
  --batch 8 \
  --imgsz 640 \
  --project runs/stage_b_pilot_crack \
  --name baseline_v0_1 \
  --exist-ok

INFERENCE_ENGINE=stub uv run pytest -q
```

Rollback:
- Remove `runs/stage_b_pilot_crack/` and exported files under `models/stage_b_pilot_crack/`.

### HE-008 Full Inspection Flow Hardening

Status: Planned
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
INFERENCE_ENGINE=stub uv run pytest tests/test_api_inference.py tests/test_reporting.py -q
cd web
npm run lint
npm run test -- --run
```

## P2 Backlog

### HE-009 LLM Report Extension

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
