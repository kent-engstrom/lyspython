#!/usr/bin/env python
# -*- coding: Latin-1 -*-
# (C) 2001-2002 Kent Engström. Released under the GNU GPL.

import sys
import string
import re
import cStringIO
import urllib
import getopt

try:
    from regexpmatcher import M, MS, MSDeH, MSet, MList, MLimit
except ImportError:
    sys.stderr.write("*"*72 + "\nYou need regexpmatcher.py, which is "
                     "available at the same place as\nsystembolaget.py\n" \
                     + "*"*72 + "\n")
    raise

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

def left_zero_pad(str, minsize):
    return ("0"*minsize + str)[-minsize:]

def varu_url(prod_no):
    return "http://www.systembolaget.se/pris/owa/xdisplay?p_varunr=" + \
           prod_no

# Classes matching a single piece of data

class MSF(MS):
    def elaborate_pattern(self, pattern):
        return r"<B>%s</B></td>\n<td valign=top>(.*)</td></tr>" % pattern

class MSC(MS):
    def elaborate_pattern(self, pattern):
        return r'<td width=70><center><img src="/bilder/klock_([0-9]+).gif" alt="[^"]*"><br> *%s *</center></td>' % pattern


class MSVolym(MS):
    def clean(self, data):
        return re.sub("[^ ]ml", " ml",
                      string.join(string.split(string.strip(data)), " "))

# Blåfärgade artiklar finns i alla butiker
class MSAllaB(MS):
    def clean(self, data):
        if data == "0000FF":
            return "Ja"
        else:
            return "Nej"


# Product class

