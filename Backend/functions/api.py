
import json

def get_user_by_id(employee_id):
    """
    Mock API to get user details by Employee ID.
    Returns a dict with user info if found, else None.
    """
    # Mock data for testing
    if employee_id == "123456":
         # Use the sample finger data from the original authing.py for testing success
        finger_data = "504DKWpUIR7u4ZKlo5WCwPZlIE44j6GSx16/lufg3nYu/3valgrlPFO/yK+xQVSXuHAt+ocT5IKHh28XeO0sJdwivF06WnNP9RjMOzDhuLJfvV7Md1p1K2Eb6ielz94R2Bf/WKe8ctQ5E6ALGLQlnyx5K+pBFPAlKSxIY8zF0xEbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fBstyeuvDV9gKmT/R/Bs+XwbLcnrrw1fYCpk/0fwbPl8Gy3J668NX2AqZP9H8Gz5fA=="
        return {
            "user_id": "123456",
            "name": "Test User",
            "finger_data": finger_data
        }
    return None


def send_test_result(data):
    # TODO: Connect to actual API
    # requests.post("http://api.server.com/result", json=data)
    print(f"Mock sending data to API: {data}")

