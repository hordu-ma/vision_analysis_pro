"""项目配置读取"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    api_host: str = Field("0.0.0.0", description="API 监听地址")
    api_port: int = Field(8000, description="API 监听端口")
    api_reload: bool = Field(True, description="开发模式下是否自动重载")

    model_path: Path = Field(Path("models/best.pt"), description="模型文件路径")
    confidence_threshold: float = Field(0.5, ge=0, le=1, description="置信度阈值")
    iou_threshold: float = Field(0.5, ge=0, le=1, description="IoU 阈值")

    edge_device_id: str = Field("edge-01", description="边缘设备 ID")
    edge_upload_interval: int = Field(60, ge=1, description="结果上报间隔 (秒)")
    edge_video_source: str | int = Field("0", description="视频源")

    cloud_api_url: HttpUrl = Field("http://localhost:8000", description="云端 API 地址")
    cloud_api_key: str = Field("", description="云端 API Key（通过环境变量注入）")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取缓存的配置实例"""
    return Settings()
