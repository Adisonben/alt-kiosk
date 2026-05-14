import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from functions.printer import print_receipt

# Call the function exactly as the app does
print("Testing functions.printer.print_receipt...")
try:
    success = print_receipt(
        user_id="123456",
        user_name="Test User",
        value=10.5,
        status="OK",
        device_id="Kiosk-Test"
    )
    if success:
        print("Success!")
    else:
        print("Failed!")
except Exception as e:
    print(f"Exception: {e}")
