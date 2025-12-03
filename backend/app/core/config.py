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
    KEYFRAME_DIR: str = "app/data/keyframes"
    INDEX_DIR: str = "app/data/index"
    MAPPING_KF_PATH: str = "app/data/index/mapping_kf.json"
    MAPPING_SCENE_PATH: str = "app/data/index/mapping_scene.json"
    BASE_DIR: str = ""  # Will be set to backend root directory
    
    # Model Server URL (for CLIP/BEiT3/BiGG embeddings)
    MODEL_SERVER_URL: str = "https://privative-startingly-justa.ngrok-free.dev/"
    
    # Search settings
    DEFAULT_TOP_K: int = 200
    
    EMBEDDING_SERVER_QWEN: Optional[str] = None
    COHERE_API_KEYS: Optional[List[str]] = None
    # Embedding Server URL (for remote embedding API)
    EMBEDDING_SERVER_MULTIMODAL: Optional[str] = None
    GEMINI_API_KEYS: Optional[List[str]] = "AIzaSyCz7cbiDs-pvTGXxDuwOJzUnuybyNU7AiE", "AIzaSyB1OtAS0xvRIMAhcTCk11i_aG6DKKjvxF4"
    # Elasticsearch settings (if used)
    ELASTICSEARCH_HOST: Optional[str] = None
    ELASTICSEARCH_PORT: int = 9200
    ELASTICSEARCH_INDEX_PREFIX: str = "es_data"
    ELASTICSEARCH_REQUEST_TIMEOUT: int = 60
    ELASTICSEARCH_MAX_RETRIES: int = 3
    ELASTICSEARCH_RETRY_ON_TIMEOUT: bool = True
    ELASTICSEARCH_USER: Optional[str] = None
    ELASTICSEARCH_PASSWORD: Optional[str] = None
    ELASTICSEARCH_USE_SSL: bool = False
    ELASTICSEARCH_VERIFY_CERTS: bool = True
    ELASTICSEARCH_WAIT_TIMEOUT: int = 30  # Timeout in seconds for waiting Elasticsearch to be ready
    
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
    
    # Chatbox settings
    CHATBOX_DB_PATH: str = "logs/chatbox.db"  # Store in logs directory (has write permission) - DEPRECATED: Use PostgreSQL instead
    CHATBOX_ENABLED: bool = True
    CHATBOX_MAX_LIMIT: int = 200  # Max limit for fetch
    
    # PostgreSQL settings
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "aivideo_chatbox"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_MAX_OVERFLOW: int = 10
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS_ORIGINS from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v if isinstance(v, list) else []
    
    @field_validator("COHERE_API_KEYS", mode="before")
    @classmethod
    def parse_keys(cls, v):
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        return v
    
    @field_validator("GEMINI_API_KEYS", mode="before")
    @classmethod
    def parse_gemini_keys(cls, v):
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    import os
    s = Settings()
    # Set BASE_DIR to backend root directory
    if not s.BASE_DIR:
        s.BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return s


settings = get_settings()

