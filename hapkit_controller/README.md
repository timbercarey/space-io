# Hapkit Controller

Motor control and encoder reading for Space IO haptic feedback.

## Hardware Setup

### Motor Connections
Each Hapkit board controls 2 motors (steering and throttle).

**Steering Motor (Motor 1):**
- Motor+ → Motor Driver Output 1A
- Motor- → Motor Driver Output 1B
- PWM Control → Pin 5
- Direction → Pin 4

**Throttle Motor (Motor 2):**
- Motor+ → Motor Driver Output 2A
- Motor- → Motor Driver Output 2B
- PWM Control → Pin 6
- Direction → Pin 7

### Encoder Connections

**Steering Encoder:**
- Channel A → Pin 2 (interrupt capable)
- Channel B → Pin 3 (interrupt capable)
- VCC → 5V
- GND → GND

**Throttle Encoder:**
- Channel A → Pin 18 (interrupt capable)
- Channel B → Pin 19 (interrupt capable)
- VCC → 5V
- GND → GND

### Serial Connection to Teensy
- Hapkit TX → Teensy RX (Serial1 or Serial2)
- Hapkit RX → Teensy TX (Serial1 or Serial2)
- Hapkit GND → Teensy GND

## Configuration

Edit `config.h` to match your hardware:

1. **Pin assignments** - Adjust if using different pins
2. **ENCODER_CPR** - Set to your encoder's counts per revolution
3. **ENCODER_RANGE** - Physical range of motion in degrees
4. **MAX_FORCE** - Maximum force value (should match game engine)

## Upload Instructions

1. Open `hapkit_controller.ino` in Arduino IDE
2. Select Tools → Board → Arduino Uno (or your Hapkit board type)
3. Select correct COM port
4. Click Upload

## Testing

1. Open Serial Monitor (115200 baud)
2. You should see "Hapkit Controller Ready"
3. Manually move the motors - you should see position updates:
P,0.000,0.000
P,0.123,-0.045
4. Send a force command:
F,500,200
Motors should respond with force feedback.

## Message Protocol

### Received from Teensy
F,STEER,THROTTLE\n
Example: `F,500,-200\n`
- STEER: Steering force (-1000 to 1000)
- THROTTLE: Throttle force (-1000 to 1000)

### Sent to Teensy
P,STEER,THROTTLE\n
Example: `P,0.500,-0.300\n`
- STEER: Steering position (-1.0 to 1.0)
- THROTTLE: Throttle position (-1.0 to 1.0)

## Calibration

### Finding Encoder Center Position

1. Manually position both motors at their mechanical center
2. Upload the code
3. Open Serial Monitor
4. Note the position values being sent
5. Update `POSITION_CENTER` in `config.h` to match these values
6. Re-upload

### Tuning Force Response

If motors are too strong or too weak:
1. Adjust `MAX_PWM` in `config.h` (lower = weaker, max 255)
2. Or modify the game engine force values in `config.py`

## Troubleshooting

**Motors don't move:**
- Check motor driver connections
- Verify PWM pins are correct
- Check power supply to motors

**Encoders not working:**
- Verify encoder pins are interrupt-capable
- Check encoder power (5V)
- Test with simple encoder reading sketch

**Choppy/jittery force:**
- Check serial baud rate (must be 115200)
- Verify control loop is running at ~1000 Hz
- Check for serial buffer overruns

**Position drift:**
- Encoder may be missing counts
- Try using hardware interrupts for encoder reading
- Check encoder wiring