from functions.printer import print_receipt

def test_manual_print():
    print("Testing printer...")
    user_id = "123456"
    user_name = "Test User"
    value = "10.5"
    status = "OK"
    device_id = "Kiosk-TEST"
    
    success = print_receipt(user_id, user_name, value, status, device_id)
    if success:
        print("Test passed!")
    else:
        print("Test failed!")

if __name__ == "__main__":
    test_manual_print()
