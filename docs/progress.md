# 开发进度与运行指南

面向当前阶段（MVP 打通）的开发说明，涵盖环境、配置、运行、测试与目录要点。

---

## 📆 最新进度（2025-12-17）

### Day 1 完成：对齐契约 ✅

**完成时间**：2025-12-17

**目标达成**：
- ✅ 明确 `DetectionBox` 坐标系与字段定义
- ✅ 定义统一错误响应结构 `ErrorResponse`
- ✅ 更新 API schemas 并在 OpenAPI 中呈现完整示例

**关键决策与契约**：

1. **检测结果 schema（DetectionBox）**：
   - **bbox 坐标系**：像素坐标，格式为 `[x1, y1, x2, y2]`（左上角与右下角坐标）
   - **label**：字符串类型，对应类目名称（如 "crack", "rust" 等）
   - **confidence**：浮点数 [0.0, 1.0]，表示置信度

2. **错误响应结构（ErrorResponse）**：
   - **code**：错误码（如 "MODEL_NOT_LOADED"）
   - **message**：错误消息（用户友好）
   - **detail**：详细错误信息（可选，用于调试）

3. **API 响应示例**：
   ```json
   {
     "filename": "test_image.jpg",
     "detections": [
       {
         "label": "crack",
         "confidence": 0.95,
         "bbox": [100.0, 150.0, 300.0, 400.0]
       }
     ],
     "metadata": {
       "inference_time_ms": 45.2,
       "model_version": "v1.0"
     }
   }
   ```

**代码变更**：
- 更新 `src/vision_analysis_pro/web/api/schemas.py`：
  - 补充完整的字段说明与示例
  - 添加 `ErrorResponse` schema
  - 将 `box` 字段统一为 `bbox`（列表格式）
- 更新 `src/vision_analysis_pro/web/api/routers/inference.py`：
  - 适配 `bbox` 字段（兼容 box/bbox 两种 key）
  - 修复函数参数顺序（Depends 参数前置）
- 更新 `src/vision_analysis_pro/web/api/main.py`：
  - 在 FastAPI app 中注册全局错误响应示例

**DoD 验收**：
- ✅ OpenAPI 文档（访问 `/docs`）可查看完整的请求/响应示例
- ✅ 代码无语法错误（`ruff`/`pytest` 可运行）
- ✅ 契约决策已记录到本文档

**下一步（Day 2）**：
- 实现推理 stub 引擎（不依赖真实模型也能返回固定检测结果）
- 编写 stub 的单元测试

---

### Day 2 完成：Stub 推理引擎打通 ✅

**完成时间**：2025-12-17

**目标达成**：
- ✅ 实现 StubInferenceEngine（支持 normal/empty/error 三种模式）
- ✅ 编写完整单元测试（6 个测试用例全部通过）
- ✅ 更新 API 测试使用真实 stub 引擎
- ✅ 无需真实模型即可演示 API 推理流程

**关键实现**：

1. **StubInferenceEngine 三种模式**：
   - **normal**（默认）：返回固定的 3 个检测结果（crack 0.95, rust 0.88, deformation 0.72）
   - **empty**：返回空列表（模拟未检测到目标）
   - **error**：抛出 RuntimeError（模拟推理失败场景）

2. **接口符合规范**：
   - `warmup()`: 无操作（stub 不需要预热）
   - `predict()`: 返回符合 Day 1 契约的检测结果
   - 支持 `conf` 置信度阈值过滤
   - 不依赖 `model_path` 参数

3. **测试覆盖**：
   ```
   10 passed in 0.60s
   - test_health_endpoint: API 健康检查
   - test_inference_endpoint_returns_detections: 推理返回检测结果
   - test_inference_endpoint_empty_file: 空文件错误处理
   - test_stub_normal_mode: 正常模式返回 3 个检测框
   - test_stub_empty_mode: 空模式返回 0 个检测框
   - test_stub_confidence_filtering: 置信度阈值过滤
   - test_stub_error_mode: 错误模式抛出异常
   - test_stub_warmup: warmup 为空操作
   - test_stub_model_path_optional: 无需模型路径
   - test_inference_engine_placeholder: 基础推理测试
   ```

**代码变更**：
- 新增 `src/vision_analysis_pro/core/inference/stub_engine.py`：
  - 实现 `StubInferenceEngine` 类（继承 `BaseInferenceEngine`）
  - 支持通过 `mode` 参数切换行为（normal/empty/error）
  - 固定返回格式：`{"label": str, "confidence": float, "bbox": [x1,y1,x2,y2]}`
