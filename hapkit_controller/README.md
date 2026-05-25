# Hapkit Motor Receiver

Receives motor command packets from the Teensy and drives the two Hapkit motors.
Encoder reading now happens on the Teensy 4.1 controller.

This firmware is based on the verified Hapkit receiver test sketch that drove
the motors from Teensy packets.

## Hardware Setup

### Motor Connections

Each Hapkit board controls two motors.

**Steering Motor**

- PWM control -> Pin 5
- Direction -> Pin 8

**Throttle Motor**

- PWM control -> Pin 6
- Direction -> Pin 7

### Serial Connection From Teensy

- Teensy `Serial4` TX, pin 17 -> Hapkit serial RX
- Teensy GND -> Hapkit GND
- Baud rate: `115200`

## Message Protocol

The Hapkit board receives binary packets:

```text
0xAA,STEERING_BYTE,THROTTLE_BYTE,CHECKSUM
```

The checksum is:

```text
(STEERING_BYTE + THROTTLE_BYTE) mod 256
```

Command values:

- `127`: stop
- `124..130`: deadband / stop
- `131..255`: one motor direction
- `0..123`: opposite motor direction

On the current hardware, channel 1 drives throttle and channel 2 drives
steering. The Teensy controller swaps the game force order before sending the
packet, so `F,STEER,THROTTLE,0,0` still behaves naturally from the laptop side.

The firmware writes directly to Timer0 PWM registers:

- Channel 1, pin 5: `OCR0B`
- Channel 2, pin 6: `OCR0A`

Timer0 is configured for phase-correct PWM with prescaler `1`, giving about
`31.4 kHz` PWM on pins 5 and 6.

## Upload Instructions

1. Open `hapkit_controller.ino` in Arduino IDE.
2. Select the Hapkit board target.
3. Select the correct serial port.
4. Click Upload.

## Testing

Use `test_motors/test_motors.ino` first to verify PWM and direction pins. Then
upload `hapkit_controller.ino` and send a binary packet from the Teensy.

Start with low force values from the game or Teensy controller and verify motor signs:

- Positive steering force should push in the expected steering direction.
- Negative steering force should push the opposite direction.
- Positive throttle force should push in the expected throttle direction.
- Negative throttle force should push the opposite direction.

If a motor pushes the wrong way, swap its motor leads or invert the direction
mapping in firmware before increasing gains.
