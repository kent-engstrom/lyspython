# Time class for Python
# Copyright 1997, 1998 Kent Engström.
# Copyright 1999 Per Cederqvist
# Released under the GNU GPL.

# This file was written by Per Cederqvist.  Some code and much of the
# design was taken from jddate.py, so Kent Engström holds some of the
# copyright.  However, he is not to blame for any errors in this file.
# This file assumes that the fractional part of a Julian date is 0 at
# midnight, 0.5 at noon, and 0.99999999999... immediatly before the
# next midnight.  I have a feeling that astronomers are 12 hours off.
#
#			/ceder 1999-11-15

import re
import string
import time

import jddate

class Time(jddate.Date):

    # Use base constructor.

    def __repr__(self):
	if self.IsValid():
	    return "<Time %s>" % self.GetString_YYYY_MM_DD_HH_MM_SS()
	else:
	    return "<Time invalid>"

    def SetJD(self, jd):
	jddate.Date.SetJD(self, int(jd))
	self.__setjd(jd - int(jd))

    def __setjd(self, jdfraction):
	# Add half a second to make this code less fragile to rounding errors.
	jdfraction = jdfraction + 0.5 / 86400
	jdfraction = jdfraction * 24
	self.__h = int(jdfraction)
	jdfraction = 60 * (jdfraction - int(jdfraction))
	self.__m = int(jdfraction)
	jdfraction = 60 * (jdfraction - int(jdfraction))
	self.__s = int(jdfraction)

    def SetYMD(self, y, m, d):
	jddate.Date.SetYMD(self, y, m, d)
	self.__h = self.__m = self.__s = 0

    def SetYMDHMS(self, y, mo, d, h, mi, s):
	jddate.Date.SetYMD(self, y, mo, d)
	self.__h = h
	self.__m = mi
	self.__s = s

    def SetYWD(self, y, m, d):
	jddate.Date.SetYWD(self, y, m, d)
	self.__h = self.__m = self.__s = 0
	
    def GetJD(self):
	return jddate.Date.GetJD(self) + self.__getjd()

    def GetDate(self):
        # Get a new jddate.Date object for the current date
        return jddate.FromJD(jddate.Date.GetJD(self))

    def __getjd(self):
	return (self.__h + (self.__m + (self.__s / 60.0)) / 60.0) / 24.0

    def GetHMS(self):
	return (self.__h, self.__m, self.__s)

    def GetYMDHMS(self):
	return jddate.Date.GetYMD(self) + self.GetHMS()

    def GetString_YYYY_MM_DD_HH_MM_SS(self):
	return (jddate.Date.GetString_YYYY_MM_DD(self) +
		" %02d:%02d:%02d" % (self.__h, self.__m, self.__s))

    def GetString_YYYYMMDDHHMMSS(self):
	return (jddate.Date.GetString_YYYYMMDD(self) +
		"%02d%02d%02d" % (self.__h, self.__m, self.__s))

    GetString = GetString_YYYY_MM_DD_HH_MM_SS

    def __add__(self, days):
	return FromJD(self.GetJD() + days)

    def __radd__(self, days):
	return FromJD(self.GetJD() + days)

    def __sub__(self, other):
	if type(other) in [type(0), type(0.0), type(0L)]:
	    return FromJD(self.GetJD() - other)
	else: 
	    return self.GetJD()-other.GetJD()

#
# INITIALIZERS FOR THE TIME CLASS
#
# These are the functions you should call to get new instances of
# the Time class

def FromJD(jd):
    newtime = Time()
    newtime.SetJD(jd)
    return newtime

def FromDate(date):
    newtime = Time()
    (y, m, d) = date.GetYMD()
    newtime.SetYMD(y, m, d)
    return newtime

def FromYMD(y, m, d):
    newtime = Time()
    newtime.SetYMD(y, m, d)
    return newtime

def FromYMDHMS(y, mo, d, h, mi, s):
    newtime = Time()
    newtime.SetYMDHMS(y, mo, d, h, mi, s)
    return newtime

def FromYWD(y, w, d):
    newtime = Time()
    newtime.SetYWD(y, w, d)
    return newtime

def FromUnixTime(t):
    (dy,dm,dd,th,tm,ts,wd,dayno,ds)=time.localtime(t)
    return FromYMDHMS(dy, dm, dd, th, tm, ts)

def FromToday():
    return FromUnixTime(time.time())

rx_dashed=re.compile("^([0-9]+)-([0-9]+)-([0-9]+)$")
rx_dashed_coloned=re.compile("^([0-9]+)-([0-9]+)-([0-9]+)"
				" ([0-9]+):([0-9]+)(:([0-9]+))?$")
rx_yyyymmdd=re.compile("^([0-9][0-9][0-9][0-9])([0-9][0-9])([0-9][0-9])$")
rx_yymmdd=re.compile("^([0-9][0-9])([0-9][0-9])([0-9][0-9])$")
    
def FromString(str):
    newtime = Time() # Allocates an invalid time

    m = rx_dashed_coloned.match(str)
    if m:
	newtime.SetYMDHMS(string.atoi(m.group(1)),
			  string.atoi(m.group(2)),
			  string.atoi(m.group(3)),
			  string.atoi(m.group(4)),
			  string.atoi(m.group(5)),
			  string.atoi(m.group(7) or "0"))
        return newtime
    
    m = rx_dashed.match(str)
    if m:
	newtime.SetYMD(string.atoi(m.group(1)),
		       string.atoi(m.group(2)),
		       string.atoi(m.group(3)))
        return newtime
    
    m = rx_yyyymmdd.match(str)
    if m:
	newtime.SetYMD(string.atoi(m.group(1)),
		       string.atoi(m.group(2)),
		       string.atoi(m.group(3)))
        return newtime

    m = rx_yymmdd.match(str)
    if m:
	newtime.SetYMD(string.atoi(m.group(1)),
		       string.atoi(m.group(2)),
		       string.atoi(m.group(3)))
        return newtime

    return newtime
