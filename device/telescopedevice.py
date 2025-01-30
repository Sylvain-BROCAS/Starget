from threading import Timer, Lock
from device.telescope_enum import EquatorialCoordinateType, PierSide
from telescope_enum import *
from utilities import *
from logging import Logger



class TelescopeDevice:
    def __init__(self, logger:Logger):
        # Initialize telescope properties
        self.logger: Logger = logger
        self._lock = Lock()
        self._connlock = Lock()
        self._timer = None

        # --------------------------- Telescope parameters --------------------------- #
        # Example, adjust as needed
        self._alignment_mode: AlignmentModes = AlignmentModes.algGermanPolar
        self._equatorial_system = EquatorialCoordinateType.equJ2000
        self._aperture_area: float = 0.0
        self._aperture_diameter: float = 0.0
        self._focal_length: float = 0.
        self._slew_settle_time_sec: float = 0.0
        self._tracking_rates: DriveRates = DriveRates.driveSidereal
        self._axis_rate: AxisRates = AxisRates.axisRateSlow

        self._does_refraction: bool = False
        self._can_find_home: bool = True
        self._can_pulse_guide: bool = False
        self._can_set_guiderates: bool = False
        self._can_set_park: bool = False
        self._can_set_pierside: bool = False
        self._can_set_RA_rate: bool = True
        self._can_set_DEC_rate: bool = True
        self._can_set_tracking: bool = True
        self._can_slew: bool = True
        self._can_slew_async: bool = True
        self._can_slew_altaz: bool = False
        self._can_slew_altaz_async: bool = False
        self._can_sync: bool = True
        self._can_sync_altaz: bool = False
        self._can_sync_to_target: bool = False
        self._can_sync_to_target_async: bool = False
        self._can_park: bool = True
        self._can_unpark: bool = True

        self._steps_per_sec: int = 6
        self._conn_time_sec: float = 5.0    # Async connect delay
        self._step_size: float = 1.0
        # ----------------------------- Telescope status ----------------------------- #
        self._connected: bool = False
        self._connecting: bool = False
        self._sync_write_connected: bool = True
        
        self._RA: float = 0.0
        self._DEC: float = 0.0
        self._at_home: bool = False
        self._at_park: bool = False
        self._side_of_pier: PierSide = PierSide.pierUnknown

        self._is_tracking: bool = False
        self._is_pulse_guiding: bool = False
        self._is_moving: bool = False
        self._stopped: bool = False
        self._parked: bool = False
        self._slewing: bool = False

        self._target_ra: float = 0.0
        self._target_dec: float = 0.0
        self._RA_rate: float = 0.0 # ["/SI s]
        self._DEC_rate: float = 0.0 # ["/SI s]
        self._guide_RA_rate: float = 0.0
        self._guide_DEC_rate: float = 0.0

        self._utc_date: str = ''
        self._local_sidereal_time: float = 0.0
        
        # ----------------------------------- Setup ---------------------------------- #
        
    # ---------------------------------------------------------------------------- #
    #                                  Properties                                  #
    # ---------------------------------------------------------------------------- #

    # -------------------------------- Connection -------------------------------- #
    @property
    def connected(self) -> bool:
        self._connlock.acquire()
        res = self._connected
        self._connlock.release()
        return res
    @connected.setter
    def connected(self, toconnect: bool) -> None:
        self._connlock.acquire()
        if (not toconnect) and self._connected and self._is_moving:
            self._connlock.release()
            # Yes you could call Halt() but this is for illustration
            raise RuntimeError('Cannot disconnect while rotator is moving')
        if toconnect:
            if (self._sync_write_connected):
                self._connected = True
                self.logger.info('[instant connected]')
                self._connlock.release()
            else:
                self._connlock.release()
                self.logger.info('[delayed connecting]')
                self.Connect()      # Does own locking
        else:
            self._connected = False
            self._connlock.release()
            self.logger.info('[instant disconnected]')

    @property
    def connecting(self) -> bool:
        self._connlock.acquire()
        res = self._connecting
        self._connlock.release()
        return res

    # --------------------------- Site properties --------------------------- #
    @property
    def SiteElevation(self) -> float:
        self._lock.acquire()
        res =  self._site_elevation
        self._lock.release()
        return res 
    @SiteElevation.setter
    def SiteElevation(self, elevation: float) -> None:
        self._lock.acquire()
        self._site_elevation = elevation
        self._lock.release()
        self.logger.debug(f'[Site elevation] {str(elevation)}')
    
    @property
    def SiteLatitude(self) -> float:
        self._lock.acquire()
        res =  self._site_latitude
        self._lock.release()
        return res
    @SiteLatitude.setter
    def SiteLatitude(self, latitude: float) -> None:
        self._lock.acquire()
        self._site_latitude = latitude
        self._lock.release()
        self.logger.debug(f'[Site latitude] {str(latitude)}')

    @property
    def SiteLongitude(self) -> float:
        self._lock.acquire()
        res = self._site_longitude
        self._lock.release()
        return res
    @SiteLongitude.setter
    def SiteLongitude(self, longitude: float) -> None:
        self._lock.acquire()
        self._site_longitude = longitude
        self._lock.release()
        self.logger.debug(f'[Site longitude] {str(longitude)}')

    # --------------------------- Telescope properties --------------------------- #
    @property
    def AlignmentMode(self) -> AlignmentModes:
        self._lock.acquire()
        res = self._alignment_mode
        self._lock.release()
        return res
    @AlignmentMode.setter
    def AlignmentMode(self, mode: AlignmentModes) -> None:
        self._lock.acquire()
        self._alignment_mode = mode
        self._lock.release()
        self.logger.debug(f'[Alignment mode] {str(mode)}')

    @property
    def ApertureArea(self) -> float:
        self._lock.acquire()
        res = self._aperture_area
        self._lock.release()
        return res
    
    @property
    def ApertureDiameter(self) -> float:
        self._lock.acquire()
        res = self._aperture_diameter
        self._lock.release()
        return res
    
    @property
    def SlewSettleTime(self) -> float:
        self._lock.acquire()
        res = self._slew_settle_time_sec
        self._lock.release()
        return res
    @SlewSettleTime.setter
    def SlewSettleTime(self, time_sec: float) -> None:
        self._lock.acquire()
        self._slew_settle_time_sec = time_sec
        self._lock.release()
        self.logger.debug(f'[Slew settle time] {str(time_sec)}')
    
    @property
    def EquatorialSystem(self) -> EquatorialCoordinateType:
        self._lock.acquire()
        res: EquatorialCoordinateType = self._equatorial_system
        self._lock.release()
        return res
    @EquatorialSystem.setter
    def EquatorialSystem(self, system: EquatorialCoordinateType) -> None:
        self._lock.acquire()
        self._equatorial_system = system
        self._lock.release()
        self.logger.debug(f'[Equatorial system] {str(system)}')

    @property
    def FocalLength(self) -> float:
        self._lock.acquire()
        res: float = self._focal_length
        self._lock.release()
        return res
    
    @property
    def StepSize(self) -> float:
        self._lock.acquire()
        res: float = self._step_size
        self._lock.release()
        return res
    @StepSize.setter
    def StepSize(self, step_size: float) -> None:
        self._lock.acquire()
        self._step_size = step_size
        self._lock.release()
        self.logger.debug(f'[Step size] {str(step_size)}')
    
    @property
    def StepPerSec(self) -> int:
        self._lock.acquire()
        res: int = self._steps_per_sec
        self._lock.release()
        return res
    @StepPerSec.setter
    def StepPerSec(self, steps_per_sec: int) -> None:
        self._lock.acquire()
        self._steps_per_sec = steps_per_sec
        self._lock.release()
        self.logger.debug(f'[Steps per second] {str(steps_per_sec)}')
     
    # -------------------------- Telescope capabilities -------------------------- #
    @property
    def CanFindHome(self) -> bool:
        self._lock.acquire()
        res = self._can_find_home
        self._lock.release()
        return res
    
    @property
    def CanPulseGuide(self) -> bool:
        self._lock.acquire()
        res = self._can_pulse_guide
        self._lock.release()
        return res
    
    @property
    def CanSetGuiderates(self) -> bool:
        self._lock.acquire()
        res = self._can_set_guiderates
        self._lock.release()
        return res
    
    @property
    def CanSetDECRate(self) -> bool:
        self._lock.acquire()
        res = self._can_set_DEC_rate
        self._lock.release()
        return res

    @property
    def CanSetTracking(self) -> bool:
        self._lock.acquire()
        res = self._can_set_tracking
        self._lock.release()
        return res
    
    @property
    def CanSlew(self) -> bool:
        self._lock.acquire()
        res = self._can_slew
        self._lock.release()
        return res
    
    @property
    def CanSlewAsync(self) -> bool:
        self._lock.acquire()
        res = self._can_slew_async
        self._lock.release()
        return res
    
    @property
    def CanSlewAltAz(self) -> bool:
        self._lock.acquire()
        res = self._can_slew_altaz
        self._lock.release()
        return res
    
    @property
    def CanSlewAltAzAsync(self) -> bool:
        self._lock.acquire()
        res = self._can_slew_altaz_async
        self._lock.release()
        return res
    
    @property
    def CanSync(self) -> bool:
        self._lock.acquire()
        res = self._can_sync
        self._lock.release()
        return res
    
    @property
    def CanUnpark(self) -> bool:
        self._lock.acquire()
        res = self._can_unpark
        self._lock.release()
        return res
    
    @property
    def CanPark(self) -> bool:
        self._lock.acquire()
        res = self._can_park
        self._lock.release()
        return res
    
    @property
    def CanSetPark(self) -> bool:
        self._lock.acquire()
        res = self._can_set_park
        self._lock.release()
        return res
    
    @property
    def CanSetPierside(self) -> bool:
        self._lock.acquire()
        res = self._can_set_pierside
        self._lock.release()
        return res
    
    @property
    def CanSetRaRate(self) -> bool:
        self._lock.acquire()
        res = self._can_set_RA_rate
        self._lock.release()
        return res
    
    @property
    def CanSetDecRate(self) -> bool:
        self._lock.acquire()
        res = self._can_set_DEC_rate
        self._lock.release()
        return res
    
    @property
    def CanSyncAltAz(self) -> bool:
        self._lock.acquire()
        res = self._can_sync_altaz
        self._lock.release()
        return res
    
    @property
    def DoesRefraction(self) -> bool:
        self._lock.acquire()
        res = self._does_refraction
        self._lock.release()
        return res
    
        self._lock.acquire()
        self._can_reverse = reverse
        self._lock.release()
        self.logger.debug(f'[Can reverse] {str(reverse)}')

    # ----------------------------- Telescope status ----------------------------- #
    @property
    def Altitude(self) -> float: # TODO: Convert to actual altitude
        # Implementation here
        return -1

    @property
    def Azimuth(self) -> float: # TODO: Convert to actual azimuth
        # Implementation here
        return -1
    
    @property
    def RA(self) -> float:
        self._lock.acquire()
        res = self._RA
        self._lock.release()
        return res
    @RA.setter
    def RA(self, ra: float) -> None:
        self._lock.acquire()
        self._RA = ra
        self._lock.release()
        self.logger.debug(f'[RA] {str(ra)}')
    
    @property
    def RA_Rate(self) -> float:# NOTE: Returns rate as arc"/sidereal second
        self._lock.acquire()
        res = self._RA_rate
        self._lock.release()
        return res
    @RA_Rate.setter
    def RA_Rate(self, rate: float) -> None:
        self._lock.acquire()
        self._RA_rate = rate
        self._lock.release()
        self.logger.debug(f'[RA rate] {str(rate)}')
    
    @property
    def RAGuideRate(self) -> float:
        self._lock.acquire()
        res = self._guide_RA_rate
        self._lock.release()
        return res
    @RAGuideRate.setter
    def RAGuideRate(self, rate: float) -> None:
        self._lock.acquire()
        self._guide_RA_rate = rate
        self._lock.release()
        self.logger.debug(f'[RA guide rate] {str(rate)}')

        
    @property
    def DEC(self) -> float:# NOTE: Returns rate as arc"/sidereal second
        self._lock.acquire()
        res = self._DEC
        self._lock.release()
        return res
    @DEC.setter
    def DEC(self, dec: float) -> None:
        self._lock.acquire()
        self._DEC = dec
        self._lock.release()
        self.logger.debug(f'[DEC] {str(dec)}')

    @property
    def DEC_Rate(self) -> float:
        self._lock.acquire()
        res = self._DEC_rate
        self._lock.release()
        return res
    @DEC_Rate.setter
    def DEC_Rate(self, rate: float) -> None:
        self._lock.acquire()
        self._DEC_rate = rate
        self._lock.release()
        self.logger.debug(f'[DEC rate] {str(rate)}')
    
    @property
    def DECGuideRate(self) -> float:
        self._lock.acquire()
        res = self._guide_DEC_rate
        self._lock.release()
        return res
    @DECGuideRate.setter
    def DECGuideRate(self, rate: float) -> None:
        self._lock.acquire()
        self._guide_DEC_rate = rate
        self._lock.release()
        self.logger.debug(f'[DEC guide rate] {str(rate)}')

    @property
    def Slewing(self) -> bool:
        self._lock.acquire()
        res = self._slewing
        self._lock.release()
        return res

    @property
    def Tracking(self) -> bool:
        self._lock.acquire()
        res = self._is_tracking
        self._lock.release()
        return res
    @Tracking.setter
    def Tracking(self, tracking: bool) -> None:
        self._lock.acquire()
        self._is_tracking = tracking
        #TODO : start tracking method if tracking is True
        self._lock.release()
        self.logger.debug(f'[Tracking] {str(tracking)}')

    @property
    def TrackingRate(self) -> float:
        self._lock.acquire()
        res = self._tracking_rate
        self._lock.release()
        return res
    @TrackingRate.setter
    def TrackingRate(self, rate: float) -> None:
        self._lock.acquire()
        self._tracking_rate = rate
        self._lock.release()
        self.logger.debug(f'[Tracking rate] {str(rate)}')
    
    @property
    def PulseGuiding(self) -> bool:
        self._lock.acquire()
        res = self._is_pulse_guiding
        self._lock.release()
        return res
    
    @property
    def TrackingRates(self) -> list[DriveRates]:
        return [rate for rate in DriveRates]
    
    @property
    def AtHome(self) -> bool:
        self._lock.acquire()
        res = self._at_home
        self._lock.release()
        return res

    @property
    def AtPark(self) -> bool:
        self._lock.acquire()
        res = self._at_park
        self._lock.release()
        return res
  
    @property
    def SideOfPier(self) -> PierSide:
        self._lock.acquire()
        res = self._side_of_pier
        self._lock.release()
        return res
    @SideOfPier.setter
    def SideOfPier(self, side) -> None:
        self._lock.acquire()
        self._side_of_pier = side
        self._lock.release()
        self.logger.debug(f'[Side of pier] {str(side)}')
    
    @property
    def TargetRightAscension(self) -> float:
        self._lock.acquire()
        res = self._target_ra
        self._lock.release()
        return res
    @TargetRightAscension.setter
    def TargetRightAscension(self, ra: float) -> None:
        self._lock.acquire()
        self._target_ra = ra
        self._lock.release()
        self.logger.debug(f'[Target RA] {str(ra)}')

    @property
    def TargetDeclination(self) -> float:
        self._lock.acquire()
        res = self._target_declination
        self._lock.release()
        return res
    @TargetDeclination.setter
    def TargetDeclination(self, declination: float) -> None:
        self._lock.acquire()
        self._target_declination = declination
        self._lock.release()
        self.logger.debug(f'[Target declination] {str(declination)}')

    
    
    # ---------------------------------- Others ---------------------------------- #
    @property
    def SiderealTime(self) -> float:
        self._lock.acquire()
        res = self._sidereal_time
        self._lock.release()
        return res
    @SiderealTime.setter
    def SiderealTime(self, sidereal_time: float) -> None:
        self._lock.acquire()
        self._sidereal_time = sidereal_time
        self._lock.release()
        self.logger.debug(f'[Sidereal time] {str(sidereal_time)}')

    @property
    def UTCDate(self):
        self._lock.acquire()
        res = self._utc_date
        self._lock.release()
        return res
    @UTCDate.setter
    def UTCDate(self, utc_date) -> None:
        self._lock.acquire()
        self._utc_date = utc_date
        self._lock.release()
        self.logger.debug(f'[UTC date] {str(utc_date)}')
    # ---------------------------------------------------------------------------- #
    #                                    Methods                                   #
    # ---------------------------------------------------------------------------- #
    # ------------------------ Connection related methods ------------------------ #
    def Connect(self) -> None:
        self.logger.debug(f'[Connect]')
        self._connlock.acquire()
        if self._connected:
            self._connecting = False
            self._connlock.release()
            self.logger.debug(f'[Already connected]')
            return
        self._connecting = True
        self._connected = False
        self._connlock.release()
        self._timer = Timer(self._conn_time_sec, self._conn_complete)
        self._timer.name = 'Connect delay'
        # print('[connect] now start the timer')
        self._timer.start()

    def Disconnect(self) -> None:
        self.logger.debug(f'[Disconnect]')
        self._connlock.acquire()
        if not self._connected:
            self._connecting = False
            self._connlock.release()
            self.logger.debug(f'[Already disconnected]')
            return
        if self._is_moving:
            self._connlock.release()
            # Yes you could call Halt() but this is for illustration
            raise RuntimeError('Cannot disconnect while rotator is moving')
        self._connected = False
        self._connlock.release()

    def _conn_complete(self):
        self._connlock.acquire()
        self.logger.info('[connected]')
        self._connecting = False
        self._connected = True
        self._connlock.release()
    # --------------------------- Slew related methods --------------------------- #
    # Utilities
    def Park(self):
        # Implementation here
        pass
    def FindHome(self):
        # Implementation here
        pass

    def AbortSlew(self):
        # Implementation here
        pass

    def SlewToAltAz(self, Altitude: float, Azimuth: float, Duration: float = 0.0):
        # Implementation here
        pass

    def SlewToAltAzAsync(self, Altitude: float, Azimuth: float, Duration: float = 0.0):
        # Implementation here
        pass

    def SlewToAltAzSync(self, Altitude: float, Azimuth: float, Duration: float = 0.0):
        # Implementation here
        pass

    def SlewToCoordinates(self, RightAscension: float, Declination: float, Duration: float = 0.0):
        # Implementation here
        pass
    def SlewToCoordinatesAsync(self, RightAscension: float, Declination: float, Duration: float = 0.0):
        # Implementation here
        pass

    def SlewToTarget(self):
        # Implementation here
        pass

    def SlewToTargetAsync(self):
        # Implementation here
        pass

    def DestinationSideOfPier(self, ra, dec) -> PierSide:
        lst = get_lst()

        ha = lst - ra

        # Normalisation de HA entre -12 et +12 heures
        if ha < -12:
            ha += 24
        elif ha > 12:
            ha -= 24
        # Détermination du côté du pilier en fonction de HA
        if -6 <= ha <= 6:
            return PierSide.pierEast
        else:
            return PierSide.pierWest

    # -------------------------- Guiding relatedmethods -------------------------- #
    def PulseGuide(self, Direction, Duration):
        # Implementation here
        pass

    # ---------------------- Telescope parameters related methods --------------------- #
    def AxisRates(self, Axis:int) -> list[int]: # NOTE : Both axes have the same rates range
        """
        Retrieves the rates at which the telescope can be moved about the specified axis.

        Args:
            Axis (TelescopeAxes): The axis for which to retrieve the rates.

        Returns:
            List[DriveRates]: A collection of DriveRates objects representing the 
                              supported rates for the specified axis.
        """
        # Implement logic to return axis rates
        return [e.value for e in AxisRates]

    def CanMoveAxis(self, Axis:int) -> bool:
        """
        Indicates whether the telescope can move the requested axis.

        Args:
            Axis (TelescopeAxes): The axis to check for movement capability.

        Returns:
            bool: True if the axis can be moved, False otherwise.
        """
        # Implement logic to check if axis can be moved
        return False

    # ---------------------- Telescope state related method ---------------------- #
    def Unpark(self):
        """
        Unparks the mount.

        This method takes the telescope out of the parked state, allowing it to be slewed.
        """
        # Implement logic to unpark the telescope


    def SyncToCoordinates(self, RightAscension, Declination) -> None:
        """
        Syncs the telescope to the specified equatorial coordinates.

        This method instructs the telescope that it is pointing at the given coordinates.

        Args:
            RightAscension (float): The right ascension coordinate to sync to, in hours.
            Declination (float): The declination coordinate to sync to, in degrees.
        """
        self._RA = RightAscension
        self.Dec = Declination

    def SyncToAltAz(self, Altitude: float, Azimuth: float) -> None:
        """
        Syncs the telescope to the specified altitude and azimuth coordinates.
        
        This method instructs the telescope that it is pointing at the given altitude and azimuth coordinates.

        Args:
            Altitude (float): The altitude coordinate to sync to, in degrees.
            Azimuth (float): The azimuth coordinate to sync to, in degrees.
        """
        self._alt = Altitude
        self._az = Azimuth
        # TODO : Update telescope position

    def SyncToTarget(self) -> None:
        """
        Syncs the telescope to the current target.
        
        This method instructs the telescope to point at the current target.
        """
        # Implement logic to sync to target
        pass

    # --------------------------------- Utilities -------------------------------- #
    