prod_m = MSet([("grupp", MSDeH(r"<tr><td width=144> </td><td>\n(.+)\n")),
               ("namn", MS(r"<b>([^(]+)\(nr [^)]*\)")),
               ("varunr", MS(r"\(nr ([^)]*)\)")),
               ("ursprung",MSF("Ursprung")),
               ("producent",MSF("Producent")),
               ("förpackningar",
                MLimit(r'(?s)<td><table border="0" cellspacing="3">(.*?)</table></td></tr>',
                       MList("<tr>",
                             MSet([("namn", MS(r"<td>&#149; ([^<]+)</td>")),
                                   ("storlek", MS(r"<td align=right>([^<]+)</td>")),
                                   ("pris", MS(r"<td align=right>([^<]+)</td>")),
                                   ("anm1", MSDeH(r"<td>(.*?)</td>")),
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
               ("druvsorter",MSF("Druvsorter/Råvaror")),
               ("provad_årgång",MSF("Provad årgång")),
               ("provningsdatum",MSF("Provningsdatum")),
               ("alkoholhalt",MS("<B>Alkoholhalt</B></td>\n<td valign=top>(.*)</td></tr>")),
               ])    

class Product:
    def __init__(self, webpage):
        (self.dict, pos) = prod_m.match(webpage, 0, len(webpage))

    def valid(self):
        return self.dict.has_key("namn")

    def typical_price(self):
        # Typical price, suitable for HTML display
        # Choose price for 700 or 750 ml if present, else first price.
        vald = None
        normala = ["750 ml", "700 ml"]
        for f_dict in self.dict["förpackningar"]:
            if vald is None or f_dict.get("storlek")in normala:
                vald = f_dict

        pris = string.replace(string.replace(string.replace(vald["pris"],
                                                            ".", ":"),
                                             ":00", ":-"),
                              " kr", "")
        
        if vald["storlek"] in normala:
            return pris
        else:
            storlek = string.replace(vald["storlek"], "0 ml", " cl")
            return pris + " / " + storlek

    def clock_table(self):
        f = cStringIO.StringIO()
        f.write("<TABLE><TR>\n")
        for egenskap in ["sötma","fyllighet", "strävhet",
                         "fruktsyra", "beska"]:
            if self.dict.has_key(egenskap):
                f.write("<TD><CENTER><IMG SRC=klock_%s.gif><BR>%s&nbsp;</CENTER></TD>\n" % (
                    self.dict[egenskap],
                    string.capitalize(egenskap)))
        f.write("</TR></TABLE>\n")
        return f.getvalue()
            
    def to_string(self):
        f = cStringIO.StringIO()
        add_field(f, self.dict, "Namn","namn")
        add_field(f, self.dict, "Nr","varunr")
        add_field(f, self.dict, "Grupp","grupp")
        add_field(f, self.dict, "Ursprung","ursprung")
        add_field(f, self.dict, "Producent","producent")
        add_field(f, self.dict, "Druvsorter","druvsorter")
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

    def to_string_html(self):
        f = cStringIO.StringIO()
        f.write('<TR><TD COLSPAN=2><B>%s (nr <a href=%s>%s</a>) %s</B></TD></TR>\n' % \
                (self.dict["namn"],
                 varu_url(self.dict["varunr"]),
                 self.dict["varunr"],
                 self.typical_price()))

        f.write("<TR><TD>%s<BR>\n" % self.dict["ursprung"])
        try:
            f.write("%s<BR>\n" % self.dict["druvsorter"])
        except KeyError: pass
        f.write("%s</TD>\n" % string.replace(self.dict["alkoholhalt"], "volymprocent", "%"))

        f.write("<TD>%s</TD></TR>\n" % self.clock_table())

        f.write("<TR><TD COLSPAN=2><UL>\n")
        for rubrik in ["färg","doft","smak"]:
            if self.dict.has_key(rubrik):
                f.write("<LI>%s" % (self.dict[rubrik]))
        f.write("</UL></TD></TR>\n")
        
        f.write("<TR><TD COLSPAN=2>&nbsp;</TD></TR>\n")


        return f.getvalue()
            

class ProductFromWeb(Product):
    def __init__(self, prodno):
        self.url = varu_url(prodno)
        u = urllib.urlopen(self.url)
        webpage = u.read()
        Product.__init__(self, webpage)


# Search class

search_m = MSet([("typlista",
                  MList(r'<tr><td><font face="TimesNewRoman, Arial, Helvetica, sans-serif" size="5">',
                        MSet([("typrubrik", MSDeH(r'<b>(.*?) *</b>')),
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
                                                        ("allabutiker", MSAllaB(r'<font [^>]*?color="#([0-9A-Fa-f]+)">')),
                                                        ("pris", MS(r'([0-9.]+ kr)')),
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
                    if forp["allabutiker"] == "Ja":
                        ab = " alla"
                    else:
                        ab = ""
                    fps.append("%11s (%s)%s" % (forp["pris"],
                                                  forp["volym"],
                                                  ab))
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
        url = "http://www.systembolaget.se/pris/owa/zname?p_namn=%s&p_wwwgrptxt=%%25&p_rest=0&p_soundex=%s&p_ordinarie=%s" % (urllib.quote(key), soundex, ordinarie)
        u = urllib.urlopen(url)
        webpage = u.read()
        Search.__init__(self, webpage)



# ProductSearch class

p_search_m = MSet([("rubrik", MSDeH(r'(?s)<font face="TimesNewRoman, Arial, Helvetica, sans-serif" size="5"><b>([<A-ZÅÄÖ].*?)</b>')),
                   ("prodlista",
                    MList(r'<A HREF="xdisplay',
                          MSet([("varunr", MS(r'p_varunr=([0-9]+)')),
                                ("namn", MS('<B>(.*?)</B>')),
                                ("årgång", MSDeH(r'<font [^>]*?>([0-9]+|&nbsp;)<')),
                                ("varunr2", MS(r'<font [^>]*?>([0-9]+)<')),
                                ("land", MS(r'<font [^>]*?>(.*?)</font>')),
                                ("förplista",
                                 MList(r'<font face="Arial, Helvetica, sans-serif" size="2">[0-9]+ ml',
                                       MSet([("volym", MSVolym(r'<font [^>]*?>(.*?)<')),
                                             ("allabutiker", MSAllaB(r'<font [^>]*?color="#([0-9A-Fa-f]+)">')),
                                             ("pris", MS(r'([0-9.]+ kr)')),
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
                if forp["allabutiker"] == "Ja":
                    ab = " alla"
                else:
                    ab = ""
                fps.append("%11s (%s)%s" % (forp["pris"], forp["volym"], ab))
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
                 best = 0,
                 begr_butik = None,
                 p_type = None,
                 p_eko = None,
                 p_kosher = None,
                 p_nyhet = None,
                 p_varutyp = None,
                 p_ursprung = None,
                 p_klockor = [0,0,0],
                 p_fat_k = 0):
        if best:
            ordinarie = "0"
        else:
            ordinarie = "1"

        if begr_butik is None:
            begr_butik = "0"

        if p_type is None:
            p_type = "0"

        if p_eko:
            p_eko = "&p_eko=yes"
        else:
            p_eko = ""

        if p_kosher:
            p_kosher = "&p_kosher=yes"
        else:
            p_kosher = ""

        if p_nyhet:
            p_nyhet = "&p_nyhet=yes"
        else:
            p_nyhet = ""

        if p_varutyp is None:
            p_varutyp = ""
        else:
            p_varutyp = urllib.quote(p_varutyp)

        if p_ursprung is None:
            p_ursprung = ""
        else:
            p_ursprung = urllib.quote(p_ursprung)

        grupp = urllib.quote(grupp)
        url = "http://www.systembolaget.se/pris/owa/sokpipe.sokpara?p_wwwgrp=%s&p_varutyp=%s&p_ursprung=%s&p_prismin=%s&p_prismax=%s&p_type=%s&p_kl_1=%d&p_kl_2=%d&p_kl_3=%d&p_kl_fat=%d%s%s%s&p_butnr=%s&p_ordinarie=%s&p_rest=0&p_back=" % \
              (grupp, p_varutyp, p_ursprung,
               min_pris, max_pris,
               p_type,
               p_klockor[0], p_klockor[1], p_klockor[2], 
               p_fat_k,
               p_eko,
               p_kosher,
               p_nyhet,
               begr_butik, ordinarie)

        u = urllib.urlopen(url)
        webpage = u.read()
        ProductSearch.__init__(self, webpage)


# Stores class

stores_butikslista = MList(r'<tr><td width="200" valign=top>',
                           MSet([("kod", MS(r'thebut=([0-9]+)')),
                                 ("ort", MS(r'>(.*?)</a>')),
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
                butikslista = self.to_string_butiklista(lan["butikslista"])
                if butikslista:
                    f.write(lan["län"] + "\n\n")
                    f.write(butikslista)
                    f.write("\n")

        return f.getvalue()

    def to_string_butiklista(self, butiker):
        f = cStringIO.StringIO()
        for butik in butiker:
            if not butik.has_key("ort"):
                continue
            if self.ort and string.find(string.lower(butik["ort"]),
                                        string.lower(self.ort)) <> 0:
                continue
            f.write("  %s, %s (%s) [kod %s]\n" % \
                    (butik["ort"],
                     butik["adress"],
                     butik["telefon"],
                     left_zero_pad(butik["kod"],4)))
        return f.getvalue()

class StoresFromWeb(Stores):
    def __init__(self, prodno, lan, ort):
        url = "http://www.systembolaget.se/pris/owa/zvselect?p_artspec=&p_varunummer=%s&p_lan=%s&p_back=&p_rest=0" % (prodno, lan)
        u = urllib.urlopen(url)
        webpage = u.read()
        Stores.__init__(self, webpage,
                        single_lan = (lan <> "99"),
                        ort = ort)

# HTML-lista

def do_html(nr_lista):
    print "<BODY BGCOLOR=white>"
    print "<TABLE>"
    for varunr in nr_lista:
        prod = ProductFromWeb(varunr)
        if prod.valid():
            print prod.to_string_html()
        else:
            print "<TR><TD COLSPAN=2>Varunr %s saknas.</TD></TR>\n" % varunr
    print "</TABLE>"
    print "<P><FONT SIZE=-2>Uppgifterna är hämtade från <A HREF=http://www.systembolaget.se/svenska/varor/prislist/xindex.htm>Systembolagets katalog</A>.</FONT>"
    print "</BODY>"
    

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
begr_butik = None
grupp = None
p_type = None
p_eko = 0
p_kosher = 0
p_nyhet = 0
p_varutyp = None
p_ursprung = None
p_klockor = [0,0,0]
pos_fyllighet = None
pos_stravhet = None
pos_fruktsyra = None
pos_sotma = None
pos_beska = None
p_fat_k = 0

F_HELP = 0
F_NAMN = 1
F_PRODUKT = 2
F_VARA = 3
F_HTML = 4

funktion = F_HELP

options, arguments = getopt.getopt(sys.argv[1:],
                                   "",
                                   ["debug",
                                    "namn=",
                                    "html=",
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
                                    "öl",
                                    "cider",
                                    "blanddrycker",
                                    "lättdrycker",
                                    
                                    "min-pris=",
                                    "max-pris=",
                                    "begränsa-butik=",

                                    "större-flaskor",
                                    "helflaskor",
                                    "halvflaskor",
                                    "mindre-flaskor",
                                    "bag-in-box",
                                    "pappförpackningar",
                                    "burkar",
                                    "stora-burkar",

                                    "ekologiskt-odlat",
                                    "kosher",
                                    "nyheter",
                                    
                                    "varutyp=",
                                    "ursprung=",

                                    "fyllighet=",
                                    "strävhet=",
                                    "fruktsyra=",
                                    "sötma=",
                                    "beska=",
                                    
                                    "fat-karaktär",
                                    "ej-fat-karaktär",
                                    ])

for (opt, optarg) in options:
    if opt == "--debug":
        debug = 1
    elif opt == "--namn":
        funktion = F_NAMN
        namn = optarg
    elif opt == "--html":
        funktion = F_HTML
        nr_lista = optarg
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
        butiker = 1
        kanske_lan = find_lan(optarg)
        if kanske_lan is not None:
            lan = kanske_lan
        else:
            sys.stderr.write("[Län '%s' ej funnet --- ingen länsbegränsning.]\n" % optarg)
    elif opt == "--ort":
        butiker = 1
        ort = optarg
    elif opt == "--röda-viner":
        funktion = F_PRODUKT
        grupp = "RÖDA VINER"
        (pos_fyllighet, pos_stravhet, pos_fruktsyra) = range(0,3)
    elif opt == "--vita-viner":
        funktion = F_PRODUKT
        grupp = "VITA VINER"
        (pos_sotma, pos_fyllighet, pos_fruktsyra) = range(0,3)
    elif opt == "--övriga-viner":
        funktion = F_PRODUKT
        grupp = "ÖVRIGA VINER"
        (pos_sotma, pos_fyllighet, pos_fruktsyra) = range(0,3)
    elif opt == "--starkvin":
        funktion = F_PRODUKT
        grupp = "STARKVIN M. M."
    elif opt == "--sprit":
        funktion = F_PRODUKT
        grupp = "SPRIT"
    elif opt == "--öl":
        funktion = F_PRODUKT
        grupp = "ÖL"
        p_sotma_pos = 2
        (pos_beska, pos_fyllighet, pos_sotma) = range(0,3)
    elif opt == "--cider":
        funktion = F_PRODUKT
        grupp = "CIDER"
        (pos_sotma, pos_fyllighet, pos_fruktsyra) = range(0,3)
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
    elif opt == "--begränsa-butik":
        begr_butik = optarg
    elif opt == "--större-flaskor":
        p_type = "2"
    elif opt == "--helflaskor":
        p_type = "5"
    elif opt == "--halvflaskor":
        p_type = "7"
    elif opt == "--mindre-flaskor":
        p_type = "1"
    elif opt == "--bag-in-box":
        p_type = "3"
    elif opt == "--pappförpackningar":
        p_type = "4"
    elif opt == "--burkar":
        p_type = "6"
    elif opt == "--stora-burkar":
        p_type = "9"
    elif opt == "--kosher":
        p_kosher = 1
    elif opt == "--ekologiskt-odlat":
        p_eko = 1
    elif opt == "--nyheter":
        p_nyhet = 1
    elif opt == "--varutyp":
        p_varutyp = optarg
    elif opt == "--ursprung":
        p_ursprung = optarg
    elif opt == "--fyllighet":
        p_klockor[pos_fyllighet] = int(optarg)
    elif opt == "--strävhet":
        p_klockor[pos_stravhet] = int(optarg)
    elif opt == "--fruktsyra":
        p_klockor[pos_fruktsyra] = int(optarg)
    elif opt == "--sötma":
        p_klockor[pos_sotma] = int(optarg)
    elif opt == "--beska":
        p_klockor[pos_beska] = int(optarg)
        
    elif opt == "--fat-karaktär":
        p_fat_k = 1
    elif opt == "--ej-fat-karaktär":
        p_fat_k = 2
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
            
elif funktion == F_HTML:
    # HTML-lista
    do_html(string.split(nr_lista,","))
           
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
                                 best = best,
                                 begr_butik = begr_butik,
                                 p_type = p_type,
                                 p_eko = p_eko,
                                 p_kosher = p_kosher,
                                 p_nyhet = p_nyhet,
                                 p_varutyp = p_varutyp,
                                 p_ursprung = p_ursprung,
                                 p_klockor = p_klockor,
                                 p_fat_k = p_fat_k)
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
    print "Varuvisning i HTML-format:"
    print """
   %s --html VARUNR,VARUNR,...
""" % ((sys.argv[0],))
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
   %s [{ --större-flaskor | --mindre-flaskor |
   %s    --helflaskor     | --halvflaskor |
   %s    --bag-in-box     | --pappförpackningar |
   %s    --burkar         | --stora-burkar}]
   %s [{--ekologiskt-odlat | --kosher | --nyheter}
   %s [--varutyp=EXAKT-TYP]
   %s [--ursprung=EXAKT-LAND/REGION]
   %s [--begränsa-butik=BUTIKSKOD]
   %s [{--fyllighet=N | --strävhet=N | --fruktsyra=N |
   %s   --sötma=N     | --beska=N}]
   %s [{--fat-karaktär | --ej-fat-karaktär}]
""" % ((sys.argv[0],) + (" " * len(sys.argv[0]),)*15)
    
    
