from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置类"""
    DATABASE_URL: str = "sqlite+aiosqlite:///./model_viz.db"
    
    # 上游 API 配置（默认使用智谱 AI - 免费）
    UPSTREAM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    UPSTREAM_API_KEY: str = ""
    
    # 支持的模型列表
    DEFAULT_MODEL: str = "glm-4-flash"
    AVAILABLE_MODELS: list = [
        "glm-4-flash",      # 智谱 AI - 完全免费
        "glm-4",            # 智谱 AI - 收费
        "glm-4v",           # 智谱 AI - 视觉模型
        "deepseek-chat",    # DeepSeek
        "deepseek-coder",   # DeepSeek - 代码模型
    ]
    
    WS_PING_INTERVAL: int = 3
    WS_PING_TIMEOUT: int = 10
    METRICS_WINDOW_SECONDS: int = 5
    DATA_RETENTION_DAYS: int = 7

    class Config:
        env_file = ".env"


settings = Settings()
