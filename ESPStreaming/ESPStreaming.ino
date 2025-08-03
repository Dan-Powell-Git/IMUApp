#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecureBearSSL.h>
std::unique_ptr<BearSSL::WiFiClientSecure> client(new BearSSL::WiFiClientSecure());

Adafruit_MPU6050 mpu;

HTTPClient http;

// 🔧 CHANGED: Updated to Android default hotspot IP
const char* ssid = "DanHotSpot";
const char* password = "urvz4131";
const char* serverName = "https://imuapp-production.up.railway.app/imu_data"; // default IP for Android hotspots

unsigned long lastSendTime = 0;
const unsigned long sendInterval = 60 * 1000; //60 seconds
String imuBuffer = "[";
bool firstInBatch = true;
const int MAX_BATCH_READINGS = 100;
static int readingCount = 0;

void setup() {
  Serial.begin(115200);

  // 🔧 CHANGED: WiFi connect with timeout (avoid infinite loop)
  Serial.print(F("Connecting to WiFi"));
  WiFi.begin(ssid, password);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 20) {
    delay(500);
    Serial.print(".");
    retry++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(F("\nWiFi Connected!"));
  } else {
    Serial.println(F("\nWiFi Failed. Check credentials or signal."));
    // Optionally retry or halt here
  }

  // Initialize the IMU sensor
  if (!mpu.begin()) {
    Serial.println(F("MPU6050 not found!"));
    while (1) delay(10);
  }
  Serial.println(F("MPU6050 Ready!!"));

  client->setInsecure();  // Not ideal for production, but necessary for self-signed certs or quick testing

}

void loop() {
  // 🔧 CHANGED: WiFi reconnect logic if dropped
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("WiFi disconnected! Attempting reconnect..."));
    WiFi.begin(ssid, password);
    delay(1000); // wait a moment before retrying
    return;
  }

  sensors_event_t a, g, temp;

  // 🔧 CHANGED: Optional sensor read check (defensive)
  mpu.getEvent(&a, &g, &temp); // This usually doesn't fail, but can be wrapped with error checks if needed

  // 🔧 CHANGED: Add timestamp to payload
  String json = String("{") +
    "\"timestamp\":" + String(millis()) + "," +
    "\"ax\":" + String(a.acceleration.x, 2) + "," +
    "\"ay\":" + String(a.acceleration.y, 2) + "," +
    "\"az\":" + String(a.acceleration.z, 2) + "," +
    "\"gx\":" + String(g.gyro.x, 2) + "," +
    "\"gy\":" + String(g.gyro.y, 2) + "," +
    "\"gz\":" + String(g.gyro.z, 2) + "}";


  //appending to buffer
  if (!firstInBatch) imuBuffer += ",";
  imuBuffer += json;
  readingCount++;
  firstInBatch = false;

  // check if time to send
  if (readingCount >= MAX_BATCH_READINGS || millis() - lastSendTime >= sendInterval){
    imuBuffer += "]"; //close json
    Serial.println(F("IMU Buffer Contents:"));
    Serial.println(imuBuffer.length());
    Serial.println(imuBuffer);
    http.begin(*client, serverName);
    http.addHeader("Content-Type", "application/json");
    
    int httpResponseCode = http.POST(imuBuffer);

    if (httpResponseCode > 0) {
      Serial.print(F("Data Sent - Response Code: "));
      Serial.println(httpResponseCode);
      
    } else {
      Serial.print(F("Failed to send data. Code: "));
      Serial.println(httpResponseCode);
      String response = http.getString();
      Serial.println(F("Server Response:"));
      Serial.println(response); 
      
    }
    imuBuffer = "[";
    firstInBatch = true;
    lastSendTime = millis();
    readingCount = 0;

    http.end();  // clean up

    }


  delay(200); // Adjust this if needed
}
