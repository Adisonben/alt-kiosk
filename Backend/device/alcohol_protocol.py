"""
Alcohol sensor serial protocol — constants and pure parsing functions.

Extracted from functions/alcohol.py.
No side effects, no I/O — only protocol definitions and message parsing.
"""

import re
from typing import Optional, Dict

# ── Serial configuration ─────────────────────────────────────
BAUDRATE = 4800
DATA_BITS = 8
STOP_BITS = 1
PARITY = "N"
READ_TIMEOUT = 0.1

# ── Timing ────────────────────────────────────────────────────
MEASUREMENT_TIMEOUT = 90  # seconds — overall test deadline
WARMUP_TIMEOUT = 20       # seconds — max wait for device ready

# ── Wire format ───────────────────────────────────────────────
CR_LF = b"\x0D\x0A"
CMD_START = b"$START" + CR_LF
CMD_RESET = b"$RESET" + CR_LF

# ── Known device messages ─────────────────────────────────────
STATE_TOKENS = ("$END", "$WAIT", "$STANBY", "$BREATH", "$TRIGGER", "$CALIBRATION")
FLOW_ERROR_TOKEN = "$FLOW,ERR"

_RESULT_RE = re.compile(r"\$RESULT,(\d+\.\d+)-(OK|HIGH)")


def parse_state(line: str) -> Optional[str]:
    """
    Extract a known state token from a raw serial line.

    Returns the matched token string (e.g. "$STANBY", "$FLOW,ERR") or None.
    """
    if FLOW_ERROR_TOKEN in line:
        return FLOW_ERROR_TOKEN
    for token in STATE_TOKENS:
        if token in line:
            return token
    return None


def parse_result(line: str) -> Optional[Dict[str, object]]:
    """
    Parse a $RESULT line into a dict with 'value' (float) and 'status' (str).

    Example input:  "$RESULT,0.021-OK"
    Example output: {"value": 0.021, "status": "OK"}

    Returns None if the line does not match the result pattern.
    """
    m = _RESULT_RE.match(line)
    if m:
        return {"value": float(m.group(1)), "status": m.group(2)}
    return None
