"""
Printer protocol — ESC/POS constants and asset paths.

Extracted from functions/printer.py.
"""

import os

# ── USB ESC/POS printer identifiers ──────────────────────────
VENDOR_ID = 0x04B8
PRODUCT_ID = 0x0E28

# ── Asset directory ───────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(_BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
