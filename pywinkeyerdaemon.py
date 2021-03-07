#!/usr/bin/env python3

"""
pywinkeyerdaemon

Use "pywinkeyerdaemon --help" for help.

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


class Winkeyer():
    """singleton handler for a winkeyer

    methods are specific to use as a cwdaemon
    """

    SUPPORTED_VERSIONS = (23, 30)

    def __init__(self, serial_device=None):
        self.port = serial.Serial(serial_device, 1200)
        self.host_open()

    def host_open(self):
        self.host_close()
        self.port.flushInput()
        self.port.timeout = 1
        self.port.write((chr(0x0) + chr(0x2)).encode())
        version = ord(self.port.read(1).decode())
        printdbg("host_open returned:  " + str(version))
        assert version in self.SUPPORTED_VERSIONS, version
        self.port.timeout = 0.1
        atexit.register(self.host_close)

    def host_close(self):
        self.port.write((chr(0x0) + chr(0x3)).encode())

    def setspeed(self, speed):
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

    def ptt(self, ptt):
        if ptt:
            self.port.write((chr(0x18) + chr(1)).encode())
        else:
            self.port.write((chr(0x18) + chr(0)).encode())

    def sidetoneenable(self, enable):
        if enable:
            self.port.write((chr(0x09) + chr(0b0110)).encode())
        else:
            self.port.write((chr(0x09) + chr(0b0100)).encode())


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


class CwdaemonServer(socketserver.BaseRequestHandler):
    """singleton cwdaemon using a singleton winkeyer"""

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
            printdbg("Warning:  chr(0) in client message")
            data = data[:data.index(chr(0))]

        if data[0] == ESC:
            if data[1] == '0':
                printdbg("Warning:  'set defaults' not implemented.")
            elif data[1] == '2':
                speed = data[2:]
                printdbg("set speed:  {}".format(speed))
                set_speed(int(speed))
                winkeyer.setspeed(int(speed))
            elif data[1] == '3':
                tone = data[2:]
                printdbg("set tone:  {}".format(tone))
                printdbg(data[2:])
            elif data[1] == '4':
                printdbg("abort message")
                winkeyer.abort()
            elif data[1] == '5':
                printdbg("Warning:  'exit daemon' not implemented.")
            elif data[1] == '6':
                printdbg("Warning:  'set uninterruptible word mode'"
                         " not implemented.")
            elif data[1] == '7':
                printdbg("Warning:  'set weighting' not implemented.")
            elif data[1] == '8':
                printdbg("Warning:  'set device for keying' not implemented.")
            elif data[1] == '9':
                printdbg("Warning:  obsolete cwdaemon command.")
            elif data[1] == 'a':
                ptt = data[2:]
                if ptt not in ("0", "1"):
                    printdbg(
                        "Warning:  "
                        "unsupported value for 'ptt keying off or on'")
                else:
                    if get_delay() == 0:
                        printdbg("Cannot set PTT.  PTT disabled by delay = 0.")
                    else:
                        if ptt == "0":
                            if get_ptt():
                                winkeyer.ptt(False)
                                set_ptt(False)
                        else:
                            if not get_ptt():
                                winkeyer.ptt(True)
                                set_ptt(True)
            elif data[1] == 'b':
                printdbg("Warning:  'ssb signal from microphone or soundcard'"
                         " not implemented.")
            elif data[1] == 'c':
                seconds = int(data[2:])
                if 0 <= seconds <= 99:
                    if seconds:
                        printdbg("tune for {} seconds".format(seconds))
                        if seconds > 10:
                            printdbg(
                                "allowing longer tune than cwdaemon's"
                                " 10 second max")
                        winkeyer.tune(seconds)
                    else:
                        printdbg("tune for 0 seconds ignored")
                else:
                    printdbg(
                        "tune for {} seconds out of range"
                        " 0 to 99 seconds".format(seconds))
            elif data[1] == 'd':
                # TODO:  implement range check.  CW daemon uses 0 to 50 and
                #        truncates into range.
                # TODO:  use value for more than enable/disable PTT.
                #        Probably round and use for winkeyer lead in time.
                delay = data[2:]
                printdbg("set delay:  {}".format(delay))
                set_delay(int(delay))
                printdbg("delay set to:  {:d}".format(get_delay()))
            elif data[1] == 'e':
                printdbg("Warning:  'bandindex' not implemented.")
            elif data[1] == 'f':
                printdbg("Warning:  'set sound device' not implemented.")
            elif data[1] == 'g':
                printdbg("Warning:  'set soundcard volume' not implemented.")
            elif data[1] == 'h':
                printdbg("Warning:  'echo when done' not implemented.")
        else:
            printdbg("message:  {}".format(repr(data)))
            if data.rstrip(WHITESPACE_TO_STRIP) != data:
                printdbg(
                    "message trailing whitespace (not including ' ') removed")
                data = data.rstrip(WHITESPACE_TO_STRIP)
            printdbg("message:  {}".format(repr(data)))

            winkeyer_data = _expand_cwdaemon_prosigns_for_winkeyer(data)
            if winkeyer_data != data:
                data = winkeyer_data
                printdbg("prosigns expanded")
                printdbg("message:  {}".format(repr(data)))

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
                    printdbg("cwdaemon +/- speed controls expanded/translated")
                else:
                    printdbg(
                        "speed not set, yet,"
                        " so cwdaemon +/- speed controls ignored")
                data = speed_message_data
                printdbg("message:  {}".format(repr(data)))

            winkeyer.send(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", nargs="?",
                        help="network port to listen (default {})".format(
                            _DEFAULT_PORT),
                        type=int, default=_DEFAULT_PORT)
    parser.add_argument("-d", "--device", nargs="?",
                        help="device file on unix, ex. /dev/ttyS0,"
                        " and device name on MS-Windows, ex. COM1",
                        type=str)
    parser.add_argument("--accept-remote-hosts",
                        help="respond to requests from hosts other than"
                             " localhost",
                        action="store_true")
    parser.add_argument("--debug",
                        help="print debug statements to standard output",
                        action="store_true")
    parser.add_argument("--sidetoneon",
                        help="start with sidetone on (default off)",
                        action="store_true")

    args = parser.parse_args()

    debug = args.debug

    def printdbg(s):
        if debug:
            print(s)

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
    winkeyer = Winkeyer(args.device)
    winkeyer.sidetoneenable(args.sidetoneon)
    server = socketserver.UDPServer(
        (_LOCALHOST_ADDRESS, args.port), CwdaemonServer)
    server.serve_forever()

# vim: ts=4 sw=4 expandtab
