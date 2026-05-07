"""
Serial utility helpers — port detection and connection with retry.

Used by AlcoholService to manage the serial connection to the breath sensor.
"""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import serial
    import serial.tools.list_ports
    _serial_available = True
except ImportError:
    serial = None
    _serial_available = False
    logger.warning("pyserial not installed — serial functions disabled")


def is_serial_available() -> bool:
    """Check if the pyserial library is installed."""
    return _serial_available


def auto_detect_port() -> Optional[str]:
    """
    Scan system serial ports and return the first USB/ACM device path.
    Falls back to the first available port if no USB/ACM match.
    Returns None if no ports found or pyserial is unavailable.
    """
    if not _serial_available:
        return None

    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "USB" in p.device.upper() or "ACM" in p.device.upper():
            logger.info("auto_detect_port: found USB/ACM port %s (%s)", p.device, p.description)
            return p.device

    if ports:
        fallback = ports[0].device
        logger.info("auto_detect_port: no USB/ACM, falling back to %s", fallback)
        return fallback

    logger.warning("auto_detect_port: no serial ports found")
    return None


def open_serial(
    port: str,
    baudrate: int = 4800,
    bytesize: int = 8,
    stopbits: int = 1,
    parity: str = "N",
    timeout: float = 0.1,
    retries: int = 3,
    backoff: float = 1.0,
):
    """
    Open a serial connection with retry and exponential backoff.

    Args:
        port: Device path (e.g. /dev/ttyUSB0).
        baudrate: Baud rate.
        bytesize: Data bits.
        stopbits: Stop bits.
        parity: Parity ('N', 'E', 'O').
        timeout: Read timeout in seconds.
        retries: Number of retry attempts on failure.
        backoff: Initial backoff delay in seconds (doubles each retry).

    Returns:
        An open serial.Serial instance.

    Raises:
        serial.SerialException: If all retries are exhausted.
        RuntimeError: If pyserial is not installed.
    """
    if not _serial_available:
        raise RuntimeError("pyserial is not installed")

    delay = backoff
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                stopbits=stopbits,
                parity=parity,
                timeout=timeout,
            )
            logger.info("open_serial: connected to %s on attempt %d", port, attempt)
            return ser
        except serial.SerialException as exc:
            last_error = exc
            logger.warning(
                "open_serial: attempt %d/%d failed for %s — %s (retry in %.1fs)",
                attempt, retries, port, exc, delay,
            )
            if attempt < retries:
                time.sleep(delay)
                delay *= 2  # exponential backoff

    raise last_error
