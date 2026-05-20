"""
AlcoholService — Manages the alcohol breath sensor lifecycle.

Subscribes to CommandBus for: START_ALCOHOL, STOP_ALCOHOL, RESET.
Publishes alcohol_state and alcohol_result events to EventBus.
Runs the serial reader in a background thread with auto-reconnect.
"""

import asyncio
import threading
import time
import logging
from typing import Optional

from app.hardware.alcohol_protocol import (
    BAUDRATE, DATA_BITS, STOP_BITS, PARITY, READ_TIMEOUT,
    MEASUREMENT_TIMEOUT, WARMUP_TIMEOUT,
    CMD_START, CMD_RESET,
    parse_state, parse_result,
)
from app.utils.serial_utils import auto_detect_port, open_serial, is_serial_available

logger = logging.getLogger(__name__)

_STATUS_MSG = {
    "connecting":      "กำลังเชื่อมต่ออุปกรณ์... / Connecting...",
    "warming_up":      "กำลังอุ่นเครื่อง... / Warming up...",
    "ready":           "พร้อมเป่า! กรุณาเป่าลมหายใจ / Ready! Please blow",
    "breath_detected": "ตรวจพบลมหายใจ / Breath detected",
    "sampling":        "กำลังเก็บตัวอย่าง... / Sampling breath...",
    "analyzing":       "กำลังวิเคราะห์... / Analyzing...",
    "flow_error":      "เป่าไม่ถูกต้อง กรุณารอแล้วลองใหม่ / Incorrect breath, retrying...",
    "timeout":         "หมดเวลา กรุณาลองใหม่ / Timeout, please retry",
    "error":           "ไม่สามารถเชื่อมต่ออุปกรณ์ได้ / Device connection error",
}


