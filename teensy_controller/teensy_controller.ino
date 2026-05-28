/*
 * Space IO - Teensy 4.1 Controller
 *
 * Reads four hardware quadrature encoder channels, reports raw counts and
 * calculated velocities to the laptop, and forwards player force commands to
 * two Hapkit motor boards.
 *
 * Message Format:
 *   FROM LAPTOP: F,P1S,P1T,P2S,P2T[,LED_MASK]\n
 *   TO LAPTOP:   P,P1S_COUNTS,P1T_COUNTS,P2S_COUNTS,P2T_COUNTS,P1S_VEL,P1T_VEL,P2S_VEL,P2T_VEL[,VEL_AGE_US]\n
 *
 * Force values are integers (-1000 to 1000). Encoder positions are raw counts.
 * Encoder velocities are filtered counts per second.
 latest
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
int p2SteeringForce = 0;
int p2ThrottleForce = 0;

enum Player1SwitchPosition {
  P1_SWITCH_CENTER = 0,
  P1_SWITCH_POSITION_1 = 1,
  P1_SWITCH_POSITION_2 = 2,
  P1_SWITCH_BOTH_ACTIVE = 3
};

Player1SwitchPosition p1SwitchPosition = P1_SWITCH_CENTER;
bool p2SwitchActive = false;

unsigned long lastControlUpdate = 0;
unsigned long lastPositionSend = 0;
unsigned long lastForceCommandMillis = 0;
unsigned long lastLedFlashToggle = 0;
unsigned long lastStarLedFlashToggle = 0;
unsigned long lastDeathLedFlashToggle = 0;
bool ledFlashOn = false;
bool starLedFlashOn = false;
bool deathLedFlashOn = false;
bool p1LedPresent = true;
bool p1LedStarActive = false;
bool p1LedDead = false;
bool p2LedPresent = false;
bool p2LedStarActive = false;
bool p2LedDead = false;

const unsigned long CONTROL_UPDATE_INTERVAL_US = 1000000UL / CONTROL_UPDATE_RATE;
const unsigned long POSITION_SEND_INTERVAL_MS = 1000UL / POSITION_UPDATE_RATE;
const unsigned long LED_FLASH_INTERVAL_MS = 250;
const unsigned long STAR_LED_FLASH_INTERVAL_MS = 180;
const unsigned long DEATH_LED_FLASH_INTERVAL_MS = 70;
const int LED_MASK_P1_PRESENT = 1 << 0;
const int LED_MASK_P1_STAR = 1 << 1;
const int LED_MASK_P1_DEAD = 1 << 2;
const int LED_MASK_P2_PRESENT = 1 << 3;
const int LED_MASK_P2_STAR = 1 << 4;
const int LED_MASK_P2_DEAD = 1 << 5;

void sendForcesToHapkit(Print& hapkitSerial, int steeringForce, int throttleForce);
byte forceToHapkitCommand(int force);
void stopForcesIfLaptopTimedOut();
void setupPlayerControls();
void readPlayerControls();
Player1SwitchPosition readPlayer1Switch();
bool readPlayer2Switch();
int player1DifficultyLevel();
void updateLedFlashTest();
void applyLedStatusMask(int ledMask);
void updateGameStatusLeds();
void setPlayer1Leds(bool led1On, bool led2On);
void setPlayer2Leds(bool led1On, bool led2On);

void setup() {
  LAPTOP_SERIAL.begin(LAPTOP_BAUD_RATE);
  HAPKIT_A_SERIAL.begin(HAPKIT_BAUD_RATE);
  HAPKIT_B_SERIAL.begin(HAPKIT_BAUD_RATE);

  setupPlayerControls();

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
  lastForceCommandMillis = millis();
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
#if LED_FLASH_TEST_ENABLED
  updateLedFlashTest();
#else
  updateGameStatusLeds();
#endif

  if (currentMillis - lastPositionSend >= POSITION_SEND_INTERVAL_MS) {
    sendPositionsToLaptop();
    lastPositionSend = currentMillis;
  }
}

void updateControlLoop(unsigned long elapsedMicros) {
  readEncoders();
  readPlayerControls();
  updateVelocities(elapsedMicros);
  stopForcesIfLaptopTimedOut();
  // Logical game P1 is the 3-way-switch station on hardware channel B.
  // Logical game P2 is the optional 2-way-switch station on hardware channel A.
  sendForcesToHapkit(HAPKIT_A_SERIAL, p2SteeringForce, p2ThrottleForce);
  sendForcesToHapkit(HAPKIT_B_SERIAL, p1SteeringForce, p1ThrottleForce);
}

void setupPlayerControls() {
  pinMode(P1_LED_1_PIN, OUTPUT);
  pinMode(P1_LED_2_PIN, OUTPUT);
  pinMode(P2_LED_1_PIN, OUTPUT);
  pinMode(P2_LED_2_PIN, OUTPUT);

  digitalWrite(P1_LED_1_PIN, LED_OFF_LEVEL);
  digitalWrite(P1_LED_2_PIN, LED_OFF_LEVEL);
  digitalWrite(P2_LED_1_PIN, P2_LED_1_OFF_LEVEL);
  digitalWrite(P2_LED_2_PIN, LED_OFF_LEVEL);

  pinMode(P1_SWITCH_POSITION_1_PIN, P1_SWITCH_INPUT_MODE);
  pinMode(P1_SWITCH_POSITION_2_PIN, P1_SWITCH_INPUT_MODE);
  pinMode(P2_SWITCH_PIN, P2_SWITCH_INPUT_MODE);

  readPlayerControls();
}

void readPlayerControls() {
  p1SwitchPosition = readPlayer1Switch();
  p2SwitchActive = readPlayer2Switch();
}

Player1SwitchPosition readPlayer1Switch() {
  bool position1Active = digitalRead(P1_SWITCH_POSITION_1_PIN) == P1_SWITCH_ACTIVE_LEVEL;
  bool position2Active = digitalRead(P1_SWITCH_POSITION_2_PIN) == P1_SWITCH_ACTIVE_LEVEL;

  if (position1Active && position2Active) {
    return P1_SWITCH_BOTH_ACTIVE;
  }
  if (position1Active) {
    return P1_SWITCH_POSITION_1;
  }
  if (position2Active) {
    return P1_SWITCH_POSITION_2;
  }
  return P1_SWITCH_CENTER;
}

bool readPlayer2Switch() {
  return digitalRead(P2_SWITCH_PIN) == P2_SWITCH_ACTIVE_LEVEL;
}

int player1DifficultyLevel() {
  if (p1SwitchPosition == P1_SWITCH_POSITION_1) {
    return 1;
  }
  if (p1SwitchPosition == P1_SWITCH_POSITION_2) {
    return 3;
  }
  return 2;
}

void updateLedFlashTest() {
  unsigned long currentMillis = millis();

  if (currentMillis - lastLedFlashToggle < LED_FLASH_INTERVAL_MS) {
    return;
  }

  lastLedFlashToggle = currentMillis;
  ledFlashOn = !ledFlashOn;
  setPlayer1Leds(ledFlashOn, ledFlashOn);
  setPlayer2Leds(ledFlashOn, ledFlashOn);
}

void setPlayer1Leds(bool led1On, bool led2On) {
  digitalWrite(P1_LED_1_PIN, led1On ? LED_ON_LEVEL : LED_OFF_LEVEL);
  digitalWrite(P1_LED_2_PIN, led2On ? LED_ON_LEVEL : LED_OFF_LEVEL);
}

void setPlayer2Leds(bool led1On, bool led2On) {
  digitalWrite(P2_LED_1_PIN, led2On ? P2_LED_1_ON_LEVEL : P2_LED_1_OFF_LEVEL);
  digitalWrite(P2_LED_2_PIN, led1On ? LED_ON_LEVEL : LED_OFF_LEVEL);
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
  // Expected format: F,P1S,P1T,P2S,P2T[,LED_MASK]
  // Example: F,500,-200,0,0,11
  if (message[0] != 'F') {
    return;
  }

  int p1s, p1t, p2s, p2t, ledMask;
  int parsed = sscanf(message, "F,%d,%d,%d,%d,%d", &p1s, &p1t, &p2s, &p2t, &ledMask);

  if (parsed >= 4) {
    p1SteeringForce = constrain(p1s, -1000, 1000);
    p1ThrottleForce = constrain(p1t, -1000, 1000);
    p2SteeringForce = constrain(p2s, -1000, 1000);
    p2ThrottleForce = constrain(p2t, -1000, 1000);
    if (parsed >= 5) {
      applyLedStatusMask(ledMask);
    }
    lastForceCommandMillis = millis();
  }
}

void applyLedStatusMask(int ledMask) {
  p1LedPresent = (ledMask & LED_MASK_P1_PRESENT) != 0;
  p1LedStarActive = (ledMask & LED_MASK_P1_STAR) != 0;
  p1LedDead = (ledMask & LED_MASK_P1_DEAD) != 0;
  p2LedPresent = (ledMask & LED_MASK_P2_PRESENT) != 0;
  p2LedStarActive = (ledMask & LED_MASK_P2_STAR) != 0;
  p2LedDead = (ledMask & LED_MASK_P2_DEAD) != 0;
}

void updateGameStatusLeds() {
  unsigned long currentMillis = millis();

  if (currentMillis - lastStarLedFlashToggle >= STAR_LED_FLASH_INTERVAL_MS) {
    lastStarLedFlashToggle = currentMillis;
    starLedFlashOn = !starLedFlashOn;
  }

  if (currentMillis - lastDeathLedFlashToggle >= DEATH_LED_FLASH_INTERVAL_MS) {
    lastDeathLedFlashToggle = currentMillis;
    deathLedFlashOn = !deathLedFlashOn;
  }

  bool p1Led1On = p1LedPresent;
  bool p1Led2On = p1LedStarActive && starLedFlashOn;
  bool p2Led1On = p2LedPresent;
  bool p2Led2On = p2LedStarActive && starLedFlashOn;

  if (p1LedDead) {
    p1Led1On = deathLedFlashOn;
    p1Led2On = deathLedFlashOn;
  }

  if (p2LedDead) {
    p2Led1On = deathLedFlashOn;
    p2Led2On = deathLedFlashOn;
  }

  setPlayer1Leds(p1Led1On, p1Led2On);
  setPlayer2Leds(p2Led1On, p2Led2On);
}

void stopForcesIfLaptopTimedOut() {
  if (millis() - lastForceCommandMillis <= FORCE_COMMAND_TIMEOUT_MS) {
    return;
  }

  p1SteeringForce = 0;
  p1ThrottleForce = 0;
  p2SteeringForce = 0;
  p2ThrottleForce = 0;
}

void sendForcesToHapkit(Print& hapkitSerial, int steeringForce, int throttleForce) {
  byte steeringCommand = forceToHapkitCommand(steeringForce);
  byte throttleCommand = forceToHapkitCommand(throttleForce);

  // Hapkit channel 1 is physically wired to throttle, channel 2 to steering.
  byte hapkitChannel1Command = throttleCommand;
  byte hapkitChannel2Command = steeringCommand;
  byte checksum = (byte)(hapkitChannel1Command + hapkitChannel2Command);

  hapkitSerial.write((byte)0xAA);
  hapkitSerial.write(hapkitChannel1Command);
  hapkitSerial.write(hapkitChannel2Command);
  hapkitSerial.write(checksum);
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
  // Format: P,P1S_COUNTS,P1T_COUNTS,P2S_COUNTS,P2T_COUNTS,P1S_VEL,P1T_VEL,P2S_VEL,P2T_VEL[,VEL_AGE_US],DIFFICULTY,P2_ENABLED,PIN25_ACTIVE,PIN26_ACTIVE,PIN9_ACTIVE
  LAPTOP_SERIAL.print("P,");
  // Logical game P1 is the 3-way-switch station on hardware channel B.
  LAPTOP_SERIAL.print(p2SteeringCounts);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p2ThrottleCounts);
  LAPTOP_SERIAL.print(",");
  // Logical game P2 is the optional 2-way-switch station on hardware channel A.
  LAPTOP_SERIAL.print(p1SteeringCounts);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p1ThrottleCounts);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p2SteeringVelocity, 2);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p2ThrottleVelocity, 2);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p1SteeringVelocity, 2);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p1ThrottleVelocity, 2);
#if VELOCITY_SEND_SAMPLE_AGE_ENABLED
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(latestVelocitySampleAgeUs());
#endif
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(player1DifficultyLevel());
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p2SwitchActive ? 1 : 0);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(digitalRead(P1_SWITCH_POSITION_1_PIN) == P1_SWITCH_ACTIVE_LEVEL ? 1 : 0);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(digitalRead(P1_SWITCH_POSITION_2_PIN) == P1_SWITCH_ACTIVE_LEVEL ? 1 : 0);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.println(digitalRead(P2_SWITCH_PIN) == P2_SWITCH_ACTIVE_LEVEL ? 1 : 0);
}
