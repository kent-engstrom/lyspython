#!/usr/bin/env python
#
# Code provided for personal instructional purposes only. No warranty.
# Please respect the copyright law.
# Requires Python 1.6 or above

import urllib
import os
import jddate
import re

class dilberterror(Exception): pass

def fetch_many_dilberts():
    d = jddate.FromToday()
    while 1:
        filename = "%s.gif" % d.GetString_YYYYMMDD()
        if os.path.exists(filename):
            print filename, "already present"
        else:
            try:
                fetch_dilbert(d, filename)
            except dilberterror:
                print "-- not a GIF file, aborting"
                return
        d = d - 1

def fetch_dilbert(date, filename):
    page_url = "http://www.dilbert.com/comics/dilbert/archive/dilbert-%s.html" % date.GetString_YYYYMMDD()
    print page_url
    u = urllib.urlopen(page_url)
    html = u.read()
    u.close()

    m = re.search(r"archive/images/dilbert([0-9]+).gif", html)
    secret = m.group(1)
    pic_url = "http://www.dilbert.com/comics/dilbert/archive/images/dilbert" + secret + ".gif"
    print pic_url
    
    u = urllib.urlopen(pic_url)
    pic = u.read()
    u.close()
    if not pic.startswith("GIF"): raise dilberterror
    
    f = open(filename, "wb")
    f.write(pic)
    f.close()
    print "-- done"
    print
    
    

if __name__ == '__main__':
    fetch_many_dilberts()
    
