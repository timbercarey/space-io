/*
 * Space IO - Teensy 4.1 Controller
 *
 * Reads four hardware quadrature encoder channels, reports raw counts and
 * calculated velocities to the laptop, and forwards player 1 force commands to
 * the Hapkit motor board.
 *
 * Message Format:
 *   FROM LAPTOP: F,P1S,P1T,P2S,P2T\n
 *   TO LAPTOP:   P,P1S_COUNTS,P1T_COUNTS,P2S_COUNTS,P2T_COUNTS,P1S_VEL,P1T_VEL,P2S_VEL,P2T_VEL[,VEL_AGE_US]\n
 *
 * Force values are integers (-1000 to 1000). Encoder positions are raw counts.
 * Encoder velocities are filtered counts per second.
 */

#include "config.h"
#include "QuadEncoder.h"
#include <math.h>

#define LAPTOP_SERIAL Serial
#define BUFFER_SIZE 128

QuadEncoder p1SteeringEncoder(
  P1_STEERING_ENCODER_CHANNEL,
  P1_STEERING_ENCODER_A,
  P1_STEERING_ENCODER_B
);
QuadEncoder p1ThrottleEncoder(
  P1_THROTTLE_ENCODER_CHANNEL,
  P1_THROTTLE_ENCODER_A,
  P1_THROTTLE_ENCODER_B
);
QuadEncoder p2SteeringEncoder(
  P2_STEERING_ENCODER_CHANNEL,
  P2_STEERING_ENCODER_A,
  P2_STEERING_ENCODER_B
);
QuadEncoder p2ThrottleEncoder(
  P2_THROTTLE_ENCODER_CHANNEL,
  P2_THROTTLE_ENCODER_A,
  P2_THROTTLE_ENCODER_B
);

char laptopBuffer[BUFFER_SIZE];
int laptopBufferIndex = 0;

long p1SteeringCounts = 0;
long p1ThrottleCounts = 0;
long p2SteeringCounts = 0;
long p2ThrottleCounts = 0;

struct VelocityState {
  long previousCounts;
  long accumulatedDeltaCounts;
  unsigned long accumulatedMicros;
  unsigned long lastSampleMicros;
  float filteredVelocity;
  bool zeroLatched;
};

float p1SteeringVelocity = 0.0f;
float p1ThrottleVelocity = 0.0f;
float p2SteeringVelocity = 0.0f;
float p2ThrottleVelocity = 0.0f;

VelocityState p1SteeringVelocityState = {0, 0, 0, 0, 0.0f, true};
VelocityState p1ThrottleVelocityState = {0, 0, 0, 0, 0.0f, true};
VelocityState p2SteeringVelocityState = {0, 0, 0, 0, 0.0f, true};
VelocityState p2ThrottleVelocityState = {0, 0, 0, 0, 0.0f, true};

int p1SteeringForce = 0;
int p1ThrottleForce = 0;

unsigned long lastControlUpdate = 0;
unsigned long lastPositionSend = 0;

const unsigned long CONTROL_UPDATE_INTERVAL_US = 1000000UL / CONTROL_UPDATE_RATE;
const unsigned long POSITION_SEND_INTERVAL_MS = 1000UL / POSITION_UPDATE_RATE;

void setup() {
  LAPTOP_SERIAL.begin(LAPTOP_BAUD_RATE);
  HAPKIT_SERIAL.begin(HAPKIT_BAUD_RATE);

  p1SteeringEncoder.setInitConfig();
  p1SteeringEncoder.init();
  p1ThrottleEncoder.setInitConfig();
  p1ThrottleEncoder.init();
  p2SteeringEncoder.setInitConfig();
  p2SteeringEncoder.init();
  p2ThrottleEncoder.setInitConfig();
  p2ThrottleEncoder.init();

  readEncoders();
  initializeVelocityState(p1SteeringVelocityState, p1SteeringCounts);
  initializeVelocityState(p1ThrottleVelocityState, p1ThrottleCounts);
  initializeVelocityState(p2SteeringVelocityState, p2SteeringCounts);
  initializeVelocityState(p2ThrottleVelocityState, p2ThrottleCounts);

  delay(500);
  lastControlUpdate = micros();
  lastPositionSend = millis();
  LAPTOP_SERIAL.println("Teensy Controller Ready");
}