- 新增 `tests/test_stub_engine.py`：
  - 6 个测试用例覆盖所有模式与边界条件
  - 测试置信度过滤逻辑
- 更新 `tests/test_api_inference.py`：
  - 使用真实 `StubInferenceEngine` 替代 Mock
  - 新增空文件上传错误场景测试
- 环境修复：
  - 添加 `httpx` 到开发依赖（API 测试必需）

**DoD 验收**：
- ✅ StubInferenceEngine 有单元测试且全部通过
- ✅ API 可在无真实模型情况下演示推理流程
- ✅ 返回结果符合 Day 1 定义的 bbox 格式
- ✅ 代码无语法错误（ruff 检查通过）

**下一步（Day 3）**：
- 实现 API 上传闭环（文件校验、错误响应、异步处理）
- 处理非法文件格式与大小限制

---

### Day 3 完成：API 上传闭环 ✅

**完成时间**：2025-12-17

**目标达成**：
- ✅ 实现完整的文件上传校验（空文件、大小限制、格式检查）
- ✅ 统一异常处理机制（HTTPException 和通用异常）
- ✅ 所有错误响应符合 ErrorResponse 契约
- ✅ 编写完整的 API 集成测试（6 个测试用例）

**关键实现**：

1. **文件校验规则**：
   - **空文件检查**：`len(file_bytes) == 0` → 400 EMPTY_FILE
   - **大小限制**：最大 10MB → 400 FILE_TOO_LARGE
   - **格式校验**：仅允许 image/jpeg, image/png, image/jpg, image/webp → 400 INVALID_FORMAT

2. **统一异常处理**：
   - `http_exception_handler`: 处理 HTTPException，支持字典格式的 detail（包含 code/message/detail）
   - `general_exception_handler`: 捕获所有未处理异常，返回 500 INTERNAL_ERROR
   - 推理失败抛出 500 INFERENCE_ERROR（RuntimeError → HTTPException）

3. **错误码定义**：
   ```
   - EMPTY_FILE: 上传的文件为空
   - FILE_TOO_LARGE: 文件大小超过限制（10MB）
   - INVALID_FORMAT: 不支持的文件格式
   - INFERENCE_ERROR: 推理失败（引擎抛出异常）
   - INTERNAL_ERROR: 服务器内部错误（兜底）
   ```

4. **测试覆盖**：
   ```
   13 passed in 0.39s
   - test_health_endpoint: 健康检查
   - test_inference_endpoint_returns_detections: 正常推理返回结果
   - test_inference_endpoint_empty_file: 空文件返回 400 EMPTY_FILE
   - test_inference_endpoint_file_too_large: 超大文件返回 400 FILE_TOO_LARGE
   - test_inference_endpoint_invalid_format: PDF 文件返回 400 INVALID_FORMAT
   - test_inference_endpoint_error_mode: 推理失败返回 500 INFERENCE_ERROR
   + 6 个 stub 引擎单元测试
   + 1 个基础推理测试
   ```

**代码变更**：
- 更新 `src/vision_analysis_pro/web/api/routers/inference.py`：
  - 添加文件校验常量（MAX_FILE_SIZE, ALLOWED_MIME_TYPES）
  - 实现三层校验逻辑（空文件、大小、格式）
  - 所有错误返回标准 ErrorResponse 格式（dict with code/message/detail）
  - 捕获 RuntimeError 转换为 INFERENCE_ERROR
- 更新 `src/vision_analysis_pro/web/api/main.py`：
  - 添加全局异常处理器（http_exception_handler, general_exception_handler）
  - 支持字典格式的 detail 直接返回
  - 兜底异常统一返回 INTERNAL_ERROR
- 更新 `tests/test_api_inference.py`：
  - 新增 4 个错误场景测试（空文件、超大文件、非法格式、推理失败）
  - 验证所有错误响应包含 code/message 字段
- 更新 `src/vision_analysis_pro/core/inference/stub_engine.py`：
  - error 模式改为在 predict 时抛出（而非 __init__）
  - 错误消息改为"模拟：推理失败"
- 更新 `tests/test_stub_engine.py`：
  - 修复 error 模式测试（调用 predict 而非初始化）

