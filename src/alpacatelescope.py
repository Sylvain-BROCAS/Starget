from src.alpacaserver import *
from src.alpacadevice import AlpacaDevice
from math import radians, degrees, cos, sin, acos, asin
from machine import RTC

rtc = RTC()

# ASCOM Alpaca telescope device
class TelescopeDevice(AlpacaDevice):

    def __init__(self, devnr, devname, uniqueid, config_file):
        super().__init__(devnr, devname, uniqueid)
        # ---------------------------- Driver informations --------------------------- #
        self.interface_version = 3
        self.driver_info = "ASCOM Alpaca Telescope Driver"
        self.driver_version = "0.0.1"
        self.supported_actions = []
        self.devnr = devnr
        # Load telescope configuration
        self.config_file = config_file
        self.config = readJson(self.config_file)

        # ---------------------------- Telescope & site parameters ---------------------------- #
        self.alignment_mode = self.config[self.devnr]["alignment_mode"]

        self.aperture_area = self.config[self.devnr]["aperture_area"]
        self.aperture_diameter = self.config[self.devnr]["aperture_diameter"]
        self.focal_length = self.config[self.devnr]["focal_length"]
    
        self.equatorial_system = self.config[self.devnr]["equatorial_system"]
        self.does_refraction = self.config[self.devnr]["does_refraction"]
        self.slew_settle_time = self.config[self.devnr]["slew_settle_time"]
        self.tracking_rates = self.config[self.devnr]["tracking_rates"]
        self.axis_rates = self.config[self.devnr]["axis_rates"]
        
        self.site_elevation = self.config[self.devnr]["site_elevation"]
        self.site_latitude = self.config[self.devnr]["site_latitude"]
        self.site_longitude = self.config[self.devnr]["site_longitude"]
        

        # ----------------------------- Telescope actions ---------------------------- #
        self.can_find_home = self.config[self.devnr]["can_find_home"]

        self.can_park = self.config[self.devnr]["can_park"]
        self.can_unpark = self.config[self.devnr]["can_unpark"]
        self.can_set_park = self.config[self.devnr]["can_set_park"]
        self.park_pos = self.config[self.devnr]["park_pos"] # Park position (Mount referential): [RA, DEC]
        self.can_set_DEC = self.config[self.devnr]["can_set_DEC"]
        self.can_set_RA = self.config[self.devnr]["can_set_RA"]
        self.can_set_DEC_rate = self.config[self.devnr]["can_set_DEC_rate"]
        self.can_set_RA_rate = self.config[self.devnr]["can_set_RA_rate"]
        self.can_move_axis = self.config[self.devnr]["can_move_axis"]

        self.can_slew = self.config[self.devnr]["can_slew"]
        self.can_slew_async = self.config[self.devnr]["can_slew_async"]
        self.can_slew_AltAz = self.config[self.devnr]["can_slew_AltAz"]
        self.can_slew_AltAz_async = self.config[self.devnr]["can_slew_AltAz_async"]

        self.can_set_tracking = self.config[self.devnr]["can_set_tracking"]
        self.can_set_sidereal_rate = self.config[self.devnr]["can_set_sidereal_rate"]

        self.can_pulse_guide = self.config[self.devnr]["can_pulse_guide"]
        self.can_set_guide_rates = self.config[self.devnr]["can_set_guide_rates"]

        self.can_sync = self.config[self.devnr]["can_sync"]
        self.can_sync_AltAz = self.config[self.devnr]["can_sync_AltAz"]

        self.can_set_pier_side = self.config[self.devnr]["can_set_pier_side"]
        # -------------------------- Positionning variables -------------------------- #
        self.sidereal_time = 0
        self.UTC_date = ""

        self.RA = 0
        self.DEC = 0
        self.altitude = 0
        self.azimuth = 0

        self.RA_rate = 0
        self.DEC_rate = 0

        self.guide_rate_RA = 0
        self.guide_rate_DEC = 0

        self.tracking_rate = 0

        self.target_RA = 0
        self.target_DEC = 0
        
        self.destination_side_of_pier = ""
        # ------------------------------- Scope states ------------------------------- #
        self.at_home = False
        self.at_park = False
        self.slewing = False
        self.tracking = False
        self.is_pulse_guiding = False
        self.side_of_pier = ""

        self.hemisphere = self.config[self.devnr]["hemisphere"]
        if self.hemisphere == "north":
            self.tracking_dir = 1
        elif self.hemisphere == "south":
            self.tracking_dir = -1

    # ----------------------------------- Utils ---------------------------------- #
    # get telescope id from request
    def get_device_id(self, request):
        try:
            idarg = getArg(request, "Id")
            
            # N.I.N.A compatibility workaround
            if idarg == None:
                idarg = getArg(request, "ID")
                
            id = int(idarg)
        except (ValueError, TypeError):
           raise CallArgError("Telescope ID invalid")
        return id
    
    def UTC_time(self):
        return 0
    
    def Altaz_to_equatorial(self, alt, az):
        # Units conversion to radians
        alt = radians(alt)
        az = radians(az)
        lat = radians(self.site_latitude)

        # RA and DEC calculation
        DEC = degrees(asin(sin(lat)*sin(alt)+cos(lat)*cos(az)))
        HA = acos( (sin(alt)-sin(lat)*sin(DEC)) / (cos(lat)*cos(DEC)) )
        RA = degrees(self.sidereal_time - HA)

        return RA, DEC
    # ---------------------------------------------------------------------------- #
    #                             Define ASCOM methodes                             #
    # ---------------------------------------------------------------------------- #
    # ----------------------- Telescope and site parameters ---------------------- #
    def GET_alignmentmode(self, request):
        return self.reply(request, self.alignment_mode)
    # ---------------------------------------------------------------------------- #
    def GET_aperturearea(self, request):
        return self.reply(request, self.aperture_area)

    def GET_aperturediameter(self, request):
        return self.reply(request, self.aperture_diameter)
    
    def GET_focallength(self, request):
        return self.reply(request, self.focal_length)
    # ---------------------------------------------------------------------------- #
    def GET_equatorialsystem(self, request):
        return self.reply(request, self.equatorial_system)

    def GET_doesrefraction(self, request):
        return self.reply(request, self.does_refraction)

    def set_does_refraction(self, value):
        self.does_refraction = value
    def PUT_doesrefraction(self, request):
        if request.form['DoesRefraction'] is None:
            raise CallArgError("Invalid or missing value for does_refraction")
        v = bool(request.form['DoesRefraction'])
        self.set_does_refraction(v)
        return self.reply(request, "")

    def GET_slewsettletime(self, request):
        return self.reply(request, self.slew_settle_time)
    
    def set_slew_settle_time(self, value):
        self.slew_settle_time = value
    def PUT_slewsettletime(self, request):
        if request.form['SlewSettleTime'] is None:
            raise CallArgError("Invalid or missing value for slew_settle_time")
        v = float(request.form['SlewSettleTime'])
        self.set_slew_settle_time(v)
        return self.reply(request, "")
    
    def GET_trackingrates(self, request):
        return self.reply(request, self.tracking_rates)

    def GET_axisrates(self, request):
        return self.reply(request, self.axis_rates)
    # ---------------------------------------------------------------------------- #
    def GET_siteelevation(self, request):
        return self.reply(request, self.site_elevation)

    def set_site_elevation(self, value):
        self.site_elevation = value
    def PUT_siteelevation(self, request):
        if request.form['SiteElevation'] is None:
            raise CallArgError("Invalid or missing value for site_elevation")
        v = float(request.form['SiteElevation'])
        self.set_site_elevation(v)
        return self.reply(request, "")

    def GET_sitelatitude(self, request):
        return self.reply(request, self.site_latitude)

    def set_site_latitude(self, value):
        self.site_latitude = value
    def PUT_sitelatitude(self, request):
        if request.form['SiteLatitude'] is None:
            raise CallArgError("Invalid or missing value for site_latitude")
        v = float(request.form['SiteLatitude'])
        self.set_site_latitude(v)
        return self.reply(request, "")

    async def GET_sitelongitude(self, request):
        return self.reply(request, self.site_longitude)

    def set_site_longitude(self, value):
        self.site_longitude = value
    def PUT_sitelongitude(self, request):
        if request.form['SiteLongitude'] is None:
            raise CallArgError("Invalid or missing value for site_longitude")
        v = float(request.form['SiteLongitude'])
        self.set_site_longitude(v)
        return self.reply(request, "")
    
    # ----------------------------- Telescope actions ---------------------------- #
    def GET_canfindhome(self, request):
        return self.reply(request, self.can_find_home)
    # ---------------------------------------------------------------------------- #
    def GET_canpark(self, request):
        return self.reply(request, self.can_park)    

    def GET_canunpark(self, request):
        return self.reply(request, self.can_unpark)  

    def GET_cansetpark(self, request):
        return self.reply(request, self.can_set_park)
    # ---------------------------------------------------------------------------- #
    def GET_cansetrightascension(self, request):
        return self.reply(request, self.can_set_RA)

    def GET_cansetdeclinaiton(self, request):
        return self.reply(request, self.can_set_DEC)  

    def GET_cansetrightascensionrate(self, request):
        return self.reply(request, self.can_set_RA_rate)

    def GET_cansetdeclinationrate(self, request):
        return self.reply(request, self.can_set_DEC_rate)

    def GET_canmoveaxis(self, request):
        return self.reply(request, self.can_move_axis)
    # ---------------------------------------------------------------------------- #
    def GET_canslew(self, request):
        return self.reply(request, self.can_slew)

    def GET_canslewasync(self, request):
        return self.reply(request, self.can_slew_async)

    def GET_canslewaltaz(self, request):
        return self.reply(request, self.can_slew_AltAz)
    
    def GET_canslewaltazasync(self, request):
        return self.reply(request, self.can_slew_AltAz_async)
    # ---------------------------------------------------------------------------- #
    def GET_cansettracking(self, request):
        return self.reply(request, self.can_set_tracking)
    # ---------------------------------------------------------------------------- #
    def GET_canpulseguide(self, request):
        return self.reply(request, self.can_pulse_guide)
    
    def GET_cansetguiderates(self, request):
        return self.reply(request, self.can_set_guide_rates)    
    # ---------------------------------------------------------------------------- #
    def GET_cansync(self, request):
        return self.reply(request, self.can_sync)
    # ---------------------------------------------------------------------------- #
    def GET_cansetpierside(self, request):
        return self.reply(request, self.can_set_pier_side)
       
    # ---------------------- Telescope positioning methodes ---------------------- #

    def get_sidereal_time(self): 
        pass
    def GET_siderealtime(self, request):
        sidereal_time = self.get_sidereal_time()
        return self.reply(request, sidereal_time)

    def get_utc_date(self):
        pass
    def GET_utcdate(self, request):
        utd_date = self.get_utc_date()
        return self.reply(request, utd_date)

    def set_utc_date(self, date):
        self.UTC_date
    def PUT_utcdate(self, request):
        if request.form['UTCDate'] is None:
            raise CallArgError("Invalid or missing value for UTC_date")
        v = str(request.form['UTCDate'])
        self.set_utc_date(v)
        return self.reply(request, "")

    # ---------------------------------------------------------------------------- #
    def get_RA(self):
        pass
    def GET_rightascension(self, request):
        RA = self.get_RA
        return self.reply(request, RA)

    def get_DEC(self):
        pass
    def GET_declination(self, request):
        DEC = self.get_DEC
        return self.reply(request, DEC)

    def get_altitude(self):
        pass
    def GET_altitude(self, request):
        altitude = self.get_altitude()
        return self.reply(request, altitude)

    def get_azimuth(self):
        pass
    def GET_azimuth(self, request):
        azimuth = self.get_azimuth()
        return self.reply(request, azimuth) 
    # ---------------------------------------------------------------------------- #
    def get_RA_rate(self):
        pass
    def GET_rightascensionrate(self, request):
        RA_rate = self.get_RA_rate()
        return self.reply(request, RA_rate)

    def set_RA_rate(self, value):
        self.RA_rate = value
    def PUT_rightascensionrate(self, request):
        if self.can_set_RA_rate == False:
            raise NotImplementedError("Right ascension rate can not be set.")
        if request.form['RighAscensionRate'] is None:
            raise CallArgError("Invalid or missing value for RA_rate")
        v = float(request.form['RightAscensionRate'])
        self.set_RA_rate(v)
        return self.reply(request, "")
    
    def get_DEC_rate(self):
        pass
    def GET_declinationrate(self, request):
        DEC_rate = self.get_DEC_rate()
        return self.reply(request, DEC_rate)

    def set_DEC_rate(self, value):
        self.DEC_rate = value
    def PUT_declinationrate(self, request):
        if self.can_set_DEC_rate == False:
            raise NotImplementedError("Declination rate can not be set.")
        if request.form['DeclinationRate'] is None:
            raise CallArgError("Invalid or missing value for DEC_rate")
        v = float(request.form['DeclinationRate'])
        self.set_DEC_rate(v)
        return self.reply(request, "")
    # ---------------------------------------------------------------------------- #
    def GET_guideraterightascension(self, request):
        return self.reply(request, self.guide_rate_RA)
    
    def set_guide_rate_RA(self, value):
        self.guide_rate_RA = value
    def PUT_guideraterightascension(self, request):
        if self.can_set_guide_rate_RA == False:
            raise NotImplementedError("Guide rate right ascension can not be set.")
        if request.form['GuideRateRightAscension'] is None:
            raise CallArgError("Invalid or missing value for guide_rate_RA")
        v = float(request.form['GuideRateRightAscension'])
        self.set_guide_rate_RA(v)
        return self.reply(request, "")

    def GET_guideratedeclination(self, request):
        return self.reply(request, self.guide_rate_DEC)

    def set_guide_rate_DEC(self, value):
        self.guide_rate_DEC = value
    def PUT_guideratedeclination(self, request):
        if self.can_set_guide_rate_DEC == False:
            raise NotImplementedError("Guide rate declination can not be set.")
        if request.form['GuideRateDeclination'] is None:
            raise CallArgError("Invalid or missing value for guide_rate_DEC")
        v = float(request.form['GuiderateDeclination'])
        self.set_guide_rate_DEC(v)
        return self.reply(request, "")
    # ---------------------------------------------------------------------------- #
    def GET_trackingrate(self, request):
        return self.reply(request, self.tracking_rate)

    def set_tracking_rate(self, value):
        self.tracking_rate = value
    def PUT_trackingrate(self, request):
        if self.can_set_sidereal_rate == False:
            raise NotImplementedError("Tracking rate can not be set.")
        if request.form['TrackingRate'] is None:
            raise CallArgError("Invalid or missing value for tracking_rate")

        v = int(request.form['TrackingRate'])

        if v not in self.tracking_rates:
            raise CallArgError("Invalid value for tracking_rate, check available tracking rates")
        self.set_guide_rate_RA(v)
        return self.reply(request, "")
    # ---------------------------------------------------------------------------- #
    def GET_targetrightascension(self, request):
        return self.reply(request, self.target_RA)

    def set_target_RA(self, value):
        self.target_RA = value
    def PUT_targetrightascension(self, request):
        if request.form['TargetRightAscension'] is None:
            raise CallArgError("Invalid or missing value for target_RA")
        v = float(request.form['targetRightAscension'])
        self.set_target_RA(v)
        return self.reply(request, "")

    def GET_targetdeclination(self, request):
        return self.reply(request, self.target_DEC)

    def set_target_DEC(self, value):
        self.target_DEC = value
    def PUT_targetdeclination(self, request):
        if request.form['TargetDeclination'] is None:
            raise CallArgError("Invalid or missing value for target_DEC")
        v = float(request.form['TargetDeclination'])
        self.set_target_DEC(v)
        return self.reply(request, "")
    # ---------------------------------------------------------------------------- #
    # I have a fork mount, so I will not implement this function. 
    # Feel free to improve this file for your own usage
    def GET_destinationsideofpier(self, request):
        raise NotImplementedError("Get destinationside of pier is not implemented")

    # ------------------------------- Scope states ------------------------------- #
    def GET_athome(self, request):
        return self.reply(request, self.at_home)

    def GET_atpark(self, request):
        return self.reply(request, self.at_park)

    def GET_slewing(self, request):
        return self.reply(request, self.slewing)
    
    def GET_tracking(self, request):
        return self.reply(request, self.tracking)
    
    def set_tracking(self, state):
        self.tracking = state
    def PUT_tracking(self, request):
        if self.can_set_tracking == False:
            raise NotImplementedError("Tracking state cannot be set")
        if request.form['Tracking'] is None:
            raise CallArgError("Invalid or missing value for tracking state")
        v = bool(request.form['Tracking'])
        self.set_tracking(v)
        return self.reply(request, self.tracking)


    def GET_ispulseguiding(self, request):
        return self.reply(request, self.is_pulse_guiding)

    def get_side_of_pier(self):
        pass
    def GET_sidemarker(self, request):
        side_of_pier = self.get_side_of_pier()
        return self.reply(request, side_of_pier)

    def set_side_of_pier(self, side_of_pier):
        pass
    def PUT_sideofpier(self, request):
        #I have a fork mount, so I will not implement that.
        # Feel free to improve this file
        raise NotImplementedError("Side of pier cannot be set")
    # ------------------------------ Slewing methods ----------------------------- #
    def find_home(self):
        pass
    def PUT_findhome(self, request):
        if self.can_find_home == False:
            raise NotImplementedError("Home finding cannot be set")
        self.find_home()
        return self.reply(request, "")
    # ---------------------------------------------------------------------------- #
    def abort_slew(self):
        pass
    def PUT_abortslew(self, request):
        self.abort_slew()
        return self.reply(request, "")
    # ---------------------------------------------------------------------------- #
    def set_park(self):
        park_pos = [self.RA, self.DEC]
        self.config["park_pos"] = park_pos
        writeJson(self.config_file, self.config)
    def PUT_setpark(self, request):
        if self.can_set_park == False:
            raise NotImplementedError("Parking cannot be set")
        self.set_park() 
        return self.reply(request, "")
    
    def park(self):
        pass
    def PUT_park(self, request):
        if self.can_park == False:
            raise NotImplementedError("This telescope cannot park")
        self.park()
        return self.reply(request, "")

    def unpark(self):
        pass
    def PUT_unpark(self, request):
        if self.can_unpark == False:
            raise NotImplementedError("This telescope cannot unpark")
        self.unpark()
        return self.reply(request, "")
    # ---------------------------------------------------------------------------- #
    def pulse_guide(self):
        pass
    def PUT_pulseguide(self, request):
        pass
    # ---------------------------------------------------------------------------- #
    def move_axis(self, axis, rate):
        pass
    def PUT_moveaxis(self, request):
        if self.can_move_axis == False:
            raise NotImplementedError("This telescope cannot move axis")
        axis = float(request.form['Axis'])
        rate = float(request.form['Rate'])
        self.move_axis(axis, rate) 
        return self.reply(request, "")

    def slew_to_coordinates(self, RA, DEC):
        pass
    def PUT_slewtocoordinates(self, request):
        RA = float(request.form['RA'])
        DEC = float(request.form['DEC'])
        self.slew_to_coordinates(RA, DEC)
        return self.reply(request, "")



    # Maybe a future feature
    def slew_to_coordinates_async(self):
        pass
    def PUT_slewtocoordinatesasync(self, request):
        raise NotImplementedError("Slew to coordinates async is not yet implemented")

    def slew_to_Altaz(self):
        pass
    def PUT_slewtoaltaz(self, request):
        pass

        # Maybe a future feature
    def slew_to_Altaza_sync(self):
        pass
    def PUT_slewtoaltazasync(self, request):
        raise NotImplementedError("Slew to Altaz coordinates async is not yet implemented")
    
    def slew_to_target(self):
        pass
    def PUT_slewtotarget(self, request):
        self.slew_to_coordinates()
        return self.reply(request, "")

    # Maybe a future feature
    def slew_to_target_async(self):
        pass
    def PUT_slewtotargetasync(self, request):
        raise NotImplementedError("Slew to target async is not yet implemented")


    # ------------------------------ Synchronisation ----------------------------- #
    # Not implemented by default, define these methods in my_telesope.py scripy 
    
    def sync_to_Altaz(self):
        pass
    def PUT_synctoaltaz(self, request):
        raise NotImplementedError("Sync to Altaz not implemented")

    def sync_to_coordinates(self, RA, DEC):
        pass
    def PUT_synctotarget(self, request):
        if self.can_sync == "False":
            return NotImplementedError("Scope cannot sync to coordinates. Please change config file to ativate this method.")
        RA = float(request.form["RightAscension"])
        DEC = float(request.form["Declination"])
        self.sync_to_coordinates(RA, DEC)

    def sync_to_target(self):
        self.RA = self.target_RA
        self.DEC = self.target_DEC
    def PUT_synctotarget(self, request):
        if self.can_sync == "False":
            raise NotImplementedError("Sync method not implemented. Change config file to update.")
        self.sync_to_target()
        return self.reply(request, "")