/*
 * Space IO - Hapkit Motor Receiver
 *
 * Receives binary motor command packets from the Teensy controller and drives
 * two Hapkit motors using the verified Timer0 PWM setup.
 *
 * Packet format:
 *   0xAA,STEERING_BYTE,THROTTLE_BYTE,CHECKSUM
 */

#include "config.h"

enum PacketState {
  WAIT_FOR_HEADER,
  READ_STEERING,
  READ_THROTTLE,
  READ_CHECKSUM
};

PacketState packetState = WAIT_FOR_HEADER;
byte steeringCommand = HAPKIT_STOP_COMMAND;
byte throttleCommand = HAPKIT_STOP_COMMAND;

void setup() {
  Serial.begin(BAUD_RATE);

  pinMode(STEERING_MOTOR_PIN, OUTPUT);
  pinMode(STEERING_DIR_PIN, OUTPUT);
  pinMode(THROTTLE_MOTOR_PIN, OUTPUT);
  pinMode(THROTTLE_DIR_PIN, OUTPUT);

  // Phase-correct PWM on Timer0, prescaler 1, about 31.4 kHz on pins 5 and 6.
  TCCR0A = _BV(COM0A1) | _BV(COM0B1) | _BV(WGM00);
  TCCR0B = _BV(CS00);

  stopMotors();
}

void loop() {
  readMotorPackets();
}

void readMotorPackets() {
  while (Serial.available() > 0) {
    byte value = Serial.read();

    switch (packetState) {
      case WAIT_FOR_HEADER:
        if (value == HAPKIT_PACKET_HEADER) {
          packetState = READ_STEERING;
        }
        break;

      case READ_STEERING:
        steeringCommand = value;
        packetState = READ_THROTTLE;
        break;

      case READ_THROTTLE:
        throttleCommand = value;
        packetState = READ_CHECKSUM;
        break;

      case READ_CHECKSUM:
        if (value == calculateChecksum(steeringCommand, throttleCommand)) {
          driveSteeringMotor(steeringCommand);
          driveThrottleMotor(throttleCommand);
        }
        packetState = WAIT_FOR_HEADER;
        break;
    }
  }
}

byte calculateChecksum(byte steering, byte throttle) {
  return (byte)(steering + throttle);
}

void stopMotors() {
  OCR0B = 0;
  OCR0A = 0;
}

void driveSteeringMotor(byte rawValue) {
  if (rawValue > HAPKIT_DEADBAND_HIGH) {
    digitalWrite(STEERING_DIR_PIN, HIGH);
    OCR0B = map(rawValue, HAPKIT_FORWARD_START, HAPKIT_MAX_FORWARD_COMMAND, 0, MAX_PWM);
  } else if (rawValue < HAPKIT_DEADBAND_LOW) {
    digitalWrite(STEERING_DIR_PIN, LOW);
    OCR0B = map(rawValue, HAPKIT_REVERSE_START, HAPKIT_MAX_REVERSE_COMMAND, 0, MAX_PWM);
  } else {
    OCR0B = 0;
  }
}

void driveThrottleMotor(byte rawValue) {
  if (rawValue > HAPKIT_DEADBAND_HIGH) {
    digitalWrite(THROTTLE_DIR_PIN, HIGH);
    OCR0A = map(rawValue, HAPKIT_FORWARD_START, HAPKIT_MAX_FORWARD_COMMAND, 0, MAX_PWM);
  } else if (rawValue < HAPKIT_DEADBAND_LOW) {
    digitalWrite(THROTTLE_DIR_PIN, LOW);
    OCR0A = map(rawValue, HAPKIT_REVERSE_START, HAPKIT_MAX_REVERSE_COMMAND, 0, MAX_PWM);
  } else {
    OCR0A = 0;
  }
}