class AlcoholService:
    """
    Owns the alcohol sensor thread and serial connection.

    Lifecycle:
        start() → subscribes to command bus, ready to accept commands.
        stop()  → stops sensor thread, unsubscribes.
    """

    def __init__(self, event_bus, command_bus, scan_log_svc, http_client, camera_svc, anonymous_test_svc=None):
        self._event_bus = event_bus
        self._command_bus = command_bus
        self._scan_log_svc = scan_log_svc
        self._anonymous_test_svc = anonymous_test_svc
        self._http = http_client
        self._camera_svc = camera_svc
        self._cmd_queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()
        self._is_active = False
        self._is_connected = False
        self._cmd_listener_task: Optional[asyncio.Task] = None
        self._active_employee_id: Optional[str] = None
        
        # Camera session state
        self._current_session_image: Optional[str] = None
        self._image_captured = False

    # ── Lifecycle ─────────────────────────────────────────────

    async def start(self) -> None:
        """Subscribe to command bus and start listening for commands."""
        self._loop = asyncio.get_running_loop()
        self._cmd_queue = await self._command_bus.subscribe(
            filter_types={"START_ALCOHOL", "STOP_ALCOHOL", "RESET", "RESET_SENSOR"}
        )
        self._cmd_listener_task = asyncio.create_task(self._listen_commands())
        logger.info("AlcoholService started")

    async def stop(self) -> None:
        """Stop the sensor thread and unsubscribe from command bus."""
        self._stop_measurement()
        if self._cmd_listener_task:
            self._cmd_listener_task.cancel()
            try:
                await self._cmd_listener_task
            except asyncio.CancelledError:
                pass
        if self._cmd_queue:
            await self._command_bus.unsubscribe(self._cmd_queue)
        logger.info("AlcoholService stopped")

    # ── Health ─────────────────────────────────────────────────

    def is_alive(self) -> bool:
        """True if the command listener task is running (idle = healthy)."""
        return self._cmd_listener_task is not None and not self._cmd_listener_task.done()

    def is_connected(self) -> bool:
        """True if the serial port is currently open."""
        with self._state_lock:
            return self._is_connected

    def set_active_employee_id(self, employee_id: str) -> None:
        """Store the currently active employee session ID."""
        self._active_employee_id = employee_id
        logger.info("AlcoholService: session active employee_id set to '%s'", employee_id)

    # ── Command listener ──────────────────────────────────────

    async def _listen_commands(self) -> None:
        """Async loop: wait for commands from the CommandBus."""
        try:
            while True:
                cmd = await self._cmd_queue.get()
                cmd_type = cmd.get("command")
                session_id = cmd.get("session_id")

                if cmd_type == "START_ALCOHOL":
                    employee_id = cmd.get("params", {}).get("employee_id")
                    is_anonymous = cmd.get("params", {}).get("is_anonymous", False)
                    if not employee_id:
                         employee_id = self._active_employee_id
                    self._start_measurement(session_id, employee_id, is_anonymous)
                elif cmd_type in ("STOP_ALCOHOL", "RESET"):
                    self._stop_measurement()
                    self._active_employee_id = None
                elif cmd_type == "RESET_SENSOR":
                    self._reset_sensor()
        except asyncio.CancelledError:
            pass

    # ── Measurement control ───────────────────────────────────

    def _start_measurement(
        self, session_id: Optional[str] = None, employee_id: Optional[str] = None, is_anonymous: bool = False
    ) -> None:
        """Spawn the sensor worker thread."""
        with self._state_lock:
            if self._is_active:
                logger.warning("AlcoholService: measurement already active, ignoring START")
                return
            self._is_active = True

        # Reset camera session state and start camera early for warmup
        self._current_session_image = None
        self._image_captured = False
        self._camera_svc.start()

        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._measurement_worker,
            args=(session_id, employee_id, is_anonymous),
            daemon=True,
            name="alcohol-sensor",
        )
        self._worker_thread.start()
        logger.info(
            "AlcoholService: measurement started (session=%s, employee=%s)",
            session_id, employee_id
        )

    def _stop_measurement(self) -> None:
        """Signal the worker thread to stop."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=3)
        self._worker_thread = None
        
        # Stop camera to release resources
        self._camera_svc.stop()
        logger.info("AlcoholService: measurement stopped")

    def _reset_sensor(self) -> None:
        """Trigger hardware reset in a background thread."""

        def run():
            logger.info("AlcoholService: starting hardware reset")
            success = self._reset_sensor_hardware()
            logger.info("AlcoholService: hardware reset %s", "success" if success else "failed")
            self._event_bus.publish_threadsafe(
                {"type": "reset_result", "success": success},
                self._loop,
            )

        threading.Thread(target=run, daemon=True, name="alcohol-reset").start()

    @staticmethod
    def _reset_sensor_hardware() -> bool:
        """
        Hardware-level reset: send $START → wait for $STANBY → send $RESET.
        Returns True only after $STANBY is confirmed and $RESET is sent.
        Timeout: 10 minutes.
        """
        RESET_TIMEOUT = 600  # 10 minutes
        SERIAL_READ_TIMEOUT = 0.5

        if not is_serial_available():
            logger.warning("reset_sensor_hardware: pyserial unavailable")
            return False

        port = auto_detect_port()
        if not port:
            logger.warning("reset_sensor_hardware: no serial port found")
            return False

        ser = None
        try:
            import serial
            ser = serial.Serial(
                port=port, baudrate=BAUDRATE, bytesize=DATA_BITS,
                stopbits=STOP_BITS, parity=PARITY, timeout=SERIAL_READ_TIMEOUT,
            )

            ser.write(CMD_START)
            ser.flush()
            logger.info("reset_sensor_hardware: sent $START, waiting for $STANBY (timeout=%ds)", RESET_TIMEOUT)

            deadline = time.time() + RESET_TIMEOUT
            stanby_received = False

            while time.time() < deadline:
                raw = ser.readline().decode("ascii", errors="replace").strip()
                if not raw:
                    continue

                state = parse_state(raw)
                if state:
                    logger.debug("reset_sensor_hardware: received state %s", state)

                if state == "$STANBY":
                    stanby_received = True
                    break

            if not stanby_received:
                logger.warning("reset_sensor_hardware: timed out waiting for $STANBY")
                return False

            ser.write(CMD_RESET)
            ser.flush()
            logger.info("reset_sensor_hardware: $STANBY received, sent $RESET — success")
            return True

        except Exception as exc:
            logger.exception("reset_sensor_hardware: error — %s", exc)
            return False
        finally:
            if ser and ser.is_open:
                ser.close()

    # ── Sensor worker thread ──────────────────────────────────

    def _measurement_worker(
        self, session_id: Optional[str], employee_id: Optional[str], is_anonymous: bool = False
    ) -> None:
        """
        Blocking thread: open serial, send commands, read sensor data,
        publish events to EventBus via publish_threadsafe.
        """
        ser = None

        def push(event: dict) -> None:
            if session_id:
                event["session_id"] = session_id
            self._event_bus.publish_threadsafe(event, self._loop)

        try:
            push({"type": "alcohol_state", "state": "connecting", "message": _STATUS_MSG["connecting"]})

            if not is_serial_available():
                push({"type": "alcohol_state", "state": "error", "message": _STATUS_MSG["error"]})
                push({"type": "alcohol_result", "success": False, "value": -1.0, "status": "NO_PYSERIAL"})
                return

            port = auto_detect_port()
            if port is None:
                push({"type": "alcohol_state", "state": "error", "message": _STATUS_MSG["error"]})
                push({"type": "alcohol_result", "success": False, "value": -1.0, "status": "NO_PORT"})
                return

            try:
                ser = open_serial(
                    port=port,
                    baudrate=BAUDRATE,
                    bytesize=DATA_BITS,
                    stopbits=STOP_BITS,
                    parity=PARITY,
                    timeout=READ_TIMEOUT,
                    retries=3,
                    backoff=1.0,
                )
            except Exception as exc:
                logger.error("AlcoholService: serial open failed — %s", exc)
                push({"type": "alcohol_state", "state": "error", "message": _STATUS_MSG["error"]})
                push({"type": "alcohol_result", "success": False, "value": -1.0, "status": f"SERIAL_ERROR: {exc}"})
                return

            with self._state_lock:
                self._is_connected = True

            # Reset + start
            ser.write(CMD_RESET)
            ser.flush()
            time.sleep(0.5)
            ser.reset_input_buffer()
            ser.write(CMD_START)
            ser.flush()
            push({"type": "alcohol_state", "state": "warming_up", "message": _STATUS_MSG["warming_up"]})

            deadline = time.time() + MEASUREMENT_TIMEOUT
            warmup_deadline = time.time() + WARMUP_TIMEOUT
            device_ready = False
            result_found = False

            while time.time() < deadline and not self._stop_event.is_set():
                # Warmup timeout guard
                if not device_ready and time.time() > warmup_deadline:
                    push({"type": "alcohol_state", "state": "timeout", "message": _STATUS_MSG["timeout"]})
                    push({"type": "alcohol_result", "success": False, "value": -1.0, "status": "WARMUP_TIMEOUT"})
                    return

                try:
                    raw = ser.readline()
                except Exception:
                    logger.warning("AlcoholService: serial read error, breaking")
                    break

                if self._stop_event.is_set():
                    break
                if not raw:
                    continue

                decoded = raw.decode("ascii", errors="replace").strip()
                if not decoded:
                    continue

                # Check for result
                result = parse_result(decoded)
                if result:
                    result_found = True
                    val = result["value"]
                    status = result["status"]

                    push({
                         "type": "alcohol_result",
                         "success": True,
                         "value": val,
                         "status": status,
                         "image_base64": self._current_session_image
                    })

                    # Try to upload result immediately, fallback to local DB on failure
                    if is_anonymous:
                        async def upload_anonymous_or_log():
                             success = await self._http.post_anonymous_scan_result(
                                 scan_type="alcohol",
                                 result="pass" if status == "OK" else "fail",
                                 value=val,
                                 image_base64=self._current_session_image
                             )
                             if not success:
                                 from app.config import settings
                                 await self._anonymous_test_svc.log_anonymous_test(
                                     org_id=settings.CLOUD_ORG_ID,
                                     value=val,
                                     status=status,
                                     image=self._current_session_image
                                 )
                        asyncio.run_coroutine_threadsafe(upload_anonymous_or_log(), self._loop)
                    elif employee_id:
                        async def upload_or_log():
                            success = await self._http.post_scan_result(
                                employee_id=employee_id,
                                scan_type="alcohol",
                                result="pass" if status == "OK" else "fail",
                                value=val,
                                image_base64=self._current_session_image
                            )
                            if not success:
                                await self._scan_log_svc.log_alcohol(employee_id, val, status)

                        asyncio.run_coroutine_threadsafe(upload_or_log(), self._loop)
                    continue

                # Check for state
                state = parse_state(decoded)
                if state == "$WAIT":
                    push({"type": "alcohol_state", "state": "warming_up", "message": _STATUS_MSG["warming_up"]})
                elif state == "$STANBY":
                    device_ready = True
                    push({"type": "alcohol_state", "state": "ready", "message": _STATUS_MSG["ready"]})
                elif state == "$TRIGGER":
                    push({"type": "alcohol_state", "state": "breath_detected", "message": _STATUS_MSG["breath_detected"]})
                    if not self._image_captured:
                        self._image_captured = True
                        def run_capture():
                            logger.info("AlcoholService: triggering camera snapshot capture ($TRIGGER)")
                            self._current_session_image = self._camera_svc.capture_image_base64()
                        threading.Thread(target=run_capture, daemon=True, name="alcohol-camera-capture").start()
                elif state == "$BREATH":
                    push({"type": "alcohol_state", "state": "sampling", "message": _STATUS_MSG["sampling"]})
                    if not self._image_captured:
                        self._image_captured = True
                        def run_capture():
                            logger.info("AlcoholService: triggering camera snapshot capture ($BREATH)")
                            self._current_session_image = self._camera_svc.capture_image_base64()
                        threading.Thread(target=run_capture, daemon=True, name="alcohol-camera-capture").start()
                elif state == "$FLOW,ERR":
                    push({"type": "alcohol_state", "state": "flow_error", "message": _STATUS_MSG["flow_error"]})
                elif state == "$END" and result_found:
                    break
                elif state == "$CALIBRATION":
                    push({"type": "alcohol_state", "state": "analyzing", "message": _STATUS_MSG["analyzing"]})

            # Overall timeout
            if not result_found and not self._stop_event.is_set():
                push({"type": "alcohol_state", "state": "timeout", "message": _STATUS_MSG["timeout"]})
                push({"type": "alcohol_result", "success": False, "value": -1.0, "status": "TIMEOUT"})

        except Exception as exc:
            logger.exception("AlcoholService: unexpected error in worker")
            push({"type": "alcohol_state", "state": "error", "message": _STATUS_MSG["error"]})
            push({"type": "alcohol_result", "success": False, "value": -1.0, "status": f"ERROR: {exc}"})
        finally:
            if ser and ser.is_open:
                try:
                    ser.close()
                except Exception:
                    pass
            with self._state_lock:
                self._is_connected = False
                self._is_active = False
            self._active_employee_id = None
            logger.info("AlcoholService: worker thread exited")
