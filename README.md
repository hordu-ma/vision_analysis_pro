# Vision Analysis Pro

工程基础设施图像识别智能运维系统 - 基于 YOLO 的无人机巡检解决方案

## 项目简介

针对输电塔等工程基础设施，使用人工智能图像识别技术（基于 YOLOv8/v11 框架），结合无人机巡检，识别地震、强风、雨雪等自然灾害导致的潜在安全隐患（裂缝、锈蚀、变形等），实现智能化运维。

### 核心特性

- 🚁 **无人机巡检**：支持图片/视频输入链路设计
- 🤖 **AI 检测**：YOLOv8 推理 + ONNX Runtime 高性能推理
- 🔧 **边缘计算**：完整的边缘 Agent（采集/推理/上报/离线缓存）
- 🌐 **云端管理**：FastAPI 后端 + Vue3 前端（上传 → 推理 → 展示）
- ⚡ **高性能**：ONNX 推理相比 YOLO 提升 7.25x（基准测试）

## 快速开始

### 环境要求

- Python >= 3.12，uv >= 0.9.8
- Node.js 20+（前端）
- 可选：CUDA >= 11.8（GPU 推理）

### 后端（API + 模型）

```bash
# 克隆并安装
git clone <repository_url>
cd vision_analysis_pro
uv sync                      # 基础依赖
uv sync --extra dev          # 开发/测试
uv sync --extra onnx         # ONNX Runtime 支持

# 运行 API（开发）
uv run uvicorn vision_analysis_pro.web.api.main:app --reload
# 打开 http://localhost:8000 查看 OpenAPI

# 运行测试
uv run pytest
```

### 前端（web/）

```bash
cd web
npm install

# 开发预览
npm run dev

# 质量检查与测试
npm run lint
npm run test -- --run

# 生产构建与预览
npm run build
npm run preview
```

### 边缘 Agent

```bash
# 使用配置文件启动
edge-agent -c config/edge_agent.example.yaml

# 使用命令行参数
python examples/run_edge_agent.py --source-type folder --source-path data/images/test

# 使用环境变量
EDGE_AGENT_SOURCE_TYPE=folder \
EDGE_AGENT_SOURCE_PATH=data/images/test \
EDGE_AGENT_INFERENCE_MODEL_PATH=models/best.onnx \
edge-agent
```

## 项目结构

```
vision_analysis_pro/
├── src/vision_analysis_pro/
│   ├── core/
│   │   ├── inference/          # 推理引擎（stub/yolo/onnx）
│   │   └── preprocessing/      # 预处理与可视化
│   ├── web/api/                # FastAPI 路由与依赖
│   └── edge_agent/             # 边缘 Agent 完整实现
│       ├── sources/            # 数据源（视频/图像/摄像头/RTSP）
│       ├── reporters/          # 上报器（HTTP + 离线缓存）
│       ├── agent.py            # Agent 主程序
│       ├── config.py           # 配置管理（YAML + ENV）
│       └── models.py           # 数据模型
├── scripts/                    # 训练/验证/评估/导出/基准测试脚本
├── config/                     # 配置文件示例
├── data/                       # YOLO 数据集与 data.yaml
├── models/                     # 训练/导出模型产物
├── web/                        # 前端（Vue3 + Vite + TS）
├── tests/                      # Python 测试（138 tests）
├── docs/                       # 计划与进度文档
├── pyproject.toml              # Python 依赖与工具链
└── ruff.toml                   # ruff 配置
```

## 开发指南

### AI 协作入口

- 仓库级协作规范：`AGENTS.md`
- GitHub Copilot 项目指令：`.github/copilot-instructions.md`
- 常用任务 prompt：
  - `.github/prompts/plan-visionAnalysisPro.prompt.md`
  - `.github/prompts/implement-change.prompt.md`
  - `.github/prompts/debug-failure.prompt.md`

### 代码规范

- Python：`uv run ruff check .`；格式化 `uv run ruff format .`
- 前端：`npm run lint`（ESLint + TypeScript）

### 测试

- 后端：`uv run pytest`（138 passed, 2 skipped）
- 前端：`npm run test -- --run`（28 passed）

### 提交规范

遵循 Conventional Commits：`feat(core): ...`、`fix(api): ...`、`docs(web): ...`

## 技术栈

### Python 核心

- **AI 框架**：Ultralytics YOLO (PyTorch)
- **推理引擎**：ONNX Runtime（7.25x 加速）
- **图像处理**：OpenCV, NumPy
- **Web 框架**：FastAPI, Uvicorn
- **测试**：Pytest

### 前端

- **框架**：TypeScript + Vue3 + Vite
- **组件库**：Element Plus
- **测试**：Vitest + Vue Test Utils

### 边缘 Agent

- **数据源**：视频文件、图像文件夹、摄像头、RTSP 流
- **推理引擎**：ONNX Runtime / YOLO
- **上报**：HTTP（指数退避重试）
- **离线缓存**：SQLite
- **配置**：YAML + 环境变量

## 路线图

### ✅ MVP 阶段（已完成）

- [x] YOLO 训练脚本与最小数据集
- [x] 推理引擎（Stub + YOLO + ONNX）
- [x] API 上传/可视化闭环
- [x] 前端 Web MVP（上传 → 推理 → 展示）
- [x] ONNX 导出与性能基准测试（7.25x 加速）
- [x] 前端 UX 优化（错误处理、上传进度、健康状态）

### ✅ 边缘 Agent 阶段（已完成）

- [x] 边缘 Agent 核心实现
  - [x] 多数据源支持（视频/图像/摄像头/RTSP）
  - [x] HTTP 上报（指数退避重试）
  - [x] SQLite 离线缓存
  - [x] YAML + ENV 配置
  - [x] 优雅关闭（信号处理）
- [x] 单元测试（38 tests）

### 📋 下一步计划

- [ ] CI/CD 与容器化（GitHub Actions + Dockerfile）
- [ ] 端到端集成测试
- [ ] 生产部署文档
- [ ] 可选：MQTT 上报器
- [ ] 可选：Rust/PyO3 性能优化

更多细节参见 `docs/progress.md` 与 `docs/development-plan.md`。

## 性能基准

| 引擎 | 平均延迟 (ms) | P95 (ms) | FPS | 加速比 |
|------|--------------|----------|-----|--------|
| YOLO | 33.36 | 34.78 | 29.97 | 1.0x |
| ONNX | 4.60 | 5.38 | 217.24 | **7.25x** |

*测试环境：Apple M4, 640x640 图像, 30 次迭代*

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[MIT License](LICENSE)

## 联系方式

- 作者：Liguo Ma
- 邮箱：maliguo@outlook.com
