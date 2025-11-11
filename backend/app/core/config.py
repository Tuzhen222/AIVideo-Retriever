from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Optional, Union
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    RELOAD: bool = True
    
    # CORS settings - can be comma-separated string or list
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    
    # API settings
    API_V1_PREFIX: str = "/api/v1"
    API_TITLE: str = "AI Video Retriever API"
    API_VERSION: str = "1.0.0"
    
    # Data paths
    DATA_ROOT: str = "app/data"
    KEYFRAME_DIR: str = "app/data/keyframe"
    INDEX_DIR: str = "app/data/index"
    MAPPING_KF_PATH: str = "app/data/index/mapping_kf.json"
    MAPPING_SCENE_PATH: str = "app/data/index/mapping_scene.json"
    
    # Search settings
    DEFAULT_TOP_K: int = 10
    MAX_TOP_K: int = 100
    DEFAULT_SEARCH_METHOD: str = "ensemble"
    
    # Ensemble weights (will be normalized to sum to 1.0)
    CLIP_WEIGHT: float = 1.0
    BEIT3_WEIGHT: float = 2.0
    BLIP2_WEIGHT: float = 1.0
    
    # Score scaling method
    SCORE_SCALE_METHOD: str = "min_max"  # min_max, z_score, percentile
    
    # Model settings
    DEVICE: str = "cuda"  # cuda or cpu
    BATCH_SIZE: int = 16
    
    # Embedding Server URL (for remote embedding API)
    EMBEDDING_SERVER_URL: Optional[str] = None
    
    # Gemini API (if used)
    GEMINI_API_KEY: Optional[str] = None
    
    # Elasticsearch settings (if used)
    ELASTICSEARCH_HOST: Optional[str] = None
    ELASTICSEARCH_PORT: int = 9200
    ELASTICSEARCH_INDEX: Optional[str] = None
    
    # Qdrant settings (gRPC only)
    QDRANT_HOST: str = "localhost"
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_HTTP_PORT: int = 6333  # HTTP port for health checks
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_TIMEOUT: int = 30
    QDRANT_WAIT_TIMEOUT: int = 20  # Timeout in seconds for waiting Qdrant to be ready
    QDRANT_RETRY_ATTEMPTS: int = 5  # Number of retry attempts for connection
    QDRANT_RETRY_DELAY: int = 3  # Delay in seconds between retry attempts
    QDRANT_BATCH_SIZE: int = 500  # Batch size for vector ingestion (larger = faster)
    VECTOR_SIZE: Optional[int] = None  # Vector size (dimensions). If None, will auto-detect from .bin files
    
    # Logging
    LOG_DIR: str = "logs"  # Directory for log files
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS_ORIGINS from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v if isinstance(v, list) else []


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()

