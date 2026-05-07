import sys
import os

# Add project root to path so we can import functions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from functions.printer import print_result

def test():
    print("Testing print_result function...")
    try:
        success = print_result(
            user_name="Test User",
            status="PASS",
            value="0.00"
        )
        if success:
            print("Function returned True.")
        else:
            print("Function returned False (Expected if no printer/script error).")
    except Exception as e:
        print(f"Test failed with exception: {e}")

if __name__ == "__main__":
    test()
