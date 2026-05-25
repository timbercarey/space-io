/*
 * Space IO - Teensy 4.1 Router
 * 
 * Routes messages between laptop (USB Serial) and Hapkit boards (Serial1, Serial2)
 * 
 * Message Format:
 *   FROM LAPTOP: F,P1S,P1T,P2S,P2T\n
 *   TO LAPTOP:   P,P1S_COUNTS,P1T_COUNTS,P2S_COUNTS,P2T_COUNTS\n
 *   
 * Where force values are integers (-1000 to 1000) and encoder positions are raw counts
 */

// Serial port assignments
#define LAPTOP_SERIAL Serial      // USB Serial to laptop
#define HAPKIT1_SERIAL Serial1    // Hardware Serial to Hapkit Board 1 (Player 1)
#define HAPKIT2_SERIAL Serial2    // Hardware Serial to Hapkit Board 2 (Player 2)

// Configuration
#define BAUD_RATE 115200
#define BUFFER_SIZE 128

// Buffers for incoming data
char laptopBuffer[BUFFER_SIZE];
char hapkit1Buffer[BUFFER_SIZE];
char hapkit2Buffer[BUFFER_SIZE];

int laptopBufferIndex = 0;
int hapkit1BufferIndex = 0;
int hapkit2BufferIndex = 0;

// Latest raw encoder counts from each controller
long p1_steering = 0;
long p1_throttle = 0;
long p2_steering = 0;
long p2_throttle = 0;

// Timing
unsigned long lastPositionSend = 0;
const unsigned long POSITION_SEND_INTERVAL = 16; // ~60 Hz (16ms)

void setup() {
  // Initialize serial ports
  LAPTOP_SERIAL.begin(BAUD_RATE);
  HAPKIT1_SERIAL.begin(BAUD_RATE);
  HAPKIT2_SERIAL.begin(BAUD_RATE);
  
  // Wait for serial ports to initialize
  delay(1000);
  
  // Send ready message
  LAPTOP_SERIAL.println("Teensy Router Ready");
}

void loop() {
  // Read from laptop and forward force commands to hapkits
  readFromLaptop();
  
  // Read from hapkits and aggregate position data
  readFromHapkit1();
  readFromHapkit2();
  
  // Send aggregated position data to laptop at regular intervals
  unsigned long currentTime = millis();
  if (currentTime - lastPositionSend >= POSITION_SEND_INTERVAL) {
    sendPositionsToLaptop();
    lastPositionSend = currentTime;
  }
}

void readFromLaptop() {
  while (LAPTOP_SERIAL.available() > 0) {
    char c = LAPTOP_SERIAL.read();
    
    if (c == '\n') {
      // End of message
      laptopBuffer[laptopBufferIndex] = '\0';
      processLaptopMessage(laptopBuffer);
      laptopBufferIndex = 0;
    } else if (laptopBufferIndex < BUFFER_SIZE - 1) {
      laptopBuffer[laptopBufferIndex++] = c;
    } else {
      // Buffer overflow, reset
      laptopBufferIndex = 0;
    }
  }
}

void processLaptopMessage(char* message) {
  // Expected format: F,P1S,P1T,P2S,P2T
  // Example: F,500,-200,300,100
  
  if (message[0] != 'F') {
    return; // Not a force command
  }
  
  // Parse force values
  int p1s, p1t, p2s, p2t;
  int parsed = sscanf(message, "F,%d,%d,%d,%d", &p1s, &p1t, &p2s, &p2t);
  
  if (parsed == 4) {
    // Send to Hapkit 1 (Player 1)
    HAPKIT1_SERIAL.print("F,");
    HAPKIT1_SERIAL.print(p1s);
    HAPKIT1_SERIAL.print(",");
    HAPKIT1_SERIAL.println(p1t);
    
    // Send to Hapkit 2 (Player 2)
    HAPKIT2_SERIAL.print("F,");
    HAPKIT2_SERIAL.print(p2s);
    HAPKIT2_SERIAL.print(",");
    HAPKIT2_SERIAL.println(p2t);
  }
}

void readFromHapkit1() {
  while (HAPKIT1_SERIAL.available() > 0) {
    char c = HAPKIT1_SERIAL.read();
    
    if (c == '\n') {
      // End of message
      hapkit1Buffer[hapkit1BufferIndex] = '\0';
      processHapkit1Message(hapkit1Buffer);
      hapkit1BufferIndex = 0;
    } else if (hapkit1BufferIndex < BUFFER_SIZE - 1) {
      hapkit1Buffer[hapkit1BufferIndex++] = c;
    } else {
      // Buffer overflow, reset
      hapkit1BufferIndex = 0;
    }
  }
}

void processHapkit1Message(char* message) {
  // Expected format: P,STEER_COUNTS,THROTTLE_COUNTS
  // Example: P,2000,-1200
  
  if (message[0] != 'P') {
    return; // Not a position message
  }
  
  long steer, throttle;
  int parsed = sscanf(message, "P,%ld,%ld", &steer, &throttle);
  
  if (parsed == 2) {
    p1_steering = steer;
    p1_throttle = throttle;
  }
}

void readFromHapkit2() {
  while (HAPKIT2_SERIAL.available() > 0) {
    char c = HAPKIT2_SERIAL.read();
    
    if (c == '\n') {
      // End of message
      hapkit2Buffer[hapkit2BufferIndex] = '\0';
      processHapkit2Message(hapkit2Buffer);
      hapkit2BufferIndex = 0;
    } else if (hapkit2BufferIndex < BUFFER_SIZE - 1) {
      hapkit2Buffer[hapkit2BufferIndex++] = c;
    } else {
      // Buffer overflow, reset
      hapkit2BufferIndex = 0;
    }
  }
}

void processHapkit2Message(char* message) {
  // Expected format: P,STEER_COUNTS,THROTTLE_COUNTS
  // Example: P,-800,1600
  
  if (message[0] != 'P') {
    return; // Not a position message
  }
  
  long steer, throttle;
  int parsed = sscanf(message, "P,%ld,%ld", &steer, &throttle);
  
  if (parsed == 2) {
    p2_steering = steer;
    p2_throttle = throttle;
  }
}

void sendPositionsToLaptop() {
  // Format: P,P1S_COUNTS,P1T_COUNTS,P2S_COUNTS,P2T_COUNTS
  LAPTOP_SERIAL.print("P,");
  LAPTOP_SERIAL.print(p1_steering);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p1_throttle);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.print(p2_steering);
  LAPTOP_SERIAL.print(",");
  LAPTOP_SERIAL.println(p2_throttle);
}
