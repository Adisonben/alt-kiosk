import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Configuration
    PROJECT_NAME: str = "Alcohol Testing System"
    VERSION: str = "3.0.0"
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    
    # CORS Configuration (Comma-separated list)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Alcohol Sensor Configuration
    ALCOHOL_PORT: str | None = None  # None = auto-detect
    ALCOHOL_BAUDRATE: int = 4800
    
    # Logging
    LOG_LEVEL: str = "DEBUG"
    LOG_DIR: str = "logs"
    LOG_FILE: str = "alt.log"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
