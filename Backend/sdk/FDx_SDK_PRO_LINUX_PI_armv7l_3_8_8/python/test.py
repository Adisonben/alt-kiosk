from pysgfplib import PYSGFPLib
from sgfdxdevicename import SGFDxDeviceName
from sgfdxerrorcode import SGFDxErrorCode
from sgfdxsecuritylevel import SGFDxSecurityLevel
import time

def check(result, msg):
    if result != SGFDxErrorCode.SGFDX_ERROR_NONE:
        print(f"❌ {msg} failed:", result)
        exit(1)
    else:
        print(f"✅ {msg} ok")

print("=== SecuGen Fingerprint Test ===")

# 1. Create object
sgfplib = PYSGFPLib()
check(sgfplib.Create(), "Create")

# 2. Init device (auto detect)
check(sgfplib.Init(SGFDxDeviceName.SG_DEV_AUTO), "Init")

# 3. Open device
check(sgfplib.OpenDevice(0), "OpenDevice")

# 4. Get image info
width, height = sgfplib.GetImageSize()
print(f"Image size: {width} x {height}")

# Prepare buffers
image1 = bytearray(width * height)
image2 = bytearray(width * height)

print("\n👉 Place finger (1st scan)...")
time.sleep(2)
check(sgfplib.GetImage(image1), "GetImage #1")

print("👉 Place same finger again (2nd scan)...")
time.sleep(2)
check(sgfplib.GetImage(image2), "GetImage #2")

# 5. Create templates
template1 = bytearray(400)
template2 = bytearray(400)

check(
    sgfplib.CreateSG400Template(image1, template1),
    "CreateTemplate #1"
)
check(
    sgfplib.CreateSG400Template(image2, template2),
    "CreateTemplate #2"
)

# 6. Match templates
matched, score = sgfplib.MatchTemplate(
    template1,
    template2,
    SGFDxSecurityLevel.SL_NORMAL
)

print("\n=== RESULT ===")
print("Matched :", matched)
print("Score   :", score)

# 7. Close device
sgfplib.CloseDevice()
sgfplib.Terminate()

print("=== TEST FINISHED ===")
