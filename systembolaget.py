#!/usr/bin/env python

import sys
import string
import re
import cStringIO
import urllib
import getopt

# Län

lanslista = [
    ("02", "Stockholms län"),
    ("03", "Uppsala län"),
    ("04", "Södermanlands län"),
    ("05", "Östergötlands län"),
    ("06", "Jönköpings län"),
    ("07", "Kronobergs län"),
    ("08", "Kalmar län"),
    ("09", "Gotlands län"),
    ("10", "Blekinge län"),
    ("11", "Skåne län"),
    ("13", "Hallands län"),
    ("14", "Västra Götalands län"),
    ("17", "Värmlands län"),
    ("18", "Örebro län"),
    ("19", "Västmanlands län"),
    ("20", "Dalarnas län"),
    ("21", "Gävleborgs län"),
    ("22", "Västernorrlands län"),
    ("23", "Jämtlands län"),
    ("24", "Västerbottens län"),
    ("25", "Norrbottens län"),
    ]

def find_lan(text):
    res = []
    text = string.lower(text)
    for (kod, namn) in lanslista:
        if string.find(string.lower(namn), text) == 0:
            res.append(kod)
    if len(res) == 1:
        return res[0]
    else:
        return None

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

def add_to_list_from_dict(list, dict, key, fun = None):
    if dict.has_key(key):
        data = dict[key]
        if fun:
            data = fun(data)
        list.append(data)

