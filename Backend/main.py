"""
Pao-L Kiosk Backend — Main entry point (slim).

Wires together:
    EventBus → CommandBus → AlcoholService → WebSocket

Run: python main.py
"""

import sys
import os
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils.logger import setup_logging, get_logger
from core.event_bus import EventBus
from core.command_bus import CommandBus
from services.alcohol_service import AlcoholService
from api.websocket import router as ws_router

# Initialize logging first
setup_logging()
logger = get_logger(__name__)

# ── FastAPI app ───────────────────────────────────────────────

app = FastAPI(
    title="Pao-L Alcohol Testing System API",
    description="Slim kiosk backend — WebSocket + AlcoholSensor only",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ws_router)


# ── Startup ───────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("=== Pao-L Backend starting ===")

    # Core buses
    event_bus = EventBus()
    command_bus = CommandBus()

    # Alcohol service
    alcohol_svc = AlcoholService(event_bus, command_bus)

    # Store in app.state for access by routers
    app.state.event_bus = event_bus
    app.state.command_bus = command_bus
    app.state.alcohol_svc = alcohol_svc

    # Start alcohol service
    await alcohol_svc.start()

    logger.info("=== Pao-L Backend ready ===")


# ── Shutdown ──────────────────────────────────────────────────

@app.on_event("shutdown")
async def shutdown():
    logger.info("=== Pao-L Backend shutting down ===")

    await app.state.alcohol_svc.stop()

    logger.info("=== Pao-L Backend stopped ===")


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
