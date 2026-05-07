import os
from datetime import datetime

try:
    from escpos.printer import Usb
    _escpos_available = True
except Exception:
    _escpos_available = False

try:
    from PIL import Image
    _pil_available = True
except Exception:
    _pil_available = False

VENDOR_ID = 0x04b8
PRODUCT_ID = 0x0E28

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


def print_receipt(user_name: str, user_id: str, device_id: str, status: str, value: float):
    """
    Print an alcohol test result receipt via USB ESC/POS printer.
    Returns a dict with key 'success' (bool) and optional 'error' (str).
    """
    if not _escpos_available:
        return {"success": False, "error": "python-escpos not installed"}

    try:
        p = Usb(VENDOR_ID, PRODUCT_ID)

        logo_path = os.path.join(_ASSETS_DIR, "logo.png")

        p.set(align="center", bold=True, width=3, height=3)
        if _pil_available and os.path.exists(logo_path):
            img = Image.open(logo_path).convert("1")
            p.image(img, impl="graphics")
        else:
            print(f"[printer] Logo not found at {logo_path}")

        p.text("\nALCOHOL TEST RESULT\n")
        p.set(align="left", bold=False, width=2, height=2)

        p.text("--------------------------------\n")
        p.text(f"เครื่องทดสอบ (Device ID) : {device_id}\n")
        p.text(f"รหัสผู้ทดสอบ (User ID)   : {user_id}\n")
        p.text(f"ชื่อผู้ทดสอบ (Name)      : {user_name}\n")
        p.text(f"ปริมาณแอลกอฮอล์ (Value) : {value} mg/100ml\n")
        p.text(f"สรุปผลการทดสอบ (Result) : {status}\n")
        dt_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        p.text(f"วันที่ (Date) : {dt_str}\n")
        p.text("--------------------------------\n")

        p.set(align="center", bold=True, width=2, height=2)
        if status == "PASS":
            p.text("*** PASS ***")
        elif status == "FAIL":
            p.text("*** FAIL ***")
        else:
            p.text("*** ERROR ***")

        p.cut()
        p.close()
        return {"success": True}

    except Exception as e:
        print(f"[printer] Error: {e}")
        return {"success": False, "error": str(e)}
