from src.alpacatelescope import TelescopeDevice
from machine import Pin
from src.alpacaserver import readJson
from microdot.utemplate import Template

class Starget(TelescopeDevice):

    def __init__(self,  devnr, devname, uniqueid, config_file):
        super().__init__(devnr, devname, uniqueid, config_file)       
        self.description = "Starget Alpaca device"

        # Load pinout config file
        self.config = readJson("starget_pins_config.json")
        print(self.config)
        # ------------------------------ Configure pins ------------------------------ #
        # Stepper driver control
        step_primary = Pin(self.config["step_primary"], Pin.OUT)
        dir_primary = Pin(self.config["dir_primary"], Pin.OUT)
        en_primary = Pin(self.config["en_primary"], Pin.OUT)

        step_secondary = Pin(self.config["step_secondary"], Pin.OUT)
        dir_secondary = Pin(self.config["dir_secondary"], Pin.OUT)
        en_secondary = Pin(self.config["en_secondary"], Pin.OUT)

        drivers_RX = Pin(self.config["drivers_RX"], Pin.IN)
        drivers_TX = Pin(self.config["drivers_TX"], Pin.OUT)

        # GPS (incoming)
        ########

    def setup_request(self, request):
        return Template('setup_starget.html')
    
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
        pass
    
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
    def sync_to_coordinates(self):
        pass
    
    def sync_to_Altaz(self):
        pass

    def sync_to_target(self, RA, DEC):
        self.RA = RA
        self.DEC = DEC
    def PUT_synctocoordinates(self, request):
        if self.can_sync == "False":
            return NotImplementedError("Scope cannot sync to coordinates. Please change config file to ativate this method.")
        RA = float(request.form["RightAscension"])
        DEC = float(request.form["Declination"])
        self.sync_to_coordinates(RA, DEC)