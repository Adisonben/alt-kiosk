import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────
    PROJECT_NAME: str = "Alcohol Testing System"
    VERSION: str = "4.0.0"
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"

    # CORS (comma-separated origins)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── Hardware ──────────────────────────────────────────────────
    ALCOHOL_PORT: str | None = None  # None = auto-detect serial port
    ALCOHOL_BAUDRATE: int = 4800

    # ── Local Database ────────────────────────────────────────────
    # Path to SQLite file. Relative paths resolve from the Backend/ directory.
    DB_PATH: str = "data/kiosk.db"

    # ── Cloud API ─────────────────────────────────────────────────
    CLOUD_API_URL: str = "https://alcohol.idclever.net/api"
    CLOUD_API_TOKEN: str = ""      # Bearer token — set in .env, never hardcode
    CLOUD_ORG_ID: str = ""         # Organization UUID — set in .env
    CLOUD_DEVICE_ID: str = ""      # Device identifier — set in .env
    CLOUD_REQUEST_TIMEOUT: int = 15  # seconds per HTTP request

    # ── Sync ──────────────────────────────────────────────────────
    SYNC_INTERVAL_SECONDS: int = 300    # 5 minutes between incremental syncs
    SYNC_RETRY_DELAY_SECONDS: int = 30  # Wait before retrying a failed sync

    # ── Scan Log Upload ───────────────────────────────────────────
    LOG_UPLOAD_INTERVAL_SECONDS: int = 60   # How often to flush pending logs
    LOG_RETENTION_DAYS: int = 30            # Delete uploaded logs older than N days

    # ── Logging ───────────────────────────────────────────────────
    LOG_LEVEL: str = "DEBUG"
    LOG_DIR: str = "logs"
    LOG_FILE: str = "alt.log"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
