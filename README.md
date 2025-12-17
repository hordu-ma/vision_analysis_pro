# Vision Analysis Pro

工程基础设施图像识别智能运维系统 - 基于 YOLO 的无人机巡检解决方案

## 项目简介

针对输电塔等工程基础设施，使用人工智能图像识别技术（基于 YOLOv8/v11 框架），结合无人机巡检，识别地震、强风、雨雪等自然灾害导致的潜在安全隐患（裂缝、锈蚀、变形等），实现智能化运维。

### 核心特性

- 🚁 **无人机巡检**：支持图片/视频输入链路设计
- 🤖 **AI 检测**：YOLOv8 推理（真实模型 + Stub 切换）
- 🔧 **边缘计算**：预留 Jetson/NUC 部署路径
- 🌐 **云端管理**：FastAPI 后端 + Vue3 前端（上传 → 推理 → 展示）
- ⚡ **高性能**：训练脚本、模型缓存，后续支持 ORT/TensorRT

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

## 项目结构

```
vision_analysis_pro/
├── src/vision_analysis_pro/
│   ├── core/
│   │   ├── inference/          # 推理引擎（stub/python/yolo）
│   │   └── preprocessing/      # 预处理与可视化
│   ├── web/api/                # FastAPI 路由与依赖
│   └── edge_agent/             # 边缘 Agent 原型
├── scripts/                    # 训练/验证/评估脚本
├── data/                       # YOLO 数据集与 data.yaml
├── models/                     # 训练/导出模型产物
├── web/                        # 前端（Vue3 + Vite + TS）
│   └── src/components|services # 组件与 API 客户端
├── tests/                      # Python 测试
├── docs/                       # 计划与进度文档
├── pyproject.toml              # Python 依赖与工具链
├── ruff.toml                   # ruff 配置
└── .env.example                # 环境变量示例
```

## 开发指南

### 代码规范

- Python：`uv run ruff check .`；格式化 `uv run ruff format .`
- 前端：`npm run lint`（ESLint + TypeScript）

### 测试

- 后端：`uv run pytest`
- 前端：`npm run test -- --run`

### 提交规范

遵循 Conventional Commits：`feat(core): ...`、`fix(api): ...`、`docs(web): ...`

## 技术栈

### Python 核心

- **AI 框架**：Ultralytics YOLO (PyTorch)
- **推理引擎**：ONNX Runtime, TensorRT (可选)
- **图像处理**：OpenCV, NumPy
- **Web 框架**：FastAPI, Uvicorn
- **测试**：Pytest

### Rust 扩展（可选）

- **推理绑定**：ort (ONNX Runtime)
- **Python 集成**：PyO3, Maturin
- **图像处理**：image, ndarray

### 前端（规划中）

- TypeScript + Vue3 + Vite
- 组件：Element Plus（按需引入规划中）
- 测试：Vitest + Vue Test Utils

## 路线图

### ✅ MVP 阶段（第 1-2 周）

- [x] YOLO 训练脚本与最小数据集（`scripts/train.py` + `data.yaml`）
- [x] 推理引擎（Stub + YOLO 切换）与 API 上传/可视化闭环
- [x] 前端 Web MVP（上传 → 推理 → 展示，vitest 通过）

### 🚧 优化阶段（第 3-4 周）

- [ ] 统一错误处理与用户体验优化（前端）
- [ ] ONNX/TensorRT 导出与性能基准
- [ ] 边缘 Agent Python 版本（采集/上报/缓存）

### 📋 生产阶段（第 5+ 周）

- [ ] Element Plus 按需、代码分割与生产构建
- [ ] CI/CD、容器化与监控
- [ ] Rust/PyO3 加速与边缘 Agent 重写

更多细节参见 `docs/progress.md` 与 `docs/development-plan.md`。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[MIT License](LICENSE)

## 联系方式

- 作者：Liguo Ma
- 邮箱：maliguo@outlook.com
