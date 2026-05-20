/*
 * Encoder reading functions
 */

#ifndef ENCODER_H
#define ENCODER_H

#include <Arduino.h>
#include "config.h"

class EncoderReader {
  public:
    EncoderReader(int pinA, int pinB);
    void begin();
    void update();
    long getPosition();
    float getNormalizedPosition();  // -1.0 to 1.0
    void reset();
    
  private:
    int _pinA;
    int _pinB;
    volatile long _position;
    int _lastStateA;
    
    void readEncoder();
};

#endif