# Teensy 4.1 Controller

Reads the controller encoders on the Teensy, sends raw encoder counts and
filtered encoder velocities to the laptop, and forwards player force commands
to two Hapkit motor boards.

## Hardware Connections

### Laptop

- USB cable to Teensy 4.1
- Baud rate: `1000000`

### Encoders

The controller uses the Teensy 4.1 hardware quadrature encoder channels through the
`QuadEncoder` library.

| Hardware axis | Encoder Channel | Phase A | Phase B |
| --- | --- | --- | --- |
| 2-way station steering, logical player 2 | 1 | Pin 0 | Pin 1 |
| 2-way station throttle, logical player 2 | 2 | Pin 2 | Pin 3 |
| 3-way station steering, logical player 1 | 3 | Pin 7 | Pin 8 |
| 3-way station throttle, logical player 1 | 4 | Pin 30 | Pin 31 |

### Hapkit Motor Boards

- Module A, 2-way station, logical player 2: Teensy `Serial4` TX, pin 17 -> Hapkit receiver RX
- Module B, 3-way station, logical player 1: Teensy `Serial7` TX, pin 29 -> Hapkit receiver RX
- ERM module: Teensy `Serial5` TX, pin 20 -> Hapkit ERM receiver RX
- Teensy GND -> both Hapkit GND pins
- Baud rate: `115200`

The current motor command packet is binary:

```text
0xAA,STEERING_BYTE,THROTTLE_BYTE,CHECKSUM
```

`127` is centered. The Hapkit receiver treats `124..130` as a stop deadband,
`131..255` as one direction, and `0..123` as the other direction.

On the current hardware, Hapkit channel 1 drives throttle and channel 2 drives
steering, so the Teensy swaps the game force order before sending each packet.

The ERM Hapkit receives a separate binary packet on Teensy pin 20:

```text
Legacy single-channel: 0xE1,PWM,CHECKSUM
Dual-channel:          0xE2,ERM1_PWM,ERM2_PWM,CHECKSUM
```

### Player Switches And LEDs

The 3-way switch drives the Teensy inputs high, so pins 25 and 26 use
`INPUT_PULLDOWN` and read active when the pin is `HIGH`. The 2-way switch uses
`INPUT_PULLUP` and enables player 2 when pin 9 reads `HIGH`. LED pins drive low
to turn the LEDs on, except the physical player 2 LED 1 circuit drives high.

| Control | Pin |
| --- | --- |
| Player 1 LED 1 | 28 |
| Player 1 LED 2 | 27 |
| Player 1 switch position 1 | 25 |
| Player 1 switch position 2 | 26 |
| Player 2 LED 1 | 41 |
| Player 2 LED 2 | 40 |
| Player 2 switch | 9 |

The sketch initializes these pins in `setupPlayerControls()`, reads switch state
with `readPlayerControls()`, and exposes cached values in `p1SwitchPosition` and
`p2SwitchActive`. The game sends LED status in the force command stream. LED 1
is on while that player is present, LED 2 flashes while that player has a star
boost, and both LEDs flash rapidly while that player is dead waiting for
respawn. The 3-way station is always present, and the 2-way station becomes
present when the hardware 2-way switch enables player 2. Set
`LED_FLASH_TEST_ENABLED` to `1` in `config.h` to continuously flash all LEDs for
hardware testing.

The station with the 3-way switch is treated as the primary player and is always
in the game. Its switch is reported to the laptop as difficulty `1`, `2`, or
`3`: pin 25 high is difficulty 1, center is difficulty 2, and pin 26 high is
difficulty 3. The 2-way switch is treated as the optional second player enable
and reports player 2 enabled when pin 9 reads `HIGH`.

## Upload Instructions

1. Install the Teensy `QuadEncoder` library if it is not already available.
2. Open `teensy_controller.ino` in Arduino IDE.
3. Select Tools -> Board -> Teensy 4.1.
4. Select Tools -> USB Type -> Serial.
5. Click Upload.

You can also compile from the repo root:

```bash
make teensy-compile
```

To upload from the command line, connect the Teensy, find its Teensy discovery
port with `make teensy-board-list`, then run:

```bash
make teensy-upload TEENSY_PORT=usb:...
```

### Switch Pin Test Sketch

For switch wiring tests, use the standalone pin reader sketch:

```bash
make teensy-compile TEENSY_SKETCH=teensy_controller/pin_state_reader
make teensy-upload TEENSY_SKETCH=teensy_controller/pin_state_reader TEENSY_PORT=usb:...
```

Open Serial Monitor at `1000000` baud. The sketch prints named controller pins
first, then a compact `pins,0=...,1=...` snapshot of Teensy digital pins 0-41.
The P1 switch inputs use `INPUT_PULLDOWN`, so driving pin 25 or 26 high should
print `HIGH(active)`. The P2 switch uses `INPUT_PULLUP`, so pin 9 should print
`HIGH(active)` when player 2 is enabled, matching the main controller firmware.

## Message Protocol

### From Laptop To Teensy

```text
F,P1_STEER_FORCE,P1_THROTTLE_FORCE,P2_STEER_FORCE,P2_THROTTLE_FORCE[,LED_MASK[,ERM_ENABLE]]\n
```

Example:

```text
F,500,-200,0,0
```

Force values are clamped to `-1000..1000`. `LED_MASK` is optional for backward
compatibility. Its bits are: `1` P1 present, `2` P1 star boost, `4` P1 dead,
`8` P2 present, `16` P2 star boost, and `32` P2 dead.
`ERM_ENABLE` is optional and powers the ERM Hapkit outputs when non-zero.

### From Teensy To Laptop

```text
P,P1_STEER_COUNTS,P1_THROTTLE_COUNTS,P2_STEER_COUNTS,P2_THROTTLE_COUNTS,P1_STEER_VEL,P1_THROTTLE_VEL,P2_STEER_VEL,P2_THROTTLE_VEL[,VEL_AGE_US],DIFFICULTY,P2_ENABLED\n
```

Example:

```text
P,1500,-300,0,0,1240.50,-210.00,0.00,0.00,2000,3,1
```

Encoder positions are raw counts. Encoder velocities are filtered counts per
second. The Python game normalizes both using
`STEERING_ENCODER_COUNTS_PER_ROTATION`,
`THROTTLE_ENCODER_COUNTS_PER_ROTATION`,
`STEERING_CONTROL_ROTATION_RANGE`, and `THROTTLE_CONTROL_ROTATION_RANGE`.
The optional `VEL_AGE_US` field reports the oldest Teensy velocity sample age
in microseconds so the Python side can ignore stale hardware velocity.
`DIFFICULTY` is `1..3`; `P2_ENABLED` is `0` or `1`.

Velocity processing features are controlled in `config.h`:

- `VELOCITY_ADAPTIVE_WINDOW_ENABLED`
- `VELOCITY_TIME_CONSTANT_FILTER_ENABLED`
- `VELOCITY_ASYMMETRIC_FILTER_ENABLED`
- `VELOCITY_ZERO_HYSTERESIS_ENABLED`
- `VELOCITY_STALE_DECAY_ENABLED`
- `VELOCITY_SEND_SAMPLE_AGE_ENABLED`

## Testing

Open Serial Monitor at `1000000` baud. You should see:

```text
Teensy Controller Ready
```

Then rotate each encoder and confirm the `P,...` values change. Once encoder
signs are verified, send a low force command and confirm the motor direction is
restorative before increasing haptic gains.
