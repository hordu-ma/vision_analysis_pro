"""
类目配置模块

定义基础设施图像分析的类别标签、颜色映射和相关常量。
与 docs/annotation_guidelines.md 保持一致。
"""

from typing import Final

# ========== 核心类别定义 ==========

# 类别名称到 ID 的映射
LABEL_MAP: Final[dict[int, str]] = {
    0: "crack",  # 裂缝
    1: "rust",  # 锈蚀
    2: "deformation",  # 变形
    3: "spalling",  # 剥落
    4: "corrosion",  # 腐蚀
}

# 反向映射：类别名称到 ID
LABEL_TO_ID: Final[dict[str, int]] = {v: k for k, v in LABEL_MAP.items()}

# 类别中文名称
LABEL_CN: Final[dict[str, str]] = {
    "crack": "裂缝",
    "rust": "锈蚀",
    "deformation": "变形",
    "spalling": "剥落",
    "corrosion": "腐蚀",
}

# 类别颜色（BGR 格式，用于 OpenCV 绘制）
LABEL_COLORS: Final[dict[str, tuple[int, int, int]]] = {
    "crack": (0, 0, 255),  # 红色
    "rust": (0, 136, 255),  # 橙色
    "deformation": (0, 255, 255),  # 黄色
    "spalling": (255, 0, 136),  # 紫色
    "corrosion": (255, 255, 0),  # 青色
}

# 类别严重等级
SEVERITY_LEVEL: Final[dict[str, str]] = {
    "crack": "high",
    "rust": "medium",
    "deformation": "high",
    "spalling": "medium",
    "corrosion": "medium",
}

# ========== 配置常量 ==========

# 支持的类别数量
NUM_CLASSES: Final[int] = len(LABEL_MAP)

# 默认检测阈值
DEFAULT_CONFIDENCE_THRESHOLD: Final[float] = 0.5

# 默认 NMS 阈值
DEFAULT_NMS_THRESHOLD: Final[float] = 0.4

# 最小目标尺寸（像素）
MIN_BOX_SIZE: Final[int] = 32

# 最大目标占比（相对于图像面积）
MAX_BOX_RATIO: Final[float] = 0.8


# ========== 辅助函数 ==========


def get_label_name(class_id: int) -> str:
    """获取类别英文名称"""
    return LABEL_MAP.get(class_id, "unknown")


def get_label_cn(class_id: int) -> str:
    """获取类别中文名称"""
    label = get_label_name(class_id)
    return LABEL_CN.get(label, "未知")


def get_label_color(class_id: int) -> tuple[int, int, int]:
    """获取类别颜色（BGR 格式）"""
    label = get_label_name(class_id)
    return LABEL_COLORS.get(label, (255, 255, 255))  # 默认白色


def get_severity(class_id: int) -> str:
    """获取类别严重等级"""
    label = get_label_name(class_id)
    return SEVERITY_LEVEL.get(label, "unknown")


def validate_class_id(class_id: int) -> bool:
    """验证类别 ID 是否有效"""
    return class_id in LABEL_MAP


# ========== 元数据 ==========

# 供外部模块导出的常量
__all__ = [
    "LABEL_MAP",
    "LABEL_TO_ID",
    "LABEL_CN",
    "LABEL_COLORS",
    "SEVERITY_LEVEL",
    "NUM_CLASSES",
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "DEFAULT_NMS_THRESHOLD",
    "MIN_BOX_SIZE",
    "MAX_BOX_RATIO",
    "get_label_name",
    "get_label_cn",
    "get_label_color",
    "get_severity",
    "validate_class_id",
]
