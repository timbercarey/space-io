/*
 * Configuration for Hapkit Controller
 */

#ifndef CONFIG_H
#define CONFIG_H

// Serial communication
#define BAUD_RATE 115200

// Motor pin assignments matched to the Hapkit board hardware profile
// Steering motor (motor 1): Timer0 channel B
#define STEERING_MOTOR_PIN 5    // PWM pin
#define STEERING_DIR_PIN 8      // Direction pin

// Throttle motor (motor 2): Timer0 channel A
#define THROTTLE_MOTOR_PIN 6    // PWM pin
#define THROTTLE_DIR_PIN 7      // Direction pin

// Motor parameters
#define MAX_FORCE 1000.0        // Maximum force value
#define MAX_PWM 255             // Maximum PWM value

// Binary motor command packet
#define HAPKIT_PACKET_HEADER 0xAA
#define HAPKIT_STOP_COMMAND 127
#define HAPKIT_DEADBAND_LOW 124
#define HAPKIT_DEADBAND_HIGH 130
#define HAPKIT_FORWARD_START 131
#define HAPKIT_REVERSE_START 123
#define HAPKIT_MAX_FORWARD_COMMAND 255
#define HAPKIT_MAX_REVERSE_COMMAND 0

#endif
