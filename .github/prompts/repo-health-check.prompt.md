# Vision Analysis Pro Repo Health Check

请对当前仓库做一次轻量健康检查，用于 Codex / GitHub Copilot CLI 开始工作前快速定向。

## Required Input

当前关注点：

{{focus}}

## Required Steps

1. 读取 `AGENTS.md`、`README.md` 和与 `{{focus}}` 直接相关的文件。
2. 检查当前 git 状态，区分已有改动与本次任务范围。
3. 列出真实代码入口、相关测试和配置文件，不要照搬过期路线图。
4. 给出最小验证命令；如果涉及 Edge Agent 上报，包含 `uv run pytest tests/test_api_inference.py tests/test_edge_agent.py`。
5. 标注当前轻量环境中的预期 skipped：`models/best.onnx` 与 `data/images/*` 缺失。

## Output

### Snapshot
- 当前功能状态
- 已知环境缺口

### Context Map
| File | Why it matters | Action |
|------|----------------|--------|

### Suggested Checks
- command

### Risks
- 只列与本次关注点直接相关的风险

## Constraints

- 不创建路线图，不提出泛化重构。
- 不把已实现的 `/api/v1/report`、live/ready、metrics 当作待实现能力。
- 不声称命令通过，除非已经实际执行。
