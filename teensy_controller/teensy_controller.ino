/*
 * Space IO - Teensy 4.1 Controller
 *
 * Reads four hardware quadrature encoder channels, reports raw counts and
 * calculated velocities to the laptop, and forwards player 1 force commands to
 * the Hapkit motor board.
 *
 * Message Format:
 *   FROM LAPTOP: F,P1S,P1T,P2S,P2T\n
 *   TO LAPTOP:   P,P1S_COUNTS,P1T_COUNTS,P2S_COUNTS,P2T_COUNTS,P1S_VEL,P1T_VEL,P2S_VEL,P2T_VEL\n
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

long previousP1SteeringCounts = 0;
long previousP1ThrottleCounts = 0;
long previousP2SteeringCounts = 0;
long previousP2ThrottleCounts = 0;

float p1SteeringVelocity = 0.0f;
float p1ThrottleVelocity = 0.0f;
float p2SteeringVelocity = 0.0f;
float p2ThrottleVelocity = 0.0f;

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
  previousP1SteeringCounts = p1SteeringCounts;
  previousP1ThrottleCounts = p1ThrottleCounts;
  previousP2SteeringCounts = p2SteeringCounts;
  previousP2ThrottleCounts = p2ThrottleCounts;

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

float calculateFilteredVelocity(long currentCounts, long previousCounts, float previousVelocity, float dtSeconds) {
  if (dtSeconds <= 0.0f) {
    return previousVelocity;
  }

  float rawVelocity = (float)(currentCounts - previousCounts) / dtSeconds;
  if (fabsf(rawVelocity) < VELOCITY_COUNTS_PER_SECOND_DEADBAND) {
    rawVelocity = 0.0f;
  }

  float filteredVelocity = (
    VELOCITY_FILTER_ALPHA * rawVelocity
    + (1.0f - VELOCITY_FILTER_ALPHA) * previousVelocity
  );

  if (fabsf(filteredVelocity) < VELOCITY_COUNTS_PER_SECOND_DEADBAND) {
    return 0.0f;
  }

  return filteredVelocity;
}

void updateVelocities(unsigned long elapsedMicros) {
  float dtSeconds = (float)elapsedMicros / 1000000.0f;

  p1SteeringVelocity = calculateFilteredVelocity(
    p1SteeringCounts,
    previousP1SteeringCounts,
    p1SteeringVelocity,
    dtSeconds
  );
  p1ThrottleVelocity = calculateFilteredVelocity(
    p1ThrottleCounts,
    previousP1ThrottleCounts,
    p1ThrottleVelocity,
    dtSeconds
  );
  p2SteeringVelocity = calculateFilteredVelocity(
    p2SteeringCounts,
    previousP2SteeringCounts,
    p2SteeringVelocity,
    dtSeconds
  );
  p2ThrottleVelocity = calculateFilteredVelocity(
    p2ThrottleCounts,
    previousP2ThrottleCounts,
    p2ThrottleVelocity,
    dtSeconds
  );

  previousP1SteeringCounts = p1SteeringCounts;
  previousP1ThrottleCounts = p1ThrottleCounts;
  previousP2SteeringCounts = p2SteeringCounts;
  previousP2ThrottleCounts = p2ThrottleCounts;
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
  // Format: P,P1S_COUNTS,P1T_COUNTS,P2S_COUNTS,P2T_COUNTS,P1S_VEL,P1T_VEL,P2S_VEL,P2T_VEL
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
  LAPTOP_SERIAL.println(p2ThrottleVelocity, 2);
}
