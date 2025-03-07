import serial
import struct
import time
from typing import Callable
from utilities import is_RA_homed
# try:
#     import RPi.GPIO as GPIO
# except:
#     pass
class MKSMotor:
    def __init__(self, check_home: Callable, adress:str, port='/dev/serial0', baudrate=115200, timeout=1, motor_type=1.8):
        #For Rpi :
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setwarnings(False)
        
        # For Serial
        self.ser = None #serial.Serial(port, baudrate, timeout=timeout)
        self.adress = int(adress, 16)
        self._speed = 0
        self.check_home = check_home
        self.motor_type: float = motor_type # 1.8 or 0.9 degree/step
        self.Mstep = 32

    def _send_command(self, command_bytes:list):
        command: list[int] = [self.adress] + list(command_bytes)
        tCHK: int = self.calculate_checksum(command) 
        struct.pack('<' + 'B'*(len(command) + 1), *command, tCHK)
        self.ser.write(command_bytes)
        time.sleep(0.1)
        response = self.ser.read_all()
        return response

    def calculate_checksum(self, data):
        """
        Calcule la checksum (tCHK/rCHK) en sommant les octets et en prenant le low byte.
        
        :param data: Liste des octets (sous forme d'entiers) ou chaîne hexadécimale
        :return: Checksum (entier entre 0 et 255)
        """
        # Somme des octets et masquage avec 0xFF
        return sum(data) & 0xFF

    def read_encoder_value(self):
        """Read the encoder value
        Info:
            The motor should be calibrated before reading the encoder value
            
        Args:
            None
        
        Returns:
            Driver response with the form: e0 <encoder value: uint16_t> rCHK.

        Example:
            >>> Send e0 30 10
            >>> Return e0 40 00 20"""
        command: list[int] = [0x30]
        return self._send_command(command)

    def read_pulse_nb(self):
        """Read the number of pulses received by the motor
        
        Args:
            None
        
        Returns:
            Driver response with the form: e0 <pulse number:int32_t> rCHK.
            
        Example:
            >>> Send e0 33 13
            >>> Return e0 00 00 01 00 e1 (256 pulses)"""
        command: list[int] = [0x33]
        return self._send_command(command)

    def read_shaft_angle(self):
        """Read the angle of the motor shaft. The motor rotates one circle, 
        the corresponding angle value range is 0~65535.
        
        Args:
            None
        
        Returns:
            Driver response with the form: e0 <angle:int32_t> rCHK.
            
        Example:
            >>> Send e0 36 16
            >>> Return e0 00 00 40 10 (angle 90°)"""
        command: list[int] = [0x36]
        return self._send_command(command)

    def read_angular_error(self):
        """Read the angular error of the motor shaft. The error is the difference between 
        the angle you want to control minus the real-time angle of the motor, 0-FFFF corresponds 
        to 0~360°, for example, when the angle error is 1°, the return error is 65536/360= 182.444, and so on.
        
        Args:
            None
        
        Returns:
            Driver response with the form: e0 <angle:int16_t> rCHK.
            
        Example:
            >>>Send e0 39 19
            >>>Return e0 00 b7 97 (1° error)"""
        command: list[int] = [0x39]
        return self._send_command(command)

    def read_EN_status(self):
        """Read the status EN pin. EN pin is used to control the motor driver enable signal.

        Status can be: 
            - 00-error
            - 01-enable
            - 02-disable
        
        Args:
            None
        
        Returns:
            Driver response with the form: e0 <status:uint8_t> rCHK.
            
        Example:
            >>> Send e0 3a 1a
            >>> Return e0 01 e1 (enable)"""
        command: list[int] = [0x3A]
        return self._send_command(command)

    def read_shaft_status(self):
        """Read the status of the motor shaft. The status of the motor shaft is as follows:
            - 00-Error
            - 01-blocked
            - 02-unblocked
        
        Args:
            None
        
        Returns:
            Driver response with the form: e0 <status:uint8_t> rCHK.
            
        Example:
            >>> Send e0 3e 1e
            >>> Return e0 02 e2 (unblocked)"""
        command: list[int] = [0x3e]
        return self._send_command(command)

    def set_dir(self, dir:str):
        """Set the direction of the motor. The direction of the motor is as follows:
            - 00-CW
            - 01-CCW
        Command : <adress> 86 <dir> <tCHK>

        Args:
            dir: Direction of the motor ("CCW" or "CW")
        
        Returns:
            Driver response with the form: e0 <result:uint8_t> rCHK.
            
        Example:
            >>> Send e0 86 00 66
            >>> Return e0 01 e1 (successful)"""
        match dir:
            case 'CW':
                dir_byte = 0
            case 'CCW':
                dir_byte = 1
        command: list[int] = [0x3B, dir_byte]
        return self._send_command(command)
    
    def set_zero(self):
        """Set the current position as zero. Result can be:
            - 00-failure
            - 01-success
        Command is of the form <adress> 91 <mode> <tCHK>. mode is 00 for set zero and 01 for other modes(did not find more information
        please contribute if you have more information)

        Args:
            None
        
        Returns:
            Driver response with the form: e0 <result:uint_8_t> rCHK.
            
        Example:
            >>> Send e0 91 00 71
            >>> Return e0 e7"""
        command: list[int] = [0x91, 0x00]
        return self._send_command(command)

    def return_to_zero(self):
        """Return to the zero position. Command is of the form <adress> 92 00 <tCHK>. 
        The result can be:
            - 00-failure
            - 01-success

        Args:
            None
        
        Returns:
            Driver response with the form: e0 <result:uint_8_t> rCHK.
            
        Example:
            >>> Send e0 94 00 74
            >>> Return e0 01 e1 (successful)"""
        command: list[int] = [0x94, 0x00]
        return self._send_command(command)

    def set_EN_status(self):
        """Set the EN pin status. EN pin is used to control the motor driver enable signal. 
        The status can be:
            - 00-disable
            - 01-enable
        Command is of the form <adress> f3 <status> <tCHK>.

        Args:
            None
        
        Returns:
            Driver response with the form: e0 <result:uint8_t> rCHK.
            
        Example:
            >>> Send e0 f3 01 d4 (enable)
            >>> Return e0 01 e1 (successful)"""
        command: list[int] = [0x95, 0x01]
        return self._send_command(command)
    
    def stop(self):
        """Stop the motor. Command is of the form <adress> f7 <tCHK>.
        
        Args:
            None
        
        Returns:
            Driver response with the form: e0 <result:uint8_t> rCHK.
            
        Example:
            >>> Send e0 f7 d7
            >>> Return e0 01 e1 (successful)"""
        command: list[int] = [0x97]
        return self._send_command(command)

    def is_moving(self):
        pass

    def move_constant_speed(self, dir:str, speed_rpm:float):
        """Move the motor at a constant speed. Command is of the form <adress> f6 <param> <tCHK>.
        param: 0babbb bbb with a:direction, b:speed
        Vrpm = (speed[bin] x 30000)/(Mstep x 200) for 1.8°/step motor
        Vrpm = (speed[bin] x 30000)/(Mstep x 400) for 0.9°/step motor

        Args:
            dir: Direction of the motor ("CCW" or "CW")
            speed_rpm: Speed of the motor in RPM
        
        Returns:
            Driver response with the form: e0 <result:uint8_t> rCHK.
            
        Example:
            >>> Send e0 f6 00 00 (CW)
            >>> Return e0 01 e1 (successful)"""
        match dir:
            case 'CW':
                dir_byte = 0b0
            case 'CCW':
                dir_byte = 0b1
        match self.motor_type:
            case 1.8:
                speed:int = int((speed_rpm * 200 * self.Mstep) / (30000))
            case 0.9:
                speed:int = int((speed_rpm * 400 * self.Mstep) / (30000))
        speed_byte = bytes(speed)
        param = (dir_byte << 7) | int.from_bytes(speed_byte, 'big')

        command: list[int] = [0xf6, param]
        return self._send_command(command)

    def move_to_target(self, target_position, speed_rpm): # TODO
        """Move the motor to a target position at a given speed.
        Command: <adress> fd <param> <target> <tCHK>
        param: 0babbb bbb with a:direction, b:speed
        target(number of pulse): 0xXX XX XX XX (angle = pulse/Mstep x 1.8 for a 1.8°/step motor)
        Speed [RPM] = (speed[bin] x 30000)/(Mstep x 200) for 1.8°/step motor
        Speed [RPM] = (speed[bin] x 30000)/(Mstep x 400) for 0.9°/step motor
        
        Args:
            target_position: Target position
            speed_rpm: Speed of the motor in RPM
        
        Returns:
            Driver response with the form: e0 <result:uint8_t> rCHK.
            
        Example:
            >>> Send e0 a6 05"""
        command: list[int] = [0xA6, 0x05, target_position, speed_rpm]
        return self._send_command(command)

    def move_by_angle(self, angle, speed_rpm):
        current_position = self.read_shaft_angle()
        target_position = current_position + angle
        return self.move_to_target(target_position, speed_rpm)

    def find_home(self):
        """Find the home position. Command is of the form <adress> 9a <tCHK>.
        """
        self.move_by_angle(360, 10)
        while not self.check_home():
            pass
        self.stop()
        
# Exemple d'utilisation
if __name__ == "__main__":
    pass