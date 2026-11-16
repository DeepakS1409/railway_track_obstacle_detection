# Railway Track Human & Animal Detection - Expo Go Mobile App 📱

Custom React Native mobile camera application built with **Expo Go** and `expo-camera` to stream live phone video directly to the Python YOLO + Wokwi ESP32 backend.

Replaces IP Webcam with a dedicated native camera interface, real-time alert badges, and two-way ESP32 sensor telemetry.

---

## 1. Features
- **Native Camera Preview**: Uses `expo-camera` (CameraView) with full permissions handling.
- **Configurable Backend IP**: Field to set `http://<laptop-ip>:8000` directly from the phone.
- **Health Check ("Test IP")**: Quick ping to confirm Wi-Fi connectivity with laptop backend.
- **Real-Time Track Status**:
  - 🟢 **SAFE**: Green banner when track is clear.
  - 🔴 **DANGER**: Pulsating red banner when human or animal is detected.
- **Detection HUD**: Shows detected object name(s) (Person, Cow, Dog) and confidence %.
- **Two-Way ESP32 Telemetry**: Displays Ultrasonic HC-SR04 distance (cm), PIR sensor status, and ESP32 connection state live on your phone.
- **Optimized for 8GB RAM Laptop**: Lightweight compressed frames (~35KB) prevent CPU flooding.

---

## 2. Prerequisites
1. **Node.js** installed on your laptop (verified Node v26 / npm v11).
2. **Expo Go** app installed on your Android phone (free from Google Play Store).
3. Both laptop and phone connected to the **same Wi-Fi router** or **mobile hotspot**.

---

## 3. How to Find Your Laptop's Local IPv4 Address

On Windows, open PowerShell and run:
```powershell
ipconfig
```
Look for your active network connection:
```text
Wireless LAN adapter Wi-Fi:
   IPv4 Address. . . . . . . . . . . : 172.17.24.68
```
*(Your IP will look like `192.168.1.X` or `172.17.X.X`)*.

---

## 4. How to Run

### Step 1: Start Wokwi Simulator
In VS Code, open `railway_detection/diagram.json`, press `F1`, and select:
```text
Wokwi: Start Simulator
```
*(Wokwi opens RFC2217 serial port 4000)*.

### Step 2: Start the Python FastAPI Backend
In a PowerShell terminal:
```powershell
py -3 railway_detection/python_ai/server.py
```
Backend starts on `http://0.0.0.0:8000` and automatically connects to Wokwi ESP32.

### Step 3: Start the Expo Mobile App
In another PowerShell terminal:
```powershell
cd railway_detection\mobile_app
npx expo start
```
A large QR code will appear in the terminal.

### Step 4: Open in Expo Go on Your Phone
1. Open the **Expo Go** app on your Android phone.
2. Tap **Scan QR Code** and scan the QR code from the terminal.
3. The app will bundle and open on your phone.
4. Grant Camera Permission when prompted.
5. In the bottom field, enter your laptop's IP: `http://<YOUR_LAPTOP_IP>:8000` (e.g., `http://172.17.24.68:8000`).
6. Tap **Test IP** to verify connection.
7. Tap **▶ Start Real-Time Detection**!

Point your phone at a person or picture of a cow/dog. Observe the live detection badge on your phone and the Red LED + Buzzer firing in Wokwi!
