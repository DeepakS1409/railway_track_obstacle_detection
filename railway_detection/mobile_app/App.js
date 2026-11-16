import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  TextInput,
  ScrollView,
  SafeAreaView,
  ActivityIndicator,
  Platform,
  Alert
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { StatusBar } from 'expo-status-bar';

// Default to detected Wi-Fi IP (User can edit directly in UI)
const DEFAULT_BACKEND_URL = 'http://172.17.24.68:8000';

export default function App() {
  const [permission, requestPermission] = useCameraPermissions();
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND_URL);
  const [isDetecting, setIsDetecting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('Idle'); // 'Connected' | 'Disconnected' | 'Checking'
  const [lastDetections, setLastDetections] = useState([]);
  const [isHazard, setIsHazard] = useState(false);
  const [decisionState, setDecisionState] = useState('SAFE'); // 'SAFE' | 'ALERT'
  const [telemetry, setTelemetry] = useState({
    distance: -1,
    pir: false,
    system_alert: false,
    esp_connected: false
  });
  const [fps, setFps] = useState(0);
  const [latencyMs, setLatencyMs] = useState(0);

  const cameraRef = useRef(null);
  const isDetectingRef = useRef(false);
  const frameInFlightRef = useRef(false);

  // Sync state with ref for loop
  useEffect(() => {
    isDetectingRef.current = isDetecting;
  }, [isDetecting]);

  // Request permissions if not determined
  if (!permission) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#38bdf8" />
        <Text style={styles.infoText}>Checking Camera Permission...</Text>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.titleText}>Camera Access Required</Text>
        <Text style={styles.subText}>
          The Railway Detection app requires camera access to stream track footage to the AI backend.
        </Text>
        <TouchableOpacity style={styles.actionButton} onPress={requestPermission}>
          <Text style={styles.actionButtonText}>Grant Camera Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Quick Health Check to Python Backend
  const checkBackendHealth = async () => {
    setConnectionStatus('Checking');
    try {
      const trimmedUrl = backendUrl.trim().replace(/\/$/, '');
      const response = await fetch(`${trimmedUrl}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (response.ok) {
        const data = await response.json();
        setConnectionStatus('Connected');
        Alert.alert('Backend Online', `Connected to Python YOLO backend!\nESP32 Link: ${data.esp32_connected ? 'Online' : 'Offline'}`);
      } else {
        setConnectionStatus('Disconnected');
        Alert.alert('Connection Failed', `Backend responded with HTTP status ${response.status}`);
      }
    } catch (error) {
      setConnectionStatus('Disconnected');
      Alert.alert('Connection Error', `Cannot reach ${backendUrl}.\nMake sure phone and laptop are on the same Wi-Fi.`);
    }
  };

  // Toggle Detection
  const toggleDetection = () => {
    if (isDetecting) {
      setIsDetecting(false);
      isDetectingRef.current = false;
      setIsHazard(false);
      setDecisionState('SAFE');
    } else {
      setIsDetecting(true);
      isDetectingRef.current = true;
      runDetectionLoop();
    }
  };

  // Core Frame Capture & Streaming Loop
  const runDetectionLoop = async () => {
    let lastFrameTimestamp = Date.now();
    let frameCount = 0;

    while (isDetectingRef.current) {
      if (!cameraRef.current || frameInFlightRef.current) {
        await new Promise((r) => setTimeout(r, 80));
        continue;
      }

      try {
        frameInFlightRef.current = true;
        const captureStart = Date.now();

        // Capture compressed photo directly from camera preview
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.35, // Lightweight JPEG quality for fast Wi-Fi upload
          base64: true,
          skipProcessing: true,
        });

        if (photo && photo.base64 && isDetectingRef.current) {
          const trimmedUrl = backendUrl.trim().replace(/\/$/, '');

          // Upload frame to FastAPI backend
          const response = await fetch(`${trimmedUrl}/detect`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: JSON.stringify({
              image: photo.base64,
            }),
          });

          if (response.ok) {
            const result = await response.json();
            const elapsed = Date.now() - captureStart;
            setLatencyMs(elapsed);
            setConnectionStatus('Connected');

            setIsHazard(result.is_hazard);
            setDecisionState(result.decision_state || (result.is_hazard ? 'ALERT' : 'SAFE'));
            setLastDetections(result.detections || []);
            if (result.esp32) {
              setTelemetry({
                distance: result.esp32.distance,
                pir: result.esp32.pir,
                system_alert: result.esp32.system_alert,
                esp_connected: result.esp32.connected
              });
            }

            // Calculate FPS
            frameCount++;
            const now = Date.now();
            if (now - lastFrameTimestamp >= 1000) {
              setFps(frameCount);
              frameCount = 0;
              lastFrameTimestamp = now;
            }
          } else {
            setConnectionStatus('Disconnected');
          }
        }
      } catch (err) {
        setConnectionStatus('Disconnected');
      } finally {
        frameInFlightRef.current = false;
        // Pause briefly before next frame (avoids CPU flooding on 8GB laptop)
        await new Promise((r) => setTimeout(r, 250));
      }
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" />

      {/* Camera Live Preview */}
      <View style={styles.cameraWrapper}>
        <CameraView
          style={StyleSheet.absoluteFillObject}
          facing="back"
          ref={cameraRef}
        />

        {/* Top HUD: Alert / Safe Status Banner */}
        <View style={styles.topOverlay}>
          <View
            style={[
              styles.statusBanner,
              isHazard ? styles.statusBannerAlert : styles.statusBannerSafe
            ]}
          >
            <View
              style={[
                styles.statusDot,
                { backgroundColor: isHazard ? '#ef4444' : '#10b981' }
              ]}
            />
            <Text style={styles.statusBannerText}>
              {decisionState === 'ALERT'
                ? 'DANGER! TRACK INTRUSION'
                : isDetecting
                ? 'TRACK CLEAR - SAFE'
                : 'CAMERA STANDBY'}
            </Text>
          </View>

          {/* Detections List Badge */}
          {lastDetections.length > 0 && (
            <View style={styles.detectionsBox}>
              <Text style={styles.detectionsHeader}>TARGETS DETECTED:</Text>
              {lastDetections.map((item, idx) => (
                <Text key={idx} style={styles.detectionItemText}>
                  ⚠️ {item.class_name.toUpperCase()} ({(item.confidence * 100).toFixed(0)}%)
                </Text>
              ))}
            </View>
          )}
        </View>

        {/* Floating Telemetry HUD */}
        <View style={styles.telemetryHUD}>
          <View style={styles.hudItem}>
            <Text style={styles.hudLabel}>ULTRASONIC</Text>
            <Text
              style={[
                styles.hudValue,
                { color: telemetry.distance > 0 && telemetry.distance <= 50 ? '#ef4444' : '#38bdf8' }
              ]}
            >
              {telemetry.distance > 0 ? `${telemetry.distance.toFixed(1)} cm` : 'N/A'}
            </Text>
          </View>

          <View style={styles.hudItem}>
            <Text style={styles.hudLabel}>PIR SENSOR</Text>
            <Text
              style={[
                styles.hudValue,
                { color: telemetry.pir ? '#ef4444' : '#10b981' }
              ]}
            >
              {telemetry.pir ? 'MOTION' : 'CLEAR'}
            </Text>
          </View>

          <View style={styles.hudItem}>
            <Text style={styles.hudLabel}>ESP32 LINK</Text>
            <Text
              style={[
                styles.hudValue,
                { color: telemetry.esp_connected ? '#10b981' : '#9ca3af' }
              ]}
            >
              {telemetry.esp_connected ? 'ONLINE' : 'OFFLINE'}
            </Text>
          </View>

          <View style={styles.hudItem}>
            <Text style={styles.hudLabel}>LATENCY / FPS</Text>
            <Text style={styles.hudValue}>
              {latencyMs}ms | {fps}fps
            </Text>
          </View>
        </View>
      </View>

      {/* Bottom Control & Configuration Panel */}
      <View style={styles.controlPanel}>
        {/* Backend Configuration */}
        <View style={styles.configRow}>
          <TextInput
            style={styles.urlInput}
            value={backendUrl}
            onChangeText={setBackendUrl}
            placeholder="http://<laptop-ip>:8000"
            placeholderTextColor="#64748b"
            autoCapitalize="none"
            autoCorrect={false}
          />
          <TouchableOpacity style={styles.pingButton} onPress={checkBackendHealth}>
            <Text style={styles.pingButtonText}>Test IP</Text>
          </TouchableOpacity>
        </View>

        {/* Status Line */}
        <View style={styles.statusRow}>
          <Text style={styles.statusLabel}>
            Backend: <Text style={{ color: connectionStatus === 'Connected' ? '#10b981' : '#f87171' }}>{connectionStatus}</Text>
          </Text>
          <Text style={styles.statusLabel}>
            Wokwi ESP32: <Text style={{ color: telemetry.esp_connected ? '#10b981' : '#9ca3af' }}>{telemetry.esp_connected ? 'Bridged (4000)' : 'Disconnected'}</Text>
          </Text>
        </View>

        {/* Start / Stop Detection Button */}
        <TouchableOpacity
          style={[
            styles.detectButton,
            isDetecting ? styles.detectButtonStop : styles.detectButtonStart
          ]}
          onPress={toggleDetection}
        >
          <Text style={styles.detectButtonText}>
            {isDetecting ? '⏹ Stop Detection' : '▶ Start Real-Time Detection'}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0b0f19',
  },
  centerContainer: {
    flex: 1,
    backgroundColor: '#0b0f19',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  titleText: {
    color: '#f8fafc',
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 12,
  },
  subText: {
    color: '#94a3b8',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 20,
  },
  infoText: {
    color: '#94a3b8',
    marginTop: 12,
    fontSize: 14,
  },
  actionButton: {
    backgroundColor: '#2563eb',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  actionButtonText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '600',
  },
  cameraWrapper: {
    flex: 1,
    position: 'relative',
    backgroundColor: '#000',
  },
  topOverlay: {
    position: 'absolute',
    top: Platform.OS === 'ios' ? 50 : 20,
    left: 16,
    right: 16,
    zIndex: 10,
  },
  statusBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1.5,
  },
  statusBannerSafe: {
    backgroundColor: 'rgba(6, 78, 59, 0.9)',
    borderColor: '#10b981',
  },
  statusBannerAlert: {
    backgroundColor: 'rgba(127, 29, 29, 0.95)',
    borderColor: '#ef4444',
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 10,
  },
  statusBannerText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  detectionsBox: {
    backgroundColor: 'rgba(15, 23, 42, 0.9)',
    marginTop: 8,
    padding: 10,
    borderRadius: 6,
    borderLeftWidth: 4,
    borderLeftColor: '#ef4444',
  },
  detectionsHeader: {
    color: '#f87171',
    fontSize: 11,
    fontWeight: '700',
    marginBottom: 4,
  },
  detectionItemText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '600',
    marginVertical: 1,
  },
  telemetryHUD: {
    position: 'absolute',
    bottom: 16,
    left: 12,
    right: 12,
    backgroundColor: 'rgba(11, 15, 25, 0.85)',
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#1f2937',
  },
  hudItem: {
    alignItems: 'center',
  },
  hudLabel: {
    color: '#94a3b8',
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  hudValue: {
    color: '#f8fafc',
    fontSize: 13,
    fontWeight: '700',
    marginTop: 2,
  },
  controlPanel: {
    backgroundColor: '#111827',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#1f2937',
  },
  configRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  urlInput: {
    flex: 1,
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#334155',
  },
  pingButton: {
    backgroundColor: '#334155',
    marginLeft: 8,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 8,
  },
  pingButtonText: {
    color: '#38bdf8',
    fontSize: 13,
    fontWeight: '600',
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  statusLabel: {
    color: '#94a3b8',
    fontSize: 12,
  },
  detectButton: {
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  detectButtonStart: {
    backgroundColor: '#2563eb',
  },
  detectButtonStop: {
    backgroundColor: '#dc2626',
  },
  detectButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
});
