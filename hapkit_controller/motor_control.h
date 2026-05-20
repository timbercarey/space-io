/*
 * Motor control functions
 */

#ifndef MOTOR_CONTROL_H
#define MOTOR_CONTROL_H

#include <Arduino.h>
#include "config.h"

class MotorController {
  public:
    MotorController(int pwmPin, int dirPin);
    void begin();
    void setForce(float force);  // -1000 to 1000
    
  private:
    int _pwmPin;
    int _dirPin;
    
    int forceToPWM(float force);
};

#endif