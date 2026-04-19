"""FastAPI 依赖"""

import os
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status

from vision_analysis_pro.core.inference import (
    ONNXInferenceEngine,
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
def _load_onnx_engine(model_path: str) -> ONNXInferenceEngine:
    """加载 ONNX 推理引擎（带缓存）

    Args:
        model_path: ONNX 模型文件路径（字符串，可哈希）

    Returns:
        ONNXInferenceEngine 实例

    Raises:
        HTTPException: 模型文件不存在或加载失败
    """
    path = Path(model_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ONNX 模型文件不存在: {model_path}",
        )
    try:
        return ONNXInferenceEngine(path)
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="未安装 onnxruntime，请运行: uv sync --extra onnx",
        ) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"模型文件错误: {exc}",
        ) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ONNX 模型加载失败: {exc}",
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


def clear_inference_engine_caches() -> None:
    """清理推理引擎缓存

    供测试或需要重新加载模型的场景显式调用。
    """
    _load_yolo_engine.cache_clear()
    _load_onnx_engine.cache_clear()
    _load_python_engine.cache_clear()


def get_inference_engine(
    settings: Annotated[Settings, Depends(get_settings)],
) -> YOLOInferenceEngine | ONNXInferenceEngine | StubInferenceEngine:
    """获取推理引擎实例

    根据环境变量 INFERENCE_ENGINE 选择引擎：
    - "yolo" (默认): 使用 YOLOInferenceEngine (真实 YOLO 推理)
    - "onnx": 使用 ONNXInferenceEngine (ONNX Runtime 推理)
    - "stub": 使用 StubInferenceEngine (测试用 stub)

    相关环境变量：
    - INFERENCE_ENGINE: 引擎类型 ("yolo", "onnx", "stub")
    - YOLO_MODEL_PATH: YOLO 模型路径，默认 "runs/train/exp/weights/best.pt"
    - ONNX_MODEL_PATH: ONNX 模型路径，默认 "models/best.onnx"

    Returns:
        推理引擎实例
    """
    _ = settings
    engine_type = os.getenv("INFERENCE_ENGINE", "yolo").lower()

    if engine_type == "stub":
        # 使用 stub 引擎（用于测试）
        return StubInferenceEngine(mode="normal")

    if engine_type == "onnx":
        # 使用 ONNX Runtime 引擎
        model_path = os.getenv("ONNX_MODEL_PATH", "models/best.onnx")
        return _load_onnx_engine(model_path)

    if engine_type != "yolo":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"不支持的推理引擎类型: {engine_type}，"
                "支持的类型: ['stub', 'yolo', 'onnx']"
            ),
        )

    # 默认使用 YOLO 引擎
    model_path = os.getenv(
        "YOLO_MODEL_PATH",
        "runs/train/exp/weights/best.pt",
    )
    return _load_yolo_engine(model_path)


def get_inference_engine_cache_clearer() -> Callable[[], None]:
    """返回推理引擎缓存清理函数

    供测试代码通过公开入口清理缓存，避免直接依赖私有实现细节。
    """
    return clear_inference_engine_caches
