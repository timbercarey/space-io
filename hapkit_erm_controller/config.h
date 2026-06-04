/*
 * Configuration for Hapkit ERM Controller
 */

#ifndef CONFIG_H
#define CONFIG_H

// Serial communication from Teensy TX pin 20 to this Hapkit serial RX.
#define BAUD_RATE 115200

// Motor pin assignments matched to the Hapkit board hardware profile.
// The two ERMs are connected to the two normal Hapkit motor output terminals.
// ERM 1 is commanded by player 1 events. ERM 2 is commanded by player 2 events.
#define ERM_1_MOTOR_PIN 5
#define ERM_1_DIR_PIN 8
#define ERM_2_MOTOR_PIN 6
#define ERM_2_DIR_PIN 7

// Binary ERM command packets:
//   Legacy single-channel: 0xE1,PWM,CHECKSUM
//   Dual-channel:          0xE2,ERM1_PWM,ERM2_PWM,CHECKSUM
#define ERM_PACKET_HEADER 0xE1
#define ERM_DUAL_PACKET_HEADER 0xE2

// Fail off if the Teensy command stream stops.
#define ERM_COMMAND_TIMEOUT_MS 100

#endif
