"""FastAPI 依赖"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status

from vision_analysis_pro.core.inference import PythonInferenceEngine
from vision_analysis_pro.core.inference.stub_engine import StubInferenceEngine
from vision_analysis_pro.settings import Settings, get_settings


@lru_cache(maxsize=1)
def _load_engine(model_path: str) -> PythonInferenceEngine:
    """加载推理引擎（带缓存）

    Args:
        model_path: 模型文件路径（字符串，可哈希）

    Returns:
        推理引擎实例
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
            detail="未安装 ultralytics，无法加载 YOLO 模型",
        ) from exc
    except Exception as exc:  # pragma: no cover - 保护性兜底
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"模型加载失败: {exc}",
        ) from exc


def get_inference_engine(
    settings: Annotated[Settings, Depends(get_settings)],
) -> PythonInferenceEngine | StubInferenceEngine:
    """获取推理引擎实例

    当前返回 StubInferenceEngine（MVP 阶段），
    后续可替换为真实的 PythonInferenceEngine。
    """
    # MVP 阶段：使用 stub 引擎
    return StubInferenceEngine(mode="normal")
