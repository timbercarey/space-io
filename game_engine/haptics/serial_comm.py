"""
Serial communication with Teensy for haptic feedback
"""
import serial
import time
from config import Config

class SerialComm:
    """Handles serial communication with Teensy"""
    
    def __init__(self, port=None, baud_rate=None, simulation_mode=True):
        """
        Args:
            port: Serial port (e.g., '/dev/ttyUSB0' or 'COM3')
            baud_rate: Baud rate for serial communication
            simulation_mode: If True, don't actually connect to hardware
        """
        self.port = port or Config.SERIAL_PORT
        self.baud_rate = baud_rate or Config.BAUD_RATE
        self.simulation_mode = simulation_mode
        self.serial_port = None
        self.connected = False
        
        # Buffers for latest data
        self.latest_positions = {
            1: {'steering': 0.0, 'throttle': 0.0},
            2: {'steering': 0.0, 'throttle': 0.0}
        }
        self.latest_velocities = {
            1: {'steering': 0.0, 'throttle': 0.0},
            2: {'steering': 0.0, 'throttle': 0.0}
        }
        self.has_velocity_data = False
        self.latest_velocity_sample_age_sec = 0.0
        self.latest_velocity_receive_time = 0.0
        self.latest_encoder_counts = {
            1: {'steering': 0, 'throttle': 0},
            2: {'steering': 0, 'throttle': 0}
        }
        self.zero_offsets = {
            1: {'steering': 0, 'throttle': 0},
            2: {'steering': 0, 'throttle': 0}
        }
        self.latest_controls = {
            'difficulty': 3,
            'player2_enabled': False,
            'received': False,
            'pin25_active': None,
            'pin26_active': None,
            'pin9_active': None
        }
        
        if not simulation_mode:
            self._connect()
    
    def _connect(self):
        """Attempt to connect to serial port"""
        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=0.01  # Non-blocking read with short timeout
            )
            time.sleep(2)  # Wait for Arduino to reset
            self.connected = True
            print(f"Connected to {self.port} at {self.baud_rate} baud")
        except serial.SerialException as e:
            print(f"Failed to connect to {self.port}: {e}")
            print("Running in simulation mode")
            self.simulation_mode = True
            self.connected = False
    
    def send_forces(self, p1_steer, p1_throttle, p2_steer=0, p2_throttle=0, led_mask=0):
        """
        Send force commands to Teensy
        
        Args:
            p1_steer: Player 1 steering force (-1000 to 1000)
            p1_throttle: Player 1 throttle force (-1000 to 1000)
            p2_steer: Player 2 steering force (-1000 to 1000)
            p2_throttle: Player 2 throttle force (-1000 to 1000)
            led_mask: Player LED status bitmask
        """
        if self.simulation_mode or not self.connected:
            return
        
        p1_steer *= Config.STEERING_FORCE_DIRECTION
        p1_throttle *= Config.THROTTLE_FORCE_DIRECTION
        p2_steer *= Config.STEERING_FORCE_DIRECTION
        p2_throttle *= Config.THROTTLE_FORCE_DIRECTION

        # Format: F,P1S,P1T,P2S,P2T,LED_MASK\n
        message = (
            f"F,{int(p1_steer)},{int(p1_throttle)},"
            f"{int(p2_steer)},{int(p2_throttle)},{int(led_mask)}\n"
        )
        
        try:
            self.serial_port.write(message.encode('ascii'))
        except serial.SerialException as e:
            print(f"Error sending forces: {e}")
            self.connected = False

    def stop_forces(self):
        """Command all motors to stop."""
        self.send_forces(0, 0, 0, 0)
    
    def read_positions(self):
        """
        Read encoder positions and velocities from Teensy
        
        Returns:
            dict: {player_id: {'steering': float, 'throttle': float}}
                  Raw encoder counts are normalized to -1.0 to 1.0
        """
        if self.simulation_mode or not self.connected:
            return self.latest_positions
        
        try:
            # Read all available data
            while self.serial_port.in_waiting > 0:
                line = self.serial_port.readline().decode('ascii').strip()
                self._parse_position_data(line)
        except serial.SerialException as e:
            print(f"Error reading positions: {e}")
            self.connected = False
        except UnicodeDecodeError:
            # Ignore malformed data
            pass
        
        return self.latest_positions
    
    def _parse_position_data(self, line):
        """
        Parse position data from Teensy
        
        Expected format:
        P,P1S_COUNTS,P1T_COUNTS,P2S_COUNTS,P2T_COUNTS,P1S_VEL,P1T_VEL,P2S_VEL,P2T_VEL[,VEL_AGE_US][,DIFFICULTY,P2_ENABLED[,PIN25_ACTIVE,PIN26_ACTIVE,PIN9_ACTIVE]]

        The older position-only format is still accepted:
        P,P1S_COUNTS,P1T_COUNTS,P2S_COUNTS,P2T_COUNTS
        """
        try:
            parts = line.split(',')
            if parts[0] != 'P' or len(parts) not in (5, 9, 10, 11, 12, 14, 15):
                return
            
            # Parse raw encoder counts
            p1_steer_counts = int(parts[1])
            p1_throttle_counts = int(parts[2])
            p2_steer_counts = int(parts[3])
            p2_throttle_counts = int(parts[4])
            
            p1_steer = self._normalize_encoder_counts(
                p1_steer_counts - self.zero_offsets[1]['steering'],
                'steering'
            )
            p1_throttle = self._normalize_encoder_counts(
                p1_throttle_counts - self.zero_offsets[1]['throttle'],
                'throttle'
            )
            p2_steer = self._normalize_encoder_counts(
                p2_steer_counts - self.zero_offsets[2]['steering'],
                'steering'
            )
            p2_throttle = self._normalize_encoder_counts(
                p2_throttle_counts - self.zero_offsets[2]['throttle'],
                'throttle'
            )

            p1_steer_velocity = self.latest_velocities[1]['steering']
            p1_throttle_velocity = self.latest_velocities[1]['throttle']
            p2_steer_velocity = self.latest_velocities[2]['steering']
            p2_throttle_velocity = self.latest_velocities[2]['throttle']

            if len(parts) >= 9:
                self.has_velocity_data = True
                self.latest_velocity_sample_age_sec = 0.0
                self.latest_velocity_receive_time = time.perf_counter()
                p1_steer_velocity = self._normalize_encoder_velocity(
                    float(parts[5]),
                    'steering'
                )
                p1_throttle_velocity = self._normalize_encoder_velocity(
                    float(parts[6]),
                    'throttle'
                )
                p2_steer_velocity = self._normalize_encoder_velocity(
                    float(parts[7]),
                    'steering'
                )
                p2_throttle_velocity = self._normalize_encoder_velocity(
                    float(parts[8]),
                    'throttle'
                )

            if len(parts) in (10, 12, 15):
                self.latest_velocity_sample_age_sec = max(0.0, float(parts[9]) / 1000000.0)

            if len(parts) in (11, 12, 14, 15):
                switch_offset = -5 if len(parts) in (14, 15) else -2
                difficulty = int(parts[switch_offset])
                self.latest_controls['difficulty'] = max(1, min(3, difficulty))
                self.latest_controls['player2_enabled'] = int(parts[switch_offset + 1]) != 0
                self.latest_controls['received'] = True

                if len(parts) in (14, 15):
                    self.latest_controls['pin25_active'] = int(parts[-3]) != 0
                    self.latest_controls['pin26_active'] = int(parts[-2]) != 0
                    self.latest_controls['pin9_active'] = int(parts[-1]) != 0
            
            # Update latest raw counts
            self.latest_encoder_counts[1]['steering'] = p1_steer_counts
            self.latest_encoder_counts[1]['throttle'] = p1_throttle_counts
            self.latest_encoder_counts[2]['steering'] = p2_steer_counts
            self.latest_encoder_counts[2]['throttle'] = p2_throttle_counts
            
            # Update latest positions
            self.latest_positions[1]['steering'] = p1_steer
            self.latest_positions[1]['throttle'] = p1_throttle
            self.latest_positions[2]['steering'] = p2_steer
            self.latest_positions[2]['throttle'] = p2_throttle

            self.latest_velocities[1]['steering'] = p1_steer_velocity
            self.latest_velocities[1]['throttle'] = p1_throttle_velocity
            self.latest_velocities[2]['steering'] = p2_steer_velocity
            self.latest_velocities[2]['throttle'] = p2_throttle_velocity
            
        except (ValueError, IndexError):
            # Ignore malformed data
            pass

    def _normalize_encoder_counts(self, counts, axis):
        """Convert raw encoder counts to normalized controller position."""
        if axis == 'steering':
            counts_per_rotation = Config.STEERING_ENCODER_COUNTS_PER_ROTATION
            control_rotation_range = Config.STEERING_CONTROL_ROTATION_RANGE
            direction = Config.STEERING_ENCODER_DIRECTION
        else:
            counts_per_rotation = Config.THROTTLE_ENCODER_COUNTS_PER_ROTATION
            control_rotation_range = Config.THROTTLE_CONTROL_ROTATION_RANGE
            direction = Config.THROTTLE_ENCODER_DIRECTION

        max_counts = counts_per_rotation * control_rotation_range
        if max_counts <= 0:
            return 0.0

        normalized = direction * counts / max_counts
        return max(-1.0, min(1.0, normalized))

    def _normalize_encoder_velocity(self, counts_per_second, axis):
        """Convert raw encoder counts/sec to normalized controller units/sec."""
        if axis == 'steering':
            counts_per_rotation = Config.STEERING_ENCODER_COUNTS_PER_ROTATION
            control_rotation_range = Config.STEERING_CONTROL_ROTATION_RANGE
            direction = Config.STEERING_ENCODER_DIRECTION
        else:
            counts_per_rotation = Config.THROTTLE_ENCODER_COUNTS_PER_ROTATION
            control_rotation_range = Config.THROTTLE_CONTROL_ROTATION_RANGE
            direction = Config.THROTTLE_ENCODER_DIRECTION

        max_counts = counts_per_rotation * control_rotation_range
        if max_counts <= 0:
            return 0.0

        return direction * counts_per_second / max_counts

    def _hardware_velocity_is_fresh(self):
        """Return whether the latest Teensy velocity packet is usable."""
        if not self.has_velocity_data:
            return False

        if not Config.HARDWARE_VELOCITY_STALE_REJECTION_ENABLED:
            return True

        timeout = max(0.0, Config.HARDWARE_VELOCITY_STALE_TIMEOUT_SEC)
        if timeout <= 0.0:
            return True

        if self.latest_velocity_sample_age_sec > timeout:
            return False

        if self.latest_velocity_receive_time <= 0.0:
            return False

        return (time.perf_counter() - self.latest_velocity_receive_time) <= timeout

    def get_position_velocity_snapshot(self, refresh=False):
        """Return copies of the latest hardware positions and velocities."""
        if refresh:
            self.read_positions()

        return (
            self._hardware_velocity_is_fresh(),
            {
                player_id: axes.copy()
                for player_id, axes in self.latest_positions.items()
            },
            {
                player_id: axes.copy()
                for player_id, axes in self.latest_velocities.items()
            }
        )

    def get_control_switch_snapshot(self, refresh=False):
        """Return latest hardware game-mode switch state."""
        if refresh:
            self.read_positions()

        return self.latest_controls.copy()

    def has_hardware_velocity_data(self):
        """Return True after receiving at least one velocity-bearing packet."""
        return self._hardware_velocity_is_fresh()

    def zero_inputs(self, player_ids=None, axes=None, refresh=True):
        """Use the current raw encoder counts as zero for selected players/axes."""
        if refresh:
            self.read_positions()

        if player_ids is None:
            player_ids = self.latest_encoder_counts.keys()
        if axes is None:
            axes = ('steering', 'throttle')

        for player_id in player_ids:
            if player_id not in self.latest_encoder_counts:
                continue

            for axis in axes:
                if axis not in self.latest_encoder_counts[player_id]:
                    continue

                self.zero_offsets[player_id][axis] = (
                    self.latest_encoder_counts[player_id][axis]
                )
                self.latest_positions[player_id][axis] = 0.0
        
        return {
            player_id: axes.copy()
            for player_id, axes in self.zero_offsets.items()
        }

    def zero_throttle(self, player_ids=None):
        """Use the current raw throttle count as zero for selected players."""
        return self.zero_inputs(player_ids, axes=('throttle',))
    
    def close(self):
        """Close serial connection"""
        if self.serial_port and self.connected:
            self.stop_forces()
            time.sleep(0.02)
            self.serial_port.close()
            print("Serial connection closed")
