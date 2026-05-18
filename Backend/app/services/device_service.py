import asyncio
import logging
import json
import os
from typing import Optional

from app.utils.http_client import CloudHttpClient
from app.utils.system_utils import get_serial_number, get_ip_address, get_mac_address
from app.config import settings

logger = logging.getLogger(__name__)

DEVICE_DATA_PATH = "data/device_data.json"

class DeviceService:
    def __init__(self, http_client: CloudHttpClient):
        self._http = http_client
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        logger.info("DeviceService: starting...")
        # 1. Register device
        await self._register_device()
        # 2. Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_worker(), name="device-heartbeat")

    async def stop(self) -> None:
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("DeviceService: stopped")

    async def _register_device(self) -> None:
        serial_num = settings.CLOUD_DEVICE_ID
        ip_addr = get_ip_address()
        mac_addr = get_mac_address()
        
        payload = {
            "serial_num": serial_num,
            "ip_address": ip_addr,
            "mac_address": mac_addr
        }
        
        logger.info(f"DeviceService: Registering device with serial={serial_num}, ip={ip_addr}, mac={mac_addr}")
        
        try:
            # Assuming endpoint is /device/register
            response = await self._http.post("/device/register", json=payload)
            # Handle standard json response structure from laravel
            if isinstance(response, dict):
                data = response.get("data", response)
                if response.get("success", True):  # Sometimes only returns data if success
                    self._save_device_data(data)
                    logger.info("DeviceService: Registration successful. Data saved.")
                else:
                    logger.warning(f"DeviceService: Registration failed, message={response.get('message')}")
            else:
                 logger.warning("DeviceService: Registration returned unexpected format")
        except Exception as e:
            logger.error(f"DeviceService: Registration exception - {e}")

    def _save_device_data(self, data: dict) -> None:
        os.makedirs(os.path.dirname(DEVICE_DATA_PATH) or ".", exist_ok=True)
        # Cloud response: org_id, org_code, device_id, status
        
        existing_data = {}
        if os.path.exists(DEVICE_DATA_PATH):
            try:
                with open(DEVICE_DATA_PATH, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                pass
        
        existing_data.update({
            "org_id": data.get("org_id", existing_data.get("org_id")),
            "org_code": data.get("org_code", existing_data.get("org_code")),
            "device_id": data.get("device_id", existing_data.get("device_id")),
            "status": data.get("status", existing_data.get("status"))
        })

        try:
            with open(DEVICE_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2)
        except Exception as e:
            logger.error(f"DeviceService: Failed to save device data - {e}")

    async def _heartbeat_worker(self) -> None:
        while True:
            try:
                await asyncio.sleep(60)
                device_id = settings.CLOUD_DEVICE_ID
                if device_id:
                    await self._http.post("/device/heartbeat", json={
                        "device_id": device_id,
                        "status": "online"
                    })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"DeviceService: Heartbeat error (transient) - {e}")
