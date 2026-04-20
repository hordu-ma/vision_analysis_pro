# Stage B Pilot Data Loop

Date: 2026-04-20

Task: HE-006 Stage B Pilot Data Loop

## Purpose

Stage B defines the repeatable intake path for self-owned pilot images or videos. It keeps pilot data separate from both:

- Stage A public-data crack baseline: `data/stage_a_crack/`
- Legacy five-class dataset config: `data/data.yaml`

The Stage B target dataset is:

```text
data/stage_b_pilot_crack/
```

This directory is ignored by git because raw pilot images, labels, videos, and generated train/val/test files must stay local.

## Dataset Builder

Use `scripts/prepare_stage_b_pilot_dataset.py` to create a crack-only YOLO dataset.

Image inputs with reviewed YOLO labels:

```bash
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  path/to/pilot_images \
  --labels-dir path/to/pilot_labels \
  --output data/stage_b_pilot_crack
```

Video inputs with keyframe extraction:

```bash
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  path/to/pilot_video.mp4 \
  --extract-videos \
  --interval-seconds 1.0 \
  --min-scene-delta 20 \
  --blur-threshold 10 \
  --output data/stage_b_pilot_crack
```

If images are collected before annotation is complete, create empty label files and track them as pending annotation:

```bash
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  path/to/pilot_images \
  --allow-unlabeled \
  --output data/stage_b_pilot_crack
```

The script writes:

- `data/stage_b_pilot_crack/data.yaml`
- `data/stage_b_pilot_crack/manifest.json`
- `data/stage_b_pilot_crack/images/{train,val,test}/`
- `data/stage_b_pilot_crack/labels/{train,val,test}/`
- `data/stage_b_pilot_crack/raw_keyframes/` when video extraction is used

## Local Smoke Intake

The current local smoke generated the Stage B directory from checked-in sample images to validate the data-loop mechanics:

```bash
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  data/samples/web_rust_iron.jpg \
  data/samples/web_spalling_concrete.jpg \
  data/samples/web_flaking_rust.jpg \
  data/samples/web_rust_bolt.jpg \
  data/samples/web_rust_chain.jpg \
  --output data/stage_b_pilot_crack \
  --allow-unlabeled
```

Result:

```text
total_images=5
labeled_images=0
pending_annotation_empty_label_images=5
split_counts={'train': 3, 'val': 1, 'test': 1}
```

This smoke dataset validates structure only. It is not a pilot-quality crack training set because all labels are pending.

## Validation

Run the dataset validator after every intake or annotation update:

```bash
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  --output data/stage_b_pilot_crack \
  --validate-only
```

The validator checks:

- each image has a matching `.txt` label file
- no orphan label files exist
- YOLO labels contain five fields
- class id is `0`
- bbox coordinates are normalized to `[0, 1]`
- bbox width and height are positive

## Annotation Rules

Stage B is crack-only by default:

```yaml
nc: 1
names:
  0: crack
```

Before model training or HE-007 comparison:

- replace pending empty labels with reviewed crack annotations
- keep the same image stem for each `.txt` label file
- keep target-environment videos/images out of git
- rerun `--validate-only`

## Decision

HE-006 is accepted as the Stage B data intake loop. HE-007 remains the model-comparison step: train on reviewed Stage B labels, evaluate Stage A and Stage B on the same held-out pilot validation set, then decide whether to keep Stage A, switch to Stage B, or train a merged dataset.
