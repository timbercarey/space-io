/*
 * Encoder reading implementation
 */

#include "encoder.h"

EncoderReader::EncoderReader(int pinA, int pinB) {
  _pinA = pinA;
  _pinB = pinB;
  _position = 0;
  _lastStateA = 0;
}

void EncoderReader::begin() {
  pinMode(_pinA, INPUT_PULLUP);
  pinMode(_pinB, INPUT_PULLUP);
  
  _lastStateA = digitalRead(_pinA);
}

void EncoderReader::update() {
  readEncoder();
}

void EncoderReader::readEncoder() {
  // Read current state
  int stateA = digitalRead(_pinA);
  int stateB = digitalRead(_pinB);
  
  // Check if state A changed
  if (stateA != _lastStateA) {
    // If A and B are different, we're going forward
    if (stateA != stateB) {
      _position++;
    } else {
      _position--;
    }
  }
  
  _lastStateA = stateA;
}

long EncoderReader::getPosition() {
  return _position;
}

float EncoderReader::getNormalizedPosition() {
  // Convert encoder counts to normalized position (-1.0 to 1.0)
  // Assuming encoder center is at POSITION_CENTER
  
  long relativePosition = _position - POSITION_CENTER;
  
  // Calculate range in encoder counts
  float countsPerDegree = ENCODER_CPR / 360.0;
  float maxCounts = (ENCODER_RANGE / 2.0) * countsPerDegree;
  
  // Normalize
  float normalized = (float)relativePosition / maxCounts;
  
  // Constrain to -1.0 to 1.0
  return constrain(normalized, -1.0, 1.0);
}

void EncoderReader::reset() {
  _position = 0;
}