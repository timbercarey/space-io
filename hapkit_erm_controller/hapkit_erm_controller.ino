/*
 * Space IO - Hapkit ERM Receiver
 *
 * Receives binary ERM command packets from the Teensy controller and drives
 * each Hapkit motor output at the PWM value commanded by the Teensy.
 *
 * Packet format:
 *   0xE1,PWM,CHECKSUM
 *   0xE2,ERM1_PWM,ERM2_PWM,CHECKSUM
 *
 * PWM is 0 for off or 1..255 for duty cycle. CHECKSUM is the byte sum.
 */

#include "config.h"

enum PacketState {
  WAIT_FOR_HEADER,
  READ_LEGACY_PWM,
  READ_DUAL_PWM_1,
  READ_DUAL_PWM_2,
  READ_CHECKSUM
};

PacketState packetState = WAIT_FOR_HEADER;
byte pendingPacketHeader = 0;
byte pendingPwmCommand1 = 0;
byte pendingPwmCommand2 = 0;
bool ermsEnabled = false;
unsigned long lastCommandMillis = 0;

void setup() {
  Serial.begin(BAUD_RATE);

  pinMode(ERM_1_MOTOR_PIN, OUTPUT);
  pinMode(ERM_1_DIR_PIN, OUTPUT);
  pinMode(ERM_2_MOTOR_PIN, OUTPUT);
  pinMode(ERM_2_DIR_PIN, OUTPUT);

  // Phase-correct PWM on Timer0, prescaler 1, about 31.4 kHz on pins 5 and 6.
  TCCR0A = _BV(COM0A1) | _BV(COM0B1) | _BV(WGM00);
  TCCR0B = _BV(CS00);

  setErmPwm(0, 0);
  lastCommandMillis = millis();
}

void loop() {
  readErmPackets();
  stopErmsIfTimedOut();
}

void readErmPackets() {
  while (Serial.available() > 0) {
    byte value = Serial.read();

    switch (packetState) {
      case WAIT_FOR_HEADER:
        if (value == ERM_PACKET_HEADER) {
          pendingPacketHeader = value;
          packetState = READ_LEGACY_PWM;
        } else if (value == ERM_DUAL_PACKET_HEADER) {
          pendingPacketHeader = value;
          packetState = READ_DUAL_PWM_1;
        }
        break;

      case READ_LEGACY_PWM:
        pendingPwmCommand1 = value;
        pendingPwmCommand2 = value;
        packetState = READ_CHECKSUM;
        break;

      case READ_DUAL_PWM_1:
        pendingPwmCommand1 = value;
        packetState = READ_DUAL_PWM_2;
        break;

      case READ_DUAL_PWM_2:
        pendingPwmCommand2 = value;
        packetState = READ_CHECKSUM;
        break;

      case READ_CHECKSUM:
        if (value == calculateChecksum(
            pendingPacketHeader,
            pendingPwmCommand1,
            pendingPwmCommand2
        )) {
          setErmPwm(pendingPwmCommand1, pendingPwmCommand2);
          lastCommandMillis = millis();
        }
        packetState = WAIT_FOR_HEADER;
        break;
    }
  }
}

byte calculateChecksum(byte packetHeader, byte pwmCommand1, byte pwmCommand2) {
  if (packetHeader == ERM_PACKET_HEADER) {
    return (byte)(packetHeader + pwmCommand1);
  }
  return (byte)(packetHeader + pwmCommand1 + pwmCommand2);
}

void stopErmsIfTimedOut() {
  if (!ermsEnabled) {
    return;
  }
  if (millis() - lastCommandMillis > ERM_COMMAND_TIMEOUT_MS) {
    setErmPwm(0, 0);
  }
}

void setErmPwm(byte pwmCommand1, byte pwmCommand2) {
  ermsEnabled = pwmCommand1 > 0 || pwmCommand2 > 0;

  digitalWrite(ERM_1_DIR_PIN, HIGH);
  digitalWrite(ERM_2_DIR_PIN, HIGH);

  OCR0B = pwmCommand1;
  OCR0A = pwmCommand2;
}
