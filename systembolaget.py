#!/usr/bin/env python

import sys
import string
import re
import cStringIO
import urllib

# Helper functions

def format_titled(title, text, title_size = 16, max_col = 78):
    list = string.split(text)
    left = title + ":"
    pos = 0
    res = []
    for word in list:
        # Check if we should go to next line
        # We always place at least one word per line, even if that overflows
        # the line!
        if pos > 0 and pos + 1 + len(word) > max_col:
            res.append("\n")
            pos = 0

        # Now place word after title or space
        if pos == 0:
            res.append(string.ljust(left, title_size)[:title_size])
            left = ""
            pos = title_size
        else:
            res.append(" ")
            pos = pos + 1
        res.append(word)
        pos = pos + len(word)
    res.append("\n")
    return string.join(res, "")

def format_titled_fixed(title, text_lines, title_size = 16, max_col = 78):
    left = title + ":"
    res = []
    for line in text_lines:
        res.append("%-*s%s\n" %( title_size, left, line))
        left = ""
    return string.join(res, "")
    
def add_field(f, dict, title, key):
    if dict.has_key(key):
        f.write(format_titled(title, dict[key]))


def findall_pos(pattern, data, s_pos, e_pos):
    # Find the position of the beginning of each match; search for next match after the
    # end of the current
    l = []
    pos = s_pos
    patre = re.compile(pattern)
    while 1:
        m = patre.search(data, pos, e_pos)
        if m:
            l.append(m.start(0))
            pos = m.end(0)
        else:
            return l
        

# Classes matching a single piece of data

class M:
    def __init__(self, pattern, advance=1):
        self.pattern = self.elaborate_pattern(pattern)
        self.re = re.compile(self.pattern)
        self.advance = advance
        
    def match(self, data, s_pos, e_pos):
        m = self.re.search(data, s_pos, e_pos)
        if m:
            #print "Found", m.group(1)
            data = self.clean(m.group(1))
            if self.advance:
                return (data, m.end(0))
            else:
                return (data, s_pos)
        else:
            #print "Not found"
            return (None, s_pos)

    def clean(self, data):
        return data

    def elaborate_pattern(self, pattern):
        return pattern

class MS(M):
    def clean(self, data):
        return string.join(string.split(string.strip(data)), " ")

class MSF(MS):
    def elaborate_pattern(self, pattern):
        return r"<B>%s</B></td>\n<td valign=top>(.*)</td></tr>" % pattern

class MSC(MS):
    def elaborate_pattern(self, pattern):
        return r'<td width=70><center><img src="/bilder/klock_([0-9]+).gif"\n><br> *%s *</center></td>' % pattern


class MSDeH(MS):
    def clean(self, data):
        return re.sub("&nbsp;", " ",
                      re.sub("<.*?>", "",
                             string.join(string.split(string.strip(data)), " ")))

class MSVolym(MS):
    def clean(self, data):
        return re.sub("ml", " ml",
                      string.join(string.split(string.strip(data)), " "))


# Class matching a set of data, producing a dictionary

class MSet:
    def __init__(self, matchers):
        self.matchers = matchers
        
    def match(self, data, s_pos, e_pos):
        # Execution
        dict = {}
        for (name, m) in self.matchers:
            #print "Looking for",name,"between",s_pos,"and",e_pos
            #print "--> %s" % data[s_pos:s_pos+40]
            (found, s_pos) = m.match(data, s_pos, e_pos)
            if found: # Subtle: empty dict or list is also false!
                dict[name] = found
        return (dict, s_pos)

# Class matching a list of data, producing a list

class MList:
    def __init__(self, begin, matcher):
        self.begin = begin
        self.matcher = matcher
        
    def match(self, data, s_pos, e_pos):
        # Execution
        list = []
        pos = findall_pos(self.begin, data, s_pos, e_pos) + [e_pos]
        #print "Positions for", self.begin,":", pos
        for i in range(0,len(pos)-1):
            #print "Looking for list entry between",pos[i],"and",pos[i+1]
            (found, dummy_pos) = self.matcher.match(data, pos[i], pos[i+1])
            list.append(found)
        return (list, e_pos)

