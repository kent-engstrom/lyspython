# Conversion between latitude, longitude and the RT-38
# coordinate system ("Rikets trianguleringsnät") used on Swedish
# survey maps

# Copyright 1998 Kent Engström. Released under GNU GPL.

import math

# Auxiliary functions

def deg2rad(x):
    return x * math.pi / 180

def rad2deg(x):
    return x * 180 / math.pi

def atanh(x):
    return .5 * math.log((1 + x) / (1 - x))

# Constants

y0 = 1500000
lng0 = deg2rad(15.80827778)
k0a = 6366742.5194
beta1 = .00083522527
beta2 = .000000756302
beta3 = .000000001193
delta1 = .000835225613
delta2 = .000000058706
delta3 = .000000000166



def latlong2xy(latd, lngd):
    """Convert latitude and longitude to a tuple (X,Y)."""

    lat = deg2rad(latd)
    lng = deg2rad(lngd)

    lat2 = lat - math.sin(lat) * math.cos(lat) * deg2rad(1376.68809 + 7.64689 * math.pow(math.sin(lat),2) + .053 * math.pow(math.sin(lat),4) + .0004 * math.pow(math.sin(lat),6))/3600
    ksi = math.atan(math.tan(lat2) / math.cos(lng - lng0))
    eta = atanh(math.cos(lat2) * math.sin(lng - lng0))
    x = k0a * (ksi + beta1 * math.sin(2 * ksi) * math.cosh(2 * eta) + beta2 * math.sin(4 * ksi) * math.cosh(4 * eta) + beta3 * math.sin(6 * ksi) * math.cosh(6 * eta))
    y = y0 + k0a * (eta + beta1 * math.cos(2 * ksi) * math.sinh(2 * eta) + beta2 * math.cos(4 * ksi) * math.sinh(4 * eta) + beta3 * math.cos(6 * ksi) * math.sinh(6 * eta))

    return (x,y)


def xy2latlong(x,y):
    """Convert X and Y to a tuple (latitude,longitude)."""

    ksi = x / k0a
    eta = (y - y0) / k0a
    ksi2 = ksi - delta1 * math.sin(2 * ksi) * math.cosh(2 * eta) - delta2 * math.sin(4 * ksi) * math.cosh(4 * eta) - delta3 * math.sin(6 * ksi) * math.cosh(6 * eta)
    eta2 = eta - delta1 * math.cos(2 * ksi) * math.sinh(2 * eta) - delta2 * math.cos(4 * ksi) * math.sinh(4 * eta) - delta3 * math.cos(6 * ksi) * math.sinh(6 * eta)
    lat2 = math.asin(math.sin(ksi2) / math.cosh(eta2))
    lng = math.atan(math.sinh(eta2) / math.cos(ksi2)) + lng0
    lat = lat2 + math.sin(lat2) * math.cos(lat2) * deg2rad(1385.93836 - 10.89576 * math.pow(math.sin(lat2),2) + .11751 * math.pow(math.sin(lat2),4) - .00139 * math.pow(math.sin(lat2),6)) / 3600

    return (rad2deg(lat),rad2deg(lng))
