# Implement a Change in Vision Analysis Pro

任务：

{{task}}

请按以下流程执行：

## 1. 先建立上下文
- 阅读 `AGENTS.md`
- 阅读与任务直接相关的实现文件
- 阅读对应测试、配置和命令入口
- 给出一个不超过 5 步的 TODO list
- 若任务涉及边缘上报，必须同时查看 `src/vision_analysis_pro/web/api/routers/`、`src/vision_analysis_pro/edge_agent/models.py`、`src/vision_analysis_pro/edge_agent/config.py` 和相关测试。

## 2. 实施要求
- 复用现有模式，不要平行新建无关抽象
- 修改要尽量局部，但必须完整解决问题
- 如果接口变化会影响前后端或边缘 Agent，需要同时更新被影响的一侧
- 当前云端已提供 `POST /api/v1/report` 接收 Edge Agent 批量上报；修改该契约时必须同步 schema、配置示例、README/docs 和测试。
- 前端 `npm run lint` 是只读检查；需要自动修复时才使用 `npm run lint:fix`。
- 不要声称已经跑过命令，除非你真的执行了

## 3. 输出结构
### Context Map
| File | Role | Action |
|------|------|--------|

### TODO
1. ...

### Implementation Notes
- 关键变更点
- 为什么这么改

### Validation
- 列出已执行的检查命令
- 如果未执行，明确说明原因

## 4. 质量标准
- 后端改动优先补 `tests/` 中的回归覆盖
- 前端改动优先补相邻 `*.spec.ts`
- 配置/文档/Prompt 改动必须与仓库实际命令和路径一致
- 当前轻量环境下 `models/best.onnx` 与 `data/images/*` 缺失导致的 skipped 属于预期；不要把这类 skipped 当作失败修复。
