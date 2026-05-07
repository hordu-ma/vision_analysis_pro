# Model Profile Status

Date: 2026-05-07

This note records the current status of the three inference profiles: `stub`, `yolo`, and `onnx`.

## Summary

| Profile | Purpose | Current completion | Customer-demo use |
|---------|---------|--------------------|-------------------|
| `stub` | Deterministic internal link test without model files | Complete for internal smoke only | Do not use as the source of customer-facing detection results |
| `yolo` | Load `.pt` weights through Ultralytics YOLO | Stage A crack-only model is complete for real-model smoke and evaluation; multiclass tower prototype is experimental | Can be shown as a real model path if using Stage A crack-only scope |
| `onnx` | Load exported `.onnx` weights through ONNX Runtime | Stage A crack-only ONNX is complete for deployment-route smoke and Edge Agent reporting; multiclass tower ONNX is not exported | Recommended real-model route for customer demo, with crack-only scope stated clearly |

## Verified Status On 2026-05-07

Validation sample:

```text
data/stage_a_crack/images/val/crack-1455-_jpg.rf.d78b0366a48c54f31295522b24dcf2f0.jpg
```

Stage A YOLO:

```text
model=runs/stage_a_crack/baseline_v0_1/weights/best.pt
engine=YOLOInferenceEngine
detection_count=1
label=crack
confidence=0.425392
device=cuda:0
```

Stage A ONNX:

```text
model=models/stage_a_crack/best.onnx
engine=ONNXInferenceEngine
detection_count=1
label=crack
confidence=0.425472
provider=CPUExecutionProvider
```

Multiclass tower YOLO prototype:

```text
model=runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt
engine=YOLOInferenceEngine
classes=deformation,tower_corrosion,loose_bolt,bolt_rust
sample=data/multiclass_tower_defect/images/test/bolt_rust_004.jpg
conf=0.25
detection_count=0
```

Conclusion:

- Stage A YOLO is complete for crack-only training/evaluation smoke.
- Stage A ONNX is complete for crack-only deployment-route and Edge Agent smoke.
- Multiclass tower YOLO is only a local experiment. It is not ready for ONNX export, API/frontend default integration, or customer-facing accuracy claims.
- Multiclass tower ONNX is not complete because no usable multiclass model has been promoted for export.

## Customer Demo Rule

For formal customer demos, do not use `stub` as the main detection-result source.

Use this order:

1. Start with Stage A ONNX (`INFERENCE_ENGINE=onnx`) if `models/stage_a_crack/best.onnx` is present and ready.
2. Use real images, preferably customer-provided images or traceable public/owned samples.
3. If ONNX fails, switch to YOLO (`INFERENCE_ENGINE=yolo`) with `runs/stage_a_crack/baseline_v0_1/weights/best.pt`.
4. Use `stub` only for internal pre-demo checks or fallback workflow explanation, clearly labeled as simulated output.

Recommended wording:

> This demo uses the real ONNX model path for crack detection and demonstrates the inspection workflow: upload, batch analysis, report intake, human review, summary, and export. Multiclass tower-defect recognition will be promoted only after customer field samples are collected, reviewed, and used to train the next model.

Avoid:

> This model already detects deformation, tower corrosion, loose bolts, and bolt rust in real field conditions.

## Commands

Stage A YOLO API:

```bash
INFERENCE_ENGINE=yolo \
YOLO_MODEL_PATH=runs/stage_a_crack/baseline_v0_1/weights/best.pt \
API_RELOAD=false \
uv run uvicorn vision_analysis_pro.web.api.main:app \
  --host 0.0.0.0 \
  --port 8000
```

Stage A ONNX API:

```bash
INFERENCE_ENGINE=onnx \
ONNX_MODEL_PATH=models/stage_a_crack/best.onnx \
API_RELOAD=false \
uv run uvicorn vision_analysis_pro.web.api.main:app \
  --host 0.0.0.0 \
  --port 8000
```

Internal-only stub check:

```bash
INFERENCE_ENGINE=stub \
API_RELOAD=false \
uv run uvicorn vision_analysis_pro.web.api.main:app \
  --host 127.0.0.1 \
  --port 8000
```

## Notes

- `data/samples/web_rust_bolt.jpg` is currently an HTML document with a `.jpg` suffix. Do not use it for real-model smoke.
- The Stage A ONNX model is crack-only even though the generic ONNX engine has a legacy five-class default label mapping. The current deployed Stage A result should be presented as crack-only.
