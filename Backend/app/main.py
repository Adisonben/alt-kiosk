import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.utils.logger import setup_logging, get_logger
from app.core.event_bus import EventBus
from app.core.command_bus import CommandBus
from app.db.database import DatabaseManager
from app.db.migrations import init_db
from app.services.alcohol_service import AlcoholService
from app.services.fingerprint_service import FingerprintService
from app.services.employee_service import EmployeeService
from app.services.sync_service import SyncService
from app.services.scan_log_service import ScanLogService
from app.services.identify_service import IdentifyService
from app.services.log_uploader_service import LogUploaderService
from app.utils.http_client import CloudHttpClient
from app.api.websocket import router as ws_router

# Initialize logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("=== %s starting (v%s) ===", settings.PROJECT_NAME, settings.VERSION)

    # Initialize local database (creates tables if not exists)
    os.makedirs(os.path.dirname(settings.DB_PATH) or ".", exist_ok=True)
    await init_db()

    # Initialize DB manager and services
    db = DatabaseManager(settings.DB_PATH)
    employee_svc = EmployeeService(db)

    # Initialize core buses
    event_bus = EventBus()
    command_bus = CommandBus()

    # Initialize hardware and sync services
    scan_log_svc = ScanLogService(db)
    http_client = CloudHttpClient()  # Shared client

    alcohol_svc = AlcoholService(event_bus, command_bus, scan_log_svc, http_client)
    fingerprint_svc = FingerprintService(event_bus, command_bus)
    sync_svc = SyncService(db, employee_svc, http_client, event_bus, command_bus)
    identify_svc = IdentifyService(
        employee_svc, fingerprint_svc, scan_log_svc, http_client, event_bus, command_bus
    )
    log_uploader_svc = LogUploaderService(scan_log_svc, http_client)

    # Store in app.state for access by routers and services
    app.state.db = db
    app.state.employee_svc = employee_svc
    app.state.sync_svc = sync_svc
    app.state.scan_log_svc = scan_log_svc
    app.state.identify_svc = identify_svc
    app.state.log_uploader_svc = log_uploader_svc
    app.state.event_bus = event_bus
    app.state.command_bus = command_bus
    app.state.alcohol_svc = alcohol_svc
    app.state.fingerprint_svc = fingerprint_svc

    # Start background services
    await http_client.start()
    await alcohol_svc.start()
    await fingerprint_svc.start()
    await sync_svc.start()
    await identify_svc.start()
    await log_uploader_svc.start()

    employee_count = await employee_svc.count()
    logger.info(
        "=== %s ready — %d employees in local DB ===",
        settings.PROJECT_NAME,
        employee_count,
    )

    yield

    # --- Shutdown ---
    logger.info("=== %s shutting down ===", settings.PROJECT_NAME)
    await log_uploader_svc.stop()
    await identify_svc.stop()
    await sync_svc.stop()
    await fingerprint_svc.stop()
    await alcohol_svc.stop()
    await http_client.stop()
    logger.info("=== %s stopped ===", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS from settings
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host=settings.API_HOST, 
        port=settings.API_PORT, 
        reload=True if os.environ.get("DEBUG") == "True" else False
    )
