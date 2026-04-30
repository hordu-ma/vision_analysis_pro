# Multiclass Tower Defect Prototype

Date: 2026-04-30

This note records the current prototype pivot from the previous crack-only gate to a small multiclass tower-defect workflow based on the user's local image set.

## Current Prototype Scope

Source images:

```text
/home/liguoma/Downloads/锈蚀、松动、变形、腐蚀/
```

Local ignored inbox:

```text
data/multiclass_inbox/
  raw_images/
  metadata/
  reviewed_labels/
  annotation_queue.csv
  classes.json
  manifest.json
```

`data/` is ignored by git, so raw images, metadata generated from local image files, and future labels stay local.

## Class Mapping

| ID | Class | Source folder | Current count |
|----|-------|---------------|---------------|
| 0 | `deformation` | `变形` | 4 |
| 1 | `tower_corrosion` | `塔材腐蚀` | 5 |
| 2 | `loose_bolt` | `螺栓松动` | 7 |
| 3 | `bolt_rust` | `螺栓锈蚀` | 8 |

This mapping is intentionally separate from the historical crack-only Stage A/B route. It is also separate from the legacy five-class `data/data.yaml` until enough reviewed labels exist to decide the longer-term class taxonomy.

## Prepare Inbox

Run:

```bash
uv run python scripts/prepare_multiclass_prototype_inbox.py
```

Expected output for the current local image set:

```text
multiclass_inbox=data/multiclass_inbox
total_images=24
deformation=4
tower_corrosion=5
loose_bolt=7
bolt_rust=8
ready_for_annotation=true
ready_for_training=false
```

## Annotation Rules

Use `data/multiclass_inbox/annotation_queue.csv` as the work queue.

For each image:

1. Open the image under `data/multiclass_inbox/raw_images/`.
2. Draw one or more bounding boxes around the visible defect target.
3. Save the YOLO label to `data/multiclass_inbox/reviewed_labels/<image_stem>.txt`.
4. Use one line per box:

```text
<class_id> <x_center> <y_center> <width> <height>
```

All coordinates must be normalized to 0-1.

If an image is not usable for training, leave it unlabeled and mark it outside the training set later. Do not create empty negative labels for this prototype unless the image has been explicitly reviewed as a negative example.

## Next Step After Annotation

The current local labels are AI-assisted reviewed labels for prototype smoke work. They are enough to validate the training path, but they should still receive human or domain-expert review before any accuracy claim.

After labels exist:

1. Generate `data/multiclass_tower_defect/data.yaml`.
2. Run a small YOLO smoke training from `yolov8n.pt`.
3. Export ONNX if the smoke model is usable.
4. Wire the prototype model into API inference and frontend display.

The first goal is a runnable prototype, not a reliable accuracy claim.

## Dataset and Smoke Training

Generate the local YOLO dataset:

```bash
uv run python scripts/prepare_multiclass_tower_dataset.py
uv run python scripts/prepare_multiclass_tower_dataset.py --validate-only
```

Current local result:

```text
dataset=data/multiclass_tower_defect
total_images=24
total_boxes=24
train_images=16
val_images=4
test_images=4
deformation_boxes=4
tower_corrosion_boxes=5
loose_bolt_boxes=7
bolt_rust_boxes=8
ready_for_smoke_training=true
```

Run smoke training:

```bash
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
```

Current smoke result:

```text
best_model=runs/multiclass_tower_defect/smoke_v0_1/weights/best.pt
mAP50=0.0412
mAP50-95=0.0061
precision=0.0039
recall=0.7500
```

These metrics only prove the prototype path can train and validate. They should not be used as model-quality evidence.

## Inference Smoke

Run local inference smoke:

```bash
uv run python scripts/smoke_multiclass_tower_inference.py \
  --model runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt \
  --conf 0.25 \
  --output data/multiclass_tower_defect/inference_smoke/prototype_v0_1_conf025.json \
  --preview-dir data/multiclass_tower_defect/inference_smoke/prototype_v0_1_previews_conf025
```

Current result:

```text
model=runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt
images=4
detections=0
```

Low-threshold diagnostic smoke:

```bash
uv run python scripts/smoke_multiclass_tower_inference.py \
  --model runs/multiclass_tower_defect/prototype_v0_1/weights/best.pt \
  --conf 0.001 \
  --output data/multiclass_tower_defect/inference_smoke/prototype_v0_1_conf0001.json \
  --preview-dir data/multiclass_tower_defect/inference_smoke/prototype_v0_1_previews_conf0001
```

Current result:

```text
images=4
detections=191
label_counts={"tower_corrosion": 52, "bolt_rust": 139}
```

This means the model and class mapping load correctly, but current detections are not stable enough for ONNX export or API/frontend wiring.

## Immediate Next Step

Improve the dataset before deployment integration:

1. Tighten overly broad boxes so they target local defect regions instead of whole tower members.
2. Add more close-up positive samples per class, especially `deformation` and `tower_corrosion`.
3. Allow multiple boxes per image where multiple visible defects exist.
4. Rebuild `data/multiclass_tower_defect/`, train `prototype_v0_2`, and rerun inference smoke.
