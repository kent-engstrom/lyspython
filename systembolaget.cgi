#!/usr/bin/env python2
# -*- coding: Latin-1 -*-
# (C) 2003 Kent Engström. Released under the GNU GPL.

import sys; w = sys.stdout.write; err = sys.stderr.write
import string
import os
import re
import cgi; e = cgi.escape
import cgitb; cgitb.enable()

import systembolaget

# Helper functions

def defint(x, default = 0):
    try:
        return int(x)
    except ValueError:
        return default

def escq(x):
    return string.replace(x, '"', '&quot;')

# CLASS TO HANDLE THE FORM DATA

(F_UPDATE, F_CREATE) = range(0,2)
EMPTY = 8

class Form:
    def __init__(self, fs):
        self.fs = fs
        self.get_data()
        
    def get_data(self):
        self.nr = [] 
        self.nynr = [] 
        self.beskr = []
        self.ant = 0
        left = EMPTY+1
        filled_in = 0
        while 1:
            nr = defint(fs.getfirst("nr%d" % self.ant, "0"))
            nynr = defint(fs.getfirst("nynr%d" % self.ant, "0"))
            beskr = fs.getfirst("beskr%d" % self.ant,"")
            if nr == 0 and nynr == 0:
                left = left -1
                if left == 0: break
            else:
                filled_in = filled_in + 1
                left = EMPTY+1

            self.ant = self.ant+1
            self.nr.append(nr)
            self.nynr.append(nynr)
            self.beskr.append(beskr)
        self.rubrik = fs.getfirst("rubrik", "")
        self.function = F_UPDATE
        if self.fs.has_key("create"):
            self.function = F_CREATE

        # The old version used QUERY_STRING directly.
        # Backwards compatibilty kludge follows
        if self.function == F_UPDATE and filled_in == 0 and\
           os.environ.get("QUERY_STRING","") is not "":
            err("QS hack <%s>\n" % os.environ["QUERY_STRING"])
            self.nr = []
            self.nynr = []
            self.beskr = []
            for nr in string.split(os.environ["QUERY_STRING"], ","):  
                self.nr.append(0)
                self.nynr.append(nr)
                self.beskr.append("")
            for i in range(0,EMPTY):
                self.nr.append(0)
                self.nynr.append(0)
                self.beskr.append("")
            self.ant=len(self.nr)

    def handle(self):
        # Just display what we know until now
        if self.function == F_UPDATE:
            self.update()
        elif self.function == F_CREATE:
            self.create()
            
    def update(self):
        self.html_top(rubrik = self.rubrik)

        w("""
<FORM METHOD=POST>
<P>Mata in varunummer i rutorna till vänster. Ange också en lämplig rubrik.
Används sedan knappen <b>Uppdatera</b> för att kontrollera att varorna finns i katalogen.
När rätt varor visas: välj <b>Skapa</b> för att skapa lista för utskrift.

<P>Uppgifterna hämtas direkt ur <A HREF=http://www.systembolaget.se/pris/owa/xall>Systembolagets katalog</A>.

<P>Rubrik:<BR><INPUT TYPE=TEXT NAME="rubrik" VALUE="%s" SIZE=60>
<P>
<TABLE>""" % e(self.rubrik))
        for i in range(0,self.ant):
            if self.nynr[i] == 0:
                # New or erased
                beskr = ""
                nr = 0
            elif self.nynr[i] != self.nr[i]:
                # The user has changed the form. Do a search and display new data
                nr = self.nynr[i]
                vara = systembolaget.Product().search(nr)
                if vara.valid():
                    beskr = "<TABLE>" + escq(vara.to_string_html(include_sensory=0)) + "</TABLE>"
                else:
                    beskr = "<i>Varan finns inte!</i>"
            else:
                # No change, show old data
                nr = self.nynr[i]
                beskr = self.beskr[i]
                
            # Display HTML
            if nr == 0:
                nr = ""
            if beskr == "":
                beskr = "<i>Ange nr</i>"
                    
            w('<TR VALIGN=TOP>')
            w('<TD>%d.</TD>' % (i+1))
            w('<TD><INPUT TYPE=TEXT NAME="nynr%d" VALUE="%s"></TD>' %(i, nr))
            w('<TD><INPUT TYPE=HIDDEN NAME="nr%d" VALUE="%s">' %(i, nr))
            w('<INPUT TYPE=HIDDEN NAME="beskr%d" VALUE="%s">%s</TD>' %(i, beskr, beskr))
            w('</TR>')

        w("""
</TABLE>
<INPUT TYPE=SUBMIT NAME="update" VALUE="Uppdatera">
<INPUT TYPE=SUBMIT NAME="create" VALUE="Skapa">
</FORM>
""")
        self.html_bottom()


    def html_top(self, rubrik = ""):
        if rubrik == "":
            rubrik = "Vinlista"
        w("""
<HEAD>
<TITLE>%s</TITLE>
</HEAD>
<BODY>
<H1>%s</H1>""" % (rubrik, rubrik))

    def html_bottom(self):
        w("""
</BODY>""")

    def create(self):
        self.html_top(rubrik = self.rubrik)
        w("""
<TABLE>""")

        for i in range(0, self.ant):
            vara = systembolaget.Product().search(self.nr[i])
            if vara.valid():
                w(vara.to_string_html())
        w("""
</TABLE>
<P><FONT SIZE=-2>Uppgifterna är hämtade från <A HREF=http://www.systembolaget.se/pris/owa/xall>Systembolagets katalog</A>.</FONT>
""")
        self.html_bottom()
        
# MAIN

w("Content-type: text/html\r\n\r\n")

fs = cgi.FieldStorage()
f = Form(fs)
f.handle()

sys.stdout.flush()
