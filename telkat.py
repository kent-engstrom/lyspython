#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#   
# Copyright (c) 2002, Pontus Sköld (pont@it.uu.se)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

#
# This code requires Python 2.something or later.
#

"""telkat provides an interface to query the Swedish white paper service
offered by Eniro at <URL:http://www.privatpersoner.gulasidorna.se/>

The primary functions offered by this module are

NameLookup( first, last, firsttype, lasttype, region, adress, zipcode,
            area, title, titletype )

and

NumberLookup( number )

Both of these return instances of telkatInfo or raise telkatError.

Any argument may be excluded although that may not be very useful, see
the respective functions for more information."""


# Import what we need

import sgmllib
import urllib
import string
import encodings

class telkatError( Exception ):
    "Class for errors in this module, with a friendly message"

    def __init__( self, s ):
        self.s = s

    def __str__( self ):
        return self.s



   
class telkatInfo:
    """Class to contatin the result of a query.

    Instances support the __getslice__ and __getitem__ operations
    (i.e. slicing and indexing works as supposed).

    Each item returned will be a dictionary with (at least) the keys
    number, name and adress.

    If the query failed, a telkatError will be raised.

    lostdata() will returns whatever data was lost in the query
    because of the maximum limit of 250 entries returned for any
    given query."""

    def __init__( self, tdl, txt ):

        self.datalost = 0
        self.t = ()

        if txt.find('ingen träff') != -1:                          
            raise telkatError( "Ingen träff" )
        elif txt.find('tekniskt') != -1:
            raise telkatError( "Tekniskt underhåll"  )
        elif txt.find('visar max') != -1:
            self.datalost = 1
            
        
        for p in tdl:
            if len(p) < 3:
                 raise telkatError( "Konstigt format eller ingen träf" )
             
            (name, number, address ) = p[0:3]

            if number.find("Tel.") != -1:
                 number = number[number.find("Tel.")+4:]

            name = encodings.codecs.latin_1_decode( name )[0].strip()
            address = encodings.codecs.latin_1_decode( address )[0].strip()
            number = encodings.codecs.latin_1_decode( number )[0].strip()
            
            if name and address and number:
                self.t = self.t + ( { 'number':number, 'name':name, 'adress':address, 'address':address }, )


        
        # Check for different messages that may occur instead/infront
        # of the information
         
                                

    def lostdata( self ):
        return self.datalost
    
    def __getitem__( self, i ):
        return self.t[i]
        
    def __getslice__( self, a, b ):
        return self.t[a:b]

    def __len__( self ):
        return len( self.t )
    
    def __str__( self ):
        return str( self.t )
    


class telkatParser( sgmllib.SGMLParser ):
    """Class to semi-parse the raw HTML from the query.

    Use report() to get a telkatInfo instance of what has
    been treated so far."""

    def reset( self ):
        sgmllib.SGMLParser.reset( self )
        self.tdl = [[""]]
        self.ignore = 1
        self.withintable = 0
        self.tabletxt = ''
        
    def handle_comment( self, comment ):
        if comment.strip() == 'result':
            self.ignore = 0
        elif comment.strip() == 'end result':
            self.ignore = 1
            
    def handle_data( self, data ):

        if self.ignore or not len(self.tdl): 
            return

        if not self.withintable:
            self.tdl[-1][-1] += data
        else:
            self.tabletxt += data
        
    def start_br( self, attrs ):
        if not self.ignore:
            self.tdl[-1].append("")

    def start_table( self, attrs ):
        self.withintable += 1

    def end_table( self):
        self.withintable -= 1

    def start_hr( self, attrs ):
        if not self.ignore:
            self.tdl.append([""])

    def report( self ):
        if self.tdl[0]:
            self.tdl[0] = self.tdl[0][1:-1]

        return telkatInfo( self.tdl, self.tabletxt )
     




#
# User-friendly region definitions
#

regions = { 
    'BLEKINGE':'25',
    'BORÅS':'10',
    'ESKILSTUNA':'14',
    'FALUN':'20',
    'GOTLAND':'8',
    'GÄVLE':'21',
    'GÖTEBORG':'9',
    'HALMSTAD':'6',
    'HELSINGBORG':'3',
    'JÖNKÖPING':'7',
    'KALMAR':'5',
    'KARLSTAD':'16',
    'KRISTIANSTAD':'4',
    'LULEÅ':'24',
    'MALMÖ':'1',
    'NORRKÖPING':'13',
    'LINKÖPING':'13',
    'SKÖVDE':'12',
    'STOCKHOLM':'15',
    'SUNDSVALL':'22',
    'UDDEVALLA':'11',
    'UMEÅ':'23',
    'UPPSALA':'19',
    'VÄSTERÅS':'18',
    'VÄXJÖ':'26',
    'YSTAD':'2',
    'ÖREBRO':'17',
    'ÖSTERSUND':'28',
    'HELA LANDET':''
}
    
