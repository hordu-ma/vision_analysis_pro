"""类目配置模块测试"""

from vision_analysis_pro.categories import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_NMS_THRESHOLD,
    LABEL_CN,
    LABEL_COLORS,
    LABEL_MAP,
    LABEL_TO_ID,
    MAX_BOX_RATIO,
    MIN_BOX_SIZE,
    NUM_CLASSES,
    SEVERITY_LEVEL,
    get_label_cn,
    get_label_color,
    get_label_name,
    get_severity,
    validate_class_id,
)


class TestLabelMappings:
    """测试标签映射"""

    def test_label_map_completeness(self):
        """测试类别映射完整性"""
        assert len(LABEL_MAP) == 5
        assert 0 in LABEL_MAP
        assert 4 in LABEL_MAP

        expected_labels = {"crack", "rust", "deformation", "spalling", "corrosion"}
        assert set(LABEL_MAP.values()) == expected_labels

    def test_label_to_id_reverse_mapping(self):
        """测试反向映射"""
        # 验证反向映射与正向映射一致
        for class_id, label in LABEL_MAP.items():
            assert LABEL_TO_ID[label] == class_id

        # 验证所有类别都有反向映射
        assert len(LABEL_TO_ID) == len(LABEL_MAP)

    def test_label_cn_completeness(self):
        """测试中文名称完整性"""
        # 所有类别都应有中文名称
        for label in LABEL_MAP.values():
            assert label in LABEL_CN
            assert len(LABEL_CN[label]) > 0

    def test_label_colors_completeness(self):
        """测试颜色映射完整性"""
        # 所有类别都应有颜色定义
        for label in LABEL_MAP.values():
            assert label in LABEL_COLORS
            color = LABEL_COLORS[label]
            # 验证颜色格式 (B, G, R)
            assert isinstance(color, tuple)
            assert len(color) == 3
            assert all(0 <= c <= 255 for c in color)

    def test_severity_level_completeness(self):
        """测试严重等级完整性"""
        # 所有类别都应有严重等级
        for label in LABEL_MAP.values():
            assert label in SEVERITY_LEVEL
            severity = SEVERITY_LEVEL[label]
            assert severity in {"high", "medium", "low"}


class TestConstants:
    """测试配置常量"""

    def test_num_classes(self):
        """测试类别数量常量"""
        assert NUM_CLASSES == 5
        assert NUM_CLASSES == len(LABEL_MAP)

    def test_thresholds(self):
        """测试阈值常量"""
        assert 0.0 < DEFAULT_CONFIDENCE_THRESHOLD < 1.0
        assert 0.0 < DEFAULT_NMS_THRESHOLD < 1.0

    def test_box_constraints(self):
        """测试边界框约束"""
        assert MIN_BOX_SIZE > 0
        assert 0.0 < MAX_BOX_RATIO <= 1.0


class TestHelperFunctions:
    """测试辅助函数"""

    def test_get_label_name(self):
        """测试获取类别名称"""
        assert get_label_name(0) == "crack"
        assert get_label_name(1) == "rust"
        assert get_label_name(4) == "corrosion"

        # 测试无效 ID
        assert get_label_name(999) == "unknown"
        assert get_label_name(-1) == "unknown"

    def test_get_label_cn(self):
        """测试获取中文名称"""
        assert get_label_cn(0) == "裂缝"
        assert get_label_cn(1) == "锈蚀"
        assert get_label_cn(2) == "变形"
        assert get_label_cn(3) == "剥落"
        assert get_label_cn(4) == "腐蚀"

        # 测试无效 ID
        assert get_label_cn(999) == "未知"

    def test_get_label_color(self):
        """测试获取类别颜色"""
        # 测试有效类别
        crack_color = get_label_color(0)
        assert crack_color == (0, 0, 255)  # 红色 BGR

        rust_color = get_label_color(1)
        assert rust_color == (0, 136, 255)  # 橙色 BGR

        # 测试无效 ID（返回默认白色）
        default_color = get_label_color(999)
        assert default_color == (255, 255, 255)

    def test_get_severity(self):
        """测试获取严重等级"""
        assert get_severity(0) == "high"  # crack
        assert get_severity(1) == "medium"  # rust
        assert get_severity(2) == "high"  # deformation

        # 测试无效 ID
        assert get_severity(999) == "unknown"

    def test_validate_class_id(self):
        """测试类别 ID 验证"""
        # 有效 ID
        assert validate_class_id(0) is True
        assert validate_class_id(1) is True
        assert validate_class_id(4) is True

        # 无效 ID
        assert validate_class_id(5) is False
        assert validate_class_id(-1) is False
        assert validate_class_id(999) is False


class TestIntegration:
    """测试模块集成"""

    def test_all_exports_available(self):
        """测试所有导出项可用"""
        from vision_analysis_pro import categories

        # 验证主要常量可导入
        assert hasattr(categories, "LABEL_MAP")
        assert hasattr(categories, "LABEL_COLORS")
        assert hasattr(categories, "NUM_CLASSES")

        # 验证辅助函数可导入
        assert hasattr(categories, "get_label_name")
        assert hasattr(categories, "get_label_color")
        assert hasattr(categories, "validate_class_id")

    def test_color_consistency_with_guidelines(self):
        """测试颜色定义与标注规范一致"""
        # 根据 annotation_guidelines.md 验证颜色
        expected_colors = {
            "crack": (0, 0, 255),  # 红色 #FF0000 -> BGR
            "rust": (0, 136, 255),  # 橙色 #FF8800 -> BGR
            "deformation": (0, 255, 255),  # 黄色 #FFFF00 -> BGR
            "spalling": (255, 0, 136),  # 紫色 #8800FF -> BGR
            "corrosion": (255, 255, 0),  # 青色 #00FFFF -> BGR
        }

        for label, expected_color in expected_colors.items():
            assert LABEL_COLORS[label] == expected_color
