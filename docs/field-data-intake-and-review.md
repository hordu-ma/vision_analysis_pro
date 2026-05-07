# Field Data Intake And Review SOP

Date: 2026-05-07

This SOP completes the packaging-first route for work before more real transmission-tower samples are available. The system should first become the field data intake and review entry point. More samples and model training come after the system reaches the real environment.

## Scope

This SOP covers:

- collecting real images or video frames after field access
- preserving metadata needed for reports and training
- reviewing detections and samples
- exporting samples for annotation
- generating reviewed labels and training datasets later

It does not claim the current multiclass tower-defect model is production-ready.

## Data Intake Paths

### Path A: Frontend Upload

Use when an operator manually uploads images from a browser.

Expected use:

- quick customer demo
- manual sample collection
- small batch review

Required action after upload:

- keep original file names traceable to tower or route ID where possible
- create or update batch/device notes in the report workflow
- export results for downstream review when needed

### Path B: Edge Agent Folder Source

Use when images are copied to an edge device or local folder.

Example:

```bash
uv run python examples/run_edge_agent.py \
  --device-id tower-edge-001 \
  --source-type folder \
  --source-path /path/to/field/images \
  --engine onnx \
  --model-path models/stage_a_crack/best.onnx \
  --confidence 0.1 \
  --report-url http://<api-host>:8000/api/v1/report \
  --batch-size 10 \
  --batch-interval 5
```

Use `stub` only for system-link checks. Use `onnx` when verifying the real-model route.

### Path C: Video Keyframes

Use when the customer provides videos rather than still images.

```bash
uv run python scripts/extract_keyframes.py path/to/video.mp4 \
  --output-dir data/pilot_inbox/raw_images \
  --interval-seconds 1.0 \
  --min-scene-delta 20 \
  --blur-threshold 10
```

The extracted frames still need metadata and human review before training.

## Metadata Requirements

Record these fields for each field batch or image whenever possible:

| Field | Required | Notes |
|-------|----------|-------|
| `asset_id` | yes | Tower, line segment, route, or inspection target ID. |
| `device_id` | yes | Edge Agent or acquisition device ID. |
| `site_name` | yes | Customer site, route, or work area. |
| `capture_time` | yes | Original local time or UTC. |
| `source_type` | yes | `frontend_upload`, `edge_folder`, `video_keyframe`, `rtsp_capture`, or `manual_import`. |
| `image_name` | yes | Original or stable derived file name. |
| `camera_angle` | preferred | Front, side, top, detail, or free text. |
| `weather_lighting` | preferred | Clear, rainy, night, backlight, low-light, etc. |
| `operator` | preferred | Person or role that collected the media. |
| `reviewer` | yes for reviewed labels | Person or role that confirmed labels. |
| `review_rule_version` | yes for reviewed labels | Review rule version used for label decisions. |

For local training handoff, place metadata under:

```text
data/pilot_inbox/metadata/
```

## Review Workflow

Use this order:

1. Open the report batch in the frontend.
2. Check each frame with detections or operational value.
3. Save review status:
   - `confirmed`: detection or finding is accepted for the current workflow.
   - `rejected`: detection is wrong or image is not useful.
   - `pending`: needs later expert review.
4. Add reviewer and note.
5. Export report CSV for handoff or audit.

Review is not the same as training annotation. Review confirms whether the system result is operationally useful; annotation creates exact YOLO boxes for model training.

## Annotation Handoff

After field media is collected and reviewed, create a local handoff structure:

```text
data/pilot_inbox/
  raw_images/
  raw_videos/
  metadata/
  prelabels/
  reviewed_labels/
```

For tower multiclass work, keep the class mapping aligned with:

```text
0 deformation
1 tower_corrosion
2 loose_bolt
3 bolt_rust
```

For the historical crack-only Stage B path, use class `0 crack` only.

## Prelabel And Review

If using Stage A ONNX for crack prelabels:

```bash
uv run python scripts/auto_label_onnx.py \
  --model models/stage_a_crack/best.onnx \
  --images data/pilot_inbox/raw_images \
  --output data/pilot_inbox/prelabels \
  --conf 0.30
```

Human reviewers should copy corrected labels into:

```text
data/pilot_inbox/reviewed_labels/
```

Rules:

- One `.txt` per image stem.
- YOLO normalized format: `<class_id> <x_center> <y_center> <width> <height>`.
- Empty label files are valid only after a reviewer confirms a negative image.
- Do not mix crack-only labels and tower multiclass labels in the same dataset output.

## Dataset Generation

For the tower multiclass prototype after reviewed labels exist:

```bash
uv run python scripts/prepare_multiclass_tower_dataset.py
uv run python scripts/prepare_multiclass_tower_dataset.py --validate-only
```

For the historical crack-only Stage B branch:

```bash
uv run python scripts/validate_pilot_inbox.py \
  --root data/pilot_inbox

uv run python scripts/prepare_stage_b_pilot_dataset.py \
  data/pilot_inbox/raw_images \
  --labels-dir data/pilot_inbox/reviewed_labels \
  --output data/stage_b_pilot_crack \
  --mark-reviewed
```

## Training Gate

Do not train or promote `prototype_v0_2` until all of these are true:

- representative field images exist
- labels have human or domain-expert review
- positive and negative examples are both present
- train/val/test split is generated and validated
- model metrics are recorded separately from system-link demo results

After training:

1. Evaluate per class.
2. Run inference smoke at normal thresholds.
3. Export ONNX only if detections are stable enough for demo.
4. Wire into API/frontend only after rollback to `stub` or previous ONNX is documented.

## Customer Handoff Package

For a customer-side pilot, prepare:

- deployment URL or screen-share plan
- device ID naming convention
- image/video upload path
- required metadata fields
- reviewer role and review status definitions
- export location and file naming rule
- next training decision date