**DoD 验收**：
- ✅ API 集成测试覆盖健康检查与上传推理（基于 stub）
- ✅ 文件校验完整（空文件、过大、非法格式）
- ✅ 统一错误响应（所有错误返回 ErrorResponse 格式）
- ✅ 代码无语法错误（ruff 检查通过）
- ✅ 所有测试通过（13/13 passed）

**下一步（Day 4）**：
- 实现可视化最小能力（绘制 bbox 工具函数）
- API 可选返回可视化结果或提供 debug 输出

---

### Day 4 完成：可视化最小能力 ✅

**完成时间**：2025-12-17

**目标达成**：
- ✅ 实现 bbox 绘制工具函数（输入原图 + 检测结果 → 输出带框图）
- ✅ API 支持可选可视化输出（visualize 参数）
- ✅ 可视化结果通过 base64 Data URI 返回
- ✅ 编写完整测试（6 个工具测试 + 2 个 API 测试）

**关键实现**：

1. **绘制工具函数 `draw_detections`**：
   - **输入**：图像 bytes + 检测结果列表（label/confidence/bbox）
   - **输出**：带框图的 bytes（JPEG 格式）
   - **绘制内容**：
     - 绿色矩形框（可自定义颜色和粗细）
     - 标签文本："label: confidence"（白色文本 + 黑色半透明背景）
   - **支持**：多个检测框、空检测结果、浮点数坐标自动转整数

2. **API 可视化支持**：
   - 新增查询参数 `visualize`（bool，默认 false）
   - 当 `visualize=true` 时：
     - 调用 `draw_detections` 生成带框图
     - 转换为 base64 编码
     - 返回 Data URI 格式：`data:image/jpeg;base64,{base64_data}`
   - 可视化失败不影响推理结果返回

3. **Schema 扩展**：
   ```python
   class InferenceResponse(BaseModel):
       filename: str
       detections: list[DetectionBox]
       metadata: dict[str, Any]
       visualization: str | None  # 新增字段
   ```

4. **测试覆盖**：
   ```
   21 passed in 0.47s
   可视化工具测试（6 个）：
   - test_draw_single_detection: 绘制单个检测框
   - test_draw_multiple_detections: 绘制多个检测框
   - test_draw_empty_detections: 空检测结果返回原图
   - test_invalid_image_bytes: 无效图像抛出 ValueError
   - test_custom_color_and_thickness: 自定义绘制参数
   - test_bbox_with_float_coordinates: 浮点数坐标转整数
   
   API 可视化测试（2 个）：
   - test_inference_endpoint_with_visualization: visualize=true 返回 base64
   - test_inference_endpoint_without_visualization: 默认不返回可视化
   ```

**代码变更**：
- 新增 `src/vision_analysis_pro/core/preprocessing/visualization.py`：
  - 实现 `draw_detections` 函数（使用 OpenCV cv2.rectangle + cv2.putText）
  - 支持自定义颜色、线条粗细、字体大小
  - 异常处理（图像解码失败、编码失败）
- 更新 `src/vision_analysis_pro/web/api/schemas.py`：
  - InferenceResponse 添加 `visualization` 字段（可选）
- 更新 `src/vision_analysis_pro/web/api/routers/inference.py`：
  - 导入 `draw_detections` 和 `base64`
  - 添加 `visualize` 查询参数
  - 可视化逻辑：检测结果 → 字典 → draw_detections → base64 → Data URI
  - 异常捕获（可视化失败不影响主流程）
- 新增 `tests/test_visualization.py`：
  - 6 个单元测试覆盖各种场景
  - `_create_test_image` 辅助函数生成测试图像
- 更新 `tests/test_api_inference.py`：
  - 添加 `_create_test_image` 函数（使用真实图像）
  - 新增带可视化和不带可视化的 API 测试
  - 验证 base64 解码和图像有效性

**DoD 验收**：
- ✅ 同一检测结果下，JSON 与可视化一致（bbox 位置、标签、置信度）
- ✅ 可通过 API 稳定复现输出带框图（visualize=true）
- ✅ 可视化图像可以正常解码（base64 → bytes → cv2.imdecode）
- ✅ 代码无语法错误（ruff 检查通过）
- ✅ 所有测试通过（21/21 passed）

**下一步（Day 5）**：
- 端到端 Demo Day：编写 demo 步骤文档
- 补齐关键错误路径（模型缺失、依赖缺失）的返回行为
- 在干净环境复现 demo（至少本机新 venv）

---

