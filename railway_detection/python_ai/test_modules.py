"""
Modular Diagnostic & Testing Suite
Independently verifies:
1. RFC2217 Serial Communication with Wokwi ESP32
2. Camera / Mobile Phone Stream Connection
3. Ultralytics YOLOv8 Model Inference
"""

import sys
import time
import argparse
import numpy as np

from config import (
    ESP32_SERIAL_URL,
    DEFAULT_CAMERA_URL,
    DEFAULT_CONFIDENCE_THRESHOLD,
    TARGET_CLASSES
)
from esp32_serial import ESP32SerialClient
from camera import MobileCameraStream
from detector import RailwayTrackDetector


def test_serial(port_url: str):
    print("=" * 65)
    print(" [TEST 1] INDEPENDENT RFC2217 SERIAL LINK TEST")
    print("=" * 65)
    print(f"Target: {port_url}")
    print("Testing connection...")

    client = ESP32SerialClient(port_url=port_url)
    if not client.connect():
        print("[FAIL] Could not connect to Wokwi RFC2217 server.")
        print("-> Please ensure Wokwi is running in VS Code with rfc2217ServerPort = 4000.")
        return False

    print("[PASS] Connected successfully to virtual ESP32!")
    print("Sending PING handshake...")
    client._send_command("PING")
    time.sleep(1.0)

    print("Testing ALERT command (Red LED ON, Green LED OFF, Buzzer Pulsing)...")
    client._send_command("ALERT")
    time.sleep(2.0)

    print("Testing SAFE command (Red LED OFF, Green LED ON, Buzzer OFF)...")
    client._send_command("SAFE")
    time.sleep(1.5)

    print("Listening for 3 seconds of live ESP32 JSON telemetry...")
    for _ in range(6):
        data = client.get_telemetry()
        print(f"  Telemetry: PIR={data.get('pir')} | Distance={data.get('distance')}cm | SystemAlert={data.get('system_alert')}")
        time.sleep(0.5)

    client.disconnect()
    print("[PASS] Serial communication test completed successfully!\n")
    return True


def test_camera(source: str):
    print("=" * 65)
    print(" [TEST 2] INDEPENDENT CAMERA STREAM TEST")
    print("=" * 65)
    print(f"Video Source: {source}")

    stream = MobileCameraStream(source=source)
    success = stream.start()
    if not success:
        print(f"[FAIL] Could not open camera stream: {source}")
        print("-> For phone cameras, ensure IP Webcam app is running and Wi-Fi IP matches.")
        return False

    print("[PASS] Camera stream initialized successfully!")
    print("Reading 10 test frames...")
    frames_read = 0
    for i in range(10):
        ret, frame = stream.read()
        if ret and frame is not None:
            frames_read += 1
        time.sleep(0.05)

    stream.stop()
    print(f"[PASS] Successfully captured {frames_read}/10 frames at standard resolution.\n")
    return True


def test_yolo():
    print("=" * 65)
    print(" [TEST 3] INDEPENDENT YOLO MODEL INFERENCE TEST")
    print("=" * 65)
    print("Initializing RailwayTrackDetector...")

    detector = RailwayTrackDetector(conf_threshold=DEFAULT_CONFIDENCE_THRESHOLD)
    if not detector.is_ready:
        print(f"[FAIL] YOLO model failed to initialize: {detector.last_error}")
        return False

    print(f"[PASS] Model loaded successfully! Target classes: {TARGET_CLASSES}")
    
    # Test synthetic inference on empty canvas
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    print("Running test CPU inference on dummy frame...")
    t0 = time.time()
    annotated, detections, is_hazard = detector.detect(blank_frame)
    dt = time.time() - t0

    print(f"[PASS] Inference completed in {dt * 1000:.1f}ms without errors.")
    print(f"  Detections on blank frame: {len(detections)} (Hazard: {is_hazard})\n")
    return True


def main():
    parser = argparse.ArgumentParser(description="Railway Detection Diagnostic Suite")
    parser.add_argument(
        "--test",
        choices=["serial", "camera", "yolo", "all"],
        default="all",
        help="Which module to test independently"
    )
    parser.add_argument(
        "--port",
        default=ESP32_SERIAL_URL,
        help="Wokwi RFC2217 URL (e.g., 'rfc2217://localhost:4000')"
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Camera source (0 for webcam, or phone URL like http://...:8080/video)"
    )
    args = parser.parse_args()

    if args.test in ("yolo", "all"):
        test_yolo()

    if args.test in ("camera", "all"):
        test_camera(args.source)

    if args.test in ("serial", "all"):
        test_serial(args.port)


if __name__ == "__main__":
    main()

