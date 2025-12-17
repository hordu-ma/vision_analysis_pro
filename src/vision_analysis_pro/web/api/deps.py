"""FastAPI 依赖"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status

from vision_analysis_pro.core.inference import (
    PythonInferenceEngine,
    StubInferenceEngine,
    YOLOInferenceEngine,
)
from vision_analysis_pro.settings import Settings, get_settings


@lru_cache(maxsize=1)
def _load_yolo_engine(model_path: str) -> YOLOInferenceEngine:
    """加载 YOLO 推理引擎（带缓存）

    Args:
        model_path: 模型文件路径（字符串，可哈希）

    Returns:
        YOLOInferenceEngine 实例

    Raises:
        HTTPException: 模型文件不存在或加载失败
    """
    path = Path(model_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"模型文件不存在: {model_path}",
        )
    try:
        return YOLOInferenceEngine(path)
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="未安装 ultralytics，无法加载 YOLO 模型",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"模型文件错误: {exc}",
        ) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"模型加载失败: {exc}",
        ) from exc


@lru_cache(maxsize=1)
def _load_python_engine(model_path: str) -> PythonInferenceEngine:
    """加载 Python 推理引擎（带缓存）

    Args:
        model_path: 模型文件路径（字符串，可哈希）

    Returns:
        PythonInferenceEngine 实例

    Raises:
        HTTPException: 模型文件不存在或加载失败
    """
    path = Path(model_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"模型文件不存在: {model_path}",
        )
    try:
        return PythonInferenceEngine(path)
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="未安装 ultralytics，无法加载模型",
        ) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"模型加载失败: {exc}",
        ) from exc


def get_inference_engine(
    settings: Annotated[Settings, Depends(get_settings)],
) -> YOLOInferenceEngine | StubInferenceEngine:
    """获取推理引擎实例

    根据环境变量 INFERENCE_ENGINE 选择引擎：
    - "yolo" (默认): 使用 YOLOInferenceEngine (真实 YOLO 推理)
    - "stub": 使用 StubInferenceEngine (测试用 stub)
    - "yolo_path" (环境变量): YOLO 模型路径，默认 "runs/train/exp/weights/best.pt"

    Returns:
        推理引擎实例（YOLOInferenceEngine 或 StubInferenceEngine）
    """
    engine_type = os.getenv("INFERENCE_ENGINE", "yolo").lower()

    if engine_type == "stub":
        # 使用 stub 引擎（用于测试）
        return StubInferenceEngine(mode="normal")

    # 默认使用 YOLO 引擎
    model_path = os.getenv(
        "YOLO_MODEL_PATH",
        "runs/train/exp/weights/best.pt",
    )
    return _load_yolo_engine(model_path)
