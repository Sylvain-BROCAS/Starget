from threading import Timer, Lock

from serial import protocol_handler_packages
from telescope_enum import AlignmentModes
from telescope_enum import *
from utilities import *
from logging import Logger
from motor_control import MKSMotor
from config import Config
from datetime import datetime
import asyncio
from typing import Coroutine, Any
from astropy.time import Time as astropyTime

class TelescopeDevice:
    def __init__(self, logger:Logger):
        # Initialize telescope properties
        self.logger: Logger = logger
        self.name:str = 'Starget Mount Device'
        self._lock = Lock()
        self._connlock = Lock()
        self._timer = None

        # --------------------------------- Settings --------------------------------- #
        self.r = 100 # reduction ratio of the motor gear
        self.steps_rotation = 200 # steps per degree of the motor
        self.max_rpm: int = 10000 # maximum rotational speed in revolutions per minute
        self.microstepping = 32 # miccrostepping division factor
        # --------------------------- Telescope parameters --------------------------- #
        # Example, adjust as needed
        self._alignment_mode: AlignmentModes = AlignmentModes(Config.alignment_mode)
        self._equatorial_system = EquatorialCoordinateType(Config.equatorial_system)
        self._aperture_area: float = Config.aperture_area
        self._aperture_diameter: float = Config.aperture_diameter
        self._focal_length: float = Config.focal_length
        self._slew_settle_time_sec: float = Config.slew_settle_time
        self._tracking_rates: list[int] = [e.value for e in DriveRates]
        self._axis_rates: list[float] = Config.axis_rates
        self._site_latitude: float = Config.site_latitude
        self._site_longitude: float = Config.site_longitude 
        self._site_elevation: float = Config.site_elevation

        self._does_refraction: bool = Config.does_refraction
        self._can_find_home: bool = Config.can_find_home
        self._can_pulse_guide: bool = Config.can_pulse_guide
        self._can_set_guiderates: bool = Config.can_set_guide_rates
        self._can_set_park: bool = Config.can_set_park
        self._can_set_pierside: bool = Config.can_set_pier_side
        self._can_set_RA_rate: bool = Config.can_set_RA_rate
        self._can_set_DEC_rate: bool = Config.can_set_DEC_rate
        self._can_set_tracking: bool = Config.can_set_tracking
        self._can_slew: bool = Config.can_slew
        self._can_slew_async: bool = Config.can_slew_async
        self._can_slew_altaz: bool = Config.can_slew_AltAz
        self._can_slew_altaz_async: bool = Config.can_slew_AltAz_async
        self._can_sync: bool = Config.can_sync
        self._can_sync_altaz: bool = Config.can_sync_AltAz
        self._can_sync_to_target: bool = Config.can_sync_to_target
        self._can_park: bool = Config.can_park
        self._can_unpark: bool = Config.can_unpark

        self._conn_time_sec: float = 5   # Async connect delay

        # ----------------------------- Telescope status ----------------------------- #
        self._connected: bool = False
        self._connecting: bool = False
        self._sync_write_connected: bool = True

        self._RA: float = 0.0
        self._DEC: float = 0.0
        self._target_rightascension: float = 0.0
        self._target_declination: float = 0.0

        self._at_home: bool = False
        self._at_park: bool = False
        self._side_of_pier: PierSide = PierSide.pierUnknown

        self._is_tracking: bool = False
        self._is_pulse_guiding: bool = False
        self._is_moving: bool = False
        self._parked: bool = True
        self._slewing: bool = False

        self._target_ra: float = 0.0
        self._target_dec: float = 0.0
        self._RA_rate: float = 0.0 # ["/SI s]
        self._DEC_rate: float = 0.0 # ["/SI s]
        self._guide_RA_rate: float = 0.0
        self._guide_DEC_rate: float = 0.0
        self._tracking_rate: DriveRates = DriveRates.driveSidereal

        self._utc_date: str =  str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self._local_sidereal_time: float = 0.0

        # ----------------------------------- Setup ---------------------------------- #
        self._RA_motor = MKSMotor(is_RA_homed, "e0")
        self._DEC_motor = MKSMotor(is_DEC_homed, "e1")

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
    def connected (self, toconnect: bool):
        self._connlock.acquire()
        if (not toconnect) and self._connected and self._is_moving:
            self._connlock.release()
            # Yes you could call Halt() but this is for illustration
            raise RuntimeError('Cannot disconnect while telescope is moving')
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
    @connecting.setter
    def connecting(self, toconnect: bool) -> None:
        self._connlock.acquire()
        self._connecting = toconnect
        self._connlock.release()

    # --------------------------- Site properties --------------------------- #
    @property
    def SiteElevation(self) -> float:
        self._lock.acquire()
        res: float =  self._site_elevation
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
        res: float =  self._site_latitude
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
        res: float = self._site_longitude
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
        res: AlignmentModes = self._alignment_mode
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
        res: float = self._aperture_area
        self._lock.release()
        return res

    @property
    def ApertureDiameter(self) -> float:
        self._lock.acquire()
        res: float = self._aperture_diameter
        self._lock.release()
        return res

    @property
    def SlewSettleTime(self) -> float:
        self._lock.acquire()
        res: float = self._slew_settle_time_sec
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

    @property # NOTE : Useful ???
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

    @property # NOTE : Useful ???
    def StepPerSec(self) -> float:
        self._lock.acquire()
        res: float = self._steps_per_sec
        self._lock.release()
        return res
    @StepPerSec.setter
    def StepPerSec(self, steps_per_sec: int) -> None:
        self._lock.acquire()
        self._steps_per_sec = steps_per_sec
        self._lock.release()
        self.logger.debug(f'[Steps per second] {str(steps_per_sec)}')

    @property
    def AxisRates(self) -> list[float]:
        self._lock.acquire()
        res = self._axis_rates
        self._lock.release()
        return res
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
        res: bool = self._can_set_guiderates
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

    @property
    def CanSyncToTarget(self) -> bool:
        self._lock.acquire()
        res: bool = self._can_sync_to_target
        self._lock.release()
        return res
    # ----------------------------- Telescope status ----------------------------- #
    @property
    def Altitude(self) -> float:
        elevation = self.SiteElevation
        latitude = self.SiteLatitude
        longitude = self.SiteLongitude
        time = astropyTime.now()
        return convert_eq_to_altaz(self.RA, self.DEC, latitude, longitude, elevation, time)[0]

    @property
    def Azimuth(self) -> float:
        elevation = self.SiteElevation
        latitude = self.SiteLatitude
        longitude = self.SiteLongitude
        time = astropyTime.now()
        return convert_eq_to_altaz(self.RA, self.DEC, latitude, longitude, elevation, time)[1]
    
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
        self._tracking_rate = DriveRates(rate)
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
        res = get_local_sidereal_time(self.SiteLatitude, self.SiteLongitude, self.SiteElevation)
        self._lock.release()
        return res
    @SiderealTime.setter
    def SiderealTime(self, sidereal_time: float) -> None:
        self._lock.acquire()
        self._local_sidereal_time = sidereal_time
        self._lock.release()
        self.logger.debug(f'[Sidereal time] {str(sidereal_time)}')

    @property
    def UTCDate(self):
        self._lock.acquire()
        res = get_UTC_date()
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
        #print('[connect] now start the timer')
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
            self.AbortSlew()
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
    async def MoveAxis(self, axis:int, rate:float) -> None:
        if rate>0:
            dir = "CW"
        else:
            dir = "CCW"

        self._is_moving = True
        self._at_home = False
        self._at_park = False
        if axis == 'RA':
            await self._RA_motor.move_constant_speed(dir, abs(rate))
        elif axis == 'DEC':
            await self._DEC_motor.move_constant_speed(dir, abs(rate))

    async def Park(self) -> None:
        self.logger.info("Parking telescope...")
        self._is_moving = True
        tasks = [self._RA_motor.return_to_zero,
            self._DEC_motor.return_to_zero
        ]
        await asyncio.gather(*tasks)
        self._is_moving = False
        self._at_park = True
        self.logger.info("Telescope parked.")
    
    async def FindHome(self) -> None:
        self.logger.info("Finding home position...")
        tasks: list[Coroutine[Any, Any, None]] = [
            self._find_home_ra(),
            self._find_home_dec()
        ]
        await asyncio.gather(*tasks)
        self._at_home = True
        self.logger.info("Home position found.")

    async def _find_home_ra(self) -> None:
        await asyncio.to_thread(self._RA_motor.find_home)

    async def _find_home_dec(self):
        await asyncio.to_thread(self._DEC_motor.find_home)

    def AbortSlew(self):
        self.logger.info("Aborting slew...")
        self._RA_motor.stop()
        self._DEC_motor.stop()
        self._is_moving = False
        self.logger.info("Slew aborted.")

    def SlewToAltAz(self, Altitude: float, Azimuth: float, Duration: float = 0.0):# TODO : Not implemented yet
        # Implementation here
        pass

    def SlewToAltAzAsync(self, Altitude: float, Azimuth: float, Duration: float = 0.0):# TODO : Not implemented yet
        # Implementation here
        pass

    def SlewToAltAzSync(self, Altitude: float, Azimuth: float, Duration: float = 0.0):# TODO : Not implemented yet
        # Implementation here
        pass

    async def SlewToCoordinates(self, RightAscension: float, Declination: float):
        pass
    
    def SlewToCoordinatesAsync(self, RightAscension: float, Declination: float, Duration: float = 0.0):# TODO : Not implemented yet
        # Implementation here
        pass

    def SlewToTarget(self):# TODO : Not implemented yet
        # Implementation here
        pass

    def SlewToTargetAsync(self):# TODO : Not implemented yet
        # Implementation here
        pass

    def DestinationSideOfPier(self, ra:float, dec: float) -> PierSide:# TODO
        lst: float = get_lst()

        ha: float = lst - ra

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
    def PulseGuide(self, Direction, Duration):# TODO : Not implemented yet
        # Implementation here
        pass

    # ---------------------- Telescope parameters related methods --------------------- #
    def CanMoveAxis(self, Axis:int) -> bool:# NOTE : Can always move each axis
        """
        Indicates whether the telescope can move the requested axis.

        Args:
            Axis (TelescopeAxes): The axis to check for movement capability.

        Returns:
            bool: True if the axis can be moved, False otherwise.
        """
        axis = TelescopeAxes(Axis)

        # Implement logic to check if axis can be moved
        return True

    # ---------------------- Telescope state related method ---------------------- #
    def Unpark(self) -> None:
        """
        Unparks the mount.

        This method takes the telescope out of the parked state, allowing it to be slewed.
        """
        self._parked = False


    def SyncToCoordinates(self, RightAscension:float, Declination:float) -> None:
        """
        Syncs the telescope to the specified equatorial coordinates.

        This method instructs the telescope that it is pointing at the given coordinates.

        Args:
            RightAscension (float): The right ascension coordinate to sync to, in hours.
            Declination (float): The declination coordinate to sync to, in degrees.
        """
        self._RA:float = RightAscension
        self._DEC:float = Declination

    def SyncToAltAz(self, Altitude: float, Azimuth: float) -> None:# TODO : change time source
        """
        Syncs the telescope to the specified altitude and azimuth coordinates.
        
        This method instructs the telescope that it is pointing at the given altitude and azimuth coordinates.

        Args:
            Altitude (float): The altitude coordinate to sync to, in degrees.
            Azimuth (float): The azimuth coordinate to sync to, in degrees.
        """
        RA, DEC = convert_altaz_to_eq(Altitude, Azimuth, self._site_latitude, self._site_longitude, self._site_elevation, Time.now())
        self._RA = RA
        self._DEC = DEC

    def SyncToTarget(self) -> None:
        """
        Syncs the telescope to the current target.
        
        This method instructs the telescope to point at the current target.
        """
        # Implement logic to sync to target
        self._RA = self._target_ra
        self._DEC = self._target_dec

    # --------------------------------- Utilities -------------------------------- #
    