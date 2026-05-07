# Trial Hardware Bundle

Date: 2026-05-07

This document defines the recommended minimum hardware bundle for selling Vision Analysis Pro as a soft-hardware trial package. The goal is to standardize daily user experience, make pilot delivery repeatable, and provide procurement-control parameters without overcommitting to drone operations too early.

## Positioning

The minimum bundle should not start with a drone. The first commercial package should sell the inspection operations system plus a standardized edge kit:

```text
software system
+ edge AI compute box
+ rugged tablet or laptop
+ 4G/5G network device
+ portable power / UPS
+ storage and delivery accessories
```

This keeps the offer focused on:

- real-model inference route
- Edge Agent reporting
- offline cache and replay
- human review
- report export
- field data intake for later model improvement

Drone hardware should be an optional higher-tier package because it introduces pilot licensing, airspace coordination, insurance, batteries, maintenance, and safety responsibility.

## Recommended Package Tiers

| Tier | Hardware | Best fit |
|------|----------|----------|
| Standard Trial Kit | Edge AI box, rugged tablet/laptop, 4G/5G router, portable power, SSD, delivery case | Customer already has images, drones, or inspection teams |
| Field Collection Kit | Standard kit plus handheld camera, action camera, or fixed PoE camera | Ground inspection, early sample collection, low-risk pilots |
| UAV Inspection Kit | Standard kit plus enterprise UAV and zoom/thermal payload | Customer wants a full collection-to-report inspection package |

The current recommended sales package is **Standard Trial Kit**.

## Standard Trial Kit

| Module | Recommended configuration | Purpose |
|--------|---------------------------|---------|
| Edge AI compute box | NVIDIA Jetson Orin NX industrial computer, preferably 16GB memory | Run ONNX inference, Edge Agent, local cache, and field reporting |
| Operator terminal | Rugged tablet or lightweight laptop with stable browser, outdoor screen, and 4G/5G option | Upload images, inspect batches, review frames, export reports |
| Network device | Industrial 4G/5G router with LAN, Wi-Fi, VPN, and SIM support | Connect field kit to API/cloud or local server |
| Portable power | UPS or portable power station sized for the edge box and router for 2-4 hours | Keep field demo and temporary inspection running |
| Local storage | 1TB-2TB SSD / NVMe | Store images, video clips, report cache, exports, and handoff datasets |
| Delivery accessories | Waterproof or rugged case, labels, QR codes, spare cables, power adapters | Make delivery repeatable and easy to operate |

## Edge AI Box Specification

Use capability-based wording in proposals or procurement documents instead of locking to one brand:

- AI module: NVIDIA Jetson Orin NX or equivalent edge AI module.
- AI performance: not lower than 70 TOPS; 100 TOPS class preferred.
- Memory: not lower than 16GB.
- Storage: not lower than 1TB NVMe SSD.
- OS: Ubuntu/Linux; supports Docker, NVIDIA JetPack, ONNX Runtime, and Python runtime.
- Network: at least two Gigabit Ethernet ports; 4G/5G via built-in module or external industrial router.
- Camera/input interfaces: USB 3.0 and Ethernet; PoE camera input preferred when fixed cameras are in scope.
- Environment: industrial-grade thermal design; wide-temperature operation preferred.
- Reliability: supports local disk cache, offline operation, and replay after network recovery.
- Serviceability: supports remote SSH/VPN access, log export, and model file replacement.

Suggested implementation choices:

- Pilot/dev unit: Jetson Orin Nano or Orin NX developer/industrial kit when cost is the main constraint.
- Delivery unit: industrial Jetson Orin NX computer, preferably with rugged enclosure, wide-temperature design, and PoE/network expansion.
- Higher-spec unit: Jetson AGX Orin or newer high-end edge AI computer only when multiple camera streams, larger models, or long-term onsite deployment justify the cost.

## Operator Terminal

Minimum:

- Browser capable of running the Vue frontend.
- Wi-Fi and 4G/5G connectivity.
- Screen usable in field lighting.
- Enough battery for a half-day inspection workflow.

