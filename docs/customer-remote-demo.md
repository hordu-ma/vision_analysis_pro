# Customer Remote Demo Runbook

Date: 2026-05-07

This runbook is for customer demos when the deployment machine is not brought to the customer site. The demo is a remote trial-system demonstration, not a live on-site acquisition test.

## Demo Positioning

Use this wording:

- The system trial package is ready for remote demonstration and pilot rehearsal.
- The current demo proves deployment, upload, batch task, Edge Agent reporting, human review, summary, export, metrics, and rollback paths.
- Customer-facing detection results should come from a real model profile: Stage A ONNX first, Stage A YOLO as fallback.
- `stub` is internal-only for pre-demo link checks and must be clearly labeled as simulated if it is ever mentioned.
- Stage A ONNX is the recommended real-model route demonstration.
- The multiclass tower-defect model remains experimental until real field data is collected, reviewed, and used to train `prototype_v0_2`.

Avoid these claims:

- Do not claim the multiclass tower-defect model has real field accuracy.
- Do not say customer-site validation has already been completed.
- Do not describe remote Edge Agent replay as live customer-site acquisition.

## Access Modes

### Recommended: Screen Share

Use screen sharing from the deployment machine or a machine that can reach it.

Advantages:

- Lowest network risk.
- No customer-side firewall or browser access dependency.
- You control the sequence, sample images, and fallback.

### Optional: Customer Browser Access

Use only if prepared before the meeting:

- Expose the frontend through HTTPS.
- Reverse-proxy API requests under the same origin or configure `CORS_ALLOW_ORIGINS`.
- Enable `CLOUD_API_KEY` if the URL is reachable outside your trusted network.
- Confirm `/api/v1/health`, frontend load, upload, report detail, and export before the meeting.

Do not improvise public tunneling during the customer meeting unless the customer explicitly asks for hands-on access and accepts the risk.

## Pre-Demo Checklist

Run these checks on the deployment machine before the customer session:

```bash
docker compose config
```

For a customer-facing real-model demo:

```bash
INFERENCE_ENGINE=onnx \
ONNX_MODEL_PATH=models/stage_a_crack/best.onnx \
API_RELOAD=false \
uv run uvicorn vision_analysis_pro.web.api.main:app \
  --host 0.0.0.0 \
  --port 8000
```

In another shell:

```bash
cd web
npm run dev -- --host 0.0.0.0
```

Verify:

```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/health/live
curl http://127.0.0.1:8000/api/v1/metrics
```

If ONNX is unavailable, use Stage A YOLO as the real-model fallback:

```bash
INFERENCE_ENGINE=yolo \
YOLO_MODEL_PATH=runs/stage_a_crack/baseline_v0_1/weights/best.pt \
API_RELOAD=false \
uv run uvicorn vision_analysis_pro.web.api.main:app \
  --host 0.0.0.0 \
  --port 8000
```

Use `stub` only for internal pre-demo checks:

```bash
INFERENCE_ENGINE=stub \
API_RELOAD=false \
uv run uvicorn vision_analysis_pro.web.api.main:app \
  --host 127.0.0.1 \
  --port 8001
```

Use valid JPEG samples such as `data/samples/web_rust_chain.jpg` or Stage A images under `data/stage_a_crack/images/val/`. Do not use `data/samples/web_rust_bolt.jpg` for real-engine smoke because it is currently an HTML document despite the `.jpg` suffix.

## Demo Script

### 1. Opening

Say:

> This is the remote trial demonstration of the transmission-tower inspection operations system. Today we focus on the system workflow: deployment, upload, batch analysis, edge reporting, human review, report generation, export, metrics, and rollback. Real customer-site data collection is the next stage after the system is introduced into the field.

### 2. Workspace

Open the frontend workspace and point out:

- single-image upload
- batch task history
- edge report batches
- device overview
- review and report entry points

### 3. Single Image

Upload one valid sample image.

Explain:

- Stage A ONNX produces real model results for the crack-only route.
- If a customer image returns no detections, show it as a real negative/uncertain result and move into human review and data-capture discussion.

### 4. Batch Task

Upload multiple images and open the completed task.

Show:

- task status
- completed files
- detection count
- export entry

### 5. Edge Report

Submit or replay one report batch.

Explain:

- On site, this batch would come from Edge Agent, UAV capture, or another acquisition terminal.
- In this remote demo, the batch is a controlled report-path rehearsal.

### 6. Human Review

Open the report detail, select a frame, and save:

- review status
- reviewer
- note

Explain that reviewed outputs become the handoff point for later training data preparation.

### 7. Summary And Export

Show:

- report summary
- CSV export
- batch list
- device list
- alert summary

Explain that reports preserve source detection facts and review status.

### 8. Operations And Rollback

Show or explain:

- health checks
- Prometheus metrics
- duplicate `batch_id` idempotency
- Edge Agent offline cache and replay
- rollback to `INFERENCE_ENGINE=stub`

## Fallback Plan

If ONNX readiness or sample inference fails, try YOLO:

```bash
export INFERENCE_ENGINE=yolo
export YOLO_MODEL_PATH=runs/stage_a_crack/baseline_v0_1/weights/best.pt
```

If both real-model profiles fail, use `stub` only to explain the workflow and state clearly that the displayed detections are simulated.

If frontend dev server fails:

- keep API and curl commands ready for upload/report/review/export.
- use OpenAPI at `http://<host>:8000/docs` as a backup.

If external access fails:

- switch to screen sharing from the deployment machine.
- do not debug customer network live unless the meeting purpose changes to technical deployment support.

## Customer Follow-Up

End with the next field-stage plan:

1. Deploy or connect the system in the customer's reachable environment.
2. Collect real tower images or videos.
3. Review and label representative samples.
4. Generate training data from reviewed labels.
5. Train `prototype_v0_2`.
6. Evaluate and decide whether to promote the new model to the trial profile.
