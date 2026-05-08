"""
Fingerprint scanner protocol — binary paths and encoding helpers.

Extracted from functions/fingerprint.py.
No side effects — only constants and pure conversion functions.
"""

import os
import base64

# ── Binary paths ──────────────────────────────────────────────
# Calculate paths relative to the Backend root directory
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND_DIR = os.path.dirname(_APP_DIR)

BIN_PATH = os.path.join(_BACKEND_DIR, "bin", "finger_scan")
MATCH_BIN_PATH = os.path.join(_BACKEND_DIR, "bin", "match_template")

SCAN_CMD = ["sudo", BIN_PATH, "5000"] # 5000ms timeout
MATCH_CMD_BASE = ["sudo", MATCH_BIN_PATH]

SCAN_PROCESS_TIMEOUT = 15  # seconds
MATCH_PROCESS_TIMEOUT = 5  # seconds

TEMPLATE_SIZE = 400  # bytes — expected fingerprint template length


def raw_to_base64(raw_bytes: bytes) -> str:
    """Encode raw fingerprint bytes to base64 string."""
    if raw_bytes is None:
        return ""
    return base64.b64encode(raw_bytes).decode("utf-8")


def base64_to_raw(b64_str: str) -> bytes:
    """Decode a base64 string back to raw bytes."""
    if not b64_str:
        return b""
    try:
        return base64.b64decode(b64_str)
    except Exception:
        return b""
