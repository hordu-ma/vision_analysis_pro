"""FastAPI 依赖"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status

from vision_analysis_pro.core.inference import PythonInferenceEngine
from vision_analysis_pro.settings import Settings, get_settings


@lru_cache(maxsize=1)
def _load_engine(settings: Settings) -> PythonInferenceEngine:
    if not settings.model_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"模型文件不存在: {settings.model_path}",
        )
    try:
        return PythonInferenceEngine(settings.model_path)
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="未安装 ultralytics，无法加载 YOLO 模型",
        ) from exc
    except Exception as exc:  # pragma: no cover - 保护性兜底
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"模型加载失败: {exc}",
        ) from exc


def get_inference_engine(
    settings: Annotated[Settings, Depends(get_settings)],
) -> PythonInferenceEngine:
    """获取推理引擎实例，依赖于配置"""
    return _load_engine(settings)
