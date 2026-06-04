/*
 * Space IO - Teensy 4.1 Pin State Reader
 *
 * Minimal hardware test sketch for checking switch wiring. It reads the
 * controller switch inputs with their configured input mode and prints named
 * control
 * states and a full digital pin snapshot over USB serial.
 *
 * Open Serial Monitor at 1000000 baud.
 */

#include "config.h"

#define SERIAL_PORT Serial
#define REPORT_INTERVAL_MS 100
#define FIRST_DIGITAL_PIN 0
#define LAST_DIGITAL_PIN 41

struct NamedPin {
  const char* name;
  int pin;
  int inputMode;
  int activeLevel;
};

const NamedPin NAMED_PINS[] = {
  {"P1_SWITCH_POSITION_1", P1_SWITCH_POSITION_1_PIN, P1_SWITCH_INPUT_MODE, P1_SWITCH_ACTIVE_LEVEL},
  {"P1_SWITCH_POSITION_2", P1_SWITCH_POSITION_2_PIN, P1_SWITCH_INPUT_MODE, P1_SWITCH_ACTIVE_LEVEL},
  {"P2_SWITCH", P2_SWITCH_PIN, P2_SWITCH_INPUT_MODE, P2_SWITCH_ACTIVE_LEVEL},
  {"P1_LED_1", P1_LED_1_PIN, INPUT, LOW},
  {"P1_LED_2", P1_LED_2_PIN, INPUT, LOW},
  {"P2_LED_1", P2_LED_1_PIN, INPUT, HIGH},
  {"P2_LED_2", P2_LED_2_PIN, INPUT, LOW},
  {"P1_STEERING_ENCODER_A", P1_STEERING_ENCODER_A, INPUT, HIGH},
  {"P1_STEERING_ENCODER_B", P1_STEERING_ENCODER_B, INPUT, HIGH},
  {"P1_THROTTLE_ENCODER_A", P1_THROTTLE_ENCODER_A, INPUT, HIGH},
  {"P1_THROTTLE_ENCODER_B", P1_THROTTLE_ENCODER_B, INPUT, HIGH},
  {"P2_STEERING_ENCODER_A", P2_STEERING_ENCODER_A, INPUT, HIGH},
  {"P2_STEERING_ENCODER_B", P2_STEERING_ENCODER_B, INPUT, HIGH},
  {"P2_THROTTLE_ENCODER_A", P2_THROTTLE_ENCODER_A, INPUT, HIGH},
  {"P2_THROTTLE_ENCODER_B", P2_THROTTLE_ENCODER_B, INPUT, HIGH},
};

const int NAMED_PIN_COUNT = sizeof(NAMED_PINS) / sizeof(NAMED_PINS[0]);

unsigned long lastReportMillis = 0;

void setupPins();
void printNamedPins();
void printDigitalSnapshot();
void printPinState(int pin);

void setup() {
  SERIAL_PORT.begin(LAPTOP_BAUD_RATE);
  setupPins();

  delay(500);
  SERIAL_PORT.println("Teensy Pin State Reader Ready");
  SERIAL_PORT.println("P1 3-way uses INPUT_PULLDOWN and reads HIGH/active.");
  SERIAL_PORT.println("P2 2-way uses INPUT_PULLUP and reads HIGH/active.");
}

void loop() {
  unsigned long now = millis();
  if (now - lastReportMillis < REPORT_INTERVAL_MS) {
    return;
  }

  lastReportMillis = now;
  printNamedPins();
  printDigitalSnapshot();
  SERIAL_PORT.println();
}

void setupPins() {
  for (int i = 0; i < NAMED_PIN_COUNT; i++) {
    pinMode(NAMED_PINS[i].pin, NAMED_PINS[i].inputMode);
  }
}

void printNamedPins() {
  SERIAL_PORT.print("named");

  for (int i = 0; i < NAMED_PIN_COUNT; i++) {
    int state = digitalRead(NAMED_PINS[i].pin);
    bool active = state == NAMED_PINS[i].activeLevel;

    SERIAL_PORT.print(',');
    SERIAL_PORT.print(NAMED_PINS[i].name);
    SERIAL_PORT.print("=");
    SERIAL_PORT.print(state == HIGH ? "HIGH" : "LOW");
    SERIAL_PORT.print(active ? "(active)" : "(inactive)");
  }

  SERIAL_PORT.println();
}

void printDigitalSnapshot() {
  SERIAL_PORT.print("pins");

  for (int pin = FIRST_DIGITAL_PIN; pin <= LAST_DIGITAL_PIN; pin++) {
    SERIAL_PORT.print(',');
    printPinState(pin);
  }

  SERIAL_PORT.println();
}

void printPinState(int pin) {
  SERIAL_PORT.print(pin);
  SERIAL_PORT.print('=');
  SERIAL_PORT.print(digitalRead(pin) == HIGH ? '1' : '0');
}
