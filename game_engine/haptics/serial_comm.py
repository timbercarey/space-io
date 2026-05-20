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
    
    def send_forces(self, p1_steer, p1_throttle, p2_steer=0, p2_throttle=0):
        """
        Send force commands to Teensy
        
        Args:
            p1_steer: Player 1 steering force (-1000 to 1000)
            p1_throttle: Player 1 throttle force (-1000 to 1000)
            p2_steer: Player 2 steering force (-1000 to 1000)
            p2_throttle: Player 2 throttle force (-1000 to 1000)
        """
        if self.simulation_mode or not self.connected:
            return
        
        # Format: F,P1S,P1T,P2S,P2T\n
        message = f"F,{int(p1_steer)},{int(p1_throttle)},{int(p2_steer)},{int(p2_throttle)}\n"
        
        try:
            self.serial_port.write(message.encode('ascii'))
        except serial.SerialException as e:
            print(f"Error sending forces: {e}")
            self.connected = False
    
    def read_positions(self):
        """
        Read encoder positions from Teensy
        
        Returns:
            dict: {player_id: {'steering': float, 'throttle': float}}
                  Values are normalized -1.0 to 1.0
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
        
        Expected format: P,P1S,P1T,P2S,P2T
        Example: P,0.5,-0.3,0.2,0.8
        """
        try:
            parts = line.split(',')
            if parts[0] != 'P' or len(parts) != 5:
                return
            
            # Parse values
            p1_steer = float(parts[1])
            p1_throttle = float(parts[2])
            p2_steer = float(parts[3])
            p2_throttle = float(parts[4])
            
            # Clamp to valid range
            p1_steer = max(-1.0, min(1.0, p1_steer))
            p1_throttle = max(-1.0, min(1.0, p1_throttle))
            p2_steer = max(-1.0, min(1.0, p2_steer))
            p2_throttle = max(-1.0, min(1.0, p2_throttle))
            
            # Update latest positions
            self.latest_positions[1]['steering'] = p1_steer
            self.latest_positions[1]['throttle'] = p1_throttle
            self.latest_positions[2]['steering'] = p2_steer
            self.latest_positions[2]['throttle'] = p2_throttle
            
        except (ValueError, IndexError):
            # Ignore malformed data
            pass
    
    def close(self):
        """Close serial connection"""
        if self.serial_port and self.connected:
            self.serial_port.close()
            print("Serial connection closed")