void loop() {
  readFromLaptop();

  unsigned long currentMicros = micros();
  if (currentMicros - lastControlUpdate >= CONTROL_UPDATE_INTERVAL_US) {
    updateControlLoop(currentMicros - lastControlUpdate);
    lastControlUpdate = currentMicros;
  }

  unsigned long currentMillis = millis();
  if (currentMillis - lastPositionSend >= POSITION_SEND_INTERVAL_MS) {
    sendPositionsToLaptop();
    lastPositionSend = currentMillis;
  }
}

void updateControlLoop(unsigned long elapsedMicros) {
  readEncoders();
  updateVelocities(elapsedMicros);
  sendForcesToHapkit(p1SteeringForce, p1ThrottleForce);
}

void readEncoders() {
  p1SteeringCounts = p1SteeringEncoder.read();
  p1ThrottleCounts = p1ThrottleEncoder.read();
  p2SteeringCounts = p2SteeringEncoder.read();
  p2ThrottleCounts = p2ThrottleEncoder.read();
}

void initializeVelocityState(VelocityState& state, long counts) {
  state.previousCounts = counts;
  state.accumulatedDeltaCounts = 0;
  state.accumulatedMicros = 0;
  state.lastSampleMicros = micros();
  state.filteredVelocity = 0.0f;
  state.zeroLatched = true;
}

float clampVelocityAlpha(float alpha) {
  if (alpha < 0.0f) {
    return 0.0f;
  }
  if (alpha > 1.0f) {
    return 1.0f;
  }
  return alpha;
}

float calculateTimeConstantAlpha(float dtSeconds, float tauSeconds) {
  if (dtSeconds <= 0.0f) {
    return 0.0f;
  }
  if (tauSeconds <= 0.0f) {
    return 1.0f;
  }
  return clampVelocityAlpha(1.0f - expf(-dtSeconds / tauSeconds));
}

float selectVelocityFilterAlpha(float rawVelocity, float previousVelocity, float dtSeconds) {
#if VELOCITY_ASYMMETRIC_FILTER_ENABLED
  bool fastResponse = (
    rawVelocity * previousVelocity < 0.0f
    || fabsf(rawVelocity) > fabsf(previousVelocity)
  );

  #if VELOCITY_TIME_CONSTANT_FILTER_ENABLED
    return calculateTimeConstantAlpha(
      dtSeconds,
      fastResponse ? VELOCITY_FILTER_FAST_TAU_SECONDS : VELOCITY_FILTER_SLOW_TAU_SECONDS
    );
  #else
    return clampVelocityAlpha(
      fastResponse ? VELOCITY_FILTER_ALPHA_FAST : VELOCITY_FILTER_ALPHA_SLOW
    );
  #endif
#else
  #if VELOCITY_TIME_CONSTANT_FILTER_ENABLED
    return calculateTimeConstantAlpha(dtSeconds, VELOCITY_FILTER_TAU_SECONDS);
  #else
    return clampVelocityAlpha(VELOCITY_FILTER_ALPHA);
  #endif
#endif
}

float applyVelocityZeroLogic(float velocity, VelocityState& state) {
#if VELOCITY_ZERO_HYSTERESIS_ENABLED
  float speed = fabsf(velocity);

  if (state.zeroLatched) {
    if (speed < VELOCITY_ZERO_EXIT_COUNTS_PER_SECOND) {
      return 0.0f;
    }
    state.zeroLatched = false;
  } else if (speed < VELOCITY_ZERO_ENTER_COUNTS_PER_SECOND) {
    state.zeroLatched = true;
    return 0.0f;
  }

  return velocity;
#else
  if (fabsf(velocity) < VELOCITY_COUNTS_PER_SECOND_DEADBAND) {
    return 0.0f;
  }

  return velocity;
#endif
}

