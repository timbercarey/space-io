# Space IO

Space IO is a two-player pygame game with haptic steering/throttle controls.
The Python game runs on the laptop, a Teensy 4.1 reads encoder values and
forwards motor commands, and the Hapkit board drives the motors.

## Repo Layout

- `game_engine/` - Python game, haptics, input, rendering, and configuration.
- `teensy_controller/` - Teensy 4.1 firmware for encoders and force forwarding.
- `hapkit_controller/` - Hapkit motor receiver firmware.

## First-Time Setup

1. Clone the repo.

   ```bash
   git clone https://github.com/timbercarey/space-io.git
   cd space-io
   ```

2. Create and activate a Python virtual environment.

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the Python requirements.

   ```bash
   pip install -r game_engine/requirements.txt
   ```

4. Check the serial port in `game_engine/config.py`.

   ```python
   SERIAL_PORT = '/dev/cu.usbmodem199646501'
   BAUD_RATE = 1000000
   SIMULATION_MODE = False
   ```

   Update `SERIAL_PORT` if your Teensy appears under a different port. On
   Windows this will usually look like `COM3` or similar.

5. Make sure the Arduino IDE can build the firmware.

   - Install Teensyduino / Teensy board support.
   - Install the Teensy `QuadEncoder` library.
   - Confirm Arduino IDE can see the Teensy serial port.

## Updating Firmware

Before running the game, make sure the code on the Teensy and Hapkit board
matches the sketches in this repo. If either board is out of date, upload the
current sketch from the repo.

### Teensy 4.1

1. Open `teensy_controller/teensy_controller.ino` in Arduino IDE.
2. Select `Tools -> Board -> Teensy 4.1`.
3. Select `Tools -> USB Type -> Serial`.
4. Select the Teensy serial port.
5. Click Upload.

The Teensy reads encoder counts, calculates encoder velocities, and sends both
to the laptop at `1000000` baud.

### Hapkit Board

1. Open `hapkit_controller/hapkit_controller.ino` in Arduino IDE.
2. Select the Hapkit board target.
3. Select the correct serial port.
4. Click Upload.

The Hapkit board receives motor commands from the Teensy and drives the two
motors. If motor direction is wrong, fix the wiring or firmware direction
mapping before increasing force gains.

## Hardware Startup

1. Upload current firmware to the Teensy and Hapkit board if needed.
2. Plug in power to the Hapkit board or boards.
3. Connect Teensy GND to Hapkit GND.
4. Connect Teensy `Serial4` TX, pin 17, to the Hapkit serial RX.
5. Plug the Teensy into the computer over USB.
6. Confirm `game_engine/config.py` points at the Teensy serial port.
7. Close Arduino Serial Monitor or any other program using the Teensy serial
   port before starting the game.

## Run The Game

From the repo root:

```bash
cd game_engine
python3 main.py
```

The game opens a menu where you can select one or two players and start.

For keyboard-only testing, set this in `game_engine/config.py`:

```python
SIMULATION_MODE = True
```

Set it back to `False` before using haptic hardware.

## Controls

The game prints the current controls when a round starts.

Keyboard simulation:

- Player 1: `W` / `S` throttle, `A` / `D` steering.
- Player 2: arrow keys.

General controls:

- `ESC`: quit current game.
- `R`: restart the current game without returning to the menu.
- `H`: toggle haptic visualization.
- `B`: toggle hitbox display.
- `Z`: zero throttle, hardware mode only.
- Round over: `SPACEBAR` starts the next round.
- Game over: `SPACEBAR` returns to the menu.

## Teensy Serial Testing

You can use Arduino IDE Serial Monitor to verify encoder values and manually
send force commands.

1. Upload `teensy_controller/teensy_controller.ino`.
2. Open Arduino IDE Serial Monitor.
3. Set the baud rate to `1000000`.
4. Rotate each encoder and watch for lines like:

   ```text
   P,P1_STEER_COUNTS,P1_THROTTLE_COUNTS,P2_STEER_COUNTS,P2_THROTTLE_COUNTS,P1_STEER_VEL,P1_THROTTLE_VEL,P2_STEER_VEL,P2_THROTTLE_VEL
   ```

   Example:

   ```text
   P,1500,-300,0,0,1240.50,-210.00,0.00,0.00
   ```

5. To send a force command from Serial Monitor, send:

   ```text
   F,P1_STEER_FORCE,P1_THROTTLE_FORCE,P2_STEER_FORCE,P2_THROTTLE_FORCE
   ```

   Example:

   ```text
   F,100,-100,0,0
   ```

   Start with small values and verify motor direction before increasing force.
   Force values are clamped to `-1000..1000`.

6. Close Serial Monitor before running the Python game. The game cannot open
   the Teensy serial port while Arduino IDE has it open.

## Common Issues

- `SerialException` or port busy: close Arduino Serial Monitor and any other
  serial tools, then restart the game.
- No hardware input: check `SERIAL_PORT`, USB connection, Teensy firmware, and
  that `SIMULATION_MODE = False`.
- Motors do not move: check Hapkit power, Teensy-to-Hapkit serial wiring,
  common ground, and Hapkit firmware.
- Motor force pushes the wrong way: stop testing at low force and fix motor
  wiring, firmware direction mapping, or force direction signs in
  `game_engine/config.py`.
