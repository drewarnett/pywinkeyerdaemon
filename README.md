# pywinkeyerdaemon

pywinkeyerdaemon is a network interface for K1EL's WinKeyer.  It implements
the de facto standard cwdaemon protocol over UDP.

Project page:

    https://github.com/drewarnett/pywinkeyerdaemon


## prerequisites

* Python3 [tested with 3.7.3]
* pyserial [tested with 3.4]

Note:  Python2 has been discontinued after a 10 year transition period.
Contact me if you really need to run under Python2.

On MS Windows, and in general, use `py -3 -m pip install pyserial`.

With a unix package manager like Debian, install `python3` and
`python3-serial`.  (Or use pip.)

pywinkeyerdaemon is Python, so it will run on anything.  Many unix programs
support the cwdaemon protocol.  It isn't popular on MS Windows.  Yet.  :-)


## invocation

On unix:

    `python3 pywinkeyerdaemon.py [arguments...]`

or if given executable permissions:

    `pywinkeyerdaemon.py [arguments...]`.

On MS Windows the Python3 installer includes the Python Launcher for Windows
(py.exe) and associates it to .py files.  So:

    `pywinkeyerdaemon.py [arguments...]`

or alternatively:

    `py -3 pywinkeyerdaemon.py [arguments...]`.

Use -h or --help to get full description of command line arguments.  Some are
mandatory.  At the least, the serial port device must be provided.


## finding the serial port

This is easier than it used to be.  On unix:

    `python3 -m serial.tools.list_ports --verbose`

or on MS Windows:

    `py -3 -m serial.tools.list_ports --verbose`

On one machine, my WinKeyer USB gives:

```
/dev/ttyUSB0
    desc: FT232R USB UART
    hwid: USB VID:PID=0403:6001 SER=A5051JLZ LOCATION=6-2
```

It is using the same popular FTDI chip that many other projects use.
Unforunately, the VID:PID is not enough to tell me which serial port is my
WinKeyer USB and which is the my rig's CAT cable.  Plug and unplug and see the
list change.  Label the FTDI serial number on the bottom of your WinKeyer USB.

On linux, do take advantage of /dev/serial/by-id.  I like to make soft links
like $HOME/keyer and $HOME/cat.  Beats the heck out of udev rules!


## history

Some of the programs that can use cwdaemon can also talk directly to a
WinKeyer.  However, while looking for a good CW contesting logger in Debian
jessie, I was interested in using tlf which only supports cwdaemon.

Yes, there have been other published projects that do the same thing this
project does implemented in perl and pascal.  I prefer Python.


## status

This project is a barebones, very simple implementation at this point.
However, it works fine for my simple use case with tlf.  Feel free to submit
feature requests and bug reports.

Only a subset of the cwdaemon protocol has been implemented.  And, only a
subset of the WinKeyer protocol has been utilized.

Some debugging features have been included.  These can identify features client
programs may be able to use that have not been implemented, yet.  And, they
can be used to identify variations in how client programs talk to cwdaemon.


## prosigns

Not always a 1:1 mapping available, so will use the buffered merge characters
command to build the prosigns for WinKeyer.  Per cwdaemon docs these are:

| character | prosign |
|-----------|---------|
| `*`       | AR      |
| `=`       | BT      |
| `<`       | SK      |
| `(`       | KN      |
| `!`       | SN      |
| `&`       | AS      |
| `>`       | BK      |


## TODOs

* detect and filter characters not explicitly supported by cwdaemon protocol
    * WinKeyer will ignore some but not all of these

* consider adding null device as in cwdaemon

* add debugging function to report on all commands received


## references

These references may all be found on the web.

* cwdaemon project
* unixcw project (used by cwdaemon)
* K1EL's WinKeyer documentation
* K3NG's Arduino keyer project
* winkeyerdaemon implemented in perl
* winkeyerdaemon implemented in pascal
* some brilliant(!) notes that tipped me off to /dev/serial/by-id


Drew Arnett, n7da
