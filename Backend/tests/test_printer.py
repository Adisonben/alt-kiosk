from escpos.printer import Usb
from datetime import datetime

def print_result(user_name, result, value):
    p = Usb(0x04b8, 0x0e28)

    p.set(align='center', bold=True, width=2, height=2)
    p.text("ALCOHOL TEST RESULT\n")
    p.set(align='left', bold=False, width=1, height=1)

    p.text("--------------------------------\n")
    p.text(f"Name : {user_name}\n")
    p.text(f"Result : {result}\n")
    p.text(f"Value : {value} mg%\n")
    p.text(f"Date : {datetime.now()}\n")
    p.text("--------------------------------\n")

    if result == "PASS":
        p.set(align='center', bold=True)
        p.text("\n*** PASS ***\n")
    else:
        p.set(align='center', bold=True)
        p.text("\n*** FAIL ***\n")

    p.text("\n\n")
    p.cut()

# เรียกใช้
print_result("Meanie", "PASS", 0.00)