import os
import subprocess
import sys
import base64
import binascii

SCAN_CMD = ["sudo", "./finger_scan", "5000"]
MATCH_CMD_BASE = ["sudo", "./match_template"]

def scan_finger(label="Finger"):
    print(f"\n=== {label} Scan ===")
    try:
        proc = subprocess.Popen(
            SCAN_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = proc.communicate(timeout=10)

        if stderr:
            print(f"[{label}] STDERR:", stderr.decode(errors="ignore").strip())

        # ---- Interpret result by size ----
        if len(stdout) == 400:
            print(f"[{label}] STATUS: SUCCESS")
            # Return raw bytes
            return stdout
        elif len(stdout) == 8:
            print(f"[{label}] STATUS: TIMEOUT")
        elif len(stdout) == 5:
            print(f"[{label}] STATUS: ERROR")
        else:
            print(f"[{label}] STATUS: UNKNOWN (Size: {len(stdout)})")
        
        return None

    except subprocess.TimeoutExpired:
        print(f"ERROR: [{label}] scan timed out")
        return None
    except Exception as e:
        print(f"ERROR: [{label}] {e}")
        return None

def main():
    # Step 1: Scan first finger
    print("Please place your FIRST finger on the scanner...")
    raw_1 = scan_finger("First Finger")
    if not raw_1:
        print("Failed to capture first template. Exiting.")
        sys.exit(1)

    # Step 2: Scan second finger
    print("\nPlease place your SECOND finger on the scanner...")
    raw_2 = scan_finger("Second Finger")
    if not raw_2:
        print("Failed to capture second template. Exiting.")
        sys.exit(1)

    # Step 3: Match templates
    print("\n=== Comparing Templates ===")
    
    # Save to temp files
    file1 = "/tmp/template1.bin"
    file2 = "/tmp/template2.bin"
    
    try:
        with open(file1, "wb") as f:
            f.write(raw_1)
        with open(file2, "wb") as f:
            f.write(raw_2)

        match_proc = subprocess.Popen(
            MATCH_CMD_BASE + [file1, file2],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = match_proc.communicate(timeout=5)

        if stderr:
            print("Match Debug Info:", stderr.decode(errors="ignore").strip())

        result = stdout.decode().strip()
        if result == "1":
            print("\nRESULT: MATCH (Templates are from the same finger)")
        elif result == "0":
            print("\nRESULT: NO MATCH (Templates are from different fingers)")
        else:
            print(f"\nRESULT: ERROR or UNKNOWN ({result})")

    except Exception as e:
        print(f"ERROR during matching: {e}")
    finally:
        # Cleanup
        for fpath in [file1, file2]:
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except:
                    pass

if __name__ == "__main__":
    main()
