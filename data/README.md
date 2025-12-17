# 数据集目录说明

本目录包含用于 YOLO 模型训练的标注数据集。

## 📁 目录结构

```
data/
├── images/               # 图像文件
│   ├── train/           # 训练集图像
│   ├── val/             # 验证集图像
│   └── test/            # 测试集图像
├── labels/              # 标注文件（YOLO 格式）
│   ├── train/           # 训练集标注
│   ├── val/             # 验证集标注
│   └── test/            # 测试集标注
├── samples/             # 样例图片（标注参考）
│   ├── good/            # 正例样例
│   ├── edge/            # 边界案例
│   ├── negative/        # 负例样例
│   └── README.md
├── data.yaml            # YOLO 数据集配置文件
└── README.md            # 本文件
```

## 🎯 数据集组织规则

### 1. 图像与标注对应关系

- 每张图像必须有对应的标注文件
- 文件名必须一致（仅扩展名不同）
- 示例：
  ```
  images/train/crack_001.jpg  →  labels/train/crack_001.txt
  images/val/rust_002.png     →  labels/val/rust_002.txt
  ```

### 2. YOLO 标注格式

每个标注文件（`.txt`）包含多行，每行格式：

```
<class_id> <center_x> <center_y> <width> <height>
```

- `class_id`: 类别 ID（0-4）
- `center_x, center_y`: 边界框中心点（归一化坐标，范围 [0, 1]）
- `width, height`: 边界框宽高（归一化坐标，范围 [0, 1]）

**示例**：
```
0 0.5 0.3 0.2 0.15    # crack: 中心 (0.5, 0.3), 宽高 (0.2, 0.15)
1 0.7 0.6 0.1 0.08    # rust: 中心 (0.7, 0.6), 宽高 (0.1, 0.08)
```

### 3. 类别定义

根据 `src/vision_analysis_pro/categories.py` 和 `docs/annotation_guidelines.md`：

| class_id | 类别名称 | 英文标签 | 描述 |
|----------|---------|---------|------|
| 0 | 裂缝 | crack | 结构表面的线性或网状裂纹 |
| 1 | 锈蚀 | rust | 金属构件表面的氧化锈蚀 |
| 2 | 变形 | deformation | 构件弯曲、扭曲等形变 |
| 3 | 剥落 | spalling | 混凝土保护层剥离脱落 |
| 4 | 腐蚀 | corrosion | 化学腐蚀导致的材料损坏 |

### 4. 数据集切分比例

推荐比例（可根据实际情况调整）：

- **训练集 (train)**: 70-80%
- **验证集 (val)**: 10-15%
- **测试集 (test)**: 10-15%

**切分原则**：
- 随机打乱后按比例切分
- 确保各类别在三个集合中分布均衡
- 同一场景/系列图片应在同一集合（避免数据泄露）

### 5. 图像要求

- **格式**: JPEG、PNG、WebP
- **分辨率**: 建议 ≥ 640x640
- **质量**: 清晰、光线均匀、无严重模糊或过曝
- **命名**: 使用有意义的名称（如 `bridge_crack_001.jpg`）

### 6. 标注质量要求

参考 `docs/annotation_guidelines.md`：

- bbox 紧贴目标边界，留白 < 5%
- bbox 面积 > 32x32 像素
- IoU ≥ 0.70（合格），≥ 0.85（优秀）
- 遮挡 > 50% 的目标不标注

## 📊 数据集统计

当前数据集统计（运行 `scripts/validate_data.py` 生成）：

```
训练集: 0 张图像, 0 个目标
验证集: 0 张图像, 0 个目标
测试集: 0 张图像, 0 个目标

类别分布:
- crack: 0
- rust: 0
- deformation: 0
- spalling: 0
- corrosion: 0
```

（待数据准备完成后更新）

## 🔧 数据准备工作流

### 1. 收集原始图像

- 从现场拍摄或公开数据集获取
- 确保图像质量符合要求
- 按类别或场景组织

### 2. 数据标注

- 使用标注工具（LabelImg、CVAT、Labelme）
- 严格遵循 `docs/annotation_guidelines.md` 规范
- 质检审核确保标注质量

### 3. 数据切分

```python
# 示例代码
import random
from pathlib import Path
import shutil

# 设置随机种子确保可复现
random.seed(42)

# 读取所有图像路径
all_images = list(Path("raw_images").glob("*.jpg"))
random.shuffle(all_images)

# 按比例切分
train_ratio, val_ratio = 0.7, 0.15
n_train = int(len(all_images) * train_ratio)
n_val = int(len(all_images) * val_ratio)

train_images = all_images[:n_train]
val_images = all_images[n_train:n_train + n_val]
test_images = all_images[n_train + n_val:]

# 复制到对应目录
for img in train_images:
    shutil.copy(img, "data/images/train/")
    shutil.copy(img.with_suffix(".txt"), "data/labels/train/")
# ... 同理处理 val 和 test
```

### 4. 验证数据集

```bash
# 运行验证脚本
python scripts/validate_data.py

# 检查输出，确认：
# - 图像与标注文件一一对应
# - 标注格式正确
# - 类别分布合理
# - 无缺失或损坏文件
```

## ⚠️ 注意事项

1. **版本控制**：
   - 图像和标注文件较大，不建议直接提交到 Git
   - 使用 Git LFS 或单独的存储方案（云存储、NAS）
   - `.gitignore` 已配置忽略 `data/images/` 和 `data/labels/`

2. **数据安全**：
   - 注意图像中的隐私信息（项目名称、人员等）
   - 标注文件中不包含敏感信息
   - 公开数据集需确认使用权限

3. **数据备份**：
   - 定期备份原始图像和标注文件
   - 使用版本化管理（如 data_v1.0, data_v1.1）
   - 记录数据变更日志

4. **持续更新**：
   - 根据模型性能反馈收集难例
   - 定期扩充数据集提升泛化能力
   - 更新后重新运行验证脚本

## 📚 相关文档

- [标注规范](../docs/annotation_guidelines.md) - 详细的标注规则和质量标准
- [类目配置](../src/vision_analysis_pro/categories.py) - 类别定义和颜色映射
- [开发计划](../docs/development-plan.md) - Week 2 数据准备计划

## 🔄 更新记录

- 2025-12-17: 创建数据集目录结构和说明文档（Day 7）
