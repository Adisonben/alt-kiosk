"""
REST API — Health, device status, fingerprint, and printer endpoints.

These endpoints remain REST because they are request-response in nature.
Real-time events flow through WebSocket /ws instead.
"""

import os
import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request models ────────────────────────────────────────────

class CompareRequest(BaseModel):
    """Request model for fingerprint comparison."""
    data1: str = Field(..., description="Base64-encoded fingerprint template 1 (must decode to 400 bytes)")
    data2: str = Field(..., description="Base64-encoded fingerprint template 2 (must decode to 400 bytes)")


class PrintRequest(BaseModel):
    """Request model for printing alcohol test result receipt."""
    user_name: str = Field(..., description="Full name of the person who took the test")
    user_id: str = Field(..., description="Unique identifier for the user")
    device_id: str = Field(..., description="Identifier of the alcohol testing device")
    status: str = Field(..., description="Test result status (PASS, FAIL, ERROR)")
    value: float = Field(..., description="Alcohol concentration value in mg/100ml", ge=0)


# ── Health endpoints ──────────────────────────────────────────

@router.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Pao-L Alcohol Testing System API",
        "version": "2.0.0",
        "docs": "/docs",
        "ws": "/ws",
    }


@router.get("/health", tags=["health"])
async def health_check(request=None):
    """App health check including device statuses."""
    from fastapi import Request
    # Access device_manager from app.state
    app = request.app if request else None
    if app and hasattr(app.state, "device_manager"):
        devices = app.state.device_manager.health_check()
    else:
        devices = {}

    return {
        "status": "healthy",
        "devices": devices,
    }


@router.get("/devices", tags=["devices"])
async def device_status(request=None):
    """Return status of all registered devices."""
    from fastapi import Request
    app = request.app if request else None
    if app and hasattr(app.state, "device_manager"):
        return app.state.device_manager.health_check()
    return {}


# ── Fingerprint endpoints ─────────────────────────────────────

@router.get("/fingerprint/status", tags=["fingerprint"])
async def fingerprint_status(request=None):
    """Check if the fingerprint scanner binary is available."""
    from device.fingerprint_protocol import BIN_PATH
    exists = os.path.exists(BIN_PATH)
    return {"available": exists, "binary_path": BIN_PATH}


@router.post("/fingerprint/scan", tags=["fingerprint"])
async def fingerprint_scan(request=None):
    """
    Run the finger_scan binary and return the fingerprint template as base64.
    Blocks until the scan completes or times out (15 seconds).
    """
    from device.fingerprint_protocol import BIN_PATH
    if not os.path.exists(BIN_PATH):
        raise HTTPException(status_code=503, detail=f"finger_scan binary not found at {BIN_PATH}")

    app = request.app if request else None
    if app and hasattr(app.state, "device_manager"):
        fingerprint_svc = app.state.device_manager.get_service("fingerprint")
        if fingerprint_svc:
            return await fingerprint_svc.scan()

    raise HTTPException(status_code=503, detail="FingerprintService not available")


@router.post("/fingerprint/compare", tags=["fingerprint"])
async def fingerprint_compare(body: CompareRequest, request=None):
    """
    Compare two base64-encoded fingerprint templates.
    Returns {"match": bool, "message": str}.
    """
    app = request.app if request else None
    if app and hasattr(app.state, "device_manager"):
        fingerprint_svc = app.state.device_manager.get_service("fingerprint")
        if fingerprint_svc:
            return await fingerprint_svc.compare(body.data1, body.data2)

    raise HTTPException(status_code=503, detail="FingerprintService not available")


# ── Printer endpoints ─────────────────────────────────────────

@router.post("/printer/print", tags=["printer"])
async def print_receipt(body: PrintRequest, request=None):
    """Print an alcohol test result receipt via USB ESC/POS printer."""
    app = request.app if request else None
    if app and hasattr(app.state, "device_manager"):
        printer_svc = app.state.device_manager.get_service("printer")
        if printer_svc:
            result = await printer_svc.print_receipt(
                user_name=body.user_name,
                user_id=body.user_id,
                device_id=body.device_id,
                status=body.status,
                value=body.value,
            )
            if not result["success"]:
                raise HTTPException(status_code=503, detail=result.get("error", "Unknown error"))
            return {"success": True}

    raise HTTPException(status_code=503, detail="PrinterService not available")
