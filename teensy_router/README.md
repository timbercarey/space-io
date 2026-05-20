# Teensy 4.1 Router

Routes serial messages between laptop and Hapkit boards.

## Hardware Connections

### Laptop Connection
- USB cable to Teensy 4.1

### Hapkit Board 1 (Player 1)
- Teensy Pin 0 (RX1) → Hapkit TX
- Teensy Pin 1 (TX1) → Hapkit RX
- Teensy GND → Hapkit GND

### Hapkit Board 2 (Player 2)
- Teensy Pin 7 (RX2) → Hapkit TX
- Teensy Pin 8 (TX2) → Hapkit RX
- Teensy GND → Hapkit GND

## Upload Instructions

1. Open `teensy_router.ino` in Arduino IDE
2. Select Tools → Board → Teensy 4.1
3. Select Tools → USB Type → Serial
4. Click Upload

## Testing

Open Serial Monitor (115200 baud) and you should see "Teensy Router Ready"

## Message Protocol

### From Laptop to Teensy