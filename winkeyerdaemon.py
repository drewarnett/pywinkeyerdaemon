#!/usr/bin/env python3

"""
pywinkeyerdaemon

Use "winkeyerdaemon --help" for help.

Just like cwdaemon, this listens for UDP messages.  However, it supports
winkeyer or winkeyer compatible keyer hardware only.

See README.md for more information.

See https://github.com/drewarnett/pywinkeyerdaemon for even more information.
"""

import string
import socketserver
import argparse
import atexit

import serial


_LOCALHOST_ADDRESS = "127.0.0.1"
_DEFAULT_PORT = 6789

ESC = chr(27)

WK_SIDETONE_CODES = {
    4000:  0x1,
    2000:  0x2,
    1333:  0x3,
    1000:  0x4,
    800:  0x5,
    666:  0x6,
    571:  0x7,
    500:  0x8,
    444:  0x9,
    400:  0xa}

WK_SIDETONE_FREQUENCIES = tuple(sorted(WK_SIDETONE_CODES))


def wk_sidetone_code(freq):

    assert isinstance(freq, int), (type(freq), freq)
    chosen_freq = None
    min_freq = min(WK_SIDETONE_FREQUENCIES)
    max_freq = max(WK_SIDETONE_FREQUENCIES)
    if freq <= min_freq:
        chosen_freq = min_freq
    elif freq >= max_freq:
        chosen_freq = max_freq
    else:
        for i, current_freq in enumerate(WK_SIDETONE_FREQUENCIES[:-1]):
            next_freq = WK_SIDETONE_FREQUENCIES[i + 1]
            if freq < next_freq:
                if freq - current_freq < next_freq - freq:
                    chosen_freq = current_freq
                else:
                    chosen_freq = next_freq
                break
    return WK_SIDETONE_CODES[chosen_freq]


WK_ULTIMATIC_PRIORITY_CODES = {
    'normal':  0b00,
    'dahs':  0b01,
    'dits':  0b10
    }

WK_ULTIMATIC_PRIORITIES = tuple(WK_ULTIMATIC_PRIORITY_CODES)

WK_HANG_TIME_CODES = {
    1:  0b00,
    2:  0b01,
    4:  0b10,
    8:  0b11}

WK_HANG_TIMES = tuple(sorted(WK_HANG_TIME_CODES))

# K[12]_ENABLE bit field per example WinKyer USB and WK3 documentation  :-)
WK_PINCONFIG_KEY_BITS = {   # [corrected][key]
    False:  {
        1:  2,
        2:  3},
    True:  {
        1:  3,
        2:  2}}


