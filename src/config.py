"""Конфигурация приложения."""

from pathlib import Path
from typing import Optional

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Telegram Bot
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    
    # Database
    database_url: str = Field(
        "postgresql://username:password@localhost:5432/itmo_bot_db",
        env="DATABASE_URL"
    )
    db_host: str = Field("localhost", env="DB_HOST")
    db_port: int = Field(5432, env="DB_PORT")
    db_name: str = Field("itmo_bot_db", env="DB_NAME")
    db_user: str = Field("username", env="DB_USER")
    db_password: str = Field("password", env="DB_PASSWORD")
    
    # Anthropic API
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    
    # Application settings
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # RAG settings
    vector_db_path: str = Field("./vector_db", env="VECTOR_DB_PATH")
    chunk_size: int = Field(1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(200, env="CHUNK_OVERLAP")
    
    # Web scraping
    request_timeout: int = Field(30, env="REQUEST_TIMEOUT")
    rate_limit_delay: int = Field(1, env="RATE_LIMIT_DELAY")
    
    # Paths
    data_dir: str = Field("./data", env="DATA_DIR")
    logs_dir: str = Field("./logs", env="LOGS_DIR")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def ensure_directories(self) -> None:
        """Создает необходимые директории."""
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
        Path(self.vector_db_path).mkdir(parents=True, exist_ok=True)


# Глобальная конфигурация
settings = Settings() 