/*
  Sensor node — ESP32

  Reads DHT22 (temp/humidity), HC-SR04 (ultrasonic distance), a microphone
  module (analog sound level), a beam-break sensor (digital), and battery
  voltage (ADC), then pushes one JSON reading to the Pi's WebSocket server
  every READ_INTERVAL_MS. The Pi just relays it straight to the dashboard —
  see detect_server.py.

  Libraries needed (Arduino Library Manager):
    - DHT sensor library (Adafruit) + its Adafruit Unified Sensor dependency
    - ArduinoJson (Benoit Blanchon)
    - WebSockets (Markus Sattler — search "arduinoWebSockets")
*/

#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ---- Wi-Fi + Pi connection — fill these in ----
const char* WIFI_SSID = "your-network";
const char* WIFI_PASSWORD = "your-password";
const char* PI_HOST = "raspberrypi.local"; // or the Pi's IP address, e.g. "192.168.1.42"
const uint16_t PI_PORT = 8765;

// ---- Pin assignments — adjust to match your actual wiring ----
#define DHT_PIN 4
#define DHT_TYPE DHT22
#define ULTRASONIC_TRIG_PIN 5
#define ULTRASONIC_ECHO_PIN 18
#define MIC_ANALOG_PIN 34   // must be an ADC1 pin (32-39) — ADC2 pins don't work while Wi-Fi is active
#define BEAM_BREAK_PIN 19   // digital input; assumes the sensor pulls LOW when the beam is broken
#define BATTERY_ADC_PIN 35  // also ADC1

const unsigned long READ_INTERVAL_MS = 2000; // how often to send a reading

DHT dht(DHT_PIN, DHT_TYPE);
WebSocketsClient webSocket;
unsigned long lastReadTime = 0;

float readDistanceCm() {
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG_PIN, LOW);

  long durationUs = pulseIn(ULTRASONIC_ECHO_PIN, HIGH, 30000); // 30ms timeout ≈ 5m range
  if (durationUs == 0) return -1; // no echo — out of range, or nothing to bounce off
  return durationUs / 58.0;       // standard speed-of-sound conversion for HC-SR04
}

float readBatteryVoltage() {
  // Adjust DIVIDER_RATIO to match whatever voltage-divider circuit you build —
  // this assumes a 2:1 divider bringing a ~7.4V pack down under the ESP32's 3.3V max.
  const float DIVIDER_RATIO = 2.0;
  int raw = analogRead(BATTERY_ADC_PIN);
  return (raw / 4095.0) * 3.3 * DIVIDER_RATIO;
}

void sendReading() {
  StaticJsonDocument<256> doc;
  doc["type"] = "sensor";
  doc["temperature"] = dht.readTemperature();
  doc["humidity"] = dht.readHumidity();
  doc["distance_cm"] = readDistanceCm();
  doc["sound_level"] = analogRead(MIC_ANALOG_PIN);
  doc["beam_broken"] = digitalRead(BEAM_BREAK_PIN) == LOW;
  doc["battery_v"] = readBatteryVoltage();
  doc["timestamp"] = (double)millis(); // relative time is fine for a demo; swap for NTP if you need wall-clock time

  String payload;
  serializeJson(doc, payload);
  webSocket.sendTXT(payload);
}

void onWebSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  // Not reacting to messages from the Pi right now — logging is enough for a demo.
  if (type == WStype_CONNECTED) Serial.println("WebSocket connected to Pi");
  if (type == WStype_DISCONNECTED) Serial.println("WebSocket disconnected — will retry automatically");
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(ULTRASONIC_ECHO_PIN, INPUT);
  pinMode(BEAM_BREAK_PIN, INPUT_PULLUP);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected");

  webSocket.begin(PI_HOST, PI_PORT, "/");
  webSocket.onEvent(onWebSocketEvent);
  webSocket.setReconnectInterval(3000); // auto-retry if the Pi drops or isn't up yet
}

void loop() {
  webSocket.loop();

  if (millis() - lastReadTime >= READ_INTERVAL_MS) {
    lastReadTime = millis();
    sendReading();
  }
}
