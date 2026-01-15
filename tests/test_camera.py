"""
Test camera streaming from Bambu Lab A1
"""
from bambulab import JPEGFrameStream
import time

# Printer configuration
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
MODEL = "A1"

print(f"Connecting to camera at {PRINTER_IP}...")
print(f"Using access code: {ACCESS_CODE}")
print(f"Model: {MODEL}")

try:
    stream = JPEGFrameStream(PRINTER_IP, ACCESS_CODE)
    stream.connect()
    print("✅ Connected to camera!")
    
    # Try to get a frame
    print("Getting frame...")
    frame = stream.get_frame()
    
    if frame:
        print(f"✅ Got frame! Size: {len(frame)} bytes")
        # Save snapshot (frame is raw JPEG bytes)
        with open("camera_test.jpg", "wb") as f:
            f.write(frame)
        print("✅ Snapshot saved as camera_test.jpg")
    else:
        print("❌ No frame received")
    
    stream.disconnect()
    print("Disconnected")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
