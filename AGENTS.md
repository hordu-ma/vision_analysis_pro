# Repository Guidelines

## Project Structure & Module Organization
- Python backend lives in `src/vision_analysis_pro/` with `core/` (inference, preprocessing), `web/api/` (FastAPI routes), and `edge_agent/` (data sources, reporters, config).  
- Frontend resides in `web/` (Vue 3 + Vite).  
- Shared resources: `config/` for YAML examples, `data/` and `models/` for datasets/artifacts, `scripts/` for training/export/benchmark helpers, `tests/` for Python test suites, `docs/` for plans and progress notes, `examples/` for edge-agent entry points.

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
