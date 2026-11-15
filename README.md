# Railway Track Human & Animal Detection System 🚆

An intelligent multi-sensor embedded IoT and computer vision prototype designed for college demonstration and research. The system integrates an ESP32 hardware simulation in Wokwi, Ultralytics YOLOv8 real-time object detection, non-blocking serial communication, and a dark-themed Streamlit monitoring dashboard.

> [!CAUTION]
> **Educational & Research Prototype Disclaimer**:
> This project is designed strictly as an academic prototype for laboratory demonstration and learning purposes. It is **not** certified for safety-critical railway deployment or live operational rail infrastructure.

---

## 1. Project Architecture & Workflow

```
[ Camera Stream / Video / Webcam ]
               │
               ▼
   [ OpenCV Video Handler ]
               │
               ▼
[ Ultralytics YOLOv8 Nano Inference ] (Person, Dog, Cow)
               │
               ▼
   [ Python Decision Engine ]
          │          ▲
(ALERT / SAFE)    (Telemetry: PIR, Distance)
          ▼          │
 [ PySerial RFC2217 / COM Manager ]
               │
               ▼
      [ ESP32 Firmware ]
     ┌─────────┴─────────┐
     ▼                   ▼
[ Red LED + Buzzer ]  [ Green LED ]
     (ALERT)             (SAFE)
```

---

## 2. Hardware Pin Assignments (ESP32)

| Component | ESP32 GPIO | Description / Mode |
|---|---|---|
| **Red LED** | `GPIO 4` | Alert visual indicator (Active HIGH) |
| **Green LED** | `GPIO 16` | Safe status indicator (Active HIGH) |
| **PIR Sensor OUT** | `GPIO 27` | Human/animal motion sensor (Digital INPUT) |
| **HC-SR04 TRIG** | `GPIO 25` | Ultrasonic trigger pulse (Digital OUTPUT) |
| **HC-SR04 ECHO** | `GPIO 26` | Ultrasonic echo measurement (Digital INPUT) |
| **Buzzer (+)** | `GPIO 17` | Audible alarm (Pulsed alert tone) |
| **Buzzer (-)** | `GND` | Ground reference |

---

## 3. Directory Layout

```
railway_detection/
│
├── esp32/
│   ├── sketch.ino          # ESP32 C++ firmware (non-blocking, JSON telemetry)
│   ├── diagram.json        # Wokwi circuit definition with exact pin assignments
│   └── wokwi.toml          # Wokwi simulation config (RFC2217 port 4000 enabled)
│
├── python/
│   ├── config.py           # Centralized configuration (ports, classes, thresholds)
│   ├── serial_manager.py   # Thread-safe PySerial / RFC2217 communication manager
│   ├── test_serial.py      # Stage 1 verification script (ping, alert, safe, telemetry)
│   ├── detector.py         # Lightweight YOLOv8n object detector
│   ├── camera.py           # Robust video stream handler (Webcam, file, IP camera)
│   └── main.py             # Desktop OpenCV HUD runner
│
├── dashboard/
│   └── app.py              # Streamlit live monitoring dashboard
│
├── requirements.txt        # Python dependency manifest
└── README.md
```

---

## 4. Step-by-Step Installation & Staged Verification

### Prerequisites
- Python 3.9+ (Check on Windows using `py -3 --version`)
- Visual Studio Code with the **Wokwi Simulator** extension installed

### Step A: Install Python Dependencies
Open PowerShell in this project folder and run:

```powershell
py -3 -m pip install -r requirements.txt
```

---

### Step B: Stage 1 – ESP32 Wokwi Simulation & Serial Setup

1. Open this workspace in **VS Code**.
2. Open `railway_detection/esp32/diagram.json`.
3. Press `F1` (or `Ctrl+Shift+P`) and type:
   ```text
   Wokwi: Start Simulator
   ```
4. The simulation will boot. Notice the `wokwi.toml` setting:
   ```toml
   [wokwi]
   version = 1
   firmware = "sketch.ino"
   rfc2217ServerPort = 4000
   ```
   Wokwi will start an RFC2217 TCP server on port `4000`.

5. **Run the Stage 1 Serial Verification Script**:
   ```powershell
   py -3 railway_detection/python/test_serial.py --port rfc2217://localhost:4000
   ```
   **What to verify:**
   - Script connects successfully to port 4000.
   - PING command receives an acknowledgement (`PONG`).
   - `ALERT` command turns the **Red LED ON** and starts the **Buzzer**.
   - `SAFE` command turns the **Red LED OFF**, **Green LED ON**, and silences the **Buzzer**.
   - Terminal prints live distance and PIR motion telemetry from Wokwi.

---

### Step C: Stage 2 – Testing Computer Vision & Desktop HUD

To test object detection with your laptop webcam and Wokwi simulation running together:

```powershell
py -3 railway_detection/python/main.py --source 0 --port rfc2217://localhost:4000
```

- When you or a pet step into frame, YOLO detects `Person` / `Dog` / `Cow`.
- Bounding box turns red and sends `ALERT` to ESP32.
- When clear, system sends `SAFE`.
- Press `q` in the OpenCV window to exit.

---

### Step D: Stage 3 – Launching the Streamlit Monitoring Dashboard

To launch the full web control center:

```powershell
py -3 -m streamlit run railway_detection/dashboard/app.py
```

The dashboard will open at `http://localhost:8501`:
1. In the sidebar, verify the connection string: `rfc2217://localhost:4000`.
2. Click **Connect** to link with the ESP32 simulation.
3. Select your camera source:
   - **Laptop Webcam (0)**
   - **Phone Camera Stream**: Install free **IP Webcam** (Android), start server, and paste `http://<phone-ip>:8080/video`.
   - **Custom Video File**: Enter path to a sample rail clip (e.g. `rail_sample.mp4`).
4. Toggle **▶ Start Live Monitoring**.
5. Observe real-time indicators:
   - Red ALERT banner when human or animal hazard is detected.
   - Green SAFE banner when clear.
   - PIR motion card and Ultrasonic distance readings.
   - Dynamic event history table.

---

## 5. Physical ESP32 Hardware Deployment

To run on a real physical ESP32 board:
1. Flash `railway_detection/esp32/sketch.ino` using the Arduino IDE or PlatformIO.
2. Connect your ESP32 via USB and check Device Manager for the COM port (e.g., `COM3`).
3. Point Python or the Dashboard to that port:
   ```powershell
   py -3 railway_detection/python/main.py --source 0 --port COM3
   ```

