"""FastAPI 应用主入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="工程基础设施图像识别智能运维系统",
    description="基于 YOLO 的无人机巡检系统后端 API",
    version="0.1.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """健康检查"""
    return {"status": "ok", "message": "API 运行正常"}


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    """健康检查接口"""
    return {"status": "healthy"}
