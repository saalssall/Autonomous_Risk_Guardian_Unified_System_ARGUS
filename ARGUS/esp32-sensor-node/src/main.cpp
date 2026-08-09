/*
  Sensor node — ESP32

  Reads DHT22 (temp/humidity), HC-SR04 (ultrasonic distance), a microphone
  module (analog sound level), and a beam-break sensor (digital), then POSTs
  one reading to the FastAPI backend's /api/sensor-data every
  READ_INTERVAL_MS, as application/x-www-form-urlencoded — matching
  ingest_sensor_data()'s exact Form field names: node_id, temperature,
  humidity, distance, sound, beam_status, latitude, longitude, plus the
  device-condition fields the shared spec calls for: esp32_online,
  dht11_status, hcsr04_status, ir_beam_status, network_status.

  On a sensor read failure, this falls back to the last known-good value
  for that sensor (rather than skipping the whole cycle, or sending a
  sentinel like -1) so a single bad read doesn't get treated as a genuine
  spike by the backend's anomaly detection — while still reporting the
  real *_status as FAIL so the failure itself isn't hidden.

  Note: the backend doesn't accept battery on this endpoint (it only lives
  on the Node record, which this doesn't update), and it stamps its own
  timestamp server-side — so neither is sent here.

  Libraries needed (Arduino Library Manager):
    - DHT sensor library (Adafruit) + its Adafruit Unified Sensor dependency
  (HTTPClient and WiFi are built into the ESP32 Arduino core — nothing else to install.)
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// ---- Wi-Fi + backend connection — fill these in ----
const char* WIFI_SSID = "Hamidullah";
const char* WIFI_PASSWORD = "AI/ML2026";
const char* BACKEND_HOST = "raspberrypi.local"; // or the backend's IP address
const uint16_t BACKEND_PORT = 8000;             // FastAPI/uvicorn default

// ---- Node identity — this node is stationary, so lat/lon are fixed constants ----
// IMPORTANT: match this to whatever node_id the rest of the team is using —
// the seed script registers "node-north-01"; change this if that's the one
// your team is treating as canonical.
const char* NODE_ID = "ARGUS-01";
const float NODE_LAT = -27.5000; // set to this node's actual deployment location
const float NODE_LON = 153.0500;

// ---- Pin assignments — adjust to match your actual wiring ----
#define DHT_PIN 4
#define DHT_TYPE DHT22
#define ULTRASONIC_TRIG_PIN 5
#define ULTRASONIC_ECHO_PIN 18   // wire through a voltage divider — HC-SR04 Echo is 5V, ESP32 GPIO is 3.3V only
#define MIC_ANALOG_PIN 34        // must be an ADC1 pin (32-39) — ADC2 pins don't work while Wi-Fi is active
#define BEAM_BREAK_PIN 19        // digital input; module outputs LOW=intact/HIGH=broken directly, no pull needed

const unsigned long READ_INTERVAL_MS = 2000; // how often to send a reading

DHT dht(DHT_PIN, DHT_TYPE);
unsigned long lastReadTime = 0;

// Last known-good values — used as a fallback when a sensor read fails, so
// a single bad read doesn't register as a false spike in the backend's
// anomaly detection. NAN until the first successful read of each.
float lastGoodTemperature = NAN;
float lastGoodHumidity = NAN;
float lastGoodDistance = NAN;

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

String urlEncode(const String& value) {
  String encoded;
  char buf[4];
  for (size_t i = 0; i < value.length(); i++) {
    char c = value.charAt(i);
    if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') {
      encoded += c;
    } else {
      snprintf(buf, sizeof(buf), "%%%02X", (unsigned char)c);
      encoded += buf;
    }
  }
  return encoded;
}

void sendReading() {
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  float distance = readDistanceCm();
  int soundLevel = analogRead(MIC_ANALOG_PIN);
  bool beamBroken = digitalRead(BEAM_BREAK_PIN) == HIGH; // confirmed polarity: LOW=intact, HIGH=broken

  bool dhtOk = !isnan(temperature) && !isnan(humidity);
  if (dhtOk) {
    lastGoodTemperature = temperature;
    lastGoodHumidity = humidity;
  } else {
    temperature = lastGoodTemperature;
    humidity = lastGoodHumidity;
  }

  bool hcsr04Ok = distance > 0;
  if (hcsr04Ok) {
    lastGoodDistance = distance;
  } else {
    distance = lastGoodDistance;
  }

  if (isnan(temperature) || isnan(humidity) || isnan(distance)) {
    // No good reading yet for at least one sensor (e.g. right at boot) —
    // nothing sane to send or fall back to.
    Serial.println("No valid reading yet for at least one sensor — skipping this cycle");
    return;
  }

  bool networkOk = WiFi.status() == WL_CONNECTED;

  String body = "node_id=" + urlEncode(NODE_ID) +
                "&temperature=" + String(temperature, 1) +
                "&humidity=" + String(humidity, 1) +
                "&distance=" + String(distance, 1) +
                "&sound=" + String(soundLevel) +
                "&beam_status=" + urlEncode(beamBroken ? "broken" : "normal") +
                "&latitude=" + String(NODE_LAT, 6) +
                "&longitude=" + String(NODE_LON, 6) +
                "&esp32_online=true" +
                "&dht11_status=" + urlEncode(dhtOk ? "OK" : "FAIL") +
                "&hcsr04_status=" + urlEncode(hcsr04Ok ? "OK" : "FAIL") +
                // The beam-break module has no independent self-test line, so
                // this can't detect its own hardware failure — only whether
                // it's producing a signal at all, which it is if we got here.
                "&ir_beam_status=OK" +
                "&network_status=" + urlEncode(networkOk ? "CONNECTED" : "DISCONNECTED");

  HTTPClient http;
  String endpoint = String("http://") + BACKEND_HOST + ":" + BACKEND_PORT + "/api/sensor-data";
  http.begin(endpoint);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");

  int statusCode = http.POST(body);
  if (statusCode > 0) {
    Serial.printf("POST /api/sensor-data -> %d\n", statusCode);
  } else {
    Serial.printf("POST failed: %s\n", http.errorToString(statusCode).c_str());
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  pinMode(ULTRASONIC_TRIG_PIN, OUTPUT);
  pinMode(ULTRASONIC_ECHO_PIN, INPUT);
  pinMode(BEAM_BREAK_PIN, INPUT); // module drives this pin directly — no internal pull needed

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected");
}

void loop() {
  if (millis() - lastReadTime >= READ_INTERVAL_MS) {
    lastReadTime = millis();
    sendReading();
  }
}
