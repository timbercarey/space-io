/*
 * Simple motor test sketch
 * Tests basic motor control without serial communication
 */

#define MOTOR_PIN 5
#define DIR_PIN 8

void setup() {
  pinMode(MOTOR_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  
  Serial.begin(115200);
  Serial.println("Motor Test - Starting in 2 seconds");
  delay(2000);
}

void loop() {
  // Forward, increasing force
  Serial.println("Forward ramp up");
  digitalWrite(DIR_PIN, HIGH);
  for (int i = 0; i <= 255; i += 5) {
    analogWrite(MOTOR_PIN, i);
    delay(50);
  }
  
  delay(500);
  
  // Forward, decreasing force
  Serial.println("Forward ramp down");
  for (int i = 255; i >= 0; i -= 5) {
    analogWrite(MOTOR_PIN, i);
    delay(50);
  }
  
  delay(500);
  
  // Reverse, increasing force
  Serial.println("Reverse ramp up");
  digitalWrite(DIR_PIN, LOW);
  for (int i = 0; i <= 255; i += 5) {
    analogWrite(MOTOR_PIN, i);
    delay(50);
  }
  
  delay(500);
  
  // Reverse, decreasing force
  Serial.println("Reverse ramp down");
  for (int i = 255; i >= 0; i -= 5) {
    analogWrite(MOTOR_PIN, i);
    delay(50);
  }
  
  delay(2000);
}