float decayStaleVelocity(float previousVelocity, float dtSeconds, VelocityState& state) {
#if VELOCITY_STALE_DECAY_ENABLED
  float decayAlpha = calculateTimeConstantAlpha(dtSeconds, VELOCITY_STALE_DECAY_TAU_SECONDS);
  float decayedVelocity = previousVelocity * (1.0f - decayAlpha);
  return applyVelocityZeroLogic(decayedVelocity, state);
#else
  (void)dtSeconds;
  state.zeroLatched = true;
  return 0.0f;
#endif
}

float updateVelocityEstimate(VelocityState& state, long currentCounts, unsigned long elapsedMicros) {
  if (elapsedMicros == 0) {
    return state.filteredVelocity;
  }

#if VELOCITY_ADAPTIVE_WINDOW_ENABLED
  long deltaCounts = currentCounts - state.previousCounts;
  state.previousCounts = currentCounts;
  state.accumulatedDeltaCounts += deltaCounts;
  state.accumulatedMicros += elapsedMicros;

  bool enoughMotion = labs(state.accumulatedDeltaCounts) >= VELOCITY_MIN_DELTA_COUNTS;
  bool enoughTime = state.accumulatedMicros >= VELOCITY_MAX_WINDOW_US;
  if (!enoughMotion && !enoughTime) {
    return state.filteredVelocity;
  }

  float dtSeconds = (float)state.accumulatedMicros / 1000000.0f;
  if (dtSeconds <= 0.0f) {
    return state.filteredVelocity;
  }

  if (!enoughMotion) {
    state.filteredVelocity = decayStaleVelocity(
      state.filteredVelocity,
      dtSeconds,
      state
    );
    state.accumulatedDeltaCounts = 0;
    state.accumulatedMicros = 0;
    state.lastSampleMicros = micros();
    return state.filteredVelocity;
  }

  float rawVelocity = (float)state.accumulatedDeltaCounts / dtSeconds;
  float alpha = selectVelocityFilterAlpha(
    rawVelocity,
    state.filteredVelocity,
    dtSeconds
  );
  state.filteredVelocity = (
    alpha * rawVelocity
    + (1.0f - alpha) * state.filteredVelocity
  );
  state.filteredVelocity = applyVelocityZeroLogic(state.filteredVelocity, state);
  state.accumulatedDeltaCounts = 0;
  state.accumulatedMicros = 0;
  state.lastSampleMicros = micros();
  return state.filteredVelocity;
#else
  float dtSeconds = (float)elapsedMicros / 1000000.0f;
  if (dtSeconds <= 0.0f) {
    return state.filteredVelocity;
  }

  float rawVelocity = (float)(currentCounts - state.previousCounts) / dtSeconds;
  if (fabsf(rawVelocity) < VELOCITY_COUNTS_PER_SECOND_DEADBAND) {
    rawVelocity = 0.0f;
  }

  float alpha = selectVelocityFilterAlpha(
    rawVelocity,
    state.filteredVelocity,
    dtSeconds
  );
  state.filteredVelocity = (
    alpha * rawVelocity
    + (1.0f - alpha) * state.filteredVelocity
  );
  state.filteredVelocity = applyVelocityZeroLogic(state.filteredVelocity, state);
  state.previousCounts = currentCounts;
  state.lastSampleMicros = micros();
  return state.filteredVelocity;
#endif
}

unsigned long latestVelocitySampleAgeUs() {
  unsigned long now = micros();
  unsigned long oldestSampleMicros = p1SteeringVelocityState.lastSampleMicros;

  if (p1ThrottleVelocityState.lastSampleMicros < oldestSampleMicros) {
    oldestSampleMicros = p1ThrottleVelocityState.lastSampleMicros;
  }
  if (p2SteeringVelocityState.lastSampleMicros < oldestSampleMicros) {
    oldestSampleMicros = p2SteeringVelocityState.lastSampleMicros;
  }
  if (p2ThrottleVelocityState.lastSampleMicros < oldestSampleMicros) {
    oldestSampleMicros = p2ThrottleVelocityState.lastSampleMicros;
  }

  return now - oldestSampleMicros;
}