# Class narrowing the allowable search range without doing matching on its own

class MLimit:
    def __init__(self, pattern, matcher):
        self.pattern = pattern
        self.re = re.compile(self.pattern)
        self.matcher = matcher
        
    def match(self, data, s_pos, e_pos):
        #print "Before limit", s_pos,"to", e_pos
        #print "--> %s" % data[s_pos:s_pos+60]
        
        m = self.re.search(data, s_pos, e_pos)
        if m:
            (s_pos, e_pos) = m.span(1)
            #print "After limit", s_pos,"to", e_pos
            #print "--> %s" % data[s_pos:s_pos+40]
            return self.matcher.match(data, s_pos, e_pos)
        else:
            #print "Limit failed"
            return (None, s_pos) # or should we call the matcher with empty data?
    
# Product class

prod_m = MSet([("grupp", MS(r"<tr><td width=144> </td><td>\n(.+)\n")),
               ("namn", MS(r"<B>([^(]+)\(nr [^)]*\)")),
               ("ursprung",MSF("Ursprung")),
               ("producent",MSF("Producent")),
               ("förpackningar",
                MLimit(r'(?s)<td><table border=1><tr><td><table border=0>(.*?)</table></td></tr></table>',
                       MList("<tr>",
                             MSet([("namn", MS(r"<td>([^<]+)</td>")),
                                   ("storlek", MS(r"<td align=right>([^<]+)</td>")),
                                   ("pris", MS(r"<td align=right>([^<]+)</td>")),
                                   ("anm1", MS(r"<td>([^<]+)</td>")),
                                   ("anm2", MSDeH(r"<td>(.+?)</td>")),
                                   ])))), 
               ("färg",MSF("Färg")),
               ("doft",MSF("Doft")),
               ("smak",MSF("Smak")),
               ("sötma",MSC("Sötma", advance = 0)),
               ("fyllighet",MSC("Fyllighet", advance = 0)),
               ("strävhet",MSC("Strävhet", advance = 0)),
               ("fruktsyra",MSC("Fruktsyra", advance = 0)),
               ("beska",MSC("Beska", advance = 0)),
               ("användning",MSF("Användning")),
               ("hållbarhet",MSF("Hållbarhet")),
               ("provad_årgång",MSF("Provad årgång")),
               ("provningsdatum",MSF("Provningsdatum")),
               ("alkoholhalt",MS("<B>Alkoholhalt</B></td>\n<td valign=top>(.*\n.*)</td></tr>")),
               ])    

class Product:
    def __init__(self, webpage):
        (self.dict, pos) = prod_m.match(webpage, 0, len(webpage))

    def valid(self):
        return self.dict.has_key("namn")
    
    def to_string(self):
        f = cStringIO.StringIO()
        add_field(f, self.dict, "Grupp","grupp")
        add_field(f, self.dict, "Namn","namn")
        add_field(f, self.dict, "Ursprung","ursprung")
        add_field(f, self.dict, "Producent","producent")
        f.write("\n")
        add_field(f, self.dict, "Färg","färg")
        add_field(f, self.dict, "Doft","doft")
        add_field(f, self.dict, "Smak","smak")
        f.write("\n")
        add_field(f, self.dict, "Sötma","sötma")
        add_field(f, self.dict, "Fyllighet","fyllighet")
        add_field(f, self.dict, "Strävhet","strävhet")
        add_field(f, self.dict, "Fruktsyra","fruktsyra")
        add_field(f, self.dict, "Beska","beska")
        f.write("\n")
        add_field(f, self.dict, "Användning","användning")
        add_field(f, self.dict, "Hållbarhet","hållbarhet")
        add_field(f, self.dict, "Provad årgång","provad_årgång")
        add_field(f, self.dict, "Provad","provningsdatum")
        add_field(f, self.dict, "Alkoholhalt","alkoholhalt")
        f.write("\n")

        f_lines = []
        for f_dict in self.dict["förpackningar"]:
            f_lines.append("%-18s %7s %7s %s %s" % (
                f_dict.get("namn"),
                f_dict.get("storlek"),
                f_dict.get("pris"),
                f_dict.get("anm1", ""),
                f_dict.get("anm2", "")))

        f.write(format_titled_fixed("Förpackningar", f_lines))
        f.write("\n")
        f.write(format_titled("URL", self.url))

        return f.getvalue()

