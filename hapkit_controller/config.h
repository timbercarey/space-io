/*
 * Configuration for Hapkit Controller
 */

#ifndef CONFIG_H
#define CONFIG_H

// Serial communication
#define BAUD_RATE 115200

// Control loop timing
#define CONTROL_LOOP_FREQ 1000  // Hz
#define CONTROL_LOOP_INTERVAL_US (1000000 / CONTROL_LOOP_FREQ)

#define POSITION_SEND_FREQ 60  // Hz
#define POSITION_SEND_INTERVAL_US (1000000 / POSITION_SEND_FREQ)

// Motor pin assignments
// Steering motor (motor 1)
#define STEERING_MOTOR_PIN 5    // PWM pin for motor control
#define STEERING_DIR_PIN 4      // Direction pin

// Throttle motor (motor 2)
#define THROTTLE_MOTOR_PIN 6    // PWM pin for motor control
#define THROTTLE_DIR_PIN 7      // Direction pin

// Encoder pin assignments
// Steering encoder
#define STEERING_ENCODER_A 2    // Encoder channel A (interrupt pin)
#define STEERING_ENCODER_B 3    // Encoder channel B (interrupt pin)

// Throttle encoder
#define THROTTLE_ENCODER_A 18   // Encoder channel A (interrupt pin)
#define THROTTLE_ENCODER_B 19   // Encoder channel B (interrupt pin)

// Motor parameters
#define MAX_FORCE 1000.0        // Maximum force value
#define MAX_PWM 255             // Maximum PWM value

// Encoder parameters
#define ENCODER_CPR 500         // Counts per revolution (adjust for your encoder)
#define ENCODER_RANGE 180.0     // Physical range in degrees
#define POSITION_CENTER 0       // Center position in encoder counts

#endif