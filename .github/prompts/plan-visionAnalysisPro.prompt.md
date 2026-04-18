# Plan Vision Analysis Pro Change

面向当前仓库状态制定实现计划，而不是重新规划一个从零开始的 MVP。

## Before You Plan
- 先读取 `AGENTS.md`、`README.md`，再读取目标模块和对应测试。
- 结合仓库现状规划：项目已经包含后端、前端、推理引擎、边缘 Agent，不要重复提出“初始化项目结构”这类过时步骤。
- 如果任务涉及前后端接口、边缘上报或推理配置，明确受影响的双边文件。
- 当前 API 已包含 `/api/v1/report`、live/ready 和 metrics；不要把这些能力当作未实现项。
- 当前轻量后端测试基线允许 `models/best.onnx` 和 `data/images/*` 缺失导致的 skipped。

## Input
请基于以下需求生成计划：

{{task}}

## Required Output

### 1. Problem Framing
- 当前问题是什么
- 为什么这个问题值得现在解决
- 涉及哪些模块

### 2. Context Map
| File | Why it matters | Expected action |
|------|----------------|-----------------|
| path | dependency / test / implementation | inspect / modify / verify |

### 3. Execution Plan
- 用不超过 5 步的 TODO 列出执行顺序
- 每步都要写明验证方式
- 若是多模块改动，优先写“接口/类型/配置”再写“实现”再写“测试”

### 4. Risks
- 现有行为可能被影响的点
- 如何避免误改

### 5. Validation
- 只列出与任务直接相关的检查命令
- 后端优先使用：
  - `uv run ruff check .`
  - `uv run pytest`
- 前端优先使用：
  - `cd web && npm run lint`
  - `cd web && npm run test -- --run`
  - `cd web && npm run build`
- Edge Agent 上报/API 契约优先使用：
  - `uv run pytest tests/test_api_inference.py tests/test_edge_agent.py`

## Constraints
- 不写空泛路线图，不写周计划，不写“后续可以考虑”的泛建议，除非它直接影响本次实现。
- 不虚构文件、脚本、目录或能力。
- 如果发现需求与仓库现状冲突，先指出冲突再给计划。
