import asyncio
import threading
import time
import re

try:
    import serial
    import serial.tools.list_ports
except Exception:
    serial = None

# ── Protocol constants ────────────────────────────────────────
BAUDRATE = 4800
DATA_BITS = 8
STOP_BITS = 1
PARITY = "N"
MEASUREMENT_TIMEOUT = 90
WARMUP_TIMEOUT = 20
READ_TIMEOUT = 0.1
CR_LF = b"\x0D\x0A"

CMD_START = b"$START" + CR_LF
CMD_RESET = b"$RESET" + CR_LF

_worker_thread = None
_stop_event = threading.Event()
_is_sensor_active = False

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


def auto_detect_port():
    if serial is None:
        return None
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "USB" in p.device.upper() or "ACM" in p.device.upper():
            return p.device
    if ports:
        return ports[0].device
    return None


def parse_state(line):
    if "$FLOW,ERR" in line:
        return "$FLOW,ERR"
    for s in ("$END", "$WAIT", "$STANBY", "$BREATH", "$TRIGGER", "$CALIBRATION"):
        if s in line:
            return s
    return None


def parse_result(line):
    m = re.match(r"\$RESULT,(\d+\.\d+)-(OK|HIGH)", line)
    if m:
        return {"value": float(m.group(1)), "status": m.group(2)}
    return None


def measurement_worker(event_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    global _is_sensor_active
    ser = None

    def push(data: dict):
        asyncio.run_coroutine_threadsafe(event_queue.put(data), loop)

    try:
        _is_sensor_active = True
        push({"type": "status", "state": "connecting", "message": _STATUS_MSG["connecting"]})

        port = auto_detect_port()
        if port is None:
            push({"type": "status", "state": "error", "message": _STATUS_MSG["error"]})
            push({"type": "result", "success": False, "value": -1.0, "status": "NO_PORT"})
            return

        if serial is None:
            push({"type": "status", "state": "error", "message": _STATUS_MSG["error"]})
            push({"type": "result", "success": False, "value": -1.0, "status": "NO_PYSERIAL"})
            return

        ser = serial.Serial(
            port=port, baudrate=BAUDRATE, bytesize=DATA_BITS,
            stopbits=STOP_BITS, parity=PARITY, timeout=READ_TIMEOUT,
        )

        ser.write(CMD_RESET)
        ser.flush()
        time.sleep(0.5)
        ser.reset_input_buffer()
        ser.write(CMD_START)
        ser.flush()
        push({"type": "status", "state": "warming_up", "message": _STATUS_MSG["warming_up"]})

        deadline = time.time() + MEASUREMENT_TIMEOUT
        warmup_deadline = time.time() + WARMUP_TIMEOUT
        device_ready = False
        result_found = False

        while time.time() < deadline and not _stop_event.is_set():
            if not device_ready and time.time() > warmup_deadline:
                push({"type": "status", "state": "timeout", "message": _STATUS_MSG["timeout"]})
                push({"type": "result", "success": False, "value": -1.0, "status": "WARMUP_TIMEOUT"})
                return

            try:
                raw = ser.readline()
            except serial.SerialException:
                break

            if _stop_event.is_set():
                break
            if not raw:
                continue

            decoded = raw.decode("ascii", errors="replace").strip()
            if not decoded:
                continue

            result = parse_result(decoded)
            if result:
                result_found = True
                push({"type": "result", "success": True, "value": result["value"], "status": result["status"]})
                continue

            state = parse_state(decoded)
            if state == "$WAIT":
                push({"type": "status", "state": "warming_up", "message": _STATUS_MSG["warming_up"]})
            elif state == "$STANBY":
                device_ready = True
                push({"type": "status", "state": "ready", "message": _STATUS_MSG["ready"]})
            elif state == "$TRIGGER":
                push({"type": "status", "state": "breath_detected", "message": _STATUS_MSG["breath_detected"]})
            elif state == "$BREATH":
                push({"type": "status", "state": "sampling", "message": _STATUS_MSG["sampling"]})
            elif state == "$FLOW,ERR":
                push({"type": "status", "state": "flow_error", "message": _STATUS_MSG["flow_error"]})
            elif state == "$END" and result_found:
                break
            elif state == "$CALIBRATION":
                push({"type": "status", "state": "analyzing", "message": _STATUS_MSG["analyzing"]})

        if not result_found and not _stop_event.is_set():
            push({"type": "status", "state": "timeout", "message": _STATUS_MSG["timeout"]})
            push({"type": "result", "success": False, "value": -1.0, "status": "TIMEOUT"})

    except Exception as e:
        push({"type": "status", "state": "error", "message": _STATUS_MSG["error"]})
        push({"type": "result", "success": False, "value": -1.0, "status": f"ERROR: {e}"})
    finally:
        if ser and ser.is_open:
            try:
                ser.close()
            except Exception:
                pass
        _is_sensor_active = False
        asyncio.run_coroutine_threadsafe(event_queue.put(None), loop)  # sentinel


def reset_sensor_hardware():
    """
    Hardware-level reset: send $START → wait for $STANBY → send $RESET.
    Returns True only after $STANBY is confirmed and $RESET is sent.
    Timeout: 10 minutes.
    """
    import logging
    logger = logging.getLogger(__name__)

    RESET_TIMEOUT = 600  # 10 minutes
    SERIAL_READ_TIMEOUT = 0.5

    port = auto_detect_port()
    if not port or serial is None:
        logger.warning("reset_sensor_hardware: no port or pyserial unavailable")
        return False

    ser = None
    try:
        ser = serial.Serial(
            port=port, baudrate=BAUDRATE, bytesize=DATA_BITS,
            stopbits=STOP_BITS, parity=PARITY, timeout=SERIAL_READ_TIMEOUT,
        )

        # Send $START to begin the sensor cycle
        ser.write(CMD_START)
        ser.flush()
        logger.info("reset_sensor_hardware: sent $START, waiting for $STANBY (timeout=%ds)", RESET_TIMEOUT)

        # Wait for $STANBY (up to 10 minutes)
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

        # $STANBY confirmed — send $RESET
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
