"""FastAPI 应用主入口"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vision_analysis_pro.settings import get_settings
from vision_analysis_pro.web.api import schemas
from vision_analysis_pro.web.api.routers import inference

app = FastAPI(
    title="工程基础设施图像识别智能运维系统",
    description="基于 YOLO 的无人机巡检系统后端 API",
    version="0.1.0",
    responses={
        400: {"model": schemas.ErrorResponse, "description": "请求参数错误"},
        503: {
            "model": schemas.ErrorResponse,
            "description": "服务不可用（如模型未加载）",
        },
    },
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(inference.router)


# 统一异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """处理 HTTPException，返回统一的 ErrorResponse 格式"""
    # 如果 detail 已经是字典格式（包含 code/message/detail），直接返回
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    # 否则，构造标准错误响应
    error_code = f"HTTP_{exc.status_code}"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": error_code,
            "message": str(exc.detail) if exc.detail else "请求错误",
            "detail": None,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """捕获所有未处理的异常，返回统一的 500 错误"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
            "detail": str(exc),
        },
    )


@app.get("/", response_model=schemas.HealthResponse)
async def root() -> JSONResponse:
    """健康检查"""
    return await health()


@app.get("/api/v1/health", response_model=schemas.HealthResponse)
async def health() -> JSONResponse:
    """健康检查接口"""
    settings = get_settings()
    model_loaded = settings.model_path.exists()
    return JSONResponse(
        content={
            "status": "healthy",
            "version": app.version,
            "model_loaded": model_loaded,
        }
    )
