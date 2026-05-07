from PIL import Image
import os
from escpos.printer import Usb

try:
    # Use USB driver as verified in test_printer.py
    p = Usb(0x04b8, 0x0e28)
    
    # Locate basics/logo.png relative to this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, '..', 'assets', 'logo.png')

    if not os.path.exists(logo_path):
        print(f"Error: Logo not found at {logo_path}")
    else:
        img = Image.open(logo_path).convert("1")
        p.image(img, impl="graphics")
        p.cut()
        print("Print command sent.")

except Exception as e:
    print(f"Error: {e}")
