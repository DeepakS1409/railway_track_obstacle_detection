"""
Stage 1 Verification Script: Test ESP32 Serial Communication
Verifies Wokwi RFC2217 / Hardware COM connection, commands, and sensor telemetry.
"""

import sys
import time
import argparse
from serial_manager import SerialManager

def main():
    parser = argparse.ArgumentParser(description="Test ESP32 Serial Link")
    parser.add_argument(
        "--port",
        default="rfc2217://localhost:4000",
        help="Serial port (e.g., 'rfc2217://localhost:4000' for Wokwi or 'COM3' for hardware)"
    )
    args = parser.parse_args()

    print("=================================================================")
    print("  STAGE 1: ESP32 SERIAL COMMUNICATION & HARDWARE VERIFICATION    ")
    print("=================================================================")
    print(f"Target Connection: {args.port}")
    print("Connecting... Ensure Wokwi simulation is running with rfc2217ServerPort = 4000")
    print("-----------------------------------------------------------------")

    sm = SerialManager(port=args.port)
    if not sm.connect():
        print("\n[ERROR] Could not connect to ESP32.")
        print("Troubleshooting steps for Wokwi:")
        print("  1. In VS Code, make sure Wokwi extension is installed.")
        print("  2. Open railway_detection/esp32/diagram.json in VS Code.")
        print("  3. Press F1 -> 'Wokwi: Start Simulator'.")
        print("  4. Verify wokwi.toml has 'rfc2217ServerPort = 4000'.")
        print("  5. Run this script again.")
        sys.exit(1)

    print("\n[SUCCESS] Connected to ESP32!")
    print("\n[STEP 1] Testing PING Handshake...")
    sm.send_ping()
    time.sleep(1.0)

    print("\n[STEP 2] Testing ALERT Command (Red LED ON, Green LED OFF, Buzzer Pulsing)...")
    sm.send_alert(force=True)
    time.sleep(2.5)

    print("\n[STEP 3] Testing SAFE Command (Red LED OFF, Green LED ON, Buzzer OFF)...")
    sm.send_safe(force=True)
    time.sleep(2.0)

    print("\n[STEP 4] Monitoring Live Sensor Telemetry (PIR & HC-SR04)...")
    print("Press Ctrl+C to stop.")
    print("-----------------------------------------------------------------")
    print(f"{'TIME':<10} | {'PIR MOTION':<12} | {'DISTANCE (CM)':<15} | {'SYSTEM STATE':<12} | {'SOURCE'}")
    print("-----------------------------------------------------------------")

    try:
        while True:
            telemetry = sm.get_latest_telemetry()
            dist_str = f"{telemetry['distance']:.1f} cm" if telemetry['distance'] > 0 else "Out of Range"
            pir_str = "MOTION DETECTED" if telemetry['pir'] == 1 else "Clear"

            print(f"{time.strftime('%H:%M:%S'):<10} | {pir_str:<12} | {dist_str:<15} | {telemetry['state']:<12} | {telemetry['source']}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping verification test...")
    finally:
        sm.disconnect()
        print("Serial disconnected cleanly.")

if __name__ == "__main__":
    main()

