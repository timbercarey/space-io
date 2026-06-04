# Hapkit ERM Controller

Upload this sketch to the Hapkit board that drives the two ERMs.

## Wiring

- Teensy `Serial5` TX, pin 20 -> Hapkit serial RX
- Teensy GND -> Hapkit GND
- ERMs -> the two normal Hapkit motor output terminal pairs
- Baud rate: `115200`

## Protocol

The Teensy sends:

```text
Legacy single-channel: 0xE1,PWM,CHECKSUM
Dual-channel:          0xE2,ERM1_PWM,ERM2_PWM,CHECKSUM
```

PWM values are `0` for off or `1..255` for duty cycle. `CHECKSUM` is the byte
sum of the packet header and PWM byte(s). The sketch turns the ERMs off if
commands stop for more than `ERM_COMMAND_TIMEOUT_MS`.

Compile for the Hapkit/Arduino board, for example:

```bash
arduino-cli compile --fqbn arduino:avr:uno hapkit_erm_controller
```
