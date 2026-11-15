"""
Main Pipeline Runner: YOLO + Camera + ESP32 Serial Integration
Can be run directly from terminal for desktop monitoring.
"""

import cv2
import time
import argparse
from config import (
    DEFAULT_SERIAL_PORT,
    DEFAULT_CAMERA_SOURCE,
    SERIAL_BAUD_RATE,
    DETECTION_CONFIDENCE_THRESHOLD
)
from serial_manager import SerialManager
from detector import RailwayTrackDetector
from camera import VideoStreamHandler

def main():
    parser = argparse.ArgumentParser(description="Railway Track Obstacle Detection System")
    parser.add_argument(
        "--source",
        default=str(DEFAULT_CAMERA_SOURCE),
        help="Camera index (0), video file path, or phone stream URL (http://...:8080/video)"
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_SERIAL_PORT,
        help="Serial port / RFC2217 URL (e.g., 'rfc2217://localhost:4000' or 'COM3')"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=DETECTION_CONFIDENCE_THRESHOLD,
        help="Detection confidence threshold (0.0 to 1.0)"
    )
    args = parser.parse_args()

    print("================================================================")
    print("   RAILWAY TRACK HUMAN & ANIMAL DETECTION SYSTEM (DESKTOP)     ")
    print("================================================================")
    print(f"Video Source: {args.source}")
    print(f"ESP32 Link  : {args.port}")
    print("----------------------------------------------------------------")

    # 1. Initialize Serial Manager
    serial_manager = SerialManager(port=args.port, baudrate=SERIAL_BAUD_RATE)
    is_serial_connected = serial_manager.connect()
    if is_serial_connected:
        print("[INFO] Connected to ESP32 successfully.")
    else:
        print("[WARNING] Could not connect to ESP32. Running in vision-only mode.")

    # 2. Initialize Camera and YOLO Detector
    cam = VideoStreamHandler(source=args.source)
    detector = RailwayTrackDetector(conf_thresh=args.conf)

    fps_counter = 0
    fps_timer = time.time()
    current_fps = 0.0

    print("\nStarting video feed... Press 'q' in the window to quit.")

    try:
        while True:
            ret, frame = cam.read_frame()
            if not ret or frame is None:
                print("[WARNING] Frame capture error. Retrying...")
                time.sleep(0.1)
                continue

            # Calculate FPS
            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                current_fps = fps_counter / (time.time() - fps_timer)
                fps_counter = 0
                fps_timer = time.time()

            # Run Object Detection
            annotated_frame, detections, obstacle_found = detector.detect(frame)

            # Decision Logic -> Serial Command
            if obstacle_found:
                serial_manager.send_alert()
            else:
                serial_manager.send_safe()

            # Read latest ESP32 telemetry
            telemetry = serial_manager.get_latest_telemetry()

            # Render Telemetry HUD on OpenCV frame
            hud_bg_color = (0, 0, 180) if obstacle_found else (40, 40, 40)
            cv2.rectangle(annotated_frame, (0, 0), (640, 70), hud_bg_color, -1)

            # System Status Banner
            status_text = "STATUS: TRACK BLOCKED (ALERT)" if obstacle_found else "STATUS: TRACK CLEAR (SAFE)"
            cv2.putText(
                annotated_frame,
                status_text,
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            # Details HUD line
            dist_val = telemetry.get("distance", -1)
            dist_txt = f"{dist_val:.1f}cm" if dist_val > 0 else "N/A"
            pir_txt = "MOTION" if telemetry.get("pir") == 1 else "IDLE"
            esp_status = "CONNECTED" if serial_manager.is_connected() else "OFFLINE"

            telemetry_line = f"ESP32: {esp_status} | PIR: {pir_txt} | US-Dist: {dist_txt} | FPS: {current_fps:.1f}"
            cv2.putText(
                annotated_frame,
                telemetry_line,
                (10, 52),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (200, 255, 200) if serial_manager.is_connected() else (200, 200, 255),
                1
            )

            # Show Frame
            cv2.imshow("Railway Track Detection Monitor", annotated_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('a'):
                serial_manager.send_alert(force=True)
            elif key == ord('s'):
                serial_manager.send_safe(force=True)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        cam.release()
        cv2.destroyAllWindows()
        serial_manager.send_safe(force=True)
        serial_manager.disconnect()
        print("Application stopped cleanly.")

if __name__ == "__main__":
    main()

