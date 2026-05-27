# Teensy 4.1 Controller

Reads the controller encoders on the Teensy, sends raw encoder counts to the
laptop, and forwards player 1 force commands to the Hapkit motor board.

## Hardware Connections

### Laptop

- USB cable to Teensy 4.1
- Baud rate: `115200`

### Encoders

The controller uses the Teensy 4.1 hardware quadrature encoder channels through the
`QuadEncoder` library.

| Axis | Encoder Channel | Phase A | Phase B |
| --- | --- | --- | --- |
| Player 1 steering | 1 | Pin 0 | Pin 1 |
| Player 1 throttle | 2 | Pin 2 | Pin 3 |
| Player 2 steering | 3 | Pin 7 | Pin 8 |
| Player 2 throttle | 4 | Pin 30 | Pin 31 |

### Hapkit Motor Board

- Teensy `Serial4` TX, pin 17, sends motor commands to the Hapkit receiver
- Teensy GND -> Hapkit GND
- Baud rate: `115200`

The current motor command packet is binary:

```text
0xAA,STEERING_BYTE,THROTTLE_BYTE,CHECKSUM
```

`127` is centered. The Hapkit receiver treats `124..130` as a stop deadband,
`131..255` as one direction, and `0..123` as the other direction.

On the current hardware, Hapkit channel 1 drives throttle and channel 2 drives
steering, so the Teensy swaps the game force order before sending the packet.

## Upload Instructions

1. Install the Teensy `QuadEncoder` library if it is not already available.
2. Open `teensy_controller.ino` in Arduino IDE.
3. Select Tools -> Board -> Teensy 4.1.
4. Select Tools -> USB Type -> Serial.
5. Click Upload.

## Message Protocol

### From Laptop To Teensy

```text
F,P1_STEER_FORCE,P1_THROTTLE_FORCE,P2_STEER_FORCE,P2_THROTTLE_FORCE\n
```

Example:

```text
F,500,-200,0,0
```

Force values are clamped to `-1000..1000`.

### From Teensy To Laptop

```text
P,P1_STEER_COUNTS,P1_THROTTLE_COUNTS,P2_STEER_COUNTS,P2_THROTTLE_COUNTS\n
```

Example:

```text
P,1500,-300,0,0
```

Encoder values are raw counts. The Python game normalizes them using
`STEERING_ENCODER_COUNTS_PER_ROTATION`,
`THROTTLE_ENCODER_COUNTS_PER_ROTATION`,
`STEERING_CONTROL_ROTATION_RANGE`, and `THROTTLE_CONTROL_ROTATION_RANGE`.

## Testing

Open Serial Monitor at `115200` baud. You should see:

```text
Teensy Controller Ready
```

Then rotate each encoder and confirm the `P,...` values change. Once encoder
signs are verified, send a low force command and confirm the motor direction is
restorative before increasing haptic gains.
