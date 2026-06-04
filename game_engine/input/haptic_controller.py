"""
Haptic controller - reads from real hardware via serial
"""
import threading

from .controller import Controller
from haptics.serial_comm import SerialComm
from config import Config

class HapticController(Controller):
    """Controller that reads from haptic hardware"""
    
    def __init__(self, serial_comm=None):
        """
        Args:
            serial_comm: SerialComm instance (or None to create one)
        """
        if serial_comm is None:
            self.serial_comm = SerialComm(
                port=Config.SERIAL_PORT,
                baud_rate=Config.BAUD_RATE,
                simulation_mode=Config.SIMULATION_MODE
            )
            self.owns_serial = True
        else:
            self.serial_comm = serial_comm
            self.owns_serial = False
        self._io_lock = threading.Lock()
        
        # Current input values
        self.positions = self.serial_comm.latest_positions
        self.velocities = self.serial_comm.latest_velocities
    
    def update(self):
        """Read latest positions from hardware"""
        self.positions = self.get_positions_snapshot(refresh=True)

    def get_positions_snapshot(self, refresh=False):
        """Return a thread-safe copy of the latest controller positions."""
        with self._io_lock:
            if refresh:
                self.positions = self.serial_comm.read_positions()

            return {
                player_id: axes.copy()
                for player_id, axes in self.positions.items()
            }

    def get_position_velocity_snapshot(self, refresh=False):
        """Return hardware positions and Teensy-calculated velocities together."""
        with self._io_lock:
            initialized, positions, velocities = (
                self.serial_comm.get_position_velocity_snapshot(refresh=refresh)
            )
            self.positions = positions
            self.velocities = velocities
            return initialized, positions, velocities

    def has_hardware_velocity_data(self):
        """Return True once the serial stream has included Teensy velocity data."""
        with self._io_lock:
            return self.serial_comm.has_hardware_velocity_data()

    def get_control_switch_snapshot(self, refresh=False):
        """Return hardware game-mode switch state."""
        with self._io_lock:
            return self.serial_comm.get_control_switch_snapshot(refresh=refresh)
    
    def get_steering(self, player_id):
        """
        Get steering input for a player
        
        Args:
            player_id: 1 or 2
        
        Returns:
            float: -1.0 to 1.0 (left to right)
        """
        with self._io_lock:
            if player_id not in self.positions:
                return 0.0
            return self.positions[player_id]['steering']
    
    def get_throttle(self, player_id):
        """
        Get throttle input for a player
        
        Args:
            player_id: 1 or 2
        
        Returns:
            float: -1.0 to 1.0 (back to forward)
        """
        with self._io_lock:
            if player_id not in self.positions:
                return 0.0
            return self.positions[player_id]['throttle']
    
    def send_forces(
        self,
        p1_steer,
        p1_throttle,
        p2_steer=0,
        p2_throttle=0,
        led_mask=0,
        erm_enable=0,
        erm_pwm=0,
        p1_erm_pwm=None,
        p2_erm_pwm=None,
    ):
        """
        Send force commands to hardware
        
        Args:
            p1_steer: Player 1 steering force (-1000 to 1000)
            p1_throttle: Player 1 throttle force (-1000 to 1000)
            p2_steer: Player 2 steering force (-1000 to 1000)
            p2_throttle: Player 2 throttle force (-1000 to 1000)
            led_mask: Player LED status bitmask
            erm_enable: Non-zero to power the ERM Hapkit outputs
            erm_pwm: Legacy ERM PWM command, 0 to 255, used for both players
            p1_erm_pwm: Player 1 ERM PWM command, 0 to 255
            p2_erm_pwm: Player 2 ERM PWM command, 0 to 255
        """
        with self._io_lock:
            self.serial_comm.send_forces(
                p1_steer,
                p1_throttle,
                p2_steer,
                p2_throttle,
                led_mask,
                erm_enable,
                erm_pwm,
                p1_erm_pwm,
                p2_erm_pwm
            )

    def stop_forces(self):
        """Command all hardware motors to stop."""
        with self._io_lock:
            self.serial_comm.stop_forces()

    def zero_throttle(self, player_ids=None):
        """Use current hardware throttle count as the zero position."""
        with self._io_lock:
            return self.serial_comm.zero_throttle(player_ids)

    def zero_inputs(self, player_ids=None):
        """Use current hardware steering/throttle counts as zero positions."""
        with self._io_lock:
            offsets = self.serial_comm.zero_inputs(player_ids)
            self.positions = self.serial_comm.latest_positions
            self.velocities = self.serial_comm.latest_velocities
            return offsets
    
    def close(self):
        """Cleanup resources"""
        if self.owns_serial:
            with self._io_lock:
                self.serial_comm.close()