Recommended:

- Rugged Windows tablet or industrial Android tablet.
- Protective case and shoulder/hand strap.
- Preconfigured browser bookmark to the system URL.
- Device label and QR code for the operator guide.

## Network And Power

Network:

- Industrial 4G/5G router with SIM card.
- VPN or secure remote access option.
- LAN port for edge box.
- Wi-Fi AP for operator terminal.

Power:

- Portable power station or UPS.
- Target runtime: 2-4 hours for demo/pilot; longer if used as temporary field station.
- Include all power adapters, spare cables, and a startup checklist.

## Optional Camera Add-Ons

For early pilots, prefer simple cameras before drones:

- handheld high-resolution camera
- action camera
- fixed PoE camera
- customer-provided UAV imagery

This lets the customer start collecting field samples without creating UAV delivery risk.

## Optional UAV Kit

Only include UAV hardware as a higher-tier package.

Possible configuration:

- enterprise UAV
- zoom camera payload
- optional thermal payload
- spare batteries and charger
- data export workflow into Vision Analysis Pro
- flight and data handoff SOP

Procurement-control parameters:

- enterprise-grade flight platform
- optical zoom suitable for tower/detail inspection
- optional thermal imaging for hotspot or abnormal heating scenarios
- RTK positioning preferred
- support for structured media export
- support for safe flight operations under local policy

Do not make UAV hardware mandatory in the standard trial package.

## Procurement-Control Parameters

Use these as neutral parameters in proposals:

### Edge Compute

- Supports local AI inference with ONNX Runtime.
- Supports Dockerized application deployment.
- Supports offline result cache and network recovery replay.
- Supports at least 1TB local storage.
- Supports secure remote maintenance.
- Supports model file update and rollback.

### Field Operation

- Operator terminal can access the web UI.
- Network device supports field connectivity and local LAN.
- Portable power supports at least 2 hours of edge compute plus router operation.
- Hardware is delivered in a labeled protective case with startup checklist.

### Data Governance

- Raw media and labels remain locally stored unless explicitly exported.
- Report export supports CSV.
- Field media can be converted into reviewed training data after customer confirmation.

## Recommended Sales Wording

Use:

> The standard trial kit provides a consistent field-ready operating environment for image upload, edge reporting, human review, report export, and real-sample collection. It does not require the customer to change their existing UAV team on day one.

Avoid:

> The hardware bundle includes everything needed to complete autonomous UAV inspection and replace the customer's current inspection workflow.

## Integration With Current Software

Current software profile:

- Customer-facing demo: Stage A ONNX first, Stage A YOLO as fallback.
- Internal link check: `stub`.
- Multiclass tower model: experimental until real field data and reviewed labels are available.

Recommended deployment on the edge box:

```bash
INFERENCE_ENGINE=onnx \
ONNX_MODEL_PATH=models/stage_a_crack/best.onnx \
API_RELOAD=false \
uv run uvicorn vision_analysis_pro.web.api.main:app \
  --host 0.0.0.0 \
  --port 8000
```

Recommended Edge Agent report path:

```bash
uv run python examples/run_edge_agent.py \
  --device-id tower-edge-001 \
  --source-type folder \
  --source-path /path/to/field/images \
  --engine onnx \
  --model-path models/stage_a_crack/best.onnx \
  --report-url http://<api-host>:8000/api/v1/report
```

## Delivery Checklist

Before delivery:

- edge box boots and network is configured
- API starts in ONNX mode
- frontend is reachable from operator terminal
- Edge Agent can report one sample batch
- CSV export works
- local cache path exists
- rollback to `stub` is documented for internal troubleshooting
- delivery case contains cables, power adapters, and startup card

After delivery:

1. Collect customer field images or videos.
2. Review and label representative samples.
3. Generate the next training dataset.
4. Train `prototype_v0_2`.
5. Evaluate and decide whether to promote a multiclass model into ONNX deployment.
