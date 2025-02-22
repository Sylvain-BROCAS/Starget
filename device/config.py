# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# conf.py - Device configuration file and shared logger construction
# Part of the AlpycaDevice Alpaca skeleton/template device driver
#
# Author:   Robert B. Denny <rdenny@dc3.com> (rbd)
#
# Python Compatibility: Requires Python 3.7 or later
# GitHub: https://github.com/ASCOMInitiative/AlpycaDevice
#
# -----------------------------------------------------------------------------
# MIT License
#
# Copyright (c) 2022-2024 Bob Denny
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# -----------------------------------------------------------------------------
# Edit History:
# 24-Dec-2022   rbd 0.1 Logging
# 25-Dec-2022   rbd 0.1 More config items, separate logging section
# 27-Dec-2022   rbd 0.1 Move shared logger construction and global
#               var here. MIT license and module header. No mcast.
# 17-Feb-2024   ltf 0.6 GitHub PR #11 "docker friendly configuration"
#               https://github.com/ASCOMInitiative/AlpycaDevice/pull/11
#               (manually merged). Remove comment about "slimy hack".
# 20-Ferb-2024  rbd 0.7 Add sync_write_connected to control sync/async
#               write-Connected behavior.
#
import sys
import toml
import logging

_dict = {}
_dict = toml.load(f'{sys.path[0]}/config.toml')    # Errors here are fatal.
_dict2 = {}
try:
    # ltf - this file, if it exists can override or supplement definitions
    # in the normal config.toml. This facilitates putting the driver in a
    # docker container where installation specific configuration can be
    # put in a file that isn't pulled from a repository
    _dict2 = toml.load('/alpyca/config.toml')
except:
    _dict2 = {}
    # file is optional so it's ok if it isn't there

def get_toml(sect: str, item: str):
    setting = ''
    s = None
    try:
        setting = _dict2[sect][item]
    except:
        try:
            setting = _dict[sect][item]
        except:
            setting = ''
    return setting

_bools = ['true', 'false']                               # Only valid JSON bools allowed
def to_bool(str: str) -> bool:
    val = str.lower()
    if val not in _bools:
        return bool(val)
    else:
        return val == _bools[0]

class Config:
    """Device configuration. For docker based installation specific
        configuration, will first look for ``/alpyca/config.toml``
        and if exists, any setting there will override those in
        ``./config.toml`` (the default settings file).
    """
    # ---------------
    # Network Section
    # ---------------
    ip_address: str = get_toml('network', 'ip_address')
    port: int = int(get_toml('network', 'port'))
    # --------------
    # Server Section
    # --------------
    location: str = get_toml('server', 'location')
    verbose_driver_exceptions: bool = to_bool(get_toml('server', 'verbose_driver_exceptions'))
    # --------------
    # Device Section
    # --------------
    step_size: float = float(get_toml('device', 'step_size'))
    steps_per_sec: float = float(get_toml('device', 'steps_per_sec'))
    sync_write_connected: bool = to_bool(get_toml('device', 'sync_write_connected'))
    alignment_mode: int = int(get_toml('device', 'alignment_mode'))
    aperture_area: float = float(get_toml('device', 'aperture_area'))
    aperture_diameter: float = float(get_toml('device', 'aperture_diameter'))
    focal_length: float = float(get_toml('device', 'focal_length'))
    equatorial_system: int = int(get_toml('device', 'equatorial_system'))
    slew_settle_time: float = int(get_toml('device', 'slew_settle_time'))
    tracking_rates: list = list(get_toml('device', 'tracking_rates'))
    axis_rates: list = list(get_toml('device', 'axis_rates'))
    site_elevation: float = float(get_toml('device', 'site_elevation'))
    site_latitude: float = float(get_toml('device', 'site_latitude'))
    site_longitude: float = float(get_toml('device', 'site_longitude'))
    does_refraction: bool = to_bool(get_toml('device', 'does_refraction'))
    can_find_home: bool = to_bool(get_toml('device', 'can_find_home'))
    can_park: bool = to_bool(get_toml('device', 'can_park'))
    can_unpark: bool = to_bool(get_toml('device', 'can_unpark'))
    can_set_park: bool = to_bool(get_toml('device', 'can_set_park'))
    park_pos: list = list(get_toml('device', 'park_pos'))
    can_set_DEC: bool = to_bool(get_toml('device', 'can_set_DEC'))
    can_set_RA: bool = to_bool(get_toml('device', 'can_set_RA'))
    can_set_DEC_rate: bool = to_bool(get_toml('device', 'can_set_DEC_rate'))
    can_set_RA_rate: bool = to_bool(get_toml('device', 'can_set_RA_rate'))
    can_move_axis: bool = to_bool(get_toml('device', 'can_move_axis'))
    can_slew: bool = to_bool(get_toml('device', 'can_slew'))
    can_slew_async: bool = to_bool(get_toml('device', 'can_slew_async'))
    can_slew_AltAz: bool = to_bool(get_toml('device', 'can_slew_AltAz'))
    can_slew_AltAz_async: bool = to_bool(get_toml('device', 'can_slew_AltAz_async'))
    can_set_tracking: bool = to_bool(get_toml('device', 'can_set_tracking'))
    can_set_sidereal_rate: bool = to_bool(get_toml('device', 'can_set_sidere)al_rate'))
    can_pulse_guide: bool = to_bool(get_toml('device', 'can_pulse_guide'))
    can_set_guide_rates: bool = to_bool(get_toml('device', 'can_set_guide_rates'))
    can_sync: bool = to_bool(get_toml('device', 'can_sync'))
    can_sync_AltAz: bool = to_bool(get_toml('device', 'can_sync_AltAz'))
    can_sync_to_target: bool = to_bool(get_toml('device', 'can_sync_to_target'))
    can_set_pier_side: bool = to_bool(get_toml('device', 'can_set_pier_side'))
    
    # ---------------
    # Logging Section
    # ---------------
    log_level: int = logging.getLevelName(get_toml('logging', 'log_level'))  # Not documented but works (!!!!)
    log_to_stdout: str = get_toml('logging', 'log_to_stdout')
    max_size_mb: int = int(get_toml('logging', 'max_size_mb'))
    num_keep_logs: int = int(get_toml('logging', 'num_keep_logs'))
