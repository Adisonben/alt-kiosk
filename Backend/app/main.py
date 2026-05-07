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
from app.services.alcohol_service import AlcoholService
from app.services.fingerprint_service import FingerprintService
from app.api.websocket import router as ws_router

# Initialize logging
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("=== %s starting (v%s) ===", settings.PROJECT_NAME, settings.VERSION)

    # Initialize core buses
    event_bus = EventBus()
    command_bus = CommandBus()

    # Initialize and start services
    alcohol_svc = AlcoholService(event_bus, command_bus)
    fingerprint_svc = FingerprintService(event_bus, command_bus)
    
    # Store in app.state for access by routers
    app.state.event_bus = event_bus
    app.state.command_bus = command_bus
    app.state.alcohol_svc = alcohol_svc
    app.state.fingerprint_svc = fingerprint_svc

    # Start service background tasks
    await alcohol_svc.start()
    await fingerprint_svc.start()

    logger.info("=== %s ready ===", settings.PROJECT_NAME)
    
    yield
    
    # --- Shutdown ---
    logger.info("=== %s shutting down ===", settings.PROJECT_NAME)
    await fingerprint_svc.stop()
    await alcohol_svc.stop()
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
