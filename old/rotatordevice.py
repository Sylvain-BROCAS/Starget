# =================================================================
# ROTATORDEVICE.PY - Poor-man's simulaton of a Rotator
# =================================================================
#
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# rotatordevice.py - Poor-man's simulation of a rotator
#
# Part of the AlpycaDevice Alpaca skeleton/template device driver
#
# This is only for demo purposes. It's extremely fragile, and should
# not be used as an example of a real device. Settings not remembered.
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
# 16-Dec-2022   rbd 0.1 Initial edit for Alpaca sample/template
# 18-Dec-2022   rbd 0.1 Type hints
# 19-Dec-2022   rbd 0.1 Add logic for IRotatorV3 offsets
# 24-Dec-2022   rbd 0.1 Logging
# 25-Dec-2022   rbd 0.1 Logging typing for intellisense
# 26-Dec-2022   rbd 0.1 Do not log within lock()ed sections
# 27-Dec-2022   rbd 0.1 MIT license and module header
# 15-Jan-2023   rbd 0.1 Documentation. No logic changes.
# 15-Feb-2024   rbd 0.6 Upgrade to Rotator V4 (Platform 7)
# 20-Feb-2024   rbd 0.7 Setting for Connected-Write to be sync or async
#
from threading import Timer
from threading import Lock
from logging import Logger

