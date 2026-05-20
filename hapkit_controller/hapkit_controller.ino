/*
 * Space IO - Hapkit Controller
 * 
 * Controls two motors (steering and throttle) with force feedback
 * Reads encoders and sends positions to Teensy
 * Receives force commands from Teensy and renders them
 * 
 * Hardware:
 *   - 2x Maxon motors with encoders
 *   - Motor driver (on Hapkit board)
 *   - Encoder connections
 */

#include "config.h"
#include "motor_control.h"
#include "encoder.h"

// Motor objects
MotorController steeringMotor(STEERING_MOTOR_PIN, STEERING_DIR_PIN);
MotorController throttleMotor(THROTTLE_MOTOR_PIN, THROTTLE_DIR_PIN);

// Encoder objects
EncoderReader steeringEncoder(STEERING_ENCODER_A, STEERING_ENCODER_B);
EncoderReader throttleEncoder(THROTTLE_ENCODER_A, THROTTLE_ENCODER_B);

// Serial communication
char serialBuffer[128];
int serialBufferIndex = 0;

// Target forces (from game engine)
float steeringForce = 0.0;  // -1000 to 1000
float throttleForce = 0.0;  // -1000 to 1000

// Control loop timing
unsigned long lastControlUpdate = 0;
unsigned long lastPositionSend = 0;

void setup() {
  Serial.begin(BAUD_RATE);
  
  // Initialize motors
  steeringMotor.begin();
  throttleMotor.begin();
  
  // Initialize encoders
  steeringEncoder.begin();
  throttleEncoder.begin();
  
  delay(500);
  
  Serial.println("Hapkit Controller Ready");
}

void loop() {
  unsigned long currentTime = micros();
  
  // High-frequency control loop (~1000 Hz)
  if (currentTime - lastControlUpdate >= CONTROL_LOOP_INTERVAL_US) {
    updateControlLoop();
    lastControlUpdate = currentTime;
  }
  
  // Read serial commands
  readSerialCommands();
  
  // Send position updates at lower rate (~60 Hz)
  if (currentTime - lastPositionSend >= POSITION_SEND_INTERVAL_US) {
    sendPositions();
    lastPositionSend = currentTime;
  }
}

void updateControlLoop() {
  // Read encoder positions
  steeringEncoder.update();
  throttleEncoder.update();
  
  // Apply forces to motors
  steeringMotor.setForce(steeringForce);
  throttleMotor.setForce(throttleForce);
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n') {
      serialBuffer[serialBufferIndex] = '\0';
      processCommand(serialBuffer);
      serialBufferIndex = 0;
    } else if (serialBufferIndex < 127) {
      serialBuffer[serialBufferIndex++] = c;
    } else {
      serialBufferIndex = 0;
    }
  }
}

void processCommand(char* command) {
  // Expected format: F,STEER,THROTTLE
  // Example: F,500,-200
  
  if (command[0] != 'F') {
    return;
  }
  
  float steer, throttle;
  int parsed = sscanf(command, "F,%f,%f", &steer, &throttle);
  
  if (parsed == 2) {
    steeringForce = constrain(steer, -1000.0, 1000.0);
    throttleForce = constrain(throttle, -1000.0, 1000.0);
  }
}

void sendPositions() {
  // Get normalized positions (-1.0 to 1.0)
  float steerPos = steeringEncoder.getNormalizedPosition();
  float throttlePos = throttleEncoder.getNormalizedPosition();
  
  // Send to Teensy
  // Format: P,STEER,THROTTLE
  Serial.print("P,");
  Serial.print(steerPos, 3);
  Serial.print(",");
  Serial.println(throttlePos, 3);
}