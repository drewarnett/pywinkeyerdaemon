#/usr/bin/env python

"""
pywinkeyerdaemon

Use "pywinkeyerdaemon --help" for help.

Just like cwdaemon, this listens for UDP messages.  However, it supports
winkeyer or winkeyer compatible keyer hardware only.

See README.md for more information.

See https://github.com/drewarnett/pywinkeyerdaemon for even more information.
"""

import SocketServer
import argparse

import serial

_LOCALHOST_ADDRESS = "127.0.0.1"
_DEFAULT_PORT = 6789

ESC = chr(27)


class Winkeyer(object):
    """singleton handler for a winkeyer

    methods are specific to use as a cwdaemon
    """

    def __init__(self, serial_device=None):
        self.port = serial.Serial(serial_device, 1200)
        self.host_open()

    def host_open(self):
        self.port.write(chr(0x0) + chr(0x2))
        v = ord(self.port.read(1))
        printdbg("host_open returned:  " + str(v))
        assert v == 23

    def setspeed(self, speed):
        assert(0 <= speed <= 99)
        self.port.write(chr(0x2) + chr(speed))

    def abort(self):
        self.port.write(chr(0xa))

    def send(self, msg):
        self.port.write(msg.upper())


class CwdaemonServer(SocketServer.BaseRequestHandler):
    """singleton cwdaemon using a singleton winkeyer"""

    def verify_request(self, request, client_address):
        if accept_remote:
            return True
        elif client_address == _LOCALHOST_ADDRESS:
            return True
        else:
            return False

    def handle(self):
        data = self.request[0]

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
                printdbg("Warning:  'ptt keying off or on' not implemented.")
            elif data[1] == 'b':
                printdbg("Warning:  'ssb signal from microphone or soundcard'"
                         " not implemented.")
            elif data[1] == 'c':
                printdbg("Warning:  'tune x seconds long' not implemented.")
            elif data[1] == 'd':
                printdbg("Warning:  'ptt on delay' not implemented.")
            elif data[1] == 'e':
                printdbg("Warning:  'bandindex' not implemented.")
            elif data[1] == 'f':
                printdbg("Warning:  'set sound device' not implemented.")
            elif data[1] == 'g':
                printdbg("Warning:  'set soundcard volume' not implemented.")
            elif data[1] == 'h':
                printdbg("Warning:  'echo when done' not implemented.")
        else:
            printdbg("client message to send:  {}".format(data))
            printdbg("client message to send length:  {}".format(
                len(data)))
            printdbg("client message content:  {}".format(",".join(
                map(lambda x: str(ord(x)), data)
            )))
            stripped_data = data.strip()
            if stripped_data != data:
                printdbg("Warning:  string.strip() removed something.")
            winkeyer.send(stripped_data)

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
    args = parser.parse_args()

    debug = args.debug

    def printdbg(s):
        if debug:
            print(s)

    accept_remote = args.accept_remote_hosts
    if accept_remote:
        print("Warning:  listening to nonlocal hosts as well as localhost.")
    winkeyer = Winkeyer(args.device)
    server = SocketServer.UDPServer(
        (_LOCALHOST_ADDRESS, args.port), CwdaemonServer)
    server.serve_forever()

# vim: ts=4 sw=4 expandtab
