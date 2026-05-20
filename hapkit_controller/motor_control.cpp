/*
 * Motor control implementation
 */

#include "motor_control.h"

MotorController::MotorController(int pwmPin, int dirPin) {
  _pwmPin = pwmPin;
  _dirPin = dirPin;
}

void MotorController::begin() {
  pinMode(_pwmPin, OUTPUT);
  pinMode(_dirPin, OUTPUT);
  
  // Start with motor off
  analogWrite(_pwmPin, 0);
  digitalWrite(_dirPin, LOW);
}

void MotorController::setForce(float force) {
  // Constrain force to valid range
  force = constrain(force, -MAX_FORCE, MAX_FORCE);
  
  // Set direction
  if (force >= 0) {
    digitalWrite(_dirPin, HIGH);
  } else {
    digitalWrite(_dirPin, LOW);
    force = -force;  // Make positive for PWM calculation
  }
  
  // Convert force to PWM
  int pwm = forceToPWM(force);
  analogWrite(_pwmPin, pwm);
}

int MotorController::forceToPWM(float force) {
  // Linear mapping from force to PWM
  // force: 0 to MAX_FORCE
  // pwm: 0 to MAX_PWM
  
  int pwm = (int)((force / MAX_FORCE) * MAX_PWM);
  return constrain(pwm, 0, MAX_PWM);
}