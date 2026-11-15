
// =====================================================
// RAILWAY TRACK HUMAN & ANIMAL DETECTION SYSTEM
// ESP32 Firmware - Wokwi Prototype
// =====================================================

// -------- PIN CONFIGURATION --------
#define RED_LED       4
#define GREEN_LED     16
#define BUZZER        17

#define PIR_SENSOR    27

#define TRIG_PIN      25
#define ECHO_PIN      26

// -------- SETTINGS --------
#define DISTANCE_LIMIT 50
#define AI_TIMEOUT     4000

// -------- VARIABLES --------
bool pirMotion = false;
float distanceCM = 0;

bool aiConnected = false;
bool aiAlert = false;

bool systemAlert = false;
bool buzzerState = false;

unsigned long lastAIMessage = 0;
unsigned long lastSensorRead = 0;
unsigned long lastTelemetry = 0;
unsigned long lastBuzzerToggle = 0;

const unsigned long SENSOR_INTERVAL = 100;
const unsigned long TELEMETRY_INTERVAL = 500;
const unsigned long BUZZER_INTERVAL = 150;

// -------- ULTRASONIC SENSOR --------
float readDistance() {

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration =
    pulseIn(ECHO_PIN, HIGH, 25000);

  if (duration == 0) {
    return -1;
  }

  return duration * 0.0343 / 2.0;
}

// -------- SERIAL COMMAND HANDLER --------
void readPythonCommands() {

  static String command = "";

  while (Serial.available()) {

    char received = Serial.read();

    if (received == '\n' || received == '\r') {

      command.trim();
      command.toUpperCase();

      if (command == "ALERT") {

        aiConnected = true;
        aiAlert = true;
        lastAIMessage = millis();

        Serial.println("AI ALERT RECEIVED");

      }

      else if (command == "SAFE") {

        aiConnected = true;
        aiAlert = false;
        lastAIMessage = millis();

        Serial.println("AI SAFE RECEIVED");

      }

      else if (command == "PING") {

        aiConnected = true;
        lastAIMessage = millis();

      }

      else if (command == "RESET") {

        aiConnected = false;
        aiAlert = false;

        Serial.println("AI CONNECTION RESET");

      }

      command = "";

    }

    else if (command.length() < 30) {
      command += received;
    }
  }
}

// -------- SENSOR READING --------
void readSensors() {

  pirMotion = digitalRead(PIR_SENSOR);

  distanceCM = readDistance();
}

// -------- ALERT DECISION --------
void updateAlertStatus() {

  // Check AI connection timeout
  if (aiConnected &&
      millis() - lastAIMessage > AI_TIMEOUT) {

    aiConnected = false;
    aiAlert = false;

    Serial.println("AI CONNECTION TIMEOUT");
  }

  // AI has priority when connected
  if (aiConnected) {

    systemAlert = aiAlert;

  }

  else {

    // Standalone sensor-based detection
    bool distanceAlert =
      (distanceCM > 0 &&
       distanceCM <= DISTANCE_LIMIT);

    systemAlert =
      pirMotion || distanceAlert;
  }
}

// -------- LED CONTROL --------
void updateLEDs() {

  if (systemAlert) {

    digitalWrite(RED_LED, HIGH);
    digitalWrite(GREEN_LED, LOW);

  }

  else {

    digitalWrite(RED_LED, LOW);
    digitalWrite(GREEN_LED, HIGH);
  }
}

// -------- BUZZER CONTROL --------
void updateBuzzer() {

  unsigned long currentTime = millis();

  if (systemAlert) {

    if (currentTime - lastBuzzerToggle >=
        BUZZER_INTERVAL) {

      lastBuzzerToggle = currentTime;

      buzzerState = !buzzerState;

      digitalWrite(BUZZER, buzzerState);
    }

  }

  else {

    buzzerState = false;
    digitalWrite(BUZZER, LOW);
  }
}

// -------- JSON TELEMETRY --------
void sendTelemetry() {

  Serial.print("{");

  Serial.print("\"pir\":");
  Serial.print(pirMotion ? "true" : "false");

  Serial.print(",\"distance\":");
  Serial.print(distanceCM);

  Serial.print(",\"ai_connected\":");
  Serial.print(aiConnected ? "true" : "false");

  Serial.print(",\"ai_alert\":");
  Serial.print(aiAlert ? "true" : "false");

  Serial.print(",\"system_alert\":");
  Serial.print(systemAlert ? "true" : "false");

  Serial.println("}");
}

// -------- SETUP --------
void setup() {

  Serial.begin(115200);

  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  pinMode(PIR_SENSOR, INPUT);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  digitalWrite(RED_LED, LOW);
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(BUZZER, LOW);
  digitalWrite(TRIG_PIN, LOW);

  delay(1000);

  Serial.println("================================");
  Serial.println("RAILWAY DETECTION SYSTEM");
  Serial.println("ESP32 INITIALIZED");
  Serial.println("SYSTEM RUNNING");
  Serial.println("================================");
}

// -------- MAIN LOOP --------
void loop() {

  unsigned long currentTime = millis();

  // Receive Python commands
  readPythonCommands();

  // Read sensors periodically
  if (currentTime - lastSensorRead >=
      SENSOR_INTERVAL) {

    lastSensorRead = currentTime;

    readSensors();
  }

  // Decide alert status
  updateAlertStatus();

  // Update output devices
  updateLEDs();
  updateBuzzer();

  // Send sensor telemetry
  if (currentTime - lastTelemetry >=
      TELEMETRY_INTERVAL) {

    lastTelemetry = currentTime;

    sendTelemetry();
  }
}