## 环境与依赖
- Python 3.12（仓库含 `.python-version`）
- 推荐使用 `uv`：
  - 安装基础依赖：`uv sync`
  - 安装开发依赖：`uv sync --extra dev`
  - 如需 ONNX/TensorRT：`uv sync --extra onnx`

## 配置
- 参考 `.env.example`，常用项：
  - `MODEL_PATH`：模型路径，默认 `models/best.pt`
  - `CONFIDENCE_THRESHOLD` / `IOU_THRESHOLD`
  - `API_HOST` / `API_PORT`
- 运行时通过 `vision_analysis_pro.settings.Settings` 加载（pydantic-settings），支持 `.env`。

## 运行
- 启动 API（开发模式）：
  ```bash
  uv run uvicorn vision_analysis_pro.web.api.main:app --reload
  ```
- 核心路由：
  - `GET /api/v1/health`：健康检查（返回版本与模型加载状态）
  - `POST /api/v1/inference/image`：图片推理上传接口（当前返回占位检测结果结构）

## 测试
- 先安装开发依赖：`uv sync --extra dev`
- 运行：`uv run pytest -q`
- API 测试说明：`tests/test_api_inference.py` 使用依赖覆盖：
  - 覆盖 `get_settings` 提供假模型路径
  - 覆盖 `get_inference_engine` 使用 stub 引擎返回固定检测结果

## 目录与近期变更
- 配置层：`src/vision_analysis_pro/settings.py`
- API 依赖：`src/vision_analysis_pro/web/api/deps.py`（缓存推理引擎，缺模型/依赖时返回 503）
- API 模型：`src/vision_analysis_pro/web/api/schemas.py`
- API 路由：`src/vision_analysis_pro/web/api/routers/inference.py`（上传→推理→结构化返回）
- 健康检查：`src/vision_analysis_pro/web/api/main.py`（返回版本与模型加载状态）

## 已完成功能（本迭代）
- 建立配置读取与依赖注入（Settings + 缓存推理引擎）
- 健康检查接口加强并注册路由
- 推理上传接口雏形（带检测结果结构化返回）
- API 层测试用例（依赖覆盖、健康检查与推理路径）

## 下一步建议
1. 接入真实 YOLO 结果解析：将 `ultralytics` 输出转为 `DetectionBox` 列表。
2. 增强推理预处理：支持 ndarray/path 输入、自动尺寸/格式校验与异常返回。
3. 错误路径测试：模型缺失、未安装 `ultralytics`、空文件上传等。
4. 性能与监控：为推理与上传请求添加耗时日志、基础 metrics 钩子。


---

## 📋 开发日志 (2025-12-07)

# 开发日志 - 2025-12-07

## 📅 基本信息

- **日期**：2025年12月7日
- **开发阶段**：MVP 阶段 - 项目初始化
- **工作时长**：约 2 小时

---

## ✅ 今日完成工作

### 1. 项目规划与技术调研

**调研内容**：
- 调研了主流 YOLO 框架（YOLOv8/v9/v10/v11）及其应用场景
- 分析了 Ultralytics、PaddleDetection、MMDetection 等开源项目
- 确定了技术栈：Python + YOLOv8 + FastAPI + Vue3
- 制定了分阶段 Rust 集成策略（PyO3 扩展 + 独立边缘 Agent）

**输出文档**：
- `.github/prompts/plan-visionAnalysisPro.prompt.md` - 详细的项目开发计划

**关键决策**：
- MVP 阶段使用纯 Python 实现，快速验证功能
- 后续阶段引入 Rust 优化边缘推理性能
- 采用混合模式：云端 Python + 边缘 Rust

---

### 2. 项目结构搭建

**使用工具**：
- `uv` - Python 项目管理工具
- Git - 版本控制

**创建的目录结构**：
```
vision_analysis_pro/
├── src/vision_analysis_pro/
│   ├── core/               # 核心模块
│   │   ├── inference/      # 推理引擎（基类 + Python实现）
│   │   └── preprocessing/  # 图像预处理
│   ├── edge_agent/         # 边缘 Agent
│   └── web/api/            # FastAPI 后端
├── tests/                  # 测试模块
├── docs/                   # 文档目录
├── models/                 # 模型文件目录
└── data/                   # 数据集目录
```

**核心代码文件**：
- `core/inference/base.py` - 推理引擎抽象基类
- `core/inference/python_engine.py` - 基于 Ultralytics YOLO 的实现
- `core/preprocessing/transforms.py` - 图像预处理工具
- `web/api/main.py` - FastAPI 应用入口
- `edge_agent/agent.py` - 边缘 Agent 骨架

