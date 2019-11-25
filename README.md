pywinkeyerdaemon
=================
Just like cwdaemon, this listens for UDP messages.  However, it supports
winkeyer or winkeyer compatible keyer hardware only.

Project page:

    https://github.com/drewarnett/pywinkeyerdaemon


use
---
Serveral ways to invoke:

    python pywinkeyerdaemon [arguments...]

or on unix if permissions to run have been setup:

    pywinkeyerdaemon [arguments...]

or on MS-Windows if file name extension has been mapped to Python:

    pywinkeyerdaemon.py [arguments...]

etc.  [Yes, there are more ways, and yes, Python provides some flexiblity.]

Use -h or --help to get full description of command line arguments.

I currently use:

    pywinkeyerdaemon.py -d /dev/ttyACM0


prerequisites
-------------
python3 [tested with 3.7.3] or python2 [tested with 2.7.16]
pyserial [tested with 3.4]


history
-------
Some of the programs that can use cwdaemon will also talk to winkeyer hardware
directly or K3NG protocol keyer hardware directly.  [Or others?]  However,
looking for a good CW contesting logger in Debian jessie, I was interested in
using tlf which only supports cwdaemon.

Yes, there have been other published projects that do the same thing
implemented in perl and pascal.  I prefer python.


status
------
This project is a barebones, very simple implementation at this point.
However, it works fine for my simple use case with TLF.  Feel free to submit
feature requests and bug reports.

Only a subset of the cwdaemon protocol has been implemented.  And, only a
subset of thw winkeyer protocol has been utilized.

Some debugging features have been included.  These can identify features client
programs may be able to use that have not been implemented, yet.  And, they
can be used to identify variations in how client programs talk to cwdaemon.

prosigns
--------
Not always a 1:1 mapping available, so will use the buffered merge characters
command to build the prosigns for winkeyer.  Per cwdaemon docs these are:

| character | prosign |
|-----------|---------|
| `*`       | AR      |
| `=`       | BT      |
| `<`       | SK      |
| `(`       | KN      |
| `!`       | SN      |
| `&`       | AS      |
| `>`       | BK      |


TODOs
-----
* add inline + and - speed change handling

* consider adding null device as in cwdaemon

* add debugging function to report on all commands received


references
----------
These references may all be found on the web.

* cwdaemon project
* unixcw project (used by cwdaemon)
* K1EL's winkeyer documentation
* K3NG's Arduino keyer project
* winkeyerdaemon implemented in perl
* winkeyerdaemon implemented in pascal
* some brilliant(!) notes on how to provide permanent device names for usb
  serial devices


Drew Arnett, kb9fko
