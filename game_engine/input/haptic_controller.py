"""
Haptic controller - reads from real hardware via serial
"""
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
        
        # Current input values
        self.positions = self.serial_comm.latest_positions
    
    def update(self):
        """Read latest positions from hardware"""
        self.positions = self.serial_comm.read_positions()
    
    def get_steering(self, player_id):
        """
        Get steering input for a player
        
        Args:
            player_id: 1 or 2
        
        Returns:
            float: -1.0 to 1.0 (left to right)
        """
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
        if player_id not in self.positions:
            return 0.0
        return self.positions[player_id]['throttle']
    
    def send_forces(self, p1_steer, p1_throttle, p2_steer=0, p2_throttle=0):
        """
        Send force commands to hardware
        
        Args:
            p1_steer: Player 1 steering force (-1000 to 1000)
            p1_throttle: Player 1 throttle force (-1000 to 1000)
            p2_steer: Player 2 steering force (-1000 to 1000)
            p2_throttle: Player 2 throttle force (-1000 to 1000)
        """
        self.serial_comm.send_forces(p1_steer, p1_throttle, p2_steer, p2_throttle)
    
    def close(self):
        """Cleanup resources"""
        if self.owns_serial:
            self.serial_comm.close()