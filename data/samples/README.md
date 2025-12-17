# 样例图片说明

本目录包含用于标注培训和质量参考的样例图片。

## 📁 目录结构

```
data/samples/
├── good/         # 正例：标注正确的示例
├── edge/         # 边界案例：容易混淆的情况
├── negative/     # 负例：不应标注的情况
└── README.md     # 本文件
```

## 📸 样例图片规划

### 1. good/ - 正例样例
每个类别提供 3-5 张标注正确的典型案例：

- `crack_001.jpg` - 混凝土表面典型裂缝
- `crack_002.jpg` - 网状裂缝（密集型）
- `crack_003.jpg` - 单条长裂缝
- `rust_001.jpg` - 钢筋锈蚀（轻度）
- `rust_002.jpg` - 钢结构锈蚀（中度）
- `deformation_001.jpg` - 梁体弯曲变形
- `deformation_002.jpg` - 板面起拱
- `spalling_001.jpg` - 混凝土剥落露出钢筋
- `spalling_002.jpg` - 边角剥落
- `corrosion_001.jpg` - 化学腐蚀坑洞
- `corrosion_002.jpg` - 酸碱腐蚀痕迹

**标注要求**：
- 所有图片需配对 `.txt` 标注文件（YOLO 格式）
- 文件名格式：`{category}_{序号}.jpg` + `{category}_{序号}.txt`

### 2. edge/ - 边界案例
容易误判的典型情况：

- `crack_vs_texture.jpg` - 裂缝 vs 表面纹理（如木纹混凝土）
- `crack_vs_shadow.jpg` - 裂缝 vs 阴影线
- `rust_vs_dirt.jpg` - 锈蚀 vs 泥土污渍
- `rust_vs_paint.jpg` - 锈蚀 vs 油漆剥落
- `deformation_vs_design.jpg` - 病害变形 vs 设计曲线
- `deformation_vs_perspective.jpg` - 真实变形 vs 拍摄角度畸变
- `spalling_vs_weathering.jpg` - 深层剥落 vs 表面风化
- `spalling_vs_construction.jpg` - 自然剥落 vs 施工凿除
- `corrosion_vs_rust.jpg` - 化学腐蚀 vs 氧化锈蚀

**标注要求**：
- 提供标准答案（标注文件）
- 配文字说明区分要点

### 3. negative/ - 负例样例
不应标注的常见误判：

- `shadow_not_crack.jpg` - 阴影不是裂缝
- `paint_not_rust.jpg` - 油漆变色不是锈蚀
- `design_curve_not_deformation.jpg` - 设计造型不是变形
- `weathering_not_spalling.jpg` - 浅层风化不是剥落
- `stain_not_corrosion.jpg` - 污渍不是腐蚀
- `construction_joint.jpg` - 施工缝不是裂缝
- `expansion_joint.jpg` - 伸缩缝不是裂缝

**标注要求**：
- 不提供标注文件（或空文件）
- 配文字说明为何不标注

## 🎯 使用场景

### 1. 标注员培训
- 新标注员学习各类别特征
- 测试标注能力（使用 edge/ 目录）
- 质检标准参考

### 2. 算法开发
- 数据增强参考
- 难例分析（edge/ 目录）
- 负样本训练（negative/ 目录）

### 3. 质量审核
- 标注一致性检查
- 边界案例仲裁
- 更新标注规范

## 📝 待办事项

- [ ] 收集各类别典型样例图片（每类 3-5 张）
- [ ] 标注 good/ 目录的样例
- [ ] 收集边界案例图片（每组对比 2-3 张）
- [ ] 编写边界案例说明文档
- [ ] 收集负例图片（5-10 张）
- [ ] 团队评审并冻结样例库

## ⚠️ 注意事项

1. **版权问题**：所有样例图片需确认使用权限
2. **隐私保护**：图片中不得包含敏感信息（如项目名称、人员）
3. **命名规范**：严格遵循 `{category}_{序号}.jpg` 格式
4. **质量要求**：
   - 分辨率 ≥ 640x640
   - 清晰度高，无模糊
   - 光线均匀，无过曝/欠曝
   - 目标清晰可见

## 🔄 更新记录

- 2025-12-17: 创建目录结构和规划文档
- 待添加: 实际样例图片收集与标注
