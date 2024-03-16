from src.alpacatelescope import TelescopeDevice
from machine import Pin, UART
from src.alpacaserver import readJson
from microdot.utemplate import Template
from math import sin, asin, cos, acos, pi, radians, degrees
from stepper import Stepper
from micropyGPS import MicropyGPS

class Starget(TelescopeDevice):

    def __init__(self,  devnr, devname, uniqueid, config_file):
        super().__init__(devnr, devname, uniqueid, config_file)       
        self.description = "Starget Alpaca device"

        # Load pinout config file
        self.config = readJson("starget_pins_config.json")
        print(self.config)
        # ------------------------------ Configure pins ------------------------------ #
        # Stepper driver control
        self.step_primary = Pin(self.config["step_primary"], Pin.OUT)
        self.dir_primary = Pin(self.config["dir_primary"], Pin.OUT)
        self.en_primary = Pin(self.config["en_primary"], Pin.OUT)

        self.step_secondary = Pin(self.config["step_secondary"], Pin.OUT)
        self.dir_secondary = Pin(self.config["dir_secondary"], Pin.OUT)
        self.en_secondary = Pin(self.config["en_secondary"], Pin.OUT)

        self.s1 = Stepper(dir_pin=23, step_pin=22,steps_per_rev=200*8,speed_sps=500, en_pin=21,timer_id=-1)
        self.s2 = Stepper(dir_pin=26, step_pin=27,steps_per_rev=200*8,speed_sps=500, en_pin=13,timer_id=2)

        # End swithes
        self.endswitch_1 = Pin(self.config["end_RA"], Pin.IN, Pin.PULL_UP)
        self.endswitch_2 = Pin(self.config["end_DEC"], Pin.IN, Pin.PULL_UP)

        self.endswitch_1.irq(trigger=Pin.IRQ_FALLING, handler=self.endswitch_handler)
        self.endswitch_2.irq(trigger=Pin.IRQ_FALLING, handler=self.endswitch_handler)

        # GPS (incoming)
        self.GPS_RX = Pin(self.config["GPS_RX"], Pin.IN)
        self.GPS_TX = Pin(self.config["GPS_TX"], Pin.OUT)

        self.uart = UART(2, rx=self.GPS_TX, tx=self.GPS_RX, baudrate=9600, bits=8, parity=None, stop=1, timeout=5000, rxbuf=1024)
        self.gps = MicropyGPS()

    # ---------------------------------------------------------------------------- #
    #                                     Utils                                    #
    # ---------------------------------------------------------------------------- #
    def endswitch_handler(self, pin):
            if pin == self.endswitch_1:
                self.s1.stop()
                self.s1.overwrite_pos(0)
                self.s1.target(0)

            elif pin == self.endswitch_2:
                self.s2.stop()
                self.s2.overwrite_pos(0)
                self.s2.target(0)

    def setup_request(self, request):
        return Template('setup_starget.html')
    
    def read_GPS(self):
            buf = self.uart.readline()
            for char in buf:
                self.gps.update(chr(char))
    

    # ---------------------------------------------------------------------------- #
    #                              Telescope functions                             #
    # ---------------------------------------------------------------------------- #

    # --------------------------- Telescope parameters --------------------------- #
    # Since the goal of Starget is to handle several cameras and DSLR, it's useless to 
    # implement the following parameters to the Starget driver
    def GET_aperturearea(self, request):
        raise NotImplementedError("Get aperture area is not implemented in Starget")
    def GET_aperturediameter(self, request):
        raise NotImplementedError("Get aperture diameter is not implemented in Starget")
    def GET_focallength(self, request):
        raise NotImplementedError("Get focal length is not implemented in Starget")
    
    # ----------------------------- Slewing functions ---------------------------- #
    def find_home(self):
        # Uses 'endswitch_handler' to reset steppers position origin.
        # RA axis
        self.s1.speed(20)
        self.s1.free_run(1)
        # DEC axis
        self.s2.speed(20)
        self.s2.free_run(1)
        
        
    def park(self):
        pass

    def unpark(self):
        pass

    def abort_slew(self):
        pass

    def move_axis(self, axis, rate):
        pass

    def slew_to_coordinates(self):
        pass

    def slew_to_Altaz(self):
        pass

    def slew_to_target(self):
        pass

    # ------------------------- Synchronisation functions ------------------------ #
    def sync_to_coordinates(self, RA, DEC):
        self.RA = RA
        self.DEC = DEC

    def sync_to_Altaz(self, alt, az):
        self.RA, self.DEC = self.Altaz_to_equatorial(alt, az)       

    def sync_to_target(self, RA, DEC):
        self.RA = self.target_RA
        self.DEC = self.target_DEC

