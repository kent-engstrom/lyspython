#!/usr/bin/env python
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
# This code requires Python 1.6 or later.
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

    def __init__( self, tdl ):

        self.datalost = 0
        self.t = ()

        tdl = tdl[1:]  # The first field is always empty, throw it away
        
        # Check for different messages that may occur instead/infront
        # of the information
         
        if tdl[0] == 'Sökningen misslyckades':                          
            raise telkatError( "Sökningen misslyckades; "+tdl[4] )
        elif tdl[0][:18] == 'Tekniskt underhåll':
            raise telkatError( "Tekniskt underhåll; " + tdl[4] )
        elif tdl[0][:21] == 'Träfflistan visar max':
            self.datalost = 1
            tdl = tdl[2:]
                
        while 1:
            tmp = tdl[0:4]               # Get information about one number
            
            if len( tmp ) < 4 :          # Got less than 4 items?
                break;

            (name, dummy, adress, number) = tmp

            self.t = self.t + ( { 'number':number, 'name':name, 'adress':adress }, )
            tdl = tdl[4:]
                

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
        self.tdl = []
           
    def handle_data( self, data ):
        l = len( self.tdl ) # Have we encountered any TD?

        if not l:
            return

        i = l-1             # Find which to work with. 

        self.tdl[i] = self.tdl[i] +  string.join( data.split() ) 


    def start_td( self, attrs ):
        self.tdl.append("")

    def report( self ):
        return telkatInfo( self.tdl )
     





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
    'HELA LANDET':0
}
    
def GetNumInfo( areacode, number ):
    """GetNumInfo( areacode, number ) -> string

    Retrieves information about the phonenumber with
    areacode areacode and phonenumber number, and
    returns a string with the raw output."""

    query = "http://www.privatpersoner.gulasidorna.se/search/hits.asp?first=1&last=1&areacode=%s&phone=%s" %\
    (
        str(areacode),
        str(number)
        )

    f = urllib.URLopener().open( query )
    s = string.join( f.readlines() )
    f.close()

    return s





def GetPersInfo( first = '',
                 last = '',
                 firsttype = 'exact',
                 lasttype = 'exact',
                 region = '0',
                 adress = '',
                 zipcode = '',
                 area = '',
                 title = '',
                 titletype = 'exact'
                 ):
    """GetPersInfo( first, last, firsttype, lasttype,
             region, adress, zipcode, area, title,
             titletype ) -> string

    Perform the query to Eniro and return the raw data."""
    
    query = "http://www.privatpersoner.gulasidorna.se/search/hits.asp?first=1&last=250&firstnameType=%s&lastnameType=%s&region=%s&adress=%s&zipcode=%s&area=%s&title=%s&titleType=%s&firstname=%s&lastname=%s" % ( firsttype, lasttype, region, adress, zipcode, area, title, titletype, first, last )

    f = urllib.URLopener().open( query )
    s = string.join( f.readlines() )
    f.close()

    return s





def NumberToAreacodeAndPhone( n ):
    """numberToAreacodeAndPhone( n ) -> (string, string)

    Converts a phone number to a tuple of strings where the first element
    represents the areacode and the second represent the phone number.

    If n includes a dash (-), it is trusted to separate the areacode and
    phonenumber
    
    Given invalid input a telkatError is raised."""

    n = string.join( n.split(), '' )                       # Remove any spaces.

    if n[:3] == '+46':                             # Number in international form?
        n = '0' + n[3:]                            # Make national

    i = n.find( '-' )
        
    if -1 != i:                                   # Contains a dash?
        return ( n[ :i ], n[ i+1: ] )             # Trust it to separate correctly
        
    f = open( "riktnr.txt" )                 # No dash, fall back to file

    for p in f.readlines():
        q = p.strip()         # Get rid of surrounding spaces

        if q == str(n)[ : len(q) ]: # Found it? 
            return ( q, str(n)[ len(q) : ] )  # Return correct tuple ac, number

    raise telkatError( 'Invalid phonenumber' )           # Not found

    


# These are the two functions supposed to be useful to mortals :)

def NameLookup( first  ='',
                last = '',
                firsttype = 'exact',
                lasttype = 'exact',
                region = '0',
                adress = '',
                zipcode = '',
                area = '',
                title = '',
                titletype = 'exact'
                ):

    """NameLookup( first, lasts, firsttype, lasttype, region, adress,
    zipcode, area, title, titletype ) => list of strings

    Performs a query according to the given parameters and returns a
    telkatInfo instance (or raises a telkatError if there was a
    problem).

    All parameters have sensible defaults although. The type
    parameters may be either 'exact', 'trunc' (e.g. starts with) or
    'fuzzy' (titletype may not accept fuzzy).

    The region may be either a number in a string or one of the keys
    of telkat.region.
    """

    if not region.isdigit():                  # Need to look up region code?
        if region.upper() in regions.keys(): 
            region = regions[ region.upper() ]
        else:
            region = '0'
        
    k = telkatParser()
    k.feed( GetPersInfo( first,
                         last,
                         firsttype,
                         lasttype,
                         region,
                         adress,
                         zipcode,
                         area,
                         title,
                         titletype
                         )
            )
    k.close()

    return k.report()





def NumberLookup( number = '08' ):
    """NumberLookup( string ) => list of strings

    Performs a query for the given phone number and returns a
    telkatInfo instance (or raises a telkatError)."""

    (ac, p) = NumberToAreacodeAndPhone( number )
    k = telkatParser()
    k.feed( GetNumInfo( ac, p ))
    k.close()

    return k.report()




