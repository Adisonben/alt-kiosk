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
    CLOUD_REQUEST_TIMEOUT: int = 15  # seconds per HTTP request

    @property
    def CLOUD_ORG_ID(self) -> str:
        return self._read_device_data("org_id", "")

    @property
    def CLOUD_ORG_CODE(self) -> str:
        return self._read_device_data("org_code", "IDD")

    CLOUD_DEVICE_ID: str = ""      # Device identifier — set in .env

    def _read_device_data(self, key: str, default: str) -> str:
        import json
        import os
        path = "data/device_data.json"
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get(key, default)
            except Exception:
                pass
        return default

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
