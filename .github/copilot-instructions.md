# Vision Analysis Pro Copilot Instructions

## Mission
- Help with a production-oriented AI vision system for infrastructure inspection.
- Optimize for correct, reviewable changes over speculative breadth.
- Keep user-facing explanations in Chinese unless the user explicitly asks otherwise.

## Read Before Editing
1. `AGENTS.md`
2. `README.md`
3. The target files to change
4. Related tests and config files for that surface

## Repository-Specific Working Rules
- Backend commands must use `uv run ...`; prefer existing scripts and entry points over ad-hoc commands.
- Frontend commands live under `web/`; do not assume root-level Node tooling.
- Reuse current structure:
  - `src/vision_analysis_pro/core/` for inference and preprocessing
  - `src/vision_analysis_pro/web/api/` for FastAPI
  - `src/vision_analysis_pro/edge_agent/` for data-source/reporting flows
  - `tests/` for Python regression coverage
  - `web/src/` for Vue components and client logic

## How to Approach Tasks
- First build a context map: target file, direct dependencies, related tests, existing patterns.
- Propose a short TODO list before editing.
- Prefer updating an existing prompt, config, helper, or test over creating parallel alternatives.
- If a prompt or instruction file is stale relative to the repository state, update it instead of working around it.

## Validation Rules
- Backend-only changes: run the minimal relevant backend checks.
- Frontend-only changes: run the minimal relevant frontend checks.
- Cross-cutting changes: validate both backend and frontend if interfaces or workflows change.
- Documentation-only or prompt-only changes do not require code tests, but must be checked for consistency with actual commands and paths.

## Avoid
- Do not write generic project plans that ignore the current repository state.
- Do not add dependencies, scripts, or directories unless they solve a concrete repository need.
- Do not claim a command passed unless it was actually run.
