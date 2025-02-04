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

def is_RA_homed():
    pass

def is_DEC_homed():
    pass