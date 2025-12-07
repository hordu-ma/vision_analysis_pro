"""图像预处理变换"""

import cv2
import numpy as np
from numpy.typing import NDArray


class ImageTransform:
    """图像预处理工具类"""

    @staticmethod
    def resize_with_padding(
        image: NDArray[np.uint8], target_size: int = 640
    ) -> tuple[NDArray[np.uint8], tuple[float, float, int, int]]:
        """等比例缩放并填充到目标尺寸

        Args:
            image: 输入图像
            target_size: 目标尺寸

        Returns:
            (处理后的图像, (scale_x, scale_y, pad_w, pad_h))
        """
        h, w = image.shape[:2]
        scale = min(target_size / h, target_size / w)
        new_h, new_w = int(h * scale), int(w * scale)

        # 缩放
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # 填充
        pad_h = (target_size - new_h) // 2
        pad_w = (target_size - new_w) // 2
        padded = cv2.copyMakeBorder(
            resized,
            pad_h,
            target_size - new_h - pad_h,
            pad_w,
            target_size - new_w - pad_w,
            cv2.BORDER_CONSTANT,
            value=(114, 114, 114),
        )

        return padded, (scale, scale, pad_w, pad_h)

    @staticmethod
    def normalize(image: NDArray[np.uint8]) -> NDArray[np.float32]:
        """归一化到 [0, 1]"""
        return image.astype(np.float32) / 255.0
