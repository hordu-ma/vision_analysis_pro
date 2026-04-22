# Stage B Pilot Data Loop

Date: 2026-04-20, updated 2026-04-22

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

When real pilot media is not available yet, the repository now also supports a **public surrogate** path based on SDNET2018 and RDD2022. That path is for engineering validation only and must not be described as real pilot evidence.

2026-04-22 status: no new self-owned pilot media or reviewed positive crack labels were found in the workspace. The existing local `data/stage_b_pilot_crack/` is a proxy dataset built from Stage A test images auto-labeled by the Stage A ONNX model; it validates successfully, but it is not real pilot evidence.

## Work Before Reviewed Labels Arrive

Until reviewed positive pilot crack labels exist, the useful work is operational preparation, not model expansion:

- keep `models/stage_a_crack/best.onnx` as the recommended deployment model
- do not switch to the current Stage B proxy model
- keep all real pilot media, labels, and generated datasets out of git
- keep using `INFERENCE_ENGINE=stub` for link checks and Stage A YOLO/ONNX for real-model smoke
- use public surrogate data only for engineering validation, and mark every result as non-real-pilot evidence
- rehearse API, frontend, Edge Agent reporting, offline cache replay, review save, report summary, export, and rollback paths

### Pilot Data Handoff Checklist

Collect the following fields before or alongside the first real media drop:

| Field | Required | Notes |
|-------|----------|-------|
| `asset_id` | yes | Tower, pole, bridge span, line segment, or other stable inspection target ID. |
| `device_id` | yes | Must match the Edge Agent or acquisition device where possible. |
| `site_name` | yes | Human-readable site or route name for report filtering. |
| `capture_time` | yes | Local timestamp or UTC timestamp; keep the original timezone if known. |
| `source_type` | yes | `image_folder`, `video`, `rtsp_capture`, or `manual_upload`. |
| `camera_angle` | preferred | Front/side/top/detail, or a short free-text description. |
| `weather_lighting` | preferred | Clear/rain/night/backlight/low-light if known. |
| `reviewer` | yes for labels | Person or role that confirmed each positive or negative label. |
| `review_rule_version` | yes for labels | Use the current rules in `docs/annotation_guidelines.md` unless a newer rule is recorded. |
| `known_positive_count` | preferred | Estimate of frames/images containing visible cracks before annotation starts. |

Recommended local staging layout:

```text
data/pilot_inbox/
  raw_images/
  raw_videos/
  metadata/
  prelabels/
  reviewed_labels/
```

`data/` is ignored for local data caches, so these directories should be created locally when needed and not committed. If the media arrives through another storage path, keep the same logical split and pass those paths to the dataset builder.

### Prelabel Dry Run

When Stage A ONNX weights exist locally, use them to prelabel candidate images before human review:

```bash
uv run python scripts/auto_label_onnx.py \
  --model models/stage_a_crack/best.onnx \
  --images data/pilot_inbox/raw_images \
  --output data/pilot_inbox/prelabels \
  --conf 0.30
```

Human review then edits or replaces the generated `.txt` labels under `data/pilot_inbox/reviewed_labels`. Empty files are valid only after a reviewer confirms the image is a negative crack sample.

### Day-1 HE-007 Path After Labels Arrive

Once reviewed labels contain positive `crack` boxes, run the real-pilot branch in this order:

```bash
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  data/pilot_inbox/raw_images \
  --labels-dir data/pilot_inbox/reviewed_labels \
  --output data/stage_b_pilot_crack \
  --mark-reviewed

uv run python scripts/prepare_stage_b_pilot_dataset.py \
  --output data/stage_b_pilot_crack \
  --validate-only

uv run python scripts/train.py \
  --data data/stage_b_pilot_crack/data.yaml \
  --model runs/stage_a_crack/baseline_v0_1/weights/best.pt \
  --epochs 30 \
  --batch 8 \
  --imgsz 640 \
  --project runs/stage_b_pilot_crack \
  --name real_pilot_v0_1 \
  --exist-ok
```

After training, evaluate Stage A and Stage B on the same held-out pilot validation split. Only update the deployment recommendation if Stage B wins on that real-pilot comparison.

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

After human review, empty labels that are confirmed to contain no `crack` target can be marked as reviewed negatives:

```bash
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  path/to/pilot_images \
  --allow-unlabeled \
  --mark-reviewed \
  --output data/stage_b_pilot_crack
```

