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

// Hapkit motor command serial link.
// Serial4 TX is pin 17 on Teensy 4.1.
#define HAPKIT_SERIAL Serial4
#define HAPKIT_STOP_COMMAND 127
#define HAPKIT_MAX_FORWARD_COMMAND 255
#define HAPKIT_MAX_REVERSE_COMMAND 0

// Communication settings
#define LAPTOP_BAUD_RATE 1000000
#define HAPKIT_BAUD_RATE 115200
#define BAUD_RATE LAPTOP_BAUD_RATE
#define POSITION_UPDATE_RATE 500  // Hz
#define CONTROL_UPDATE_RATE 1000 // Hz

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
