# Plan: 工程基础设施图像智能运维 MVP

基于 YOLOv8/v11 框架构建无人机巡检系统，实现输电塔等基础设施的安全隐患自动识别。采用 Python 训练+边缘推理架构，配合 TypeScript+Vue3 管理后台，优先实现核心检测功能，后续迭代优化性能和边缘部署。

## Steps

### 1. 项目初始化与环境搭建
创建 `vision_analysis_pro` 项目结构（`core/`, `edge_agent/`, `web/` 三大模块），配置 `pyproject.toml`(uv 管理)和 `package.json`，安装 `ultralytics`、`fastapi`、`vue3` 等核心依赖

### 2. 数据集准备与模型训练
搭建数据标注流程（推荐 Label Studio），准备基础设施隐患样本（裂缝/锈蚀/变形等类别），基于 [YOLOv8](https://github.com/ultralytics/ultralytics) 训练 baseline 模型并导出 ONNX/TensorRT 格式

### 3. 推理引擎开发
在 `core/inference/` 实现统一推理接口（支持 ONNX Runtime/TensorRT 后端），封装图像预处理、NMS 后处理和结果格式化逻辑，编写 `pytest` 单元测试

### 4. Web 管理后台开发
使用 Vue3+TypeScript 开发 `web/` 前端（图像上传、检测结果可视化、模型管理），FastAPI 后端提供 `/api/v1/inference` 和 `/api/v1/models` 等 RESTful 接口

### 5. 边缘 Agent 原型
在 `edge_agent/` 实现 Python 版本的边缘推理服务（读取视频流→调用推理引擎→结果上报），支持本地存储和云端同步，为后续 Rust 重写打基础

### 6. 集成测试与文档
端到端测试完整流程（上传图像→推理→结果展示），编写 `README.md`（部署指南、API 文档），配置 `ruff`/`biome` 静态检查通过

## Further Considerations

### 1. 模型选择策略
YOLOv8n（速度优先/边缘设备）vs YOLOv9c（精度优先/云端推理）vs YOLOv10（NMS-free/实时场景），需根据实际硬件和精度要求选择，建议先用 YOLOv8n 验证流程

### 2. 边缘部署优化时机
MVP 阶段可暂时使用 Python+ONNX Runtime，待核心功能稳定后再引入 Rust+TensorRT 优化（需评估 Jetson/NUC 等目标硬件）

### 3. 数据标注与小目标优化
如遇小目标检测精度问题，可参考 PaddleDetection 的切图训练策略，或调整训练超参（`imgsz=1280`, mosaic 增强等）

## Rust 集成策略（混合模式）

### 阶段性引入方案

#### 阶段 1：MVP（第 1-2 周）- 纯 Python
- **技术栈**：Python + ONNX Runtime + OpenCV
- **目标**：快速验证核心功能，完成端到端流程
- **依赖管理**：uv 管理所有 Python 依赖
- **不引入 Rust**：避免过早优化，保持开发速度

```toml
# pyproject.toml
dependencies = [
    "ultralytics>=8.0.0",
    "onnxruntime-gpu>=1.16.0",
    "opencv-python>=4.8.0",
    "fastapi>=0.100.0",
]
```

#### 阶段 2：优化（第 3-4 周）- PyO3 扩展
- **引入场景**：图像预处理加速（resize/normalize/padding）
- **技术方案**：PyO3 + Maturin 构建 Python 扩展模块
- **集成方式**：可选依赖，保持向后兼容

**项目结构**：
```
vision_analysis_pro/
├── pyproject.toml           # uv 管理主项目
├── core/                    # Python 核心模块
│   ├── inference/
│   │   ├── python_engine.py    # 纯 Python 实现
│   │   └── rust_engine.py      # Rust 加速版（可选）
│   └── preprocessing/
├── rust_extensions/         # Rust 扩展（可选）
│   ├── Cargo.toml
│   ├── pyproject.toml          # maturin 配置
│   └── src/
│       ├── lib.rs              # PyO3 绑定
│       └── preprocessing.rs    # 图像处理加速
└── edge_agent_rust/         # 独立 Rust Agent（后续）
```

**依赖配置**：
```toml
# pyproject.toml
[project.optional-dependencies]
rust-acceleration = [
    "vision-analysis-rust @ file:///rust_extensions"
]

[tool.uv]
dev-dependencies = [
    "maturin>=1.0.0",
]
```

**使用方式**：
```python
# core/inference/engine.py
try:
    from vision_analysis_rust import RustInferenceEngine
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

def create_engine(model_path: str, use_rust: bool = True):
    if use_rust and RUST_AVAILABLE:
        return RustInferenceEngine(model_path)
    return PythonInferenceEngine(model_path)
```

**构建命令**：
```bash
# 开发时编译安装
cd rust_extensions && maturin develop && cd ..

# 可选安装 Rust 加速
uv pip install -e ".[rust-acceleration]"
```

#### 阶段 3：生产部署（第 5+ 周）- 独立 Rust Agent
- **部署场景**：边缘设备（Jetson/Raspberry Pi）7×24 运行
- **技术方案**：独立 Rust 二进制，直接调用 ONNX Runtime
- **优势**：低内存占用、高稳定性、无 Python GIL 限制

**边缘 Agent 结构**：
```
edge_agent_rust/
├── Cargo.toml
├── src/
│   ├── main.rs
│   ├── capture.rs          # 视频采集
│   ├── inference.rs        # ONNX Runtime 推理
│   ├── uploader.rs         # 结果上报云端
│   └── config.rs
└── Dockerfile              # 交叉编译
```

**依赖配置**：
```toml
# edge_agent_rust/Cargo.toml
[dependencies]
ort = "1.16"                # ONNX Runtime
image = "0.24"              # 图像处理
tokio = { version = "1.0", features = ["full"] }
reqwest = { version = "0.11", features = ["json"] }
```

**部署流程**：
```bash
# 1. 交叉编译 ARM64
cd edge_agent_rust
cargo build --release --target aarch64-unknown-linux-gnu

# 2. Python 脚本自动部署
uv run python -m core.deployment.deploy_edge \
    --binary edge_agent_rust/target/release/edge-agent \
    --target jetson-01.local
```

### 开发工作流

```bash
# 1. 初始化项目（纯 Python）
uv sync

# 2. 开发 Rust 扩展（可选）
cd rust_extensions
maturin develop
cd ..

# 3. 运行测试
uv run pytest                                        # Python 测试
cargo test --manifest-path rust_extensions/Cargo.toml  # Rust 测试

# 4. 构建发布
uv build                                            # Python wheel
cd rust_extensions && maturin build --release      # Rust 扩展
cd edge_agent_rust && cargo build --release        # 边缘 Agent
```

### Rust 引入的核心场景总结

| 场景 | 时机 | 技术方案 | 优势 |
|------|------|---------|------|
| **图像预处理加速** | 第 3-4 周 | PyO3 + Maturin | 性能提升 5-10 倍，内存安全 |
| **边缘推理 Agent** | 第 5+ 周 | 独立 Rust 二进制 | 低资源占用，7×24 稳定运行 |
| **ONNX 推理优化** | 可选 | Rust ort crate | 零拷贝推理，降低延迟 |