Reviewed labels supplied through `--labels-dir` can also be marked with `--mark-reviewed`. The manifest then records `reviewed_images`, `reviewed_negative_empty_label_images`, and per-item `annotation_status`.

The script writes:

- `data/stage_b_pilot_crack/data.yaml`
- `data/stage_b_pilot_crack/manifest.json`
- `data/stage_b_pilot_crack/images/{train,val,test}/`
- `data/stage_b_pilot_crack/labels/{train,val,test}/`
- `data/stage_b_pilot_crack/raw_keyframes/` when video extraction is used

## Public Surrogate Intake (SDNET2018 + RDD2022)

If you do not have self-owned pilot videos/images yet, use the public surrogate builder first:

```bash
uv run python scripts/prepare_public_surrogate_crack_dataset.py \
  --sdnet2018-source data/public/SDNET2018 \
  --rdd2022-source data/public/RDD2022 \
  --output data/stage_b_public_surrogate_crack
```

Source references:

- SDNET2018 official page: <https://digitalcommons.usu.edu/all_datasets/48/>
- RDD2022 official DOI / Figshare: <https://doi.org/10.6084/m9.figshare.21431547>

Behavior:

- `SDNET2018/NonCrack` images are imported as reviewed negative empty labels.
- `SDNET2018/Crack` images are skipped by default because SDNET2018 is a classification dataset, not a detection-box dataset.
- `RDD2022` images use Pascal VOC XML; `D00` / `D10` / `D20` are mapped to class `0 crack`.
- `RDD2022` images that only contain non-crack damage classes remain as negative images for crack-only training.

If local Stage A ONNX weights are available, SDNET2018 crack images can be used as proxy positives:

```bash
uv run python scripts/prepare_public_surrogate_crack_dataset.py \
  --sdnet2018-source data/public/SDNET2018 \
  --sdnet2018-crack-auto-label-model models/stage_a_crack/best.onnx \
  --rdd2022-source data/public/RDD2022 \
  --output data/stage_b_public_surrogate_crack
```

This still counts as **public surrogate / proxy** validation. It does not replace the self-owned Stage B intake loop documented above.

## Local Smoke Intake

The first local smoke generated the Stage B directory from checked-in sample images to validate the data-loop mechanics:

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

## Local Reviewed-Negative Smoke Labels

2026-04-20 update: local sample review removed one invalid image (`data/samples/web_rust_bolt.jpg`, an HTML error page saved with `.jpg`) and regenerated the local Stage B smoke dataset from four readable sample images:

```bash
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  data/samples/web_rust_iron.jpg \
  data/samples/web_spalling_concrete.jpg \
  data/samples/web_flaking_rust.jpg \
  data/samples/web_rust_chain.jpg \
  --output data/stage_b_pilot_crack \
  --allow-unlabeled \
  --mark-reviewed
```

Result:

```text
total_images=4
labeled_images=0
pending_annotation_empty_label_images=0
reviewed_images=4
reviewed_negative_empty_label_images=4
split_counts={'train': 2, 'val': 1, 'test': 1}
```

These are reviewed negative smoke labels. They prove the manifest can distinguish reviewed empty labels from pending annotation and keep invalid image files out of the dataset. They do not satisfy HE-007 training needs by themselves because there are no reviewed positive `crack` boxes in the local sample set.

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

Latest validation:

```bash
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  --output data/stage_b_pilot_crack \
  --validate-only
```

Result on 2026-04-22:

```text
validated Stage B dataset: data/stage_b_pilot_crack
```

## Annotation Rules

Stage B is crack-only by default:

```yaml
nc: 1
names:
  0: crack
```

Before model training or HE-007 comparison:

- replace pending empty labels with reviewed crack annotations
- keep reviewed negative images as empty `.txt` labels with `--mark-reviewed`
- ensure the training split includes reviewed positive `crack` boxes, not only reviewed negatives
- keep the same image stem for each `.txt` label file
- keep target-environment videos/images out of git
- rerun `--validate-only`

## Decision

HE-006 is accepted as the Stage B data intake loop. HE-007 remains the model-comparison step: train on reviewed Stage B labels, evaluate Stage A and Stage B on the same held-out pilot validation set, then decide whether to keep Stage A, switch to Stage B, or train a merged dataset.

Until reviewed positive pilot crack labels exist, keep Stage A as the deployment model and treat Stage B/public surrogate outputs as engineering validation only.