class ProductFromWeb(Product):
    def __init__(self, prodno):
        self.url = "http://www.systembolaget.se/pris/owa/xdisplay?p_varunr=" + \
                   prodno
        u = urllib.urlopen(self.url)
        webpage = u.read()
        Product.__init__(self, webpage)


# Search class

search_m = MSet([("typlista",
                  MList("<H2>",
                        MSet([("typrubrik", MSDeH(r'<H2>(.*?) *</H2>')),
                              ("prodlista",
                               MList(r'<tr valign=top><td bgcolor="#.*?" width=320>',
                                     MSet([("varunr", MS(r'p_varunr=([0-9]+)')),
                                           ("namn", MS('<B>(.*?)</B>')),
                                           ("årgång", MSDeH(r'<font [^>]*?>(.*?)</font>')),
                                           ("varunr2", MS(r'<font [^>]*?>(.*?)</font>')),
                                           ("land", MS(r'<font [^>]*?>(.*?)</font>')),
                                           ("förplista",
                                            MList(r'<font [^>]*?>[0-9]+ml</font>',
                                                  MSet([("volym", MSVolym(r'<font [^>]*?>(.*?)</font>')),
                                                        ("pris", MS(r'<font [^>]*?>(.*?)</font>')),
                                                        ]))),
                                           ]))),
                              ]))),
                 ("antal", MS(r"Din sökning gav ([0-9]+) träffar.")),
                 ])

class Search:
    def __init__(self, webpage):
        (self.dict, pos) = search_m.match(webpage, 0, len(webpage))

    def valid(self):
        return self.dict.has_key("typlista")
    
    def to_string(self):
        f = cStringIO.StringIO()
        for typ in self.dict["typlista"]:
            f.write(typ["typrubrik"] + "\n\n")
            for vara in typ["prodlista"]:
                f.write("%7s  %s\n" % (vara["varunr"],
                                       vara["namn"]))
                fps = []
                for forp in vara["förplista"]:
                    fps.append("%11s (%s)" % (forp["pris"], forp["volym"]))
                #fps_txt = string.join(fps, ", ")
                f.write("         %4s %-32s %s\n" % (vara["årgång"],
                                               vara["land"],
                                               fps[0]))
                for fp in fps[1:]:
                    f.write("                                               %s\n" % fp)
                    
                f.write("\n")
            f.write("\n")
        return f.getvalue()

class SearchFromWeb(Search):
    def __init__(self, key, best = 0):
        if best:
            ordinarie = "0"
        else:
            ordinarie = "1"
        url = "http://www.systembolaget.se/pris/owa/zname?p_namn=%s&p_wwwgrptxt=%%25&p_soundex=1&p_ordinarie=%s" % (urllib.quote(key), ordinarie)
        u = urllib.urlopen(url)
        webpage = u.read()
        Search.__init__(self, webpage)

# MAIN

if len(sys.argv) <= 1:
    print "Ange ett eller flera sökvillkor, på formen:"
    print "  <nummer>      Visa information om varan"
    print "  <text>        Sök efter text i ordinarie sortimentet"
    print "  <test>+       Sök efter text i beställningssortimentet"
    print
    
for arg in sys.argv[1:]:
    if re.match("^[0-9]+$", arg):
        prod = ProductFromWeb(arg)
        if prod.valid():
            print prod.to_string(),
        else:
            print "Varunummer %s verkar inte finnas." % arg
    else:
        if arg[-1:] == "+":
            best = 1
            key = arg[:-1]
        else:
            best = 0
            key = arg            
        s = SearchFromWeb(key, best)
        if s.valid():
            print s.to_string(),
        else:
            print "Sökningen gav inga svar."
