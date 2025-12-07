"""推理相关 API"""

from fastapi import APIRouter, File, UploadFile

router = APIRouter(prefix="/api/v1/inference", tags=["inference"])


@router.post("/image")
async def inference_image(file: UploadFile = File(...)) -> dict[str, str]:
    """图像推理接口

    Args:
        file: 上传的图像文件

    Returns:
        推理结果
    """
    # TODO: 实现图像推理逻辑
    return {"message": "推理功能开发中", "filename": file.filename}
