# Repository Guidelines

## Project Structure & Module Organization
- Python backend lives in `src/vision_analysis_pro/` with `core/` (inference, preprocessing), `web/api/` (FastAPI routes), and `edge_agent/` (data sources, reporters, config).  
- Frontend resides in `web/` (Vue 3 + Vite).  
- Shared resources: `config/` for YAML examples, `data/` and `models/` for datasets/artifacts, `scripts/` for training/export/benchmark helpers, `tests/` for Python test suites, `docs/` for plans and progress notes, `examples/` for edge-agent entry points.

## Current System Snapshot
- Main API endpoints: `GET /api/v1/health`, `GET /api/v1/health/live`, `GET /api/v1/health/ready`, `GET /api/v1/metrics`, `POST /api/v1/inference/image`, `POST /api/v1/report`.
- `POST /api/v1/report` is the cloud-side receiver for Edge Agent `ReportPayload.to_dict()` batches; it returns `202 Accepted` with batch and count metadata.
- Minimal observability is already present: request ID propagation, process-time response header, live/ready health checks, and Prometheus-style metrics.
- Current lightweight local backend baseline is `218 passed, 44 skipped`; skips are expected when legacy `models/best.onnx`, `data/images/*`, or optional local model artifacts are absent.
- Frontend baseline is `90 passed`; `npm run lint` is read-only, and `npm run lint:fix` performs automatic fixes.
- `ruff.toml` is the authoritative Ruff config; do not duplicate Ruff settings in `pyproject.toml`.

## Build, Test, and Development Commands
- Install deps: `uv sync` (base), `uv sync --extra dev`, `uv sync --extra onnx` (ONNX runtime).  
- Run API (dev): `uv run uvicorn vision_analysis_pro.web.api.main:app --reload` (OpenAPI at http://localhost:8000).  
- Python tests: `uv run pytest`.  
- Lint/format backend: `uv run ruff check .` and `uv run ruff format .`.  
- Frontend setup: `cd web && npm install`; dev server `npm run dev`; lint `npm run lint`; unit tests `npm run test -- --run`; build `npm run build`.

## Coding Style & Naming Conventions
- Python: follow Ruff defaults; prefer type hints; 4-space indent; keep modules cohesive by domain (core/web/edge_agent).  
- Frontend: TypeScript + Vue SFCs; keep components under `web/src/` with PascalCase filenames; use ESLint/Prettier settings from repo.  
- Config files use lower_snake_case keys; environment variables are UPPER_SNAKE_CASE.

## Testing Guidelines
- Python: Pytest under `tests/`; name files `test_*.py` and functions `test_*`. Aim for coverage on new paths and include edge-agent behaviors (sources/reporters).  
- Frontend: Vitest + Vue Test Utils; place tests next to components or in `web/tests/`; prefer descriptive `*.spec.ts`.  
- For new features, add regression tests for failure modes (invalid input, timeouts, missing files).

## Commit & Pull Request Guidelines
- Commit messages use Conventional Commits with scoped prefixes, e.g., `feat(core): add onnx cache`, `fix(api): handle empty upload`.  
- Keep commits focused and include tests or notes when they are omitted.  
- PRs should describe scope, include run commands/results (pytest, ruff, npm tests as relevant), and attach screenshots/GIFs for UI changes. Link issues or tasks when available.

## Security & Configuration Tips
- Avoid committing large model weights or private data; use `models/` and `data/` as git-ignored caches unless required artifacts are documented.  
- Prefer YAML configs in `config/` and environment variables for secrets; never hardcode credentials.  
- When benchmarking or exporting models, use `scripts/` to keep parameters reproducible and checked in as command examples.

## AI Collaboration Workflow

### Required Context Order
- Read `AGENTS.md` first, then `README.md`, then the target module and its related tests before proposing changes.
- For backend work, check `pyproject.toml`, `pytest.ini`, and `ruff.toml` so command, test, and lint assumptions stay correct.
- For frontend work, check `web/package.json` and the nearest component/store/test files before editing.

### Change Playbooks
- Backend API changes: inspect `src/vision_analysis_pro/web/api/`, shared models/config, and matching tests under `tests/`.
- Inference or preprocessing changes: inspect `src/vision_analysis_pro/core/` plus benchmark/export scripts if behavior or interfaces may shift.
- Edge Agent changes: inspect `src/vision_analysis_pro/edge_agent/`, config examples under `config/`, and reporter/source tests.
- Frontend changes: inspect `web/src/` plus the API contract consumed by the page or component you touch.

### Execution Rules for AI Agents
- Start with a short TODO list containing at most 5 steps.
- Prefer surgical edits over broad rewrites; reuse existing helpers and patterns before creating new abstractions.
- Validate only the relevant checks for the surface you changed:
  - Backend: `uv run ruff check .` and `uv run pytest`
  - Frontend: `cd web && npm run lint && npm run test -- --run && npm run build`
- If a task changes shared contracts between backend and frontend, validate both sides.
- If a task changes Edge Agent reporting or cloud API contracts, validate `tests/test_api_inference.py` and `tests/test_edge_agent.py`.
- Do not invent new architecture documents or planning files inside the repo unless explicitly requested.

### Completion Checklist
- Commands and file paths mentioned in the response must match the repository exactly.
- Any behavior change should be reflected in tests or in a directly related prompt/config update.
- Final summaries should state: what changed, why it changed, and how it was validated.
