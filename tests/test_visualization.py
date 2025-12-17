"""可视化工具测试"""

import cv2
import numpy as np
import pytest

from vision_analysis_pro.core.preprocessing.visualization import draw_detections


def _create_test_image(width: int = 640, height: int = 480) -> bytes:
    """创建测试图像（纯色背景）"""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (128, 128, 128)  # 灰色背景
    success, encoded = cv2.imencode(".jpg", img)
    assert success
    return encoded.tobytes()


class TestDrawDetections:
    """可视化工具测试"""

    def test_draw_single_detection(self):
        """测试绘制单个检测框"""
        image_bytes = _create_test_image()
        detections = [
            {
                "label": "crack",
                "confidence": 0.95,
                "bbox": [100.0, 100.0, 200.0, 200.0],
            }
        ]

        result_bytes = draw_detections(image_bytes, detections)

        # 验证结果可以解码
        assert result_bytes is not None
        assert len(result_bytes) > 0

        # 验证是有效的图像
        nparr = np.frombuffer(result_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert img is not None
        assert img.shape[0] == 480  # height
        assert img.shape[1] == 640  # width

    def test_draw_multiple_detections(self):
        """测试绘制多个检测框"""
        image_bytes = _create_test_image()
        detections = [
            {
                "label": "crack",
                "confidence": 0.95,
                "bbox": [100.0, 100.0, 200.0, 200.0],
            },
            {
                "label": "rust",
                "confidence": 0.88,
                "bbox": [300.0, 200.0, 400.0, 300.0],
            },
            {
                "label": "deformation",
                "confidence": 0.72,
                "bbox": [50.0, 350.0, 150.0, 450.0],
            },
        ]

        result_bytes = draw_detections(image_bytes, detections)

        # 验证结果
        assert result_bytes is not None
        nparr = np.frombuffer(result_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert img is not None

    def test_draw_empty_detections(self):
        """测试空检测结果（应返回原图）"""
        image_bytes = _create_test_image()
        detections: list = []

        result_bytes = draw_detections(image_bytes, detections)

        # 验证结果可以解码
        assert result_bytes is not None
        nparr = np.frombuffer(result_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert img is not None

    def test_invalid_image_bytes(self):
        """测试无效图像数据"""
        invalid_bytes = b"not-an-image"
        detections = [
            {
                "label": "crack",
                "confidence": 0.95,
                "bbox": [100.0, 100.0, 200.0, 200.0],
            }
        ]

        with pytest.raises(ValueError, match="无法解码图像"):
            draw_detections(invalid_bytes, detections)

    def test_custom_color_and_thickness(self):
        """测试自定义颜色和线条粗细"""
        image_bytes = _create_test_image()
        detections = [
            {
                "label": "test",
                "confidence": 0.9,
                "bbox": [50.0, 50.0, 150.0, 150.0],
            }
        ]

        result_bytes = draw_detections(
            image_bytes, detections, color=(255, 0, 0), thickness=3
        )

        # 验证结果可以解码
        assert result_bytes is not None
        nparr = np.frombuffer(result_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert img is not None

    def test_bbox_with_float_coordinates(self):
        """测试浮点数坐标（应正确转换为整数）"""
        image_bytes = _create_test_image()
        detections = [
            {
                "label": "crack",
                "confidence": 0.95,
                "bbox": [100.5, 150.7, 300.2, 400.9],
            }
        ]

        result_bytes = draw_detections(image_bytes, detections)

        # 验证结果
        assert result_bytes is not None
        nparr = np.frombuffer(result_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert img is not None

    def test_category_colors(self):
        """测试类别颜色映射功能"""
        image_bytes = _create_test_image()
        detections = [
            {"label": "crack", "confidence": 0.95, "bbox": [50, 50, 150, 150]},
            {"label": "rust", "confidence": 0.88, "bbox": [200, 50, 300, 150]},
            {
                "label": "deformation",
                "confidence": 0.92,
                "bbox": [350, 50, 450, 150],
            },
            {"label": "spalling", "confidence": 0.85, "bbox": [500, 50, 600, 150]},
        ]

        # 使用类别颜色
        result_bytes = draw_detections(
            image_bytes, detections, use_category_colors=True
        )
        assert result_bytes is not None

        # 验证图像有效
        nparr = np.frombuffer(result_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert img is not None

    def test_disable_category_colors(self):
        """测试禁用类别颜色，使用统一颜色"""
        image_bytes = _create_test_image()
        detections = [
            {"label": "crack", "confidence": 0.95, "bbox": [100, 100, 200, 200]},
            {"label": "rust", "confidence": 0.88, "bbox": [250, 100, 350, 200]},
        ]

        # 禁用类别颜色，使用自定义颜色
        custom_color = (255, 0, 0)  # 蓝色
        result_bytes = draw_detections(
            image_bytes, detections, color=custom_color, use_category_colors=False
        )
        assert result_bytes is not None

        # 验证图像有效
        nparr = np.frombuffer(result_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert img is not None