class WinKeyer():
    """singleton handler for a WinKeyer

    methods are specific to use as a cwdaemon
    """

    SUPPORTED_VERSIONS = (23, 30, 31)

    def __init__(
            self,
            serial_device=None,
            corrected=False, debug=False, set_pinconfig=True):

        assert isinstance(corrected, bool), (type(corrected), corrected)
        assert isinstance(debug, bool), (type(debug), debug)

        self._corrected = corrected
        self._debug = debug
        self.port = serial.Serial(serial_device, 1200)
        self.host_open()
        self._sidetone_enable = True
        self._key1_enable = True
        self._key2_enable = False
        self._ptt_enable = False
        self._ultimatic_priority = 'normal'
        self._hang_time = 1
        self._lead_time = 0
        self._tail_time = 0
        if set_pinconfig:
            self._set_pinconfig()

    def printdbg(self, s):
        if self._debug:
            print(s)

    def host_open(self):
        self.host_close()
        self.port.flushInput()
        self.port.timeout = 1
        self.port.write((chr(0x0) + chr(0x2)).encode())
        version = ord(self.port.read(1).decode())
        self.printdbg("host_open returned:  " + str(version))
        assert version in self.SUPPORTED_VERSIONS, version
        self.port.timeout = 0.1
        atexit.register(self.host_close)

    def host_close(self):
        self.port.write((chr(0x0) + chr(0x3)).encode())

    def set_speed(self, speed):
        assert 0 <= speed <= 99
        self.port.write((chr(0x2) + chr(speed)).encode())

    def abort(self):
        self.port.write(chr(0xa).encode())

    def send(self, msg):
        self.port.write(msg.upper().encode())

    def tune(self, seconds):
        """key down for given seconds

        Anything buffered is aborted.
        """

        assert isinstance(seconds, int), type(seconds)
        assert 0 <= seconds <= 99, seconds

        self.abort()
        self.port.write((chr(0x19) + chr(seconds)).encode())

    def set_first_extension(self, extension):
        """set extension of first keying element

        Note:  not implemented in WK3 v30 firmware.

        extension:  0 to 250 milliseconds (default 0)
        """

        assert isinstance(extension, int), (type(extension), extension)
        assert 0 <= extension <= 250, extension

        self.port.write((chr(0x10) + chr(extension)).encode())

    def set_key_compensation(self, compensation):
        """set key compensation

        extends key time for all elements

        compensation:  0 to 250 milliseconds (default 0)
        """

        assert isinstance(compensation, int), (
            type(compensation), compensation)
        assert 0 <= compensation <= 250, compensation

        self.port.write((chr(0x11) + chr(compensation)).encode())

    def set_weighting(self, weighting):
        """set weighting for keying

        weighting:  % weighting (int) 10 to 90
        """

        assert isinstance(weighting, int), (type(weighting), weighting)

        if not 10 <= weighting <= 90:
            self.printdbg(
                "weighting value given ({}) out of 10 to 90 % range".format(
                    weighting))
        if weighting < 10:
            weighting = 10
        if weighting > 90:
            weighting = 90

        self.port.write((chr(0x03) + chr(weighting)).encode())

    def _set_ptt_lead_tail_time(self, lead_time=None, tail_time=None):
        """set PTT lead and tail times (in milliseconds)

        lead_time:  PTT assert to key down from 0 to 250 in 10 ms steps (int)

        tail_time:  key up to PTT release from 0 to 250 in 10 ms steps (int)
        """

        VALID_STEPS = tuple(range(0, 250 + 10, 10))

        if lead_time is not None:
            assert isinstance(lead_time, int), (type(lead_time), lead_time)
            assert lead_time in VALID_STEPS, lead_time
            self._lead_time = lead_time
        if tail_time is not None:
            assert isinstance(tail_time, int), (type(tail_time), tail_time)
            assert tail_time in VALID_STEPS, tail_time
            self._tail_time = tail_time

        self.port.write((
            chr(0x04)
            + chr(self._lead_time//10) + chr(self._tail_time//10)).encode())

    def set_lead_time(self, lead_time):
        """set lead time

        lead_time:  PTT assert to key down from 0 to 250 in 10 ms steps (int)
        """

        self._set_ptt_lead_tail_time(lead_time=lead_time)

    def set_tail_time(self, tail_time):
        """set tail time

        Note:  applies to machine sent code, not hand sent.

        tail_time:  key up to PTT release from 0 to 250 in 10 ms steps (int)
        """

        self._set_ptt_lead_tail_time(tail_time=tail_time)

    def assert_ptt(self, ptt):
        """assert PTT

        Note:  buffered.

        Note:  this is manual control of PTT without keying.  See elsewhere
               for normal, automatic PTT.  Doesn't function if normal,
               automatic PTT is enabled.
        """

        if ptt:
            self.port.write((chr(0x18) + chr(1)).encode())
        else:
            self.port.write((chr(0x18) + chr(0)).encode())

    def _set_pinconfig(
            self,
            sidetone_enable=None,
            key1_enable=None,
            key2_enable=None,
            ptt_enable=None,
            ultimatic_priority=None,
            hang_time=None):
        """set pinconfig register

        sidetone_enable:  (bool, default False)

        ptt_enable:  (bool, default False)

        ultimatic_priority:  'normal' (default), 'dits', or 'dahs'

        hang_time:  1 (default), 2, 4, or 8 dits + 1 word space PTT hang time
        """

        assert isinstance(sidetone_enable, (bool, type(None))), (
            type(sidetone_enable), sidetone_enable)
        assert isinstance(key1_enable, (bool, type(None))), (
            type(key1_enable), key1_enable)
        assert isinstance(key2_enable, (bool, type(None))), (
            type(key2_enable), key2_enable)
        assert isinstance(ptt_enable, (bool, type(None))), (
            type(ptt_enable), ptt_enable)
        assert isinstance(ultimatic_priority, (str, type(None))), (
            type(ultimatic_priority), ultimatic_priority)
        assert isinstance(hang_time, (int, type(None))), (
            type(hang_time), hang_time)

        if sidetone_enable is not None:
            self._sidetone_enable = sidetone_enable

        if key1_enable is not None:
            self._key1_enable = key1_enable

        if key2_enable is not None:
            self._key2_enable = key2_enable

        if ptt_enable is not None:
            self._ptt_enable = ptt_enable

        if ultimatic_priority is not None:
            assert ultimatic_priority in WK_ULTIMATIC_PRIORITIES, (
                ultimatic_priority)
            self._ultimatic_priority = ultimatic_priority

        if hang_time is not None:
            assert hang_time in WK_HANG_TIMES, hang_time
            self._hang_time = hang_time

        upc = WK_ULTIMATIC_PRIORITY_CODES[self._ultimatic_priority]

        key1_enable_bit = WK_PINCONFIG_KEY_BITS[self._corrected][1]
        key2_enable_bit = WK_PINCONFIG_KEY_BITS[self._corrected][2]

        data = (
            ((upc & 0b11) << 6)
            | ((WK_HANG_TIME_CODES[self._hang_time] & 0b11) << 4)
            | ((int(self._key2_enable) & 0b1) << key2_enable_bit)
            | ((int(self._key1_enable) & 0b1) << key1_enable_bit)
            | ((int(self._sidetone_enable) & 0b1) << 1)
            | ((int(self._ptt_enable) & 0b1) << 0))

        self.port.write((chr(0x09) + chr(data)).encode())

    def set_key1_enable(self, enable):
        """set key 1 enable"""

        self._set_pinconfig(key1_enable=enable)

    def set_key2_enable(self, enable):
        """set key 2 enable"""

        self._set_pinconfig(key2_enable=enable)

    def set_ultimatic_priority(self, ultimatic_priority):
        """set ultimatic mode priority

        ultimatic_priority:  'normal' (default), 'dits', or 'dahs'
        """

        self._set_pinconfig(ultimatic_priority=ultimatic_priority)

    def set_hang_time(self, hang_time):
        """set hang time

        Note:  applies to hand sent code, not machine sent.

        hang_time:  1 (default), 2, 4, 8 dits + 1 word space PTT hang time
        """

        self._set_pinconfig(hang_time=hang_time)

    def set_ptt_enable(self, enable):
        """set PTT enable

        Note:  this is automatic PTT that happens during keying.  See elsewhere
               for manual PTT.
        """

        if self._ptt_enable:
            self.printdbg(
                "Manual PTT doesn't work when normal, automatic PTT is"
                " enabled.")
        self._set_pinconfig(ptt_enable=enable)

    def set_sidetone_enable(self, enable):
        assert isinstance(enable, bool), (type(enable), enable)
        self._set_pinconfig(sidetone_enable=enable)

    def set_sidetone_frequency(self, frequency):
        """set sidetone to nearest frequency supported by WinKeyer

        frequency:  int (Hz)
        """

        code = wk_sidetone_code(frequency)
        self.port.write((chr(0x01) + chr(code)).encode())

    def set_winkeyer_mode(
            self,
            swap=False,
            keying_mode='B',
            contest_spacing=False,
            autospace=False):
        """set WinkeyerMode register which packs a number of things

        swap:  swap paddles (swap di and dah) (bool, default False)

        keying mode:  'B' (default), 'A', 'U' (ultimatic), or 'B' (bug)

        contest_spacing:  use contest spacing (bool, default False)

        autospace:  autospace feature (bool, default False)
        """

        KEYING_CODES = {
            'B':  0b00,
            'A':  0b01,
            'ultimatic':  0b10,
            'bug':  0b11}

        assert isinstance(swap, bool), (type(swap), swap)
        assert keying_mode in KEYING_CODES, keying_mode
        assert isinstance(contest_spacing, bool), (
            type(contest_spacing), contest_spacing)
        assert isinstance(autospace, bool), (type(autospace), autospace)

        data = (
            ((KEYING_CODES[keying_mode] & 0b11) << 4)
            | ((int(swap) & 0b1) << 3)
            | ((int(autospace) & 0b1) << 1)
            | ((int(contest_spacing) & 0b1) << 0)
            )
        self.port.write((chr(0x0E) + chr(data)).encode())


def _expand_cwdaemon_prosigns_for_winkeyer(s):
    """returns string with cwdaemon prosigns expanded for winkeyer"""

    MERGE_LETTERS = "\x1b"
    TABLE = {
        '*':  "AR",
        '=':  "BT",
        '<':  "SK",
        '(':  "KN",
        '!':  "SN",
        '&':  "AS",
        '>':  "BK"
        }

    rval = ""
    for c in s:
        if c in TABLE:
            rval += MERGE_LETTERS + TABLE[c]
        else:
            rval += c
    return rval


def winkeyer_weighting(cwdaemon_value):
    """return cwdaemon weighting valueto WinKeyer weighting

    WinKeyer uses 10 to 90 (int).

    cwdaemon uses -50 to 50 (int).

    TODO:  research what the cwdaemon values mean and alter mapping if
           appropriate to better mimic cwdaemon.
    """

    assert isinstance(cwdaemon_value, int), (
        type(cwdaemon_value), cwdaemon_value)
    assert -50 <= cwdaemon_value <= 50, cwdaemon_value

    wk_value = int(cwdaemon_value*(90 - 10)/(50 - -50)) + 50
    return wk_value


class CwdaemonServer(socketserver.BaseRequestHandler):
    """singleton cwdaemon using a singleton winkeyer"""

    _debug = False

    def printdbg(self, s):
        if self._debug:
            print(s)

    def verify_request(self, request, client_address):
        if accept_remote:
            return True
        elif client_address == _LOCALHOST_ADDRESS:
            return True
        else:
            return False

    def handle(self):

        WHITESPACE_TO_STRIP = string.whitespace.replace(' ', '')

        data = self.request[0].decode()

        # NOTE:  some clients send more data than required!

        if chr(0) in data:
            self.printdbg("Warning:  chr(0) in client message")
            data = data[:data.index(chr(0))]

        if data[0] == ESC:
            if data[1] == '0':
                self.printdbg("Warning:  'set defaults' not implemented.")
            elif data[1] == '2':
                speed = data[2:]
                self.printdbg("set speed:  {}".format(speed))
                set_speed(int(speed))
                winkeyer.set_speed(int(speed))
            elif data[1] == '3':
                tone = data[2:]
                self.printdbg("set tone:  {}".format(tone))
                self.printdbg(data[2:])
                if (tone < 300 or tone > 1000):
                    self.printdbg('cwdaemon docs say 300 to 100 Hz')
                    self.printdbg('    but unixcw defines actual range')
                tone = int(tone)
                if tone == 0:
                    winkeyer.set_sidetone_enable(False)
                else:
                    winkeyer.set_sidetone_frequency(tone)
                    winkeyer.set_sidetone_enable(True)
            elif data[1] == '4':
                self.printdbg("abort message")
                winkeyer.abort()
            elif data[1] == '5':
                self.printdbg("Warning:  'exit daemon' not implemented.")
            elif data[1] == '6':
                self.printdbg(
                    "Warning:  'set uninterruptible word mode'"
                    " not implemented.")
            elif data[1] == '7':
                weighting = data[2:]
                self.printdbg("cwdaemon weighting:  {}".format(weighting))
                weighting = int(weighting)
                if -50 <= weighting <= 50:
                    winkeyer.set_weighting(winkeyer_weighting(weighting))
                else:
                    self.printdbg("weighting out of range (-50 to 50)")
            elif data[1] == '8':
                self.printdbg(
                    "Warning:  'set device for keying' not implemented.")
            elif data[1] == '9':
                self.printdbg("Warning:  obsolete cwdaemon command.")
            elif data[1] == 'a':
                ptt = data[2:]
                if ptt not in ("0", "1"):
                    self.printdbg(
                        "Warning:  "
                        "unsupported value for 'ptt keying off or on'")
                else:
                    if get_delay() > 0:
                        self.printdbg(
                            "Cannot set PTT.  ptt keying disabled by delay"
                            " != 0.")
                    else:
                        if ptt == "0":
                            if get_ptt():
                                winkeyer.assert_ptt(False)
                                set_ptt(False)
                        else:
                            if not get_ptt():
                                winkeyer.assert_ptt(True)
                                set_ptt(True)
            elif data[1] == 'b':
                self.printdbg(
                    "Warning:  'ssb signal from microphone or soundcard'"
                    " not implemented.")
            elif data[1] == 'c':
                seconds = int(data[2:])
                if 0 <= seconds <= 99:
                    if seconds:
                        self.printdbg("tune for {} seconds".format(seconds))
                        if seconds > 10:
                            self.printdbg(
                                "allowing longer tune than cwdaemon's"
                                " 10 second max")
                        winkeyer.tune(seconds)
                    else:
                        self.printdbg("tune for 0 seconds ignored")
                else:
                    self.printdbg(
                        "tune for {} seconds out of range"
                        " 0 to 99 seconds".format(seconds))
            elif data[1] == 'd':
                # TODO:  implement range check.  CW daemon uses 0 to 50 and
                #        truncates into range.
                # Note:  use 0/nonzero to enable/disable manual PTT
                # Note:  use 0/nonzero to disable/enable auto PTT?
                # Note:  Do not want to use to adjust PTT lead time.
                delay = data[2:]
                self.printdbg("set delay:  {}".format(delay))
                set_delay(int(delay))
                self.printdbg("delay set to:  {:d}".format(get_delay()))
                self.printdbg(
                    "have not implemented cwdaemon delay functionality")
            elif data[1] == 'e':
                self.printdbg("Warning:  'bandindex' not implemented.")
            elif data[1] == 'f':
                self.printdbg("Warning:  'set sound device' not implemented.")
            elif data[1] == 'g':
                self.printdbg(
                    "Warning:  'set soundcard volume' not implemented.")
            elif data[1] == 'h':
                self.printdbg("Warning:  'echo when done' not implemented.")
        else:
            self.printdbg("message:  {}".format(repr(data)))
            if data.rstrip(WHITESPACE_TO_STRIP) != data:
                self.printdbg(
                    "message trailing whitespace (not including ' ') removed")
                data = data.rstrip(WHITESPACE_TO_STRIP)
            self.printdbg("message:  {}".format(repr(data)))

            winkeyer_data = _expand_cwdaemon_prosigns_for_winkeyer(data)
            if winkeyer_data != data:
                data = winkeyer_data
                self.printdbg("prosigns expanded")
                self.printdbg("message:  {}".format(repr(data)))

            CANCEL_BUFFERED_SPEED_CHANGE = "\x1e"
            BUFFERED_SPEED_CHANGE = "\x1c"
            MIN_SPEED, MAX_SPEED = 5, 99
            speed_message_data = ""
            speed = orig_speed = get_speed()
            if '+' in data or '-' in data:
                for nextchar in data:
                    if nextchar == '+':
                        if speed:
                            if speed > MAX_SPEED - 2:
                                speed = MAX_SPEED
                            else:
                                speed += 2
                            speed_message_data += (
                                BUFFERED_SPEED_CHANGE + chr(speed))
                    elif nextchar == '-':
                        if speed:
                            if speed < MIN_SPEED + 2:
                                speed = MIN_SPEED
                            else:
                                speed -= 2
                            speed_message_data += (
                                BUFFERED_SPEED_CHANGE + chr(speed))
                    else:
                        speed_message_data += nextchar
                if speed:
                    # messages won't leave speed modified
                    speed = orig_speed
                    speed_message_data += CANCEL_BUFFERED_SPEED_CHANGE
                    self.printdbg(
                        "cwdaemon +/- speed controls expanded/translated")
                else:
                    self.printdbg(
                        "speed not set, yet,"
                        " so cwdaemon +/- speed controls ignored")
                data = speed_message_data
                self.printdbg("message:  {}".format(repr(data)))

            winkeyer.send(data)


class CwdaemonServerDebug(CwdaemonServer):
    """CwdameonServer with debugging enabled"""

    _debug = True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--device", nargs="?",
        help="device file on unix, ex. /dev/ttyS0, and device name on"
             " MS-Windows, ex. COM1",
        type=str, required=True)
    parser.add_argument(
        "-p", "--port", nargs="?",
        help="network port to listen (default {})".format(_DEFAULT_PORT),
        type=int, default=_DEFAULT_PORT)
    parser.add_argument(
        "--accept-remote-hosts",
        help="respond to requests from hosts other than localhost (default"
             " localhost only)",
        action="store_true")
    sidetone_group = parser.add_mutually_exclusive_group()
    sidetone_group.add_argument(
        "--sidetone-on",
        help="start with sidetone on (default off) using default frequency",
        action="store_true")
    sidetone_group.add_argument(
        "--sidetone",
        help="start with sidetone on (default off) using given frequency",
        type=int)
    parser.add_argument(
        "--swap",
        help="swap paddles (swap di and dah) (default off)",
        action="store_true")
    key_group = parser.add_mutually_exclusive_group()
    key_group.add_argument(
        "--key2",
        help="use KEY2 output instead of default KEY1",
        action="store_true")
    key_group.add_argument(
        "--key12",
        help="use KEY1 and KEY2 output instead of default KEY1",
        action="store_true")
    parser.add_argument(
        "--contest_spacing",
        help="use contest spacing (6 dit wordspace, default 7)",
        action="store_true")
    parser.add_argument(
        "--autospace",
        help="use autospace paddle sending (default off)",
        action="store_true")
    parser.add_argument(
        "--first_extension",
        help="extends first element 0 to 250 milliseconds (default 0)",
        type=int)
    parser.add_argument(
        "--key_compensation",
        help="extends key time for all elements 0 to 250 milliseconds"
             " (default 0)",
        type=int)
    parser.add_argument(
        "--ptt_enable",
        help="enable automatic PTT (default off)",
        action="store_true")
    parser.add_argument(
        "--ptt_lead",
        help="PTT assert to key down lead time from 0 to 250 in 10 ms steps",
        type=int)
    parser.add_argument(
        "--ptt_tail",
        help="key up to PTT release tail time from 0 to 250 in 10 ms steps"
             " Note:  applies to machine sent code only.",
        type=int)
    parser.add_argument(
        "--hang",
        help="1, 2, 4, or 8 dits + 1 word space PTT hang time (default 1)"
             " Note:  applies to hand sent code only.",
        type=int, choices=WK_HANG_TIMES)
    parser.add_argument(
        "--debug",
        help="print debug statements to standard output",
        action="store_true")

    args = parser.parse_args()

    state_delay = 0
    state_ptt = False
    state_speed = 0

    def set_delay(delay):
        global state_delay
        state_delay = delay

    def get_delay():
        global state_delay
        return state_delay

    def set_ptt(ptt):
        global state_ptt
        state_ptt = ptt

    def get_ptt():
        global state_ptt
        return state_ptt

    def set_speed(speed):
        global state_speed
        state_speed = speed

    def get_speed():
        global state_speed
        return state_speed

    accept_remote = args.accept_remote_hosts
    if accept_remote:
        print("Warning:  listening to nonlocal hosts as well as localhost.")
    winkeyer = WinKeyer(args.device, debug=args.debug)

    assert not hasattr(args, 'key1') and hasattr(args, 'key12')
    if args.key2:
        winkeyer.set_key1_enable(False)
        winkeyer.set_key2_enable(True)
    if args.key12:
        winkeyer.set_key1_enable(True)
        winkeyer.set_key2_enable(True)

    if args.sidetone is not None:
        winkeyer.set_sidetone_frequency(args.sidetone)
        winkeyer.set_sidetone_enable(True)
    else:
        winkeyer.set_sidetone_enable(args.sidetone_on)
    winkeyer.set_winkeyer_mode(
        swap=args.swap,
        contest_spacing=args.contest_spacing,
        autospace=args.autospace)
    if args.key_compensation is not None:
        winkeyer.set_first_extension(args.key_compensation)
    if args.first_extension is not None:
        winkeyer.set_first_extension(args.first_extension)
    if args.ptt_lead:
        winkeyer.set_lead_time(args.ptt_lead)
    if args.ptt_tail:
        winkeyer.set_tail_time(args.ptt_tail)
    if args.ptt_enable:
        winkeyer.set_ptt_enable(True)
    server_type = CwdaemonServerDebug if args.debug else CwdaemonServer
    server = socketserver.UDPServer(
        (_LOCALHOST_ADDRESS, args.port), server_type)
    server.serve_forever()