---

### 3. 依赖配置与环境搭建

**pyproject.toml 配置**：
- **核心依赖**：
  - `ultralytics>=8.0.0` - YOLO 框架
  - `opencv-python>=4.8.0` - 图像处理
  - `fastapi>=0.100.0` - Web 框架
  - `numpy>=1.24.0` - 数值计算

- **可选依赖**：
  - `onnx` - ONNX 格式支持（macOS 安装 onnxruntime-gpu）

- **开发依赖**：
  - `pytest>=7.4.0` - 测试框架
  - `pytest-cov>=4.1.0` - 测试覆盖率
  - `ruff>=0.1.0` - 代码检查和格式化

**移除的依赖**：
- ❌ `mypy` - MVP 阶段简化配置，暂不引入类型检查
- ❌ `tensorrt` - macOS 不支持，生产环境在 Linux 上部署
- ❌ `rust-acceleration` - 目录尚未创建，后续引入

**环境验证**：
```bash
✅ uv sync 成功安装 54 个依赖包
✅ 项目导入测试通过
```

---

### 4. 配置文件创建

**代码规范**：
- `ruff.toml` - 代码检查规则（E, W, F, I, B, C4, UP）
- `pytest.ini` - 测试配置
- `.env.example` - 环境变量模板

**Git 配置**：
- `.gitignore` - 忽略规则（虚拟环境、模型文件、数据集等）

**文档**：
- `README.md` - 项目说明、快速开始、技术栈、路线图
- `docs/README.md` - 文档索引

---

### 5. Git 仓库管理

**完成的提交**：

**首次提交** (commit: `d6a6cb6`):
```
feat: 初始化项目结构

- 使用 uv 搭建 Python 项目框架
- 配置核心模块：inference, preprocessing, edge_agent, web API
- 集成 YOLOv8 推理引擎和 FastAPI
- 添加 ruff 代码检查和 pytest 测试框架
- 创建项目文档和开发配置
```

**第二次提交** (commit: `be60342`):
```
refactor: 优化项目依赖配置

- 移除 mypy 类型检查（MVP 阶段简化配置）
- 移除 tensorrt 依赖（macOS 不支持）
- 移除 rust-acceleration 可选依赖（目录尚未创建）
- 生成 uv.lock 锁定依赖版本
- 成功安装核心依赖：ultralytics, fastapi, opencv-python
```

**远程仓库**：
- GitHub: `hordu-ma/vision_analysis_pro`
- 分支: `master`

---

## 📊 当前项目状态

### 已完成 ✅

- [x] 项目规划与技术调研
- [x] 项目结构搭建（uv 管理）
- [x] 核心模块骨架代码
- [x] 依赖配置与环境验证
- [x] Git 版本控制初始化
- [x] 基础文档编写

### 进行中 🚧

- [ ] YOLOv8 模型训练 pipeline
- [ ] Python 推理引擎完整实现
- [ ] FastAPI 接口开发

### 未开始 📋

- [ ] 数据集准备与标注
- [ ] Web 前端界面
- [ ] 边缘 Agent 实现
- [ ] 单元测试编写

---

## 🎯 下一步计划

### 短期计划（本周）

#### 1. 数据准备（优先级：高）
- [ ] 收集基础设施图像样本（输电塔、桥梁等）
- [ ] 定义检测类别：
  - `crack` - 裂缝
  - `rust` - 锈蚀
  - `deformation` - 变形
  - `loose_bolt` - 螺栓松动
  - `cable_damage` - 电缆损伤
- [ ] 使用 Label Studio 进行数据标注
- [ ] 转换为 COCO/YOLO 格式

#### 2. 模型训练（优先级：高）
- [ ] 创建 `data.yaml` 配置文件
- [ ] 编写训练脚本（基于 Ultralytics YOLO）
- [ ] 训练 baseline 模型（YOLOv8n）
- [ ] 评估模型精度（mAP, precision, recall）
- [ ] 导出 ONNX 格式模型

#### 3. 推理引擎完善（优先级：中）
- [ ] 完善 `PythonInferenceEngine` 实现
- [ ] 添加批量推理支持
- [ ] 实现结果可视化（绘制检测框）
- [ ] 编写单元测试