def move_year_to_front(name):
    m = re.match(".*([12][90][0-9][0-9])$", name)
    if m:
        name = m.group(1) + " " + string.strip(name[:-4])
    return name

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
            if debug: print "Found", m.group(1)
            data = self.clean(m.group(1))
            if self.advance:
                return (data, m.end(1))
            else:
                return (data, s_pos)
        else:
            if debug: print "Not found"
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
            if debug:
                print "Looking for",name,"between",s_pos,"and",e_pos
                print "--> %s" % data[s_pos:min(s_pos+110,e_pos)]
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
        if debug: print "Positions for", self.begin,":", pos
        for i in range(0,len(pos)-1):
            if debug:
                print "Looking for list entry between",pos[i],"and",pos[i+1]
                if (pos[i+1] - pos[i]) < 400:
                    print "Entry is:", data[pos[i]:pos[i+1]]
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
               ("varunr", MS(r"\(nr ([^)]*)\)")),
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
        add_field(f, self.dict, "Namn","namn")
        add_field(f, self.dict, "Nr","varunr")
        add_field(f, self.dict, "Grupp","grupp")
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

    def to_string_brief(self):
        f = cStringIO.StringIO()
        f.write("%s [%s]\n" %(move_year_to_front(self.dict["namn"]),
                              self.dict["varunr"]))
        lf = []
        add_to_list_from_dict(lf, self.dict, "ursprung")
        add_to_list_from_dict(lf, self.dict, "producent")
        add_to_list_from_dict(lf, self.dict, "provad_årgång")
        add_to_list_from_dict(lf, self.dict, "hållbarhet")
        f.write("      %s\n" % string.join(lf, ", "))
        lf = []
        for egenskap in ["sötma","fyllighet","strävhet","fruktsyra","beska"]:
            kod = string.capitalize(egenskap)[:2]+":"
            add_to_list_from_dict(lf, self.dict, egenskap,
                                  lambda x, kod = kod: kod + x)
        add_to_list_from_dict(lf, self.dict, "alkoholhalt",
                              lambda x: string.replace(x, " volymprocent", "%"))
            
        for f_dict in self.dict["förpackningar"]:
            lf.append("%s/%s" % (f_dict.get("pris"),
                                 f_dict.get("storlek")))
        f.write("      %s\n" % string.join(lf, ", "))
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
                               MList(r'<tr valign=top><td bgcolor="#[0-9a-fA-F]+" width=320>',
                                     MSet([("varunr", MS(r'p_varunr=([0-9]+)')),
                                           ("namn", MS('<B>(.*?)</B>')),
                                           ("årgång", MSDeH(r'<font [^>]*?>(.*?)</font>')),
                                           ("varunr2", MS(r'<font [^>]*?>(.*?)</font>')),
                                           ("land", MS(r'<font [^>]*?>(.*?)</font>')),
                                           ("förplista",
                                            MList(r'<font face="Arial, Helvetica, sans-serif" size="2">[0-9]+ml</font>',
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
    def __init__(self, key, best = 0, soundex = 0):
        if best:
            ordinarie = "0"
        else:
            ordinarie = "1"
        if soundex:
            soundex = "1"
        else:
            soundex = "0"
        url = "http://www.systembolaget.se/pris/owa/zname?p_namn=%s&p_wwwgrptxt=%%25&p_soundex=%s&p_ordinarie=%s" % (urllib.quote(key), soundex, ordinarie)
        u = urllib.urlopen(url)
        webpage = u.read()
        Search.__init__(self, webpage)



# ProductSearch class

p_search_m = MSet([("rubrik", MSDeH(r'(?s)<H2>(.*?)</H2>')),
                   ("prodlista",
                    MList(r'<A HREF="/pris/owa/xdisplay',
                          MSet([("varunr", MS(r'p_varunr=([0-9]+)')),
                                ("namn", MS('<B>(.*?)</B>')),
                                ("årgång", MSDeH(r'<font [^>]*?>(.*?)</font>')),
                                ("varunr2", MS(r'<font [^>]*?>(.*?)</font>')),
                                ("land", MS(r'<font [^>]*?>(.*?)</font>')),
                                ("förplista",
                                 MList(r'<font face="Arial, Helvetica, sans-serif" size="2">[0-9]+ml</font>',
                                       MSet([("volym", MSVolym(r'<font [^>]*?>(.*?)</font>')),
                                             ("pris", MS(r'<font [^>]*?>(.*?)</font>')),
                                           ]))),
                                ]))),
                   ("antal", MS(r"Din sökning gav ([0-9]+) träffar.")),
                   ])

class ProductSearch:
    def __init__(self, webpage):
        (self.dict, pos) = p_search_m.match(webpage, 0, len(webpage))
        
    def valid(self):
        return self.dict.has_key("prodlista")
    
    def to_string(self):
        f = cStringIO.StringIO()
        
        f.write(self.dict["rubrik"] + "\n\n")
        
        for vara in self.dict["prodlista"]:
            f.write("%7s  %s\n" % (vara["varunr"],
                                   vara["namn"]))
            fps = []
            for forp in vara["förplista"]:
                fps.append("%11s (%s)" % (forp["pris"], forp["volym"]))
            f.write("         %4s %-32s %s\n" % (vara.get("årgång",""),
                                                 vara["land"],
                                                 fps[0]))
            for fp in fps[1:]:
                f.write("                                               %s\n" % fp)
                    
            f.write("\n")
        f.write("\n")
        return f.getvalue()

class ProductSearchFromWeb(ProductSearch):
    def __init__(self, grupp,
                 typ = None,
                 ursprung = None,
                 min_pris = 0, max_pris = 1000000,
                 best = 0):
        if best:
            ordinarie = "0"
        else:
            ordinarie = "1"

        grupp = urllib.quote(grupp)
        url = "http://www.systembolaget.se/pris/owa/xasearch?p_wwwgrp=%s&p_varutyp=&p_ursprung=&p_prismin=%s&p_prismax=%s&p_type=0&p_prop=0&p_butnr=&p_ordinarie=%s&p_rest=0&p_back=" % \
              (grupp, min_pris, max_pris, ordinarie)

        u = urllib.urlopen(url)
        webpage = u.read()
        ProductSearch.__init__(self, webpage)


# Stores class

stores_butikslista = MList(r'<tr><td width="200" valign=top>',
                           MSet([("ort", MS(r'<a [^>]*>(.*?)</a>')),
                                 ("adress", MS(r'<td[^>]*>(.*?)</td>')),
                                 ("telefon", MS(r'<td[^>]*>(.*?)</td>')),
                                 ]))

stores_lan_m = MSet([("namn", MS(r'<H2><B>([^(]*?)\(')),
                     ("varunr", MS(r'\(([0-9]+)\)')),
                     ("länslista",
                      MList("<H4>",
                            MSet([("län", MS(r'<H4>(.*?)</H4>')),
                                  ("butikslista",
                                   stores_butikslista)
                                  ]))),
                     ])

stores_ejlan_m = MSet([("namn", MS(r'<H2><B>([^(]*?)\(')),
                       ("varunr", MS(r'\(([0-9]+)\)')),
                       ("butikslista", stores_butikslista),
                       ])

class Stores:
    def __init__(self, webpage, single_lan = 0, ort = None):
        self.single_lan = single_lan
        if single_lan:
            matcher = stores_ejlan_m
        else:
            matcher = stores_lan_m
        self.ort = ort
        (self.dict, pos) = matcher.match(webpage, 0, len(webpage))
        
    def valid(self):
        return self.dict.has_key("namn")
    
    def to_string(self, show_heading = 0):
        f = cStringIO.StringIO()
        if show_heading:
            f.write("%s (%s)\n\n" %(self.dict["namn"],
                                    self.dict["varunr"]))
        if self.single_lan:
            f.write(self.to_string_butiklista(self.dict["butikslista"]))
        else:
            for lan in self.dict["länslista"]:
                f.write(lan["län"] + "\n\n")
                f.write(self.to_string_butiklista(lan["butikslista"]))
                f.write("\n")

        return f.getvalue()

    def to_string_butiklista(self, butiker):
        f = cStringIO.StringIO()
        for butik in butiker:
            if self.ort and string.find(string.lower(butik["ort"]),
                                        string.lower(self.ort)) <> 0:
                continue
            f.write("  %s, %s (%s)\n" % (butik["ort"],
                                         butik["adress"],
                                         butik["telefon"]))
        return f.getvalue()

class StoresFromWeb(Stores):
    def __init__(self, prodno, lan, ort):
        url = "http://www.systembolaget.se/pris/owa/zvselect?p_artspec=&p_varunummer=%s&p_lan=%s&p_back=&p_rest=0" % (prodno, lan)
        u = urllib.urlopen(url)
        webpage = u.read()
        Stores.__init__(self, webpage,
                        single_lan = (lan <> "99"),
                        ort = ort)

# MAIN

# Option handling

debug = 0
best = 0
soundex = 0
kort = 0
butiker = 0
barabutiker = 0
lan = "99"
ort = None
min_pris = 0
max_pris = 1000000
grupp = None

F_HELP = 0
F_NAMN = 1
F_PRODUKT = 2
F_VARA = 3
funktion = F_HELP

options, arguments = getopt.getopt(sys.argv[1:],
                                   "",
                                   ["debug",
                                    "namn=",
                                    "beställningssortimentet",
                                    "soundex",
                                    "kort",
                                    "butiker",
                                    "bara-butiker",
                                    "län=",
                                    "ort=",
                                    "röda-viner",
                                    "vita-viner",
                                    "övriga-viner",
                                    "starkvin",
                                    "sprit",
                                    "öl-och-cider",
                                    "blanddrycker",
                                    "lättdrycker",
                                    "min-pris=",
                                    "max-pris=",
                                    ])

for (opt, optarg) in options:
    if opt == "--debug":
        debug = 1
    elif opt == "--namn":
        funktion = F_NAMN
        namn = optarg
    elif opt == "--beställningssortimentet":
        best = 1
    elif opt == "--soundex":
        soundex = 1
    elif opt == "--kort":
        kort = 1
    elif opt == "--butiker":
        butiker = 1
    elif opt == "--bara-butiker":
        butiker = 1
        barabutiker = 1
    elif opt == "--län":
        kanske_lan = find_lan(optarg)
        if kanske_lan is not None:
            lan = kanske_lan
        else:
            sys.stderr.write("[Län '%s' ej funnet --- ingen länsbegränsning.]\n" % optarg)
    elif opt == "--ort":
        ort = optarg
    elif opt == "--röda-viner":
        funktion = F_PRODUKT
        grupp = "RÖDA VINER"
    elif opt == "--vita-viner":
        funktion = F_PRODUKT
        grupp = "VITA VINER"
    elif opt == "--övriga-viner":
        funktion = F_PRODUKT
        grupp = "ÖVRIGA VINER"
    elif opt == "--starkvin":
        funktion = F_PRODUKT
        grupp = "STARKVIN M. M."
    elif opt == "--sprit":
        funktion = F_PRODUKT
        grupp = "SPRIT"
    elif opt == "--öl-och-cider":
        funktion = F_PRODUKT
        grupp = "ÖL & CIDER"
    elif opt == "--blanddrycker":
        funktion = F_PRODUKT
        grupp = "BLANDDRYCKER"
    elif opt == "--lättdrycker":
        funktion = F_PRODUKT
        grupp = "LÄTTDRYCKER"
    elif opt == "--min-pris":
        min_pris = optarg
    elif opt == "--max-pris":
        max_pris = optarg
    else:
        sys.stderr.write("Internt fel (%s ej behandlad)" % opt)
        sys.exit(1)

if funktion == F_HELP and len(arguments) > 0:
    funktion = F_VARA

if funktion == F_VARA:
    # Varufunktion
    for varunr in arguments:
        prod = ProductFromWeb(varunr)
        if not barabutiker:
            if prod.valid():
                if kort:
                    txt = prod.to_string_brief()
                else:
                    txt = prod.to_string()
                print txt
            else:
                print "Varunummer %s verkar inte finnas." % varunr
                continue
        
        if butiker:
            stores = StoresFromWeb(varunr, lan, ort)
            if stores.valid():
                print stores.to_string(show_heading = barabutiker)
            else:
                print "Inga butiker med vara %s funna." % varunr
            
elif funktion == F_NAMN:
    # Namnsökning
        s = SearchFromWeb(namn, best, soundex)
        if s.valid():
            print s.to_string(),
        else:
            print "Sökningen gav inga svar."

elif funktion == F_PRODUKT:
    # Produktsökning
        s = ProductSearchFromWeb(grupp,
                                 min_pris = min_pris,
                                 max_pris = max_pris,
                                 best = best)
        if s.valid():
            print s.to_string(),
        else:
            print "Sökningen gav inga svar."

else: # F_HELP
    print "systembolaget.py --- kommandoradssökning i Systembolagets katalog"
    print "-----------------------------------------------------------------"
    print 
    print "Varuvisning (med möjlighet att visa butiker som har varan):"
    print """
   %s [--kort] [--butiker] [--bara-butiker]
   %s [--län=LÄN] [--ort=ORT]
   %s VARUNR...
""" % ((sys.argv[0],) + (" " * len(sys.argv[0]),)*2)
    print "Namnsökning:"
    print """
   %s [--beställningssortimentet] [--soundex]
   %s  --namn=NAMN
""" % (sys.argv[0], " " * len(sys.argv[0]))
    print "Produktsökning:"
    print """
   %s { --röda-viner   | --vita-viner   |
   %s   --övriga-viner | --starkvin     |
   %s   --sprit        | --öl-och-cider |
   %s   --blanddrycker | --lättdrycker }
   %s [--min-pris=MIN] [--max-pris=MAX] 
""" % ((sys.argv[0],) + (" " * len(sys.argv[0]),)*4)
    
    
