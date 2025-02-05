from astropy.coordinates import AltAz, FK5, EarthLocation
from astropy.units import m, deg # type: ignore
from astropy.time import Time
import serial
import re

def read_pos_RA():
    # Implementation for reading RA position
    # NOTE range 0:+23.9999999999 hours
    pass

def read_pos_Dec():
    # Implementation for reading Dec position
    # NOTE range -90:+90 degrees
    pass

def get_lst(lat, lon):
    utc_time = get_UTC_date()
    location = EarthLocation(lat=lat*deg, lon=lon*deg)
    return utc_time.sidereal_time('apparent', longitude=location.lon).hour

def get_UTC_date():
    """The UTC date/time of the telescope's internal clock in ISO 8601 format including 
    fractional seconds. The general format (in Microsoft custom date format style) is 
    yyyy-MM-ddTHH:mm:ss.fffffffZ, e.g. 2016-03-04T17:45:31.1234567Z or 
    2016-11-14T07:03:08.1234567Z. 
    Please note the compulsary trailing Z indicating the 'Zulu', UTC time zone."""
    utc_time: Time = Time.now()
    return utc_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def is_RA_homed() -> bool:
    return False

def is_DEC_homed() -> bool:
    return True

def convert_altaz_to_eq(alt, az, longitude, latitude, elevation):
    time = get_lst(latitude, longitude)
    # Définir la position du site
    location = EarthLocation(lat=latitude*deg, lon=longitude*deg, height=elevation*m)
    
    # Définir les coordonnées AltAz
    altaz = AltAz(alt=alt*deg, az=az*deg, location=location, obstime=time)
    
    # Convertir en équatorial
    equatorial = altaz.transform_to(FK5)
    ra_float = equatorial.ra.deg
    dec_float = equatorial.dec.deg
    return ra_float, dec_float

def get_GPS():
    """reads nemea sentence, exctract lat, long, elevation and UTC date and time"""
    def get_GPS():

        # Open serial port
        ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
        ser.flush()

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').rstrip()
                if line.startswith('$GPGGA'):
                    parts = line.split(',')
                    if len(parts) > 9 and parts[6] == '1':  # Check for valid fix
                        lat = float(parts[2][:2]) + float(parts[2][2:]) / 60.0
                        if parts[3] == 'S':
                            lat = -lat
                        lon = float(parts[4][:3]) + float(parts[4][3:]) / 60.0
                        if parts[5] == 'W':
                            lon = -lon
                        elevation = float(parts[9])
                        utc_time = parts[1]
                        hours = int(utc_time[:2])
                        minutes = int(utc_time[2:4])
                        seconds = float(utc_time[4:])
                        return lat, lon, elevation, f"{hours:02}:{minutes:02}:{seconds:06.3f}Z"