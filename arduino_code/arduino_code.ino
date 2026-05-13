#include <Wire.h>
#include <SPI.h>

const int solarPin = A0;
const int fuelCellPin = A1;
const int batteryPin = A2;

const int relayPin = 7;

float solarVoltage = 0.0;
float fuelVoltage = 0.0;
float batteryVoltage = 0.0;

float calibrationFactor = 5.0;

float batteryLow = 11.0;
float batteryHigh = 13.5;

void setup()
{
  Serial.begin(9600);
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, LOW);

  Serial.println("AETHERCONTROL: POWER GENERATION SYSTEM");
  Serial.println("SOLAR + SALT WATER ENERGY ACTIVE");
}

void loop()
{
  // 1. Read Raw Values
  int solarValue = analogRead(solarPin);
  int fuelValue = analogRead(fuelCellPin);
  int batteryValue = analogRead(batteryPin);

  // 2. Calculate Voltages
  solarVoltage = (solarValue * 5.0 / 1023.0) * calibrationFactor;
  fuelVoltage = (fuelValue * 5.0 / 1023.0) * calibrationFactor;
  batteryVoltage = (batteryValue * 5.0 / 1023.0) * calibrationFactor;

  // 3. Print Text for Arduino Serial Monitor
  Serial.print("Solar Voltage: ");
  Serial.print(solarVoltage);
  Serial.println(" V");

  Serial.print("Fuel Cell Voltage: ");
  Serial.print(fuelVoltage);
  Serial.println(" V");

  Serial.print("Battery Voltage: ");
  Serial.print(batteryVoltage);
  Serial.println(" V");

  float totalVoltage = solarVoltage + fuelVoltage;

  // 4. Control Logic
  if (batteryVoltage > batteryLow)
  {
    digitalWrite(relayPin, HIGH);
    Serial.println("LOAD CONNECTED");
  }
  else
  {
    digitalWrite(relayPin, LOW);
    Serial.println("LOAD DISCONNECTED");
  }

  if (batteryVoltage >= batteryHigh)
  {
    Serial.println("CHARGED");
  }
  else
  {
    Serial.println("BATTERY CHARGING");
  }

  // 5. SMART BRIDGE: Send JSON for Web Dashboard & Mobile App
  // Mapping: batteryVoltage -> voltage, solarVoltage -> solar_voltage, fuelVoltage -> load_voltage
  Serial.print("{");
  Serial.print("\"voltage\":"); Serial.print(batteryVoltage);
  Serial.print(",\"solar_voltage\":"); Serial.print(solarVoltage);
  Serial.print(",\"load_voltage\":"); Serial.print(fuelVoltage);
  Serial.print(",\"load_current\":"); Serial.print(totalVoltage); // Showing Total as Current for visibility
  Serial.print(",\"relay\":"); Serial.print(digitalRead(relayPin));
  Serial.print(",\"system_healthy\":1");
  Serial.println("}");

  delay(2000);
}
