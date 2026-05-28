/*
 * Configuration for Teensy Controller
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
// Serial5 = pins 21 (RX) and 20 (TX)
// Serial7 = pins 28 (RX) and 29 (TX)
// etc.

// Encoder assignments for Teensy 4.1 hardware quadrature channels
#define P1_STEERING_ENCODER_CHANNEL 1
#define P1_STEERING_ENCODER_A 0
#define P1_STEERING_ENCODER_B 1

#define P1_THROTTLE_ENCODER_CHANNEL 2
#define P1_THROTTLE_ENCODER_A 2
#define P1_THROTTLE_ENCODER_B 3

#define P2_STEERING_ENCODER_CHANNEL 3
#define P2_STEERING_ENCODER_A 7
#define P2_STEERING_ENCODER_B 8

#define P2_THROTTLE_ENCODER_CHANNEL 4
#define P2_THROTTLE_ENCODER_A 30
#define P2_THROTTLE_ENCODER_B 31

// Hapkit motor command serial links.
// Module A receives player 1 force commands. Module B receives player 2.
// Only TX is needed for the motor command stream.
#define HAPKIT_A_SERIAL Serial4  // TX pin 17
#define HAPKIT_B_SERIAL Serial7  // TX pin 29
#define HAPKIT_ERM_SERIAL Serial5  // TX pin 20
#define HAPKIT_STOP_COMMAND 127
#define HAPKIT_MAX_FORWARD_COMMAND 255
#define HAPKIT_MAX_REVERSE_COMMAND 0
#define ERM_PACKET_HEADER 0xE1
#define ERM_DUAL_PACKET_HEADER 0xE2

// ERM test override. When enabled, the Teensy ignores laptop ERM commands and
// sends the configured PWM command to the ERM Hapkit continuously.
const bool ERM_TEENSY_OVERRIDE_ENABLED = false;
const bool ERM_TEENSY_ENABLED = true;
const byte ERM_TEENSY_PWM_COMMAND = 30;

// PWM used when the laptop sends only ERM_ENABLE and not an explicit ERM_PWM.
const byte ERM_LAPTOP_ENABLE_PWM_COMMAND = 255;

// Player switch and LED panel wiring. The 3-way switch drives the Teensy inputs
// high when active. The 2-way switch uses the opposite state from the grounded
// position to enable player 2.
#define P1_LED_1_PIN 28
#define P1_LED_2_PIN 27
#define P1_SWITCH_POSITION_1_PIN 25
#define P1_SWITCH_POSITION_2_PIN 26
#define P1_SWITCH_INPUT_MODE INPUT_PULLDOWN
#define P1_SWITCH_ACTIVE_LEVEL HIGH

#define P2_LED_1_PIN 41
#define P2_LED_2_PIN 40
#define P2_SWITCH_PIN 9
#define P2_SWITCH_INPUT_MODE INPUT_PULLUP
#define P2_SWITCH_ACTIVE_LEVEL HIGH

#define LED_ON_LEVEL LOW
#define LED_OFF_LEVEL HIGH
#define P2_LED_1_ON_LEVEL HIGH
#define P2_LED_1_OFF_LEVEL LOW
#define LED_FLASH_TEST_ENABLED 0

// Communication settings
#define LAPTOP_BAUD_RATE 1000000
#define HAPKIT_BAUD_RATE 115200
#define BAUD_RATE LAPTOP_BAUD_RATE
#define POSITION_UPDATE_RATE 500  // Hz
#define CONTROL_UPDATE_RATE 1000 // Hz
#define FORCE_COMMAND_TIMEOUT_MS 100

// Encoder velocity settings
#define VELOCITY_FILTER_ALPHA 0.45f
#define VELOCITY_COUNTS_PER_SECOND_DEADBAND 1.0f

// Robust velocity processing feature switches. Set any of these to 0 to return
// that part of the pipeline to the simpler baseline behavior for testing.
#define VELOCITY_ADAPTIVE_WINDOW_ENABLED 1
#define VELOCITY_TIME_CONSTANT_FILTER_ENABLED 1
#define VELOCITY_ASYMMETRIC_FILTER_ENABLED 1
#define VELOCITY_ZERO_HYSTERESIS_ENABLED 1
#define VELOCITY_STALE_DECAY_ENABLED 1
#define VELOCITY_SEND_SAMPLE_AGE_ENABLED 1

// Adaptive estimator waits for enough encoder motion or enough elapsed time
// before accepting a new raw velocity measurement.
#define VELOCITY_MIN_DELTA_COUNTS 3L
#define VELOCITY_MAX_WINDOW_US 6000UL

// Time-constant IIR settings. Smaller tau reacts faster with less phase lag.
#define VELOCITY_FILTER_TAU_SECONDS 0.003f
#define VELOCITY_FILTER_FAST_TAU_SECONDS 0.0015f
#define VELOCITY_FILTER_SLOW_TAU_SECONDS 0.0040f

// Fixed-alpha fallbacks used when VELOCITY_TIME_CONSTANT_FILTER_ENABLED is 0.
#define VELOCITY_FILTER_ALPHA_FAST 0.75f
#define VELOCITY_FILTER_ALPHA_SLOW 0.25f

// Zero hysteresis thresholds in raw encoder counts/sec.
#define VELOCITY_ZERO_ENTER_COUNTS_PER_SECOND 80.0f
#define VELOCITY_ZERO_EXIT_COUNTS_PER_SECOND 160.0f

// Smoothly decay held velocity toward zero when a measurement window expires
// without enough encoder movement.
#define VELOCITY_STALE_DECAY_TAU_SECONDS 0.010f

// Emit an extra VEL_AGE_US field when VELOCITY_SEND_SAMPLE_AGE_ENABLED is 1.
// The Python-side stale timeout lives in game_engine/config.py.

#endif
