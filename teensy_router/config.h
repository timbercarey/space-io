/*
 * Configuration for Teensy Router
 */

#ifndef CONFIG_H
#define CONFIG_H

// Serial ports
// Teensy 4.1 has multiple hardware serial ports:
// Serial  = USB (to laptop)
// Serial1 = pins 0 (RX) and 1 (TX)
// Serial2 = pins 7 (RX) and 8 (TX)
// Serial3 = pins 15 (RX) and 14 (TX)
// Serial4 = pins 16 (RX) and 17 (TX)
// etc.

// Pin assignments for Serial1 (Hapkit Board 1)
#define HAPKIT1_RX 0
#define HAPKIT1_TX 1

// Pin assignments for Serial2 (Hapkit Board 2)
#define HAPKIT2_RX 7
#define HAPKIT2_TX 8

// Communication settings
#define BAUD_RATE 115200
#define POSITION_UPDATE_RATE 60  // Hz

#endif