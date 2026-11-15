# Railway Track Human & Animal Detection System - Python AI Engine

Professional AI vision and hardware control subsystem for the Railway Track Intrusion Detection prototype.

---

## 1. Directory Structure

```
railway_detection/
│
├── wokwi.toml             # Wokwi simulation configuration (RFC2217 on port 4000)
├── diagram.json           # Wokwi circuit schematic (ESP32, LEDs, Buzzer, PIR, HC-SR04)
│
├── esp32/
│   ├── esp32.ino          # Pre-compiled working ESP32 firmware
│   └── build/
│       └── esp32.ino.bin  # Compiled binary
│
└── python_ai/
    ├── app.py             # Streamlit dark-themed monitoring dashboard
    ├── camera.py          # Zero-buffer-lag mobile phone Wi-Fi video stream handler
    ├── detector.py        # Ultralytics YOLOv8 nano model (Person, Dog, Cow)
    ├── esp32_serial.py    # Non-blocking RFC2217 serial client for Wokwi ESP32
    ├── config.py          # Centralized configuration parameters
    ├── test_modules.py    # Independent diagnostic and verification tests
    ├── requirements.txt   # Python dependency list
    ├── README.md          # Documentation & setup instructions
    └── models/            # YOLO model weights cache
```

---

## 2. Setting Up the Mobile Phone Camera (Over Wi-Fi)

To use your smartphone as the track intrusion detection camera without cables or paid software:

1. **Connect to Same Wi-Fi**: Connect both your laptop and phone to the same Wi-Fi router (or phone mobile hotspot).
2. **Install Free App**:
   - **Android**: Install **IP Webcam** (by Pavel Khlebovich) from Google Play Store.
   - **iOS**: Install **IP Camera Lite** or **EpocCam** from App Store.
3. **Start Stream (Android IP Webcam)**:
   - Open **IP Webcam**.
   - Scroll down to the bottom and tap **Start Server**.
   - Note the IP address displayed at the bottom of the screen (e.g., `http://192.168.1.105:8080`).
4. **Target Stream URL**:
   - For OpenCV real-time streaming, add `/video` to the URL:
     ```text
     http://192.168.1.105:8080/video
     ```
   - Paste this URL into the dashboard sidebar.

---

## 3. Independent Verification Tests

Before launching the full dashboard, test individual components independently:

### Test 1: Test YOLO AI Inference
Verifies model loading and CPU inference speed:
```powershell
py -3 railway_detection/python_ai/test_modules.py --test yolo
```

### Test 2: Test Camera Stream
Verifies phone camera or webcam connection:
```powershell
# For phone stream:
py -3 railway_detection/python_ai/test_modules.py --test camera --source "http://192.168.1.105:8080/video"

# For laptop webcam:
py -3 railway_detection/python_ai/test_modules.py --test camera --source 0
```

### Test 3: Test Wokwi RFC2217 Serial Communication
1. Start Wokwi in VS Code (`F1` -> `Wokwi: Start Simulator`).
2. Run:
```powershell
py -3 railway_detection/python_ai/test_modules.py --test serial --port rfc2217://localhost:4000
```
This tests:
- PING handshake
- ALERT actuation (Red LED turns ON, Buzzer pulses in Wokwi)
- SAFE actuation (Red LED turns OFF, Green LED turns ON)
- Live JSON telemetry reception (PIR, Ultrasonic distance)

---

## 4. Running the Complete Dashboard

To launch the real-time Streamlit desktop control center:

```powershell
py -3 -m streamlit run railway_detection/python_ai/app.py
```

The browser opens automatically at `http://localhost:8501`.

1. In the sidebar:
   - Confirm serial port: `rfc2217://localhost:4000`.
   - Click **Connect** to link to Wokwi.
   - Enter your phone stream URL (or select Webcam `0`).
   - Click **▶ Start**.
2. When a Person, Dog, or Cow appears:
   - Red **DANGER** banner pulses.
   - Bounding box identifies the target.
   - Red LED & Buzzer activate in Wokwi.
   - Intrusion event is logged in the history table.