def GetNumInfo( areacode, number ):
    """GetNumInfo( areacode, number ) -> string

    Retrieves information about the phonenumber with
    areacode areacode and phonenumber number, and
    returns a string with the raw output."""

    query = "http://privatpersoner.eniro.se/query?what=wp&phone_number=%s" %\
    (
        str(areacode)+
        str(number)
        )

    f = urllib.URLopener().open( query )
    s = string.join( f.readlines() )
    f.close()

    return s


def GetCompNumInfo( areacode, number ):
    """GetCompNumInfo( areacode, number ) -> string
    
    Retrieves information about the company with 
    areacode areacode and phonenumber number, and
    returns a string with the raw output."""
    
    query = "http://www.gulasidorna.se/query?what=yp&newSearch=1&phone_prefix=%s&phone_number=%s" %\
    (
        str(areacode),
        str(number)
        )

    f = urllib.URLopener().open( query )
    s = string.join( f.readlines() )
    f.close()
        
    return s
    

def GetCompInfo( name = '',
                 nametype = 'exact',
                 address = '',
                 addresstype = '',
                 zipcode = '',
                 area = ''):
    pass
                


def GetPersInfo( first = '',
                 last = '',
                 firsttype = 'exact',
                 lasttype = 'exact',
                 region = '',
                 adress = '',
                 address = '',
                 addresstype = 'exact',
                 zipcode = '',
                 area = '',
                 title = '',
                 titletype = 'exact'
                 ):
    """GetPersInfo( first, last, firsttype, lasttype,
             region, adress, address, addresstype, zipcode, area, title,
             titletype ) -> string

    Perform the query to Eniro and return the raw data."""

    if adress and not address:
        address = adress
        
    query = "http://privatpersoner.eniro.se/query?what=wp&firstnameType=%s&lastnameType=%s&region=%s&address=%s&addresstype=%s&zipcode=%s&area=%s&title=%s&titleType=%s&firstname=%s&lastname=%s" % ( firsttype, lasttype, region, address, addresstype, zipcode, area, title, titletype, first, last )
   
    f = urllib.URLopener().open( query )
    s = string.join( f.readlines() )
    f.close()

    return s




    


# These are the two functions supposed to be useful to mortals :)

def NameLookup( first  ='',
                last = '',
                firsttype = 'exact',
                lasttype = 'exact',
                region = '',
                adress = '',
                address = '',
                addresstype = 'exact',
                zipcode = '',
                area = '',
                title = '',
                titletype = 'exact'
                ):

    """NameLookup( first, last, firsttype, lasttype, region, adress,
    address, addresstype, zipcode, area, title, titletype ) => list of strings

    Performs a query according to the given parameters and returns a
    telkatInfo instance (or raises a telkatError if there was a
    problem).

    All parameters have sensible defaults although. The type
    parameters may be either 'exact', 'trunc' (e.g. starts with) or
    'fuzzy' (titletype may not accept fuzzy).

    The region may be either a number in a string or one of the keys
    of telkat.region.
    """

    if adress and not address:
        address = adress
        
    if not region.isdigit():                  # Need to look up region code?
        if region.upper() in regions.keys(): 
            region = regions[ region.upper() ]
        else:
            region = '' # All of sweden
        
    k = telkatParser()
    k.feed( GetPersInfo( first = first,
                         last = last,
                         firsttype = firsttype,
                         lasttype = lasttype,
                         region = region,
                         adress = address,
                         address = address,
                         addresstype = addresstype,
                         zipcode = zipcode,
                         area = area,
                         title = title, 
                         titletype = titletype
                         )
            )
    k.close()

    return k.report()





def NumberLookup( number = '08' ):
    """NumberLookup( string ) => list of strings

    Performs a query for the given phone number and returns a
    telkatInfo instance (or raises a telkatError)."""

    k = telkatParser()
    k.feed( GetNumInfo( "", number ))
    k.close()

    return k.report()




