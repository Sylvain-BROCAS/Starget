from astropy.coordinates import AltAz, FK5, EarthLocation
from astropy.units import m, deg # type: ignore
from astropy.time import Time

def read_pos_RA():
    # Implementation for reading RA position
    # NOTE range 0:+23.9999999999 hours
    pass

def read_pos_Dec():
    # Implementation for reading Dec position
    # NOTE range -90:+90 degrees
    pass

def get_lst() -> float:
    return 1

def get_UTC_date():
    """The UTC date/time of the telescope's internal clock in ISO 8601 format including 
    fractional seconds. The general format (in Microsoft custom date format style) is 
    yyyy-MM-ddTHH:mm:ss.fffffffZ, e.g. 2016-03-04T17:45:31.1234567Z or 
    2016-11-14T07:03:08.1234567Z. 
    Please note the compulsary trailing Z indicating the 'Zulu', UTC time zone."""
def move_to_pos(motor, position):
    pass

def is_RA_homed() -> bool:
    return False

def is_DEC_homed() -> bool:
    return True

def convert_altaz_to_eq(alt, az, latitude, longitude, elevation, time):
    # Définir la position du site
    location = EarthLocation(lat=latitude*deg, lon=longitude*deg, height=elevation*m)
    
    # Définir les coordonnées AltAz
    altaz = AltAz(alt=alt*deg, az=az*deg, location=location, obstime=time)
    
    # Convertir en équatorial
    equatorial = altaz.transform_to(FK5)
    
    # Retourner les valeurs RA et Dec
    return equatorial.ra.hour, equatorial.dec.degree