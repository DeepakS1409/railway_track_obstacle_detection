"""
Automated Test for FastAPI Backend
Simulates Expo Go mobile app uploading camera frames to /detect.
"""

import sys
import time
import base64
import requests
import cv2
import numpy as np

def run_test(server_url: str = "http://127.0.0.1:8000"):
    print("=" * 65)
    print(" [TEST] FASTAPI BACKEND & EXPO GO FRAME UPLOAD TEST")
    print("=" * 65)
    print(f"Target Server: {server_url}")

    # 1. Test Health Endpoint
    print("\n[STEP 1] Testing /health endpoint...")
    try:
        r = requests.get(f"{server_url}/health", timeout=3.0)
        print(f"Response ({r.status_code}): {r.json()}")
        assert r.status_code == 200, "Health check failed"
        print("[PASS] Health check successful!")
    except Exception as e:
        print(f"[FAIL] Could not reach server: {e}")
        return False

    # 2. Test Synthetic Frame Detection
    print("\n[STEP 2] Simulating Mobile Phone JPEG frame upload to /detect...")
    # Create a synthetic 480x640 frame
    blank_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw simple shape to simulate image
    cv2.putText(blank_img, "EXPO TEST FRAME", (180, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    
    # Encode as JPEG
    _, buffer = cv2.imencode(".jpg", blank_img, [cv2.IMWRITE_JPEG_QUALITY, 50])
    b64_str = base64.b64encode(buffer).decode("utf-8")

    t0 = time.time()
    try:
        r = requests.post(
            f"{server_url}/detect",
            json={"image": b64_str},
            headers={"Content-Type": "application/json"},
            timeout=10.0
        )
        elapsed_ms = (time.time() - t0) * 1000
        print(f"Response ({r.status_code}) in {elapsed_ms:.1f}ms:")
        data = r.json()
        print(f"  - Status        : {data.get('status')}")
        print(f"  - Hazard        : {data.get('is_hazard')}")
        print(f"  - Decision State: {data.get('decision_state')}")
        print(f"  - Detections    : {data.get('detections')}")
        print(f"  - ESP32 State   : {data.get('esp32')}")

        assert r.status_code == 200, f"Expected 200 OK, got {r.status_code}"
        assert data.get("status") == "success", "Response status is not success"
        print("[PASS] Frame processing and inference completed successfully!")
    except Exception as e:
        print(f"[FAIL] /detect request failed: {e}")
        return False

    print("\n" + "=" * 65)
    print(" ALL BACKEND TESTS PASSED SUCCESSFULLY! ")
    print("=" * 65)
    return True

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    success = run_test(url)
    sys.exit(0 if success else 1)