#### 4. API 接口开发（优先级：中）
- [ ] 实现 `/api/v1/inference/image` 接口
- [ ] 添加文件上传验证
- [ ] 返回 JSON 格式检测结果
- [ ] 集成 Swagger 文档

---

### 中期计划（2-4 周）

#### 1. Web 前端开发
- [ ] 初始化 Vue3 + TypeScript 项目
- [ ] 实现图像上传组件
- [ ] 结果可视化（Canvas 绘制检测框）
- [ ] 模型管理界面

#### 2. 边缘 Agent 开发
- [ ] 实现视频流采集（OpenCV）
- [ ] 集成推理引擎
- [ ] 结果上报云端（HTTP/MQTT）
- [ ] 本地存储与同步

#### 3. 优化与测试
- [ ] ONNX Runtime 集成
- [ ] 推理性能优化
- [ ] 集成测试
- [ ] 代码覆盖率 > 80%

---

### 长期计划（1-3 个月）

#### 1. Rust 集成
- [ ] 创建 `rust_extensions/` 目录
- [ ] 使用 PyO3 + Maturin 构建图像预处理加速模块
- [ ] 性能对比测试（Python vs Rust）

#### 2. 生产部署
- [ ] 编写 Dockerfile
- [ ] 配置 CI/CD (GitHub Actions)
- [ ] 边缘设备部署指南（Jetson/NUC）
- [ ] 监控与日志系统

#### 3. 功能扩展
- [ ] 目标跟踪（BoT-SORT/ByteTrack）
- [ ] 小目标检测优化
- [ ] 模型自动更新机制
- [ ] 多设备管理

---

## 🐛 遇到的问题与解决方案

### 问题 1: TensorRT 依赖安装失败
**现象**：`uv sync` 报错 "TensorRT currently only builds wheels for Linux and Windows"

**原因**：TensorRT 不支持 macOS

**解决方案**：
- 从 `pyproject.toml` 移除 `tensorrt` 可选依赖
- 生产环境在 Linux 服务器上部署时再引入

---

### 问题 2: Rust 扩展依赖引用失败
**现象**：`uv sync` 报错 "Distribution not found at: file:///rust_extensions"

**原因**：`rust_extensions/` 目录尚未创建

**解决方案**：
- 暂时移除 `rust-acceleration` 可选依赖
- 后续阶段创建 Rust 扩展时再添加

---

### 问题 3: 虚拟环境误创建
**现象**：运行 `uv venv list` 时创建了名为 `list` 的虚拟环境

**原因**：uv 将 `list` 参数误解析为虚拟环境名称

**解决方案**：
- 使用 `rm -rf list` 删除错误创建的目录
- 正确的命令应该查看 uv 文档

---

## 💡 技术亮点与经验总结

### 1. 使用 uv 管理 Python 项目
- ✅ 比 pip 更快的依赖解析和安装速度
- ✅ 自动管理虚拟环境（`.venv`）
- ✅ `uv.lock` 锁定依赖版本，确保环境一致性
- ✅ 支持可选依赖分组（`onnx`, `dev` 等）

### 2. 项目结构设计
- ✅ 模块化设计：`core`, `edge_agent`, `web` 职责清晰
- ✅ 抽象基类 `InferenceEngine` 支持多种推理后端
- ✅ 预留 Rust 集成接口，便于后续优化

### 3. 开发流程规范
- ✅ Conventional Commits 提交规范
- ✅ Ruff 自动化代码检查
- ✅ Pytest 测试框架
- ✅ 完善的 `.gitignore` 避免敏感信息泄露

---

## 📚 参考资源

### 技术文档
- [Ultralytics YOLO 官方文档](https://docs.ultralytics.com/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [uv 官方文档](https://github.com/astral-sh/uv)

### 参考项目
- [ultralytics/ultralytics](https://github.com/ultralytics/ultralytics) - YOLO 官方实现
- [PaddlePaddle/PaddleDetection](https://github.com/PaddlePaddle/PaddleDetection) - 小目标检测优化参考
- [open-mmlab/mmdetection](https://github.com/open-mmlab/mmdetection) - 模块化架构参考

---

## 📈 项目统计

- **代码行数**：~300 行（包含注释）
- **文件数量**：20+ 个
- **依赖包数量**：54 个
- **Git 提交**：2 次
- **测试覆盖率**：0%（待开发）

---

**下次开发日期**：2025-12-08  
**计划工作**：数据集准备与模型训练
