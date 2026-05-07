import os
import base64
import subprocess
import tempfile

BIN_PATH = os.path.join(os.getcwd(), "bin", "finger_scan")
SCAN_CMD = ["sudo", BIN_PATH, "10000"]
MATCH_BIN_PATH = os.path.join(os.getcwd(), "bin", "match_template")
MATCH_CMD_BASE = ["sudo", MATCH_BIN_PATH]
SCAN_PROCESS_TIMEOUT = 15


def raw_to_base64(raw_bytes: bytes) -> str:
    if raw_bytes is None:
        return ""
    return base64.b64encode(raw_bytes).decode("utf-8")


def base64_to_raw(b64_str: str) -> bytes:
    if not b64_str:
        return b""
    try:
        return base64.b64decode(b64_str)
    except Exception as e:
        print(f"[fingerprint] Base64 decode error: {e}")
        return b""


def run_scan() -> dict:
    """
    Run the finger_scan binary and return the fingerprint template as base64.
    Returns a dict with keys: success, data, reason.
    """
    if not os.path.exists(BIN_PATH):
        return {"success": False, "data": None, "reason": f"binary not found at {BIN_PATH}"}
    try:
        proc = subprocess.Popen(
            SCAN_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = proc.communicate(timeout=SCAN_PROCESS_TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return {"success": False, "data": None, "reason": "timeout"}

        if stderr:
            print(f"[fingerprint] STDERR: {stderr.decode(errors='ignore').strip()}")

        if len(stdout) == 400:
            return {"success": True, "data": raw_to_base64(stdout)}
        elif len(stdout) == 8:
            return {"success": False, "data": None, "reason": "timeout"}
        elif len(stdout) == 5:
            return {"success": False, "data": None, "reason": "error"}
        else:
            return {"success": False, "data": None, "reason": f"unknown_size_{len(stdout)}"}
    except Exception as e:
        return {"success": False, "data": None, "reason": str(e)}


def run_compare(data1: bytes, data2: bytes) -> dict:
    """
    Compare two 400-byte fingerprint templates.
    Returns a dict with keys: match, message.
    """
    fpath1 = fpath2 = None
    try:
        t1 = tempfile.NamedTemporaryFile(delete=False)
        t2 = tempfile.NamedTemporaryFile(delete=False)
        t1.write(data1)
        t2.write(data2)
        t1.flush(); t2.flush()
        t1.close(); t2.close()
        fpath1, fpath2 = t1.name, t2.name

        cmd = MATCH_CMD_BASE + [fpath1, fpath2]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(timeout=5)

        if stderr:
            print(f"[fingerprint] Match STDERR: {stderr.decode(errors='ignore').strip()}")

        result_str = stdout.decode().strip()
        if result_str == "1":
            return {"match": True, "message": "Match"}
        elif result_str == "0":
            return {"match": False, "message": "No Match"}
        else:
            return {"match": False, "message": f"Error: {result_str}"}

    except Exception as e:
        return {"match": False, "message": str(e)}
    finally:
        for p in [fpath1, fpath2]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
