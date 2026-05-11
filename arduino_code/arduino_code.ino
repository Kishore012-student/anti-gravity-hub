// Anti-Gravity IoT Hub - Arduino Code
// This code communicates via Serial to the Python Flask backend.

#include <ArduinoJson.h>

// --- Pin Definitions (Based on Schematic) ---
const int RELAY_PIN = 7;
const int LED_MAIN_PIN = 13;
const int LED_PINS[] = {2, 3, 4, 5, 6}; // LED Driver Logic pins

const int SOLAR_VOLT_PIN = A0;
const int BATT_VOLT_PIN = A1;
const int LOAD_VOLT_PIN = A2;
const int LOAD_CURR_PIN = A3;

// --- Variables ---
float batteryVoltage = 0.0;
float solarVoltage = 0.0;
float loadVoltage = 0.0;
float loadCurrent = 0.0;
int batteryPct = 100;
int relayState = 0;
int ledState = 0;
int systemHealthy = 1;

// Timing
unsigned long lastSendTime = 0;
const unsigned long sendInterval = 1000; // Send data every 1 second

void setup() {
  Serial.begin(9600);
  
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_MAIN_PIN, OUTPUT);
  for(int i=0; i<5; i++) pinMode(LED_PINS[i], OUTPUT);
  
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(LED_MAIN_PIN, LOW);
}

void loop() {
  // 1. Read Commands from Python
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "RELAY_ON") {
      relayState = 1;
      digitalWrite(RELAY_PIN, HIGH);
    } 
    else if (command == "RELAY_OFF") {
      relayState = 0;
      digitalWrite(RELAY_PIN, LOW);
    }
    else if (command == "LED_ON") {
      ledState = 1;
      digitalWrite(LED_MAIN_PIN, HIGH);
      for(int i=0; i<5; i++) digitalWrite(LED_PINS[i], HIGH);
    }
    else if (command == "LED_OFF") {
      ledState = 0;
      digitalWrite(LED_MAIN_PIN, LOW);
      for(int i=0; i<5; i++) digitalWrite(LED_PINS[i], LOW);
    }
    else if (command == "ESTOP") {
      relayState = 0;
      digitalWrite(RELAY_PIN, LOW);
      systemHealthy = 0; // Mark as unhealthy during e-stop
    }
    else if (command == "SYS_ON") {
      systemHealthy = 1;
    }
  }

  // 2. Read Sensors and Send Data periodically
  if (millis() - lastSendTime >= sendInterval) {
    lastSendTime = millis();
    
    // Read voltages (adjust multipliers for your specific resistors)
    int batRaw = analogRead(BATT_VOLT_PIN);
    batteryVoltage = batRaw * (5.0 / 1023.0) * 3.0; // Example 1:3 divider
    
    int solRaw = analogRead(SOLAR_VOLT_PIN);
    solarVoltage = solRaw * (5.0 / 1023.0) * 4.0; // Example 1:4 divider

    int loadVRaw = analogRead(LOAD_VOLT_PIN);
    loadVoltage = loadVRaw * (5.0 / 1023.0) * 3.0;

    int loadIRaw = analogRead(LOAD_CURR_PIN);
    loadCurrent = (loadIRaw * (5.0 / 1023.0) - 2.5) / 0.185; // Example for ACS712-05B
    if (loadCurrent < 0) loadCurrent = 0;
    
    // (Removed demo data overriding to ensure you only see true hardware values)
    // Calculate battery percentage (11V to 13.5V range for lead acid)
    float pct = ((batteryVoltage - 11.0) / (13.5 - 11.0)) * 100.0;
    batteryPct = constrain((int)pct, 0, 100);
    
    if (batteryVoltage < 11.5 && systemHealthy == 1) {
      systemHealthy = 0; // Low voltage warning
    } else if (batteryVoltage >= 11.5 && relayState == 1) { // Assume healthy if we turned it on
      systemHealthy = 1;
    }

    // 3. Construct JSON and Send
    // Allocate the JSON document
    // This size depends on the number of elements in the JSON object.
    StaticJsonDocument<200> doc;
    
    doc["voltage"] = batteryVoltage;
    doc["solar_voltage"] = solarVoltage;
    doc["load_voltage"] = loadVoltage;
    doc["load_current"] = loadCurrent;
    doc["battery_pct"] = batteryPct;
    doc["relay"] = relayState;
    doc["led"] = ledState;
    doc["system_healthy"] = systemHealthy;
    doc["power_flow"] = (solarVoltage > 14.0) ? 1 : ((relayState == 1) ? -1 : 0);
    doc["emergency_stop"] = (systemHealthy == 0 && batteryVoltage > 11.5) ? 1 : 0; 
    
    serializeJson(doc, Serial);
    Serial.println();
  }
}