void updateVelocities(unsigned long elapsedMicros) {
  p1SteeringVelocity = updateVelocityEstimate(
    p1SteeringVelocityState,
    p1SteeringCounts,
    elapsedMicros
  );
  p1ThrottleVelocity = updateVelocityEstimate(
    p1ThrottleVelocityState,
    p1ThrottleCounts,
    elapsedMicros
  );
  p2SteeringVelocity = updateVelocityEstimate(
    p2SteeringVelocityState,
    p2SteeringCounts,
    elapsedMicros
  );
  p2ThrottleVelocity = updateVelocityEstimate(
    p2ThrottleVelocityState,
    p2ThrottleCounts,
    elapsedMicros
  );
}

void readFromLaptop() {
  while (LAPTOP_SERIAL.available() > 0) {
    char c = LAPTOP_SERIAL.read();

    if (c == '\n') {
      laptopBuffer[laptopBufferIndex] = '\0';
      processLaptopMessage(laptopBuffer);
      laptopBufferIndex = 0;
    } else if (laptopBufferIndex < BUFFER_SIZE - 1) {
      laptopBuffer[laptopBufferIndex++] = c;
    } else {
      laptopBufferIndex = 0;
    }
  }
}

void processLaptopMessage(char* message) {
  // Expected format: F,P1S,P1T,P2S,P2T
  // Example: F,500,-200,0,0
  if (message[0] != 'F') {
    return;
  }

  int p1s, p1t, p2s, p2t;
  int parsed = sscanf(message, "F,%d,%d,%d,%d", &p1s, &p1t, &p2s, &p2t);

  if (parsed == 4) {
    p1SteeringForce = constrain(p1s, -1000, 1000);
    p1ThrottleForce = constrain(p1t, -1000, 1000);

    // Player 2 forces are parsed to keep the laptop protocol stable.
    (void)p2s;
    (void)p2t;
  }
}

void sendForcesToHapkit(int steeringForce, int throttleForce) {
  byte steeringCommand = forceToHapkitCommand(steeringForce);
  byte throttleCommand = forceToHapkitCommand(throttleForce);

  // Hapkit channel 1 is physically wired to throttle, channel 2 to steering.
  byte hapkitChannel1Command = throttleCommand;
  byte hapkitChannel2Command = steeringCommand;
  byte checksum = (byte)(hapkitChannel1Command + hapkitChannel2Command);

  HAPKIT_SERIAL.write((byte)0xAA);
  HAPKIT_SERIAL.write(hapkitChannel1Command);
  HAPKIT_SERIAL.write(hapkitChannel2Command);
  HAPKIT_SERIAL.write(checksum);
}

byte forceToHapkitCommand(int force) {
  force = constrain(force, -1000, 1000);

  if (force >= 0) {
    return map(
      force,
      0,
      1000,
      HAPKIT_STOP_COMMAND,
      HAPKIT_MAX_FORWARD_COMMAND
    );
  }

  return map(
    force,
    -1000,
    0,
    HAPKIT_MAX_REVERSE_COMMAND,
    HAPKIT_STOP_COMMAND
  );
}

void sendPositionsToLaptop() {
  // Format: P,P1S_COUNTS,P1T_COUNTS,P2S_COUNTS,P2T_COUNTS,P1S_VEL,P1T_VEL,P2S_VEL,P2T_VEL[,VEL_AGE_US]
  LAPTOP_SERIAL.print("P,");
  LAPTOP_SERIAL.print(p1SteeringCounts);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p1ThrottleCounts);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p2SteeringCounts);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p2ThrottleCounts);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p1SteeringVelocity, 2);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p1ThrottleVelocity, 2);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p2SteeringVelocity, 2);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p2ThrottleVelocity, 2);
#if VELOCITY_SEND_SAMPLE_AGE_ENABLED
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.println(latestVelocitySampleAgeUs());
#else
  LAPTOP_SERIAL.println();
#endif
}
