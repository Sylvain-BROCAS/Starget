import serial
import time

class MKSMotorController:
    def __init__(self, ):
        """
        Initialise le contrôleur du moteur
        :param port: Port UART (ex: '/dev/ttyUSB0' sur Linux)
        :param baudrate: Vitesse de communication (défaut: 115200)
        """
        # self.serial = serial.Serial(port, baudrate, timeout=1)
        # self.current_position = 0  # Position en degrés
        # self.steps_per_degree = 200  # Dépend du microstepping configuré
        # self.reduction_ratio = 100  # Ratio du réducteur

    def move_to_position(self, target_position_degrees):
        pass

    def move_by_angle(self, angle_degrees):
        """
        Déplace le moteur d'un angle spécifique
        :param angle_degrees: Angle de déplacement en degrés
        """
        pass

    def return_to_zero(self):
        """Retourne le moteur à la position 0"""
        return self.move_to_position(0)

    def set_zero_position(self):
        pass

    def stop(self):
        """Arrête le mouvement du moteur"""
        pass
    
    def is_moving(self):
        """Vérifie si le moteur est en mouvement"""
        pass

    def move_constant_speed(self, speed_steps_per_second, distance_steps):
        """
        Déplace le moteur à une vitesse constante
        :param speed_steps_per_second: Vitesse en steps/second
        :param distance_steps: Distance en steps
        """
        pass