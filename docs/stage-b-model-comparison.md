# Stage B Model Comparison — v0.1

> 生成于 2026-04-21  
> 对应任务：HE-007 Stage B Model Comparison

## 摘要

在相同验证集（Stage A val，462 张图像）上比较 Stage A 和 Stage B 模型，
得出结论：**当前阶段保留 Stage A 作为部署模型**。

---

## 实验设置

### 数据说明

| 项目 | Stage A | Stage B |
|------|---------|---------|
| 数据来源 | HuggingFace `senthilsk/crack_detection_dataset`（公开） | Stage A 测试集（225 张，代理试点数据） |
| 标注方式 | 人工标注 YOLO 格式（ground truth） | Stage A ONNX 自动标注（conf=0.30，代替人工复核） |
| 训练集大小 | 2263 张 | 157 张 |
| 验证集大小 | 462 张（Stage A val） | 33 张（Stage B 内部 val） |
| 测试集大小 | 225 张（用于 Stage B 数据源） | 35 张 |

> **注意**：Stage B 使用 Stage A 测试集作为"试点数据"代理，属于同分布场景。
> 真实试点场景应使用来自巡检现场的自有图像，以验证跨域泛化能力。

### 自动标注统计

Stage A 测试集（225 张）经 ONNX 自动标注结果：

- 有检测框：194 张，共 199 个框
- 空标签（判为负样本）：31 张
- 使用阈值：conf=0.30，iou=0.45

### 训练配置

| 参数 | Stage A | Stage B |
|------|---------|---------|
| 基础模型 | yolov8n.pt | yolov8n.pt |
| 训练轮数 | 50（早停于 31） | 30（早停于 29） |
| imgsz | 640 | 640 |
| batch | 8 | 8 |
| 设备 | CUDA | CUDA |
| 输出目录 | `runs/stage_a_crack/baseline_v0_1/` | `runs/stage_b_pilot_crack/comparison_v0_1/` |

---

## 评估结果（Stage A val 集，462 张图像）

| 指标 | Stage A | Stage B | 差值 |
|------|---------|---------|------|
| mAP50 | **0.9661** | 0.8711 | −0.095 |
| mAP50-95 | **0.6320** | 0.3898 | −0.242 |
| Precision | **0.9434** | 0.8844 | −0.059 |
| Recall | **0.9203** | 0.8383 | −0.082 |

> 评估命令：
> ```bash
> uv run python scripts/evaluate.py \
>   --model runs/stage_a_crack/baseline_v0_1/weights/best.pt \
>   --data data/stage_a_crack/data.yaml --split val
>
> uv run python scripts/evaluate.py \
>   --model runs/stage_b_pilot_crack/comparison_v0_1/weights/best.pt \
>   --data data/stage_a_crack/data.yaml --split val
> ```

---

## 分析

### Stage B 性能下降的原因

1. **训练集规模差距**：Stage A 使用 2263 张训练图像，Stage B 仅 157 张（约 1/14）。
   数据量是 YOLO 性能的主要驱动因素。

2. **标注质量差异**：Stage B 使用 ONNX 模型自动标注（置信度 0.30），
   存在漏标（false negative）和误标（false positive）。
   Stage A 使用人工标注的 ground truth。

3. **同分布局限**：Stage B 数据来源于 Stage A 测试集（同一公开数据集），
   无法体现真实试点场景的域适应效果。

### 自动标注流程的验证意义

本次实验成功验证了以下技术链路：

- ONNX 推理 → YOLO 格式标注文件（`scripts/auto_label_onnx.py`）
- Stage B 数据集构建（`scripts/prepare_stage_b_pilot_dataset.py`）
- YOLO 训练与评估（`scripts/train.py` + `scripts/evaluate.py`）
- 两模型在同一 val 集上的对比框架

---

## 建议

**当前阶段：保留 Stage A 作为部署模型。**

Stage B 的改进路径（按优先级）：

1. **获取真实巡检图像**（最高优先级）
   - 提供来自目标场景的巡检视频或图片
   - 用 Stage A ONNX 预标注后人工复核（30 分钟/100 张）
   - 目标：≥ 200 张正样本，训练集 ≥ 150 张

2. **以 Stage A 最佳权重为起点微调**
   - 将 `--model` 换为 `runs/stage_a_crack/baseline_v0_1/weights/best.pt`
   - 在小数据集上微调比从 yolov8n.pt 重新训练效果好

3. **对比维度扩展**
   - 目前仅比较同分布 val 集
   - 有真实试点数据后，应在真实场景测试集上对比

---

## 复现命令

```bash
# 1. 自动标注
uv run python scripts/auto_label_onnx.py \
  --model models/stage_a_crack/best.onnx \
  --images data/stage_a_crack/images/test \
  --output /tmp/stage_b_auto_labels \
  --conf 0.30

# 2. 构建 Stage B 数据集
uv run python scripts/prepare_stage_b_pilot_dataset.py \
  data/stage_a_crack/images/test \
  --labels-dir /tmp/stage_b_auto_labels \
  --output data/stage_b_pilot_crack \
  --mark-reviewed

# 3. 训练 Stage B
uv run python scripts/train.py \
  --data data/stage_b_pilot_crack/data.yaml \
  --model yolov8n.pt \
  --epochs 30 --batch 8 --imgsz 640 --device 0 \
  --project runs/stage_b_pilot_crack --name comparison_v0_1 --exist-ok

# 4. 评估对比
uv run python scripts/evaluate.py \
  --model runs/stage_a_crack/baseline_v0_1/weights/best.pt \
  --data data/stage_a_crack/data.yaml --split val

uv run python scripts/evaluate.py \
  --model runs/stage_b_pilot_crack/comparison_v0_1/weights/best.pt \
  --data data/stage_a_crack/data.yaml --split val
```
