// MedChain Sensor Node - DHT11 + LDR Module
// Reads temperature, humidity, and light every 10 seconds as JSON over Serial.

#include <DHT.h>
#include <ArduinoJson.h>

#define DHT_PIN        4
#define DHT_TYPE       DHT11
#define LDR_DO_PIN     35

#define TEMP_MIN       15.0
#define TEMP_MAX       30.0
#define HUMIDITY_MAX   75.0

DHT dht(DHT_PIN, DHT_TYPE);

unsigned long lastReadTime = 0;
const unsigned long INTERVAL = 10000;

int readCount = 0;
bool tempBreached = false;
bool humidityBreached = false;
bool lightBreached = false;

void setup() {
  Serial.begin(115200);
  pinMode(LDR_DO_PIN, INPUT);
  dht.begin();
  delay(2000);
  Serial.println("=== MedChain Sensor Node ONLINE ===");
  Serial.println("Logging every 10 seconds...");
}

void loop() {
  unsigned long now = millis();
  if (now - lastReadTime < INTERVAL) return;
  lastReadTime = now;
  readCount++;

  float temp = dht.readTemperature();
  float humidity = dht.readHumidity();
  bool lightDO = digitalRead(LDR_DO_PIN);
  if (isnan(temp) || isnan(humidity)) {
    Serial.println("{\"error\":\"DHT11 read failed - check wiring\"}");
    return;
  }

  if (temp < TEMP_MIN || temp > TEMP_MAX) tempBreached = true;
  if (humidity > HUMIDITY_MAX) humidityBreached = true;
  if (!lightDO) lightBreached = true;

  StaticJsonDocument<256> doc;
  doc["read"] = readCount;
  doc["timestamp_ms"] = now;
  doc["temp_c"] = serialized(String(temp, 1));
  doc["humidity_pct"] = serialized(String(humidity, 1));
  doc["light_exposed"] = !lightDO;
  doc["temp_breached"] = tempBreached;
  doc["humidity_breached"] = humidityBreached;
  doc["light_breached"] = lightBreached;
  doc["status"] = tempBreached || humidityBreached || lightBreached ? "BREACH" : "OK";
  serializeJson(doc, Serial);
  Serial.println();
}