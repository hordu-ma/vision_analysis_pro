"""可视化工具：绘制检测框"""

from typing import Any

import cv2
import numpy as np

from vision_analysis_pro.categories import LABEL_COLORS


def draw_detections(
    image_bytes: bytes,
    detections: list[dict[str, Any]],
    color: tuple[int, int, int] | None = None,
    thickness: int = 2,
    font_scale: float = 0.5,
    use_category_colors: bool = True,
) -> bytes:
    """在图像上绘制检测框和标签

    Args:
        image_bytes: 原始图像的字节数据
        detections: 检测结果列表，每项包含:
            - label: 类别标签 (str)
            - confidence: 置信度 (float)
            - bbox: 边界框 [x1, y1, x2, y2] (list[float])
        color: 默认绘制颜色 (BGR格式)，当 use_category_colors=False 时使用
        thickness: 线条粗细
        font_scale: 字体大小
        use_category_colors: 是否使用类别特定颜色（默认 True）

    Returns:
        绘制后的图像字节数据 (JPEG 格式)

    Raises:
        ValueError: 图像解码失败
    """
    # 解码图像
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("无法解码图像")

    # 默认颜色（绿色）
    default_color = color or (0, 255, 0)

    # 绘制每个检测框
    for det in detections:
        bbox = det["bbox"]
        label = det["label"]
        confidence = det["confidence"]

        # 转换坐标为整数
        x1, y1, x2, y2 = map(int, bbox)

        # 确定绘制颜色
        if use_category_colors and label in LABEL_COLORS:
            box_color = LABEL_COLORS[label]
        else:
            box_color = default_color

        # 绘制矩形框
        cv2.rectangle(img, (x1, y1), (x2, y2), box_color, thickness)

        # 准备标签文本
        text = f"{label}: {confidence:.2f}"

        # 计算文本大小以绘制背景
        (text_width, text_height), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
        )

        # 绘制文本背景（使用与框相同的颜色，半透明效果）
        overlay = img.copy()
        cv2.rectangle(
            overlay,
            (x1, y1 - text_height - baseline - 5),
            (x1 + text_width, y1),
            box_color,
            -1,
        )
        # 混合透明度 0.6
        cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

        # 绘制文本（白色）
        cv2.putText(
            img,
            text,
            (x1, y1 - baseline - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            thickness,
        )

    # 编码为 JPEG
    success, encoded_img = cv2.imencode(".jpg", img)
    if not success:
        raise ValueError("图像编码失败")

    return encoded_img.tobytes()
