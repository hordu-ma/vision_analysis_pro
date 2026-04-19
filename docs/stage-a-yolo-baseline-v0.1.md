# Stage A YOLO Baseline v0.1 Evaluation

Date: 2026-04-20

Task: HE-001 Stage A YOLO Baseline v0.1

## Summary

Stage A produced a reproducible single-class crack detector from the public Hugging Face `senthilsk/crack_detection_dataset` dataset. The selected model is a YOLOv8n baseline trained from `data/stage_a_crack/data.yaml`; it is suitable for exercising the real YOLO/ONNX inference paths, but it is not a production accuracy claim for the target pilot domain.

## Dataset

Source:
- Hugging Face `senthilsk/crack_detection_dataset`, CC BY 4.0.

Preparation command:

```bash
uv run python scripts/prepare_stage_a_crack_dataset.py \
  --source data/public/senthilsk_crack_detection_dataset \
  --output data/stage_a_crack
```

Prepared split summary:

| Split | Images | Positive Images | Negative Images | Objects | Skipped Objects |
|-------|--------|-----------------|-----------------|---------|-----------------|
| train | 2263 | 2169 | 94 | 2461 | 1 |
| val | 462 | 437 | 25 | 439 | 0 |
| test | 225 | 214 | 11 | 215 | 0 |

Dataset config:
- `data/stage_a_crack/data.yaml`
- Class mapping: `0 crack`

## Training

Command:

```bash
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
```

Environment:
- Ultralytics `8.3.235`
- Python `3.12.13`
- PyTorch `2.9.1+cu128`
- Device: CUDA `0`, NVIDIA RTX PRO 500 Blackwell Generation Laptop GPU, 5672 MiB

Training stopped early after 31 epochs because no improvement was observed for 5 epochs. The best model came from epoch 26 and was saved as:

```text
runs/stage_a_crack/baseline_v0_1/weights/best.pt
```

Best validation metrics:

| Epoch | Precision | Recall | mAP50 | mAP50-95 |
|-------|-----------|--------|-------|----------|
| 26 | 0.92581 | 0.91344 | 0.95556 | 0.63521 |

Final validation pass on `best.pt` reported:

| Precision | Recall | mAP50 | mAP50-95 |
|-----------|--------|-------|----------|
| 0.9265 | 0.9134 | 0.9555 | 0.6353 |

## ONNX Export

Runtime dependency setup for ONNX inference:

```bash
uv sync --extra dev --extra onnx
```

Export command:

```bash
uv run python scripts/export_onnx.py \
  --model runs/stage_a_crack/baseline_v0_1/weights/best.pt \
  --output models/stage_a_crack/best.onnx
```

Export result:
- `models/stage_a_crack/best.onnx`
- Input: `images [1, 3, 640, 640]`
- Output: `output0 [1, 5, 8400]`
- File size: 11.67 MB
- ONNX format validation passed.

## Smoke Checks

YOLO direct inference:

```bash
INFERENCE_ENGINE=yolo YOLO_MODEL_PATH=runs/stage_a_crack/baseline_v0_1/weights/best.pt uv run python - <<'PY'
from pathlib import Path
from vision_analysis_pro.core.inference import YOLOInferenceEngine

img = Path("data/stage_a_crack/images/val/crack-101-_jpg.rf.7250a8c4188a62263f703859846f833d.jpg")
engine = YOLOInferenceEngine(Path("runs/stage_a_crack/baseline_v0_1/weights/best.pt"))
print(engine.predict(img))
PY
```

Result:
- Image: `data/stage_a_crack/images/val/crack-101-_jpg.rf.7250a8c4188a62263f703859846f833d.jpg`
- Detections: 1
- First detection: `crack`, confidence `0.5878`

FastAPI inference smoke:

```bash
INFERENCE_ENGINE=yolo YOLO_MODEL_PATH=runs/stage_a_crack/baseline_v0_1/weights/best.pt uv run python - <<'PY'
from pathlib import Path
from fastapi.testclient import TestClient
from vision_analysis_pro.web.api.main import app

img = Path("data/stage_a_crack/images/val/crack-101-_jpg.rf.7250a8c4188a62263f703859846f833d.jpg")
with TestClient(app) as client:
    with img.open("rb") as f:
        resp = client.post("/api/v1/inference/image", files={"file": (img.name, f, "image/jpeg")})

data = resp.json()
assert resp.status_code == 200
assert data["metadata"]["engine"] == "YOLOInferenceEngine"
assert len(data["detections"]) >= 1
print({"status_code": resp.status_code, "detections": len(data["detections"])})
PY
```

Result:
- Status: `200`
- Engine: `YOLOInferenceEngine`
- Detections: 1

ONNX direct inference:

```bash
uv run python - <<'PY'
from pathlib import Path
from vision_analysis_pro.core.inference import ONNXInferenceEngine

img = Path("data/stage_a_crack/images/val/crack-101-_jpg.rf.7250a8c4188a62263f703859846f833d.jpg")
engine = ONNXInferenceEngine(Path("models/stage_a_crack/best.onnx"))
print(engine.predict(img))
PY
```

Result:
- Detections: 1
- First detection: `crack`, confidence `0.5877`

## Decision

HE-001 is accepted. Stage A is now good enough to validate real YOLO and ONNX inference wiring. Stage B remains required before claiming pilot readiness, because the current model is trained on a public dataset and may not match the target camera, surface, lighting, or defect distribution.