class RotatorDevice:
    """Simulated rotator device that does moves in separate Timer threads.

    Properties and  methods generally follow the Alpaca interface.
    Debug tracing here via (commented out) print() to avoid locking issues.
    Hopefully you are familiar with Python threading and the need to lock
    shared data items.

    **Mechanical vs Virtual Position**

    In this code 'mech' refers to the raw mechanical position. Note the
    conversions ``_pos_to_mech()`` and ``_mech_to_pos()``. This is where
    the ``Sync()`` offset is applied.

    """
    #
    # Only override __init_()  and run() (pydoc 17.1.2)
    #
    def __init__(self, logger: Logger):
        self._lock = Lock()
        self._connlock = Lock()
        self.name: str = 'device'
        self.logger = logger
        #
        # Rotator device constants
        #
        self._can_reverse: bool = True
        self._step_size: float = 1.0
        self._steps_per_sec: int = 6
        self._conn_time_sec: float = 5.0    # Async connect delay
        self._sync_write_connected = True
        #
        # Rotator device state variables
        #
        self._reverse = False
        self._mech_pos = 0.0
        self._tgt_mech_pos = 0.0
        self._pos_offset = 0.0      # TODO In real life this must be persisted
        self._is_moving = False
        self._connecting = False
        self._connected = False
        #
        # Rotator engine
        #
        self._timer: Timer = None
        self._interval: float = 1.0 / self._steps_per_sec
        self._stopped: bool = True
        #
        # Connect delay
        #
        self._conntimer: Timer = None

    def _pos_to_mech(self, pos: float) -> float:
        mech = pos - self._pos_offset
        if mech >= 360.0:
            mech -= 360.0
        if mech < 0.0:
            mech += 360.0
        return mech

    def _mech_to_pos(self, mech: float) -> float:
        pos = mech + self._pos_offset
        if pos >= 360.0:
            pos -= 360.0
        if pos < 0.0:
            pos += 360.0
        return pos

    def _conn_complete(self):
        self._connlock.acquire()
        self.logger.info('[connected]')
        self._connecting = False
        self._connected = True
        self._connlock.release()

    def start(self, from_run: bool = False) -> None:
        #print('[start]')
        self._lock.acquire()
        #print('[start] got lock')wo
        if from_run or self._stopped:
            self._stopped = False
            #print('[start] new timer')
            self._timer = Timer(self._interval, self._run)
            self._timer.name = 'Rotation step'
            #print('[start] now start the timer')
            self._timer.start()
            #print('[start] timer started')
            self._lock.release()
            #print('[start] lock released')
        else:
            self._lock.release()
            #print('[start] lock released')


    def _run(self) -> None:
        #print('[_run] (tmr expired) get lock')
        self._lock.acquire()
        #print(f'[_run] got lock : tgtmech={str(self._tgt_mech_pos)} mech={str(self._mech_pos)}')
        delta = self._tgt_mech_pos - self._mech_pos
        if delta < -180.0:
           delta += 360.0
        if delta >= 180.0:
           delta -= 360.0
        #print(f'[_run] final delta={str(delta)}')
        if abs(delta) > (self._step_size / 2.0):
            self._is_moving = True
            if delta > 0:
                #print('[_run] delta > 0 go positive')
                self._mech_pos += self._step_size
                if self._mech_pos >= 360.0:
                    self._mech_pos -= 360.0
            else:
                #print('[_run] delta < 0 go negative')
                self._mech_pos -= self._step_size
                if self._mech_pos < 0.0:
                    self._mech_pos += 360.0
            #print(f'[_run] new pos = {str(self._mech_to_pos(self._mech_pos))}')
        else:
            self._is_moving = False
            self._stopped = True
        self._lock.release()
        #print('[_run] lock released')
        if self._is_moving:
            #print('[_run] more motion needed, start another timer interval')
            self.start(from_run = True)

    def stop(self) -> None:
        self._lock.acquire()
        #print('[stop] Stopping...')
        self._stopped = True
        self._is_moving = False
        if self._timer is not None:
            self._timer.cancel()
        self._timer = None
        self._lock.release()

    #
    # Guarded properties
    #
    @property
    def can_reverse(self) -> bool:
        self._lock.acquire()
        res: bool =  self._can_reverse
        self._lock.release()
        return res
    @can_reverse.setter
    def can_reverse (self, reverse: bool):
        self._lock.acquire()
        self._can_reverse = reverse
        self._lock.release()

    @property
    def reverse(self) -> bool:
        self._lock.acquire()
        res =  self._reverse
        self._lock.release()
        return res
    @reverse.setter
    def reverse (self, reverse: bool):
        self._lock.acquire()
        self._reverse = reverse
        self._lock.release()

    @property
    def step_size(self) -> float:
        self._lock.acquire()
        res =  self._step_size
        self._lock.release()
        return res
    @step_size.setter
    def step_size (self, step_size: float):
        self._lock.acquire()
        self._step_size = step_size
        self._lock.release()

    @property
    def steps_per_sec(self) -> int:
        self._lock.acquire()
        res =  self._steps_per_sec
        self._lock.release()
        return res
    @steps_per_sec.setter
    def steps_per_sec (self, steps_per_sec: int):
        self._lock.acquire()
        self._steps_per_sec = steps_per_sec
        self._lock.release()

    @property
    def sync_write_connected(self) -> float:
        self._lock.acquire()
        res =  self._sync_write_connected
        self._lock.release()
        return res
    @sync_write_connected.setter
    def sync_write_connected (self, sync: float):
        self._lock.acquire()
        self._sync_write_connected = sync
        self._lock.release()

    @property
    def position(self) -> float:
        self._lock.acquire()
        res = self._mech_to_pos(self._mech_pos)
        self._lock.release()
        self.logger.debug(f'[position] {str(res)}')
        return res

    @property
    def mechanical_position(self) -> float:
        self._lock.acquire()
        res = self._mech_pos
        self._lock.release()
        self.logger.debug(f'[mech position] {str(res)}')
        return res

    @property
    def target_position(self) -> float:
        self._lock.acquire()
        res =  self._mech_to_pos(self._tgt_mech_pos)
        self._lock.release()
        self.logger.debug(f'[target_position] {str(res)}')
        return res

    @property
    def is_moving(self) -> bool:
        self._lock.acquire()
        res =  self._is_moving
        self.logger.debug(f'[is_moving] {str(res)}')
        self._lock.release()
        self.logger.debug(f'[is_moving] {str(res)}')
        return res

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
            raise RuntimeError('Cannot disconnect while rotator is moving')
        if toconnect:
            if (self.sync_write_connected):
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

    # =======
    # Methods
    # =======

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
            # Yes you could call Halt() but this is for illustration
            raise RuntimeError('Cannot disconnect while rotator is moving')
        self._connected = False
        self._connlock.release()

    # TODO - This is supposed to throw if the final position is outside 0-360, but WHICH position? Mech or user????
    #
    def Move(self, delta_pos: float) -> None:
        self.logger.debug(f'[Move] pos={str(delta_pos)}')
        self._lock.acquire()
        if self._is_moving:
            self._lock.release()
            raise RuntimeError('Cannot start a move while the rotator is moving')
        self._is_moving = True
        self._tgt_mech_pos = self._mech_pos + delta_pos - self._pos_offset
        if self._tgt_mech_pos >= 360.0:
            self._tgt_mech_pos -= 360.0
        if self._tgt_mech_pos < 0.0:
            self._tgt_mech_pos += 360.0
        self._lock.release()
        self.logger.debug(f'       targetpos={self._mech_to_pos(self._tgt_mech_pos)}')
        self.start()

    def MoveAbsolute(self, pos: float) -> None:
        self.logger.debug(f'[MoveAbs] pos={str(pos)}')
        self._lock.acquire()
        if self._is_moving:
            self._lock.release()
            raise RuntimeError('Cannot start a move while the rotator is moving')
        self._is_moving = True
        self._tgt_mech_pos = self._pos_to_mech(pos)
        self._lock.release()
        self.start()

    def MoveMechanical(self, pos: float) -> None:
        self._lock.acquire()
        if self._is_moving:
            self._lock.release()
            raise RuntimeError('Cannot start a move while the rotator is moving')
        self.logger.debug(f'[MoveMech] pos={str(pos)}')
        self._is_moving = True
        self._tgt_mech_pos = pos
        self._lock.release()
        self.start()

    def Sync(self, pos: float) -> None:
        self.logger.debug(f'[Sync] newpos={str(pos)}')
        self._lock.acquire()
        if self._is_moving:
            self._lock.release()
            raise RuntimeError('Cannot sync while rotator is moving')
        self._pos_offset = pos - self._mech_pos
        if self._pos_offset < -180.0:
           self._pos_offset += 360.0
        if self._pos_offset >= 180.0:
           self._pos_offset -= 360.0
        self._lock.release()

    def Halt(self) -> None:
        self.logger.debug('[Halt]')
        self.stop()
