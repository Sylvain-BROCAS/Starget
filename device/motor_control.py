import serial
import struct
import time
from typing import Callable
from utilities import is_RA_homed
try:
    import RPi.GPIO as GPIO
except:
    pass
class MKSMotor:
    def __init__(self, check_home: Callable, port='/dev/serial0', baudrate=115200, timeout=1):
        #For Rpi :
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setwarnings(False)
        
        # For Serial
        self.ser = serial.Serial(port, baudrate, timeout=timeout)

        # Initialisation de la connexion série sur les broches UART du Raspberry Pi
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self._speed = 0
        self.check_home = check_home

    def _send_command(self, command_bytes):
        self.ser.write(command_bytes)
        time.sleep(0.1)
        response = self.ser.read_all()
        return response

    @property
    def speed(self) -> int:
        return self._speed
    @speed.setter
    def speed(self, speed_rpm):
        speed_rpm = max(min(speed_rpm, 3000), -3000)
        command = struct.pack('<BBBhh', 0x3E, 0xA1, 0x05, speed_rpm, 0x00)
        return self._send_command(command)

    def start(self):
        command = struct.pack('<BBB', 0x3E, 0xA2, 0x01)
        return self._send_command(command)

    def stop(self):
        command = struct.pack('<BBB', 0x3E, 0xA3, 0x01)
        return self._send_command(command)

    def set_direction(self, direction):
        direction = 0 if direction == 'CW' else 1
        command = struct.pack('<BBBb', 0x3E, 0xA4, 0x02, direction)
        return self._send_command(command)

    def move_constant_speed(self, speed_rpm, direction='CW'):
        self.set_direction(direction)
        self.speed = speed_rpm
        return self.start()

    def move_by_angle(self, angle_deg, speed_rpm):
        # Commande pour déplacer d'un certain angle
        command = struct.pack('<BBBhh', 0x3E, 0xA5, 0x05, int(angle_deg), speed_rpm)
        return self._send_command(command)

    def move_to_target(self, target_position, speed_rpm):
        # Commande pour déplacer vers une position cible
        command = struct.pack('<BBBhh', 0x3E, 0xA6, 0x05, target_position, speed_rpm)
        return self._send_command(command)

    def set_zero_position(self):
        # Commande pour définir la position actuelle comme zéro
        command = struct.pack('<BBB', 0x3E, 0xA7, 0x01)
        return self._send_command(command)

    def move_to_zero_position(self):
        # Vérifier la position actuelle avant de se déplacer
        current_position = self._read_pulses()
        if current_position != 0:
            self._send_command(struct.pack('<BBBh', 0x3E, 0xA8, 0x02, 0))
         # Pas de mouvement nécessaire si déjà à zéro
    
    def _read_pulses(self):
        command = struct.pack('<BBB', 0xE0, 0x33, 0x13)
        response = self._send_command(command)
        if len(response) >= 6:
            pulses = struct.unpack('<i', response[1:5])[0]  # Extraction des 4 octets des pulsations
            return pulses
        return 0

    def is_running(self):
        pulses_1 = self._read_pulses()
        time.sleep(0.2)
        pulses_2 = self._read_pulses()
        return pulses_1 != pulses_2
    
    def close(self):
        self.ser.close()
        GPIO.cleanup()

    def find_home(self):
        self.move_constant_speed(1500, 'CCW')
        while self.is_running():
            if self.check_home():
                self.stop()
                break
                
# Exemple d'utilisation
if __name__ == "__main__":
    motor = MKSMotor(check_home=is_RA_homed, port='/dev/serial0')
    motor.move_constant_speed(1500, 'CW')
    time.sleep(5)
    motor.stop()

    motor.move_by_angle(90, 1000)
    time.sleep(2)

    motor.move_to_target(2000, 1200)
    time.sleep(3)

    motor.close()