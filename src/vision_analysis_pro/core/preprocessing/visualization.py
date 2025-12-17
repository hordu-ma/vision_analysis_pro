"""可视化工具：绘制检测框"""

from typing import Any

import cv2
import numpy as np


def draw_detections(
    image_bytes: bytes,
    detections: list[dict[str, Any]],
    color: tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
    font_scale: float = 0.5,
) -> bytes:
    """在图像上绘制检测框和标签

    Args:
        image_bytes: 原始图像的字节数据
        detections: 检测结果列表，每项包含:
            - label: 类别标签 (str)
            - confidence: 置信度 (float)
            - bbox: 边界框 [x1, y1, x2, y2] (list[float])
        color: 绘制颜色 (BGR格式)，默认绿色
        thickness: 线条粗细
        font_scale: 字体大小

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

    # 绘制每个检测框
    for det in detections:
        bbox = det["bbox"]
        label = det["label"]
        confidence = det["confidence"]

        # 转换坐标为整数
        x1, y1, x2, y2 = map(int, bbox)

        # 绘制矩形框
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

        # 准备标签文本
        text = f"{label}: {confidence:.2f}"

        # 计算文本大小以绘制背景
        (text_width, text_height), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
        )

        # 绘制文本背景（半透明黑色）
        cv2.rectangle(
            img,
            (x1, y1 - text_height - baseline - 5),
            (x1 + text_width, y1),
            (0, 0, 0),
            -1,
        )

        # 绘制文本
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
