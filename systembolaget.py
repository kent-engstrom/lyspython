#!/usr/bin/env python2
# -*- coding: Latin-1 -*-
# (C) 2001-2003 Kent Engström. Released under the GNU GPL.

import sys
import string
import re
import cStringIO
import urllib
import getopt
import md5

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
    
def add_field(f, title, data):
    if data:
        f.write(format_titled(title, data))

def add_to_list(list, data, fun = None):
    if data:
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
    return "http://www.systembolaget.se/SokDrycker/Produkt?VaruNr=" + prod_no

def klock_argument(s):
    # Parse number or range into min-max tuple
    try:
        (smin,smax) = string.split(s, "-")
    except ValueError:
        single = int(s)
        return (single, single)

    if smin == "":
        return (0,int(smax))
    elif smax== "":
        return (int(smin), 12)
    else:
        return (int(smin), int(smax))

# A helper class to make debugging easier and faster by caching
# webpages and storing them if WEBPAGE_DEBUG is true.
# This is only for debugging, as there is no code to handle GC
# nor to check for out-of-data information.

WEBPAGE_DEBUG = 0

class WebCache:
    def __init__(self):
        pass

    def filename(self, url):
        return "SYSTEMBOLAGET_" + md5.md5(url).hexdigest()
        
    def cached(self, url):
        if not WEBPAGE_DEBUG: return None
        try:
            f = open(self.filename(url))
            if WEBPAGE_DEBUG > 1: print "WP CACHED", url
            return f.read()
        except IOError:
            return None
        
    def cache(self, url, data):
        if not WEBPAGE_DEBUG: return None
        f = open(self.filename(url), "w")
        f.write(data)
        f.close()
        if WEBPAGE_DEBUG > 1: print "WP NEW", url
        
    def get(self, url): 
        cached = self.cached(url)
        if cached:
            return cached

        u = urllib.urlopen(url)
        data = u.read()
        u.close()

        self.cache(url, data)
        return data
       
The_WebCache = WebCache()

class WebPage:
    def __init__(self, url):
        self.url = url
        
    def get(self):
        return The_WebCache.get(self.url)
        
# Classes matching a single piece of data

class MSFargDoftSmak(MSDeH):
    def elaborate_pattern(self, pattern):
        return r'(?s)<b>%s</b>(.*?)<br>' % pattern

class MSC(MS):
    def elaborate_pattern(self, pattern):
        return r'<img id="ProductDetail1_ImageProduct." src="/Images/([0-9]+).gif" alt="%s.*"' % pattern

class MSF(MSDeH):
    def elaborate_pattern(self, pattern):
        return r'(?s)<td class="text10pxfet" .*?>%s</td>.*?<td.*?>(.*?)</td>' % pattern



class MSVolym(MS):
    def clean(self, data):
        # Things to clean up: spaces around the data
        # No space, or more than one space between digits and "ml"
        return string.join(string.split(string.strip(string.replace(data, "ml", " ml"))), " ")

# Object validity

(NEW, VALID, INVALID) = range(0,3)

# Product class

class Product:
    def __init__(self):
        self.state = NEW
        self.butiker = []
        
    # Parse the product page
    def from_html_normal(self, webpage):
        assert self.state == NEW

        m = MSet([("grupp", MSDeH(r'(?s)<td class=text10pxfetvit.*?>(.*?)</td>')),
                  ("namn", MSDeH(r'<span class="rubrikstor">(.*?)\(nr')),
                  ("varunr", MS(r'(?s)\(nr.*?([0-9]+)')),
                  ("distrikt", MSDeH(r'<td class="text10px">(.*?)&nbsp;')),
                  ("producent", MSDeH(r'\((.*?)\)')),
                  ("land", MSDeH(r'<img id="ProductDetail1_ImageFlag".*?>&nbsp;(.*?)</td>')),
                  ("farg", MSFargDoftSmak("Färg")),
                  ("doft", MSFargDoftSmak("Doft")),
                  ("smak", MSFargDoftSmak("Smak")),
                  ("sotma", MSC("Sötma", advance = 0)),
                  ("fyllighet", MSC("Fyllighet", advance = 0)),
                  ("stravhet", MSC("Strävhet", advance = 0)),
                  ("fruktsyra", MSC("Fruktsyra", advance = 0)),
                  ("beska", MSC("Beska", advance = 0)),
                  ("lagring", MSF("Lagring")),
                  ("druvsorter", MSF("Druvsorter/råvaror")),
                  ("alkoholhalt", MSF("Alkoholhalt")),
                  ("argang", MSF("Provad årgång")),
                  ("provningsdatum", MSF("Provningsdatum")),
                  ("anvandning", MSDeH(r'<td class="text10px" width="174" bgColor="#ffffff" height="10">(.*?)</td>')),
                  ])

        m.get_into_object(webpage, self)
        #for k,v in self.__dict__.items(): print "%-16s = %s" % (k,v)

        self.namn = self.namn.strip()
        if self.namn and self.varunr:
            self.state = VALID
        else:
            self.state = INVALID
            return self
        
        self.forpackningar = []
        for f in MLimit(r'(?s)<th align="Left" bgcolor="#CCCCCC" width="90">Förpackning</th>(.*?)</table>', \
                        MList("<tr",
                              M())).get(webpage):
            c = Container().from_html_normal(f)
            self.forpackningar.append(c)

        return self

    # Parse the product information in a name or group search result.
    # We used to have separate regexps for the two cases in the specific
    # methods below; this function should not be called directly.
    def from_html_productlist_common(self, webfragment, grupp, best = 0):
        assert self.state == NEW

        m = MSet([("varunr", MS(r'p_varunr=([0-9]+)')),
                  ("namn", MS(r'(?s)>(.*?)</a>')),
                  ("årgång", MSDeH(r'(?s)<td.*?>(.*?)</td>')),
                  ("varunr2", MSDeH(r'(?s)<td.*?>(.*?)</td>')),
                  ("land", MSDeH(r'(?s)<td.*?>(.*?)</td>')),
                  ("förpdata", M()),
                  ])

        dict = m.get(webfragment)
        self.grupp = grupp
        self.varunr = dict.get("varunr")
        self.namn = dict.get("namn")
        self.ursprung = dict.get("land")
        self.argang = dict.get("årgång","")
        
        # Earlier, we split on products and extracted a whole list of containers
        # from the product entry. Now, we are forced to parse each container as a separate
        # product, and merge them in the ProductList class.
        self.forpackningar = []
        fd = dict["förpdata"]
        c = Container().from_html_productlist(fd, best)
        self.forpackningar.append(c)

        if self.namn and self.varunr:
            self.state = VALID
        else:
            self.state = INVALID

        return self

    # Parse the product information in a name search result
    from_html_name = from_html_productlist_common
        

    # Parse the product information in a group search result
    from_html_group = from_html_productlist_common

    # Parse the stores list for a product
    def from_html_stores(self, webpage, lan, ort):
        if lan <> "99":
            # Ett enda län
            self.butiker = []
            for b in MList(r'<tr><td width="200" valign=top>', M()).get(webpage):
                s = Store().from_html(b)
                if s.matches_ort(ort):
                    self.butiker.append(s)
        else:
            # En lista av län
            lista = MList("<H4>", MSet([("län", MS(r'<H4>(.*?)</H4>')),
                                         ("butikslista",
                                          MList(r'<tr><td width="200" valign=top>',
                                               M()))])).get(webpage)
            self.butiker = []
            for l in lista:
                lan = l["län"]
                for b in l["butikslista"]:
                    s = Store().from_html(b, lan)
                    if s.matches_ort(ort):
                        self.butiker.append(s)

    def valid(self):
        return self.state == VALID

    def typical_price(self):
        # Typical price, suitable for HTML display
        # Choose price for 700 or 750 ml if present, else first price.
        vald = None
        normala = ["750 ml", "700 ml"]
        for c in self.forpackningar:
            if vald is None or c.storlek in normala:
                vald = c

        if vald is None:
            return "(pris saknas)"
        
        pris = string.replace(string.replace(string.replace(vald.pris,
                                                            ".", ":"),
                                             ":00", ":-"),
                              " kr", "")
        
        if vald.storlek in normala:
            return pris
        else:
            storlek = string.replace(vald.storlek, "0 ml", " cl")
            return pris + " / " + storlek

    def to_string_stores(self):
        f = cStringIO.StringIO()
        tidigare_lan = None
        antal_lan = 0
        for butik in self.butiker:
            if butik.lan <> tidigare_lan:
                if antal_lan >0:
                    f.write("\n")
                f.write("%s\n\n" % butik.lan)
                tidigare_lan = butik.lan
                antal_lan = antal_lan + 1
                
            f.write(butik.to_string())
            
        return f.getvalue()

    def to_string_normal(self, butiker=0):
        f = cStringIO.StringIO()
        add_field(f, "Namn", self.namn)
        add_field(f, "Nr", self.varunr)
        add_field(f, "Grupp", self.grupp)
        add_field(f, "Distrikt", self.distrikt)
        add_field(f, "Land", self.land)
        add_field(f, "Producent", self.producent)
        add_field(f, "Druvsorter", self.druvsorter)
        f.write("\n")
        add_field(f, "Färg", self.farg)
        add_field(f, "Doft", self.doft)
        add_field(f, "Smak", self.smak)
        f.write("\n")
        add_field(f, "Sötma", self.sotma)
        add_field(f, "Fyllighet", self.fyllighet)
        add_field(f, "Strävhet", self.stravhet)
        add_field(f, "Fruktsyra", self.fruktsyra)
        add_field(f, "Beska", self.beska)
        f.write("\n")
        add_field(f, "Användning", self.anvandning)
        add_field(f, "Lagring", self.lagring)
        add_field(f, "Provad årgång", self.argang)
        add_field(f, "Provad", self.provningsdatum)
        add_field(f, "Alkoholhalt", self.alkoholhalt)
        f.write("\n")

        f_lines = []
        for c in self.forpackningar:
            f_lines.append("%-18s %10s %10s %s" % (
                c.namn,
                c.storlek,
                c.pris,
                c.anm,
                ))

        f.write(format_titled_fixed("Förpackningar", f_lines))
        f.write("\n")
        f.write(format_titled("URL", self.url))

        if butiker:
            f.write("\n" + self.to_string_stores())
            
        return f.getvalue()

    def to_string_brief(self):
        f = cStringIO.StringIO()
        f.write("%s [%s]\n" %(move_year_to_front(self.namn),
                              self.varunr))
        lf = []
        add_to_list(lf, self.land)
        add_to_list(lf, self.distrikt)
        add_to_list(lf, self.producent)
        add_to_list(lf, self.argang)
        add_to_list(lf, self.lagring)
        f.write("      %s\n" % string.join(lf, ", "))
        lf = []
        for (kod, varde) in [("Sö", self.sotma),
                             ("Fy", self.fyllighet),
                             ("St", self.stravhet),
                             ("Fr", self.fruktsyra),
                             ("Be", self.beska)]:
            kod = kod + ":"
            add_to_list(lf, varde, lambda x, kod = kod: kod + x)

        add_to_list(lf, self.alkoholhalt,
                        lambda x: string.replace(x, " volymprocent", "%"))
            
        for c in self.forpackningar:
            lf.append("%s/%s" % (c.pris, c.storlek))
        f.write("      %s\n" % string.join(lf, ", "))
        return f.getvalue()

    def clock_table(self):
        f = cStringIO.StringIO()
        f.write("<TABLE><TR>\n")
        for (namn, varde) in [("Sötma",     self.sotma),
                              ("Fyllighet", self.fyllighet),
                              ("Strävhet",  self.stravhet),
                              ("Fruktsyra", self.fruktsyra),
                              ("Beska",     self.beska)]:
            if varde is not None:
                f.write("<TD><CENTER><IMG SRC=klock_%s.gif><BR>%s&nbsp;</CENTER></TD>\n" % (
                    varde, namn))
                
        f.write("</TR></TABLE>\n")
        return f.getvalue()
            
    def to_string_html(self,
                       include_sensory=1):
        f = cStringIO.StringIO()
        f.write('<TR><TD COLSPAN=2><B>%s (nr <a href=%s>%s</a>) %s</B></TD></TR>\n' % \
                (self.namn,
                 varu_url(self.varunr),
                 self.varunr,
                 self.typical_price()))

        f.write("<TR><TD>%s, %s<BR>\n" % (self.land, self.distrikt))
        if self.druvsorter is not None:
            f.write("%s<BR>\n" % self.druvsorter)
        f.write("%s</TD>\n" % string.replace(self.alkoholhalt, "volymprocent", "%"))

        f.write("<TD>%s</TD></TR>\n" % self.clock_table())

        if include_sensory:
            f.write("<TR><TD COLSPAN=2><UL>\n")
            for varde in [self.farg, self.doft, self.smak]:
                if varde is not None and varde <> "":
                    f.write("<LI>%s" % (varde))
            f.write("</UL></TD></TR>\n")
        
        f.write("<TR><TD COLSPAN=2>&nbsp;</TD></TR>\n")

        return f.getvalue()

    def to_string_productlist(self):
        f = cStringIO.StringIO()

        f.write("%7s  %s\n" % (self.varunr,
                               self.namn))
        fps = []
        for forp in self.forpackningar:
            fps.append(forp.to_string_productlist())

        f.write("         %4s %-32s %s\n" % (self.argang,
                                             self.ursprung,
                                             fps[0]))
        for fp in fps[1:]:
            f.write("                                               %s\n" % fp)
                    
        return f.getvalue()

    def search(self, prodno, butiker = 0, lan = None, ort = None):
        self.url = varu_url(str(prodno))

        # Product page
        webpage = WebPage(self.url).get()
        self.from_html_normal(webpage)

        # Stores
        if butiker:
            url = "http://www.systembolaget.se/pris/owa/zvselect?p_artspec=&p_varunummer=%s&p_lan=%s&p_back=" % (prodno, lan)
            webpage = WebPage(url).get()
            self.from_html_stores(webpage, lan, ort)
            
        # The final touch
        return self

    def add_containers_from(self, other):
        assert len(other.forpackningar) > 0
        self.forpackningar.extend(other.forpackningar)

# Container class

class Container:
    def __init__(self):
        self.state = NEW
        
    # Parse the container information in a product page
    def from_html_normal(self, webfragment):
        assert self.state == NEW

        # We use this instead of inline field = Mfoo(...).get(webfragment)
        # as we believe the matches below need to be sequenced
        # just the way MSet does.
        
        MSet([("namn", MS(r'<td bgcolor="#FFFFFF" width="90">(.*?)</td>')),
              ("storlek", MS(r'<td align="Right" bgcolor="#FFFFFF" width="60">(.*?)</td>')),
              ("pris", MS(r'<td class="text10pxfet".*?>([0-9.]+)')),
              ("anm", MSDeH(r'<td align="Center" bgcolor="#FFFFFF">(.*?)</td>')),
              ]).get_into_object(webfragment,self)
        
        self.sortiment = "?"
        
        assert self.namn and self.storlek and self.pris
        self.pris = self.pris + " kr"
        self.state = VALID

        return self

    # Parse the container information in a name or group search result
    def from_html_productlist(self, webfragment, best = 0):
        assert self.state == NEW

        dict = MSet([("volym", MSVolym(r'(?s)<td.*?>(.*?)</td>')),
                     ("pris", MS(r'(?s)<td.*?>(.*?)</td>')),
                     ("allabutiker", MS(r'(Finns i alla butiker)')),
                     ("bestsort", MS(r'(Beställningsvara)')),
                     ]).get(webfragment)
        self.namn = None
        self.storlek = dict.get("volym")
        self.pris = dict.get("pris")
        self.anm1 = None
        self.anm2 = None
        if dict.has_key("allabutiker"):
            self.sortiment = "alla"
        elif best or dict.has_key("bestsort"):
            self.sortiment = "best"
        else:
            self.sortiment = ""

        assert self.storlek and self.pris
        self.state = VALID

        return self

    def to_string_productlist(self):
        return "%11s (%s) %s" % (self.pris, self.storlek, self.sortiment)

    def valid(self):
        return self.state == VALID

# Store class

class Store:
    def __init__(self):
        self.state = NEW

    # Parse the store information in a store list item
    def from_html(self, webfragment, lan = None):
        assert self.state == NEW

        dict = MSet([("kod", MS(r'butiknr=([0-9]+)')),
                     ("ort", MS(r'>(.*?)</a>')),
                     ("adress", MS(r'<td[^>]*>(.*?)</td>')),
                     ("telefon", MS(r'<td[^>]*>(.*?)</td>')),
                     ]).get(webfragment)

        self.lan = lan
        self.kod = dict.get("kod")
        self.ort = dict.get("ort")
        self.adress = dict.get("adress")
        self.telefon = dict.get("telefon")

        assert self.kod and self.ort and self.adress
        self.state = VALID

        return self
    
    def valid(self):
        return self.state == VALID

    def matches_ort(self, ort):
        if ort is None:
            return 1 # None matches all
        return self.ort.lower().find(ort.lower()) == 0
    
    def to_string(self):
        return "  %s, %s (%s) [kod %s]\n" % \
               (self.ort,
                self.adress,
                self.telefon,
                left_zero_pad(self.kod,4))


# ProductList class

(S_BOTH, S_ORD, S_BEST) = range(0,3)

class ProductList:
    def __init__(self):
        self.state = NEW
        
    # Parse the result of a name search 
    def from_html_name(self, webpage):
        assert self.state == NEW
        
        typlista = MList(r'<table width="640" border="0" cellspacing="0" cellpadding="0">',
                         MSet([("typrubrik", MSDeH(r'(?s)<font class="rubrik2">(.*?)</font>')),
                               ("prodlista",
                                MList(r'<td width="290" align=',
                                      M())),
                               ])).get(webpage)
        self.lista = []
        for t in typlista:
            grupp = t["typrubrik"]
            
            for p in t["prodlista"]:
                prod = Product().from_html_name(p, grupp)
                
                if prod.valid():
                    # A real product
                    self.lista.append(prod)
                else:
                    # This should be a dummy product with a container
                    # to be added to the last real product
                    self.lista[-1].add_containers_from(prod)
            
        if self.lista:
            self.state = VALID
        else:
            self.state = INVALID
            
        return self
    
    # Parse the result of a group search 
    def from_html_group(self, webpage, ordinarie):
        assert self.state == NEW

        grupp = MSDeH(r'(?s)<span class="rubrik1">(.*?)</span>').get(webpage)
        g2 = grupp.replace("Beställningssortimentet", "")
        if g2 <> grupp:
            grupp = g2 + " (BESTÄLLNINGSSORTIMENTET)"

        prodlista = MList(r'<td width="290" align=',
                          M()).get(webpage)
        
        self.lista = []
        for p in prodlista:
            prod = Product().from_html_group(p, grupp, best=1)
            if prod.valid():
                # A real product
                self.lista.append(prod)
            else:
                # This should be a dummy product with a container
                # to be added to the last real product
                self.lista[-1].add_containers_from(prod)
            
        if self.lista:
            self.state = VALID
        else:
            self.state = INVALID
            
        return self

    # Object validity
    def valid(self):
            return self.state == VALID

    # Merge this product list with another
    def merge(self, other):
        # FIXME: This is to naive for anything but ordinarie/beställning
        # - It assumes that there is no overlap between lists
        # - It does not not reorder
        self.lista.extend(other.lista)
        if self.state == VALID or other.state == VALID:
            self.state = VALID # Superugly kludge
        
    # Replace the minimal Product object (from a name/group search)
    # with a full one (requires a web page fetch per product = expensive)
    def replace_with_full(self):
        l = []
        for p in self.lista:
            l.append(Product().search(p.varunr))
        self.lista = l

    def to_string(self, baravarunr = 0, fullstandig = 0, kort = 0):
        f = cStringIO.StringIO()

        if baravarunr:
            for p in self.lista:
                f.write("%s\n" % (p.varunr))
        else:
            tidigare_grupp = None

            for p in self.lista:
                grupp = p.grupp
                if grupp <> tidigare_grupp:
                    f.write(grupp + "\n\n")
                    tidigare_grupp = grupp

                if fullstandig:
                    f.write(p.to_string_normal())
                elif kort:
                    f.write(p.to_string_brief())
                else:
                    f.write(p.to_string_productlist())
                f.write("\n")

        return f.getvalue()

    def search_name(self, namn):
        url="http://www.systembolaget.se/pris/owa/sokpipe.SokNamn?p_namn=%s" % (urllib.quote(namn))
        webpage = WebPage(url).get()
        self.from_html_name(webpage)

        return self

    def search_group(self, **args):
        # Argumentet sortiment: S_ORD, S_BEST, S_BOTH
        # ska översättas till "lågnivåargumentet"
        # ordinarie=1, ordinarie=0 eller båda!
        if args.has_key("sortiment"):
            sortiment = args["sortiment"]
            a = args.copy()
            del a["sortiment"]
            if sortiment == S_ORD:
                a["ordinarie"] = 1
                return self.search_group(**a)
            elif sortiment == S_BEST:
                a["ordinarie"] = 0
                return self.search_group(**a)
            else:
                # Sök först i ordinarie (detta objekt)
                a["ordinarie"] = 1
                self.search_group(**a)
                # Sök sedan i beställning (annat objekt)
                a["ordinarie"] = 0
                pl = ProductList()
                pl.search_group(**a)
                # Sätt ihop
                self.merge(pl)
                return self

        return self.search_group_internal(**args)
    
    
    def search_group_internal(self, grupp, gruppkod,
                              min_pris, max_pris,
                              ordinarie,
                              begr_butik,
                              forpackningstyp,
                              ekologiskt,
                              kosher,
                              nyhet,
                              varutyp,
                              ursprung,
                              p_klockor,
                              fat_karaktar,
                              druva
                              ):
        if ordinarie:
            p_ordinarie = "1"
        else:
            p_ordinarie = "0"

        if begr_butik is None:
            begr_butik = "0"

        if forpackningstyp is None:
            p_type = "0"
        else:
            p_type = forpackningstyp                 

        if ekologiskt:
            p_eko = "&p_eko=yes"
        else:
            p_eko = ""

        if kosher:
            p_kosher = "&p_kosher=yes"
        else:
            p_kosher = ""

        if nyhet:
            p_nyhet = "&p_nyhet=yes"
        else:
            p_nyhet = ""

        if varutyp is None:
            p_varutyp = ""
        else:
            p_varutyp = urllib.quote(varutyp)

        if ursprung is None:
            p_ursprung = ""
        else:
            p_ursprung = urllib.quote(ursprung)

        grupp = urllib.quote(grupp)

        if druva is not None:
            # Druva
            psp = ProductSearchPage().search(gruppkod)
            (p_innehall, p_druva) = psp.get_code(druva)
        else:
            (p_innehall, p_druva) = (0,0)
            
        url = "http://www.systembolaget.se/pris/owa/sokpipe.sokpara?p_wwwgrp=%s&p_varutyp=%s&p_ursprung=%s&p_prismin=%s&p_prismax=%s&p_type=%s&p_innehall=%d&p_druva=%d&p_kl_1_1=%d&p_kl_1_2=%d&p_kl_2_1=%d&p_kl_2_2=%d&p_kl_3_1=%d&p_kl_3_2=%d&p_kl_fat=%d%s%s%s&p_butnr=%s&p_ordinarie=%s&p_back=" % \
              (grupp, p_varutyp, p_ursprung,
               min_pris, max_pris,
               p_type,
               p_innehall, p_druva,
               p_klockor[0][0],p_klockor[0][1],
               p_klockor[1][0],p_klockor[1][1],
               p_klockor[2][0],p_klockor[2][1],
               fat_karaktar,
               p_eko,
               p_kosher,
               p_nyhet,
               begr_butik, ordinarie)

        webpage = WebPage(url).get()
        self.from_html_group(webpage, ordinarie)

        return self
    
# ProductSearchPage class

class ProductSearchPage:
    def __init__(self):
        self.state = NEW
        self.druvor = []
        
    # Parse the result
    def from_html(self, webpage):
        assert self.state == NEW

        for d in MLimit(r'(?s)<select name="p_druva" class="selectDruva">(.*?)</select>',
                        MList("<option",
                              MSet([("nr", M('option value="([0-9]+)"')),
                                    ("namn", M(">(.*)</option>")),
                                    ]))).get(webpage):
        
            if d["namn"] <> "-":
                self.druvor.append((int(d["nr"]), d["namn"]))

        self.state = VALID
        return self
    
    # Object validity
    def valid(self):
            return self.state == VALID

    def search(self, groupcode):
        url = "http://www.systembolaget.se/pris/owa/plGrupp.visa?p_grupp=%d&p_ordinarie=1" % groupcode
        
        webpage = WebPage(url).get()
        self.from_html(webpage)

        return self

    # Search for a grape
    def get_code(self, txt):
        txt = string.lower(txt)
        if txt[0:1] == "=":
            p_innehall = 1
            txt = txt[1:]
        elif txt[0:1] == "-":
            p_innehall = 3
            txt = txt[1:]
        else:
            p_innehall = 2
            
        for (nr, namn) in self.druvor:
            if string.lower(namn) == txt:
                return (p_innehall, nr)

        return (0,0)
    
# COMMAND LINE OPERATION
def main():
    # Option handling
    
    debug = 0
    sortiment = S_BOTH
    kort = 0
    fullstandig = 0
    butiker = 0
    baravarunr = 0
    lan = "99"
    ort = None
    min_pris = 0
    max_pris = 1000000
    begr_butik = None
    grupp = None
    forpackningstyp = None
    ekologiskt = 0
    kosher = 0
    nyhet = 0
    varutyp = None
    ursprung = None
    p_klockor = [(0,0), (0,0) ,(0,0)]
    pos_fyllighet = None
    pos_stravhet = None
    pos_fruktsyra = None
    pos_sotma = None
    pos_beska = None
    fat_karaktar = 0
    druva = None
    
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
                                        "ordinariesortimentet",
                                        "kort",
                                        "fullständig",
                                        "butiker",
                                        "län=",
                                        "ort=",
    
                                        "röda-viner",
                                        "vita-viner",
                                        "mousserande-viner",
                                        "roséviner",
                                        "starkvin",
                                        "sprit",
                                        "öl",
                                        "cider",
                                        "blanddrycker",
                                        "alkoholfritt",
                                        
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
    
                                        "bara-varunr",

                                        "druva=",

                                        # Hidden
                                        "webpage-debug",
                                        ])
    
    for (opt, optarg) in options:
        if opt == "--debug":
            debug = 1
        elif opt == "--namn":
            funktion = F_NAMN
            namn = optarg
        elif opt == "--beställningssortimentet":
            sortiment = S_BEST
        elif opt == "--ordinariesortimentet":
            sortiment = S_ORD
        elif opt == "--kort":
            kort = 1
        elif opt == "--fullständig":
            fullstandig = 1
        elif opt == "--butiker":
            butiker = 1
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
            gruppkod = 1
            (pos_fyllighet, pos_stravhet, pos_fruktsyra) = range(0,3)
        elif opt == "--vita-viner":
            funktion = F_PRODUKT
            grupp = "VITA VINER"
            gruppkod = 2
            (pos_sotma, pos_fyllighet, pos_fruktsyra) = range(0,3)
        elif opt == "--roséviner":
            funktion = F_PRODUKT
            grupp = "ROSÉVINER"
            gruppkod = 3
            (pos_sotma, pos_fyllighet, pos_fruktsyra) = range(0,3)
        elif opt == "--mousserande-viner":
            funktion = F_PRODUKT
            grupp = "MOUSSERANDE VINER"
            gruppkod = 4
            (pos_sotma, pos_fyllighet, pos_fruktsyra) = range(0,3)
        elif opt == "--starkvin":
            funktion = F_PRODUKT
            grupp = "STARKVIN M. M."
            gruppkod = 5
        elif opt == "--sprit":
            funktion = F_PRODUKT
            grupp = "SPRIT"
            gruppkod = 6
        elif opt == "--öl":
            funktion = F_PRODUKT
            grupp = "ÖL"
            gruppkod = 7
            p_sotma_pos = 2
            (pos_beska, pos_fyllighet, pos_sotma) = range(0,3)
        elif opt == "--cider":
            funktion = F_PRODUKT
            grupp = "CIDER"
            gruppkod = 8
            (pos_sotma, pos_fyllighet, pos_fruktsyra) = range(0,3)
        elif opt == "--blanddrycker":
            funktion = F_PRODUKT
            grupp = "BLANDDRYCKER"
            gruppkod = 9
        elif opt == "--alkoholfritt":
            funktion = F_PRODUKT
            grupp = "ALKOHOLFRITT"
            gruppkod = 10
        elif opt == "--min-pris":
            min_pris = optarg
        elif opt == "--max-pris":
            max_pris = optarg
        elif opt == "--begränsa-butik":
            begr_butik = optarg
        elif opt == "--större-flaskor":
            forpackningstyp = "2"
        elif opt == "--helflaskor":
            forpackningstyp = "5"
        elif opt == "--halvflaskor":
            forpackningstyp = "7"
        elif opt == "--mindre-flaskor":
            forpackningstyp = "1"
        elif opt == "--bag-in-box":
            forpackningstyp = "3"
        elif opt == "--pappförpackningar":
            forpackningstyp = "4"
        elif opt == "--burkar":
            forpackningstyp = "6"
        elif opt == "--stora-burkar":
            forpackningstyp = "9"
        elif opt == "--kosher":
            kosher = 1
        elif opt == "--ekologiskt-odlat":
            ekologiskt = 1
        elif opt == "--nyheter":
            nyhet = 1
        elif opt == "--varutyp":
            varutyp = optarg
        elif opt == "--ursprung":
            ursprung = optarg
        elif opt == "--fyllighet":
            p_klockor[pos_fyllighet] = klock_argument(optarg)
        elif opt == "--strävhet":
            p_klockor[pos_stravhet] = klock_argument(optarg)
        elif opt == "--fruktsyra":
            p_klockor[pos_fruktsyra] = klock_argument(optarg)
        elif opt == "--sötma":
            p_klockor[pos_sotma] = klock_argument(optarg)
        elif opt == "--beska":
            p_klockor[pos_beska] = klock_argument(optarg)
            
        elif opt == "--fat-karaktär":
            fat_karaktar = 1
        elif opt == "--ej-fat-karaktär":
            fat_karaktar = 2
        elif opt == "--bara-varunr":
            baravarunr = 1
        elif opt == "--druva":
            druva = optarg
        elif opt == "--webpage-debug":
            global WEBPAGE_DEBUG
            WEBPAGE_DEBUG = WEBPAGE_DEBUG + 1
        else:
            sys.stderr.write("Internt fel (%s ej behandlad)" % opt)
            sys.exit(1)
    
    if funktion == F_HELP and len(arguments) > 0:
        funktion = F_VARA
    
    if funktion == F_VARA:
        # Varufunktion
        for varunr in arguments:
            prod = Product().search(varunr, butiker, lan, ort)
            if prod.valid():
                if kort:
                    txt = prod.to_string_brief()
                else:
                    txt = prod.to_string_normal(butiker)
                print txt
            else:
                print "Varunummer %s verkar inte finnas." % varunr
                continue
            
    elif funktion == F_NAMN:
        # Namnsökning
        pl = ProductList().search_name(namn = namn)
        if pl.valid():
            if kort or fullstandig:
                pl.replace_with_full()
            print pl.to_string(baravarunr = baravarunr,
                               fullstandig = fullstandig,
                               kort = kort),
        else:
            print "Sökningen gav inga svar."
    
    elif funktion == F_PRODUKT:
        # Produktsökning
        pl = ProductList().search_group(grupp = grupp,
                                        gruppkod = gruppkod,
                                        min_pris = min_pris,
                                        max_pris = max_pris,
                                        sortiment = sortiment,
                                        begr_butik = begr_butik,
                                        forpackningstyp = forpackningstyp,
                                        ekologiskt = ekologiskt,
                                        kosher = kosher,
                                        nyhet = nyhet,
                                        varutyp = varutyp,
                                        ursprung = ursprung,
                                        p_klockor = p_klockor,
                                        fat_karaktar = fat_karaktar,
                                        druva = druva,
                                        )
        if pl.valid():
            if kort or fullstandig:
                pl.replace_with_full()
            print pl.to_string(baravarunr = baravarunr,
                               fullstandig = fullstandig,
                               kort = kort),
        else:
            print "Sökningen gav inga svar."
    
    else: # F_HELP
        print "systembolaget.py --- kommandoradssökning i Systembolagets katalog"
        print "-----------------------------------------------------------------"
        print 
        print "Varuvisning (med möjlighet att visa butiker som har varan):"
        print """
       %s [--kort] [--butiker]
       %s [--län=LÄN] [--ort=ORT]
       %s VARUNR...
    """ % ((sys.argv[0],) + (" " * len(sys.argv[0]),)*2)
        print "Namnsökning:"
        print """
       %s [{--beställningssortimentet |
       %s   --ordinariesortimentet}]
       %s [{--bara-varunr | --kort | --fullständig}]
       %s  --namn=NAMN
    """ % ((sys.argv[0],) + (" " * len(sys.argv[0]),)*3)
        print "Produktsökning:"
        print """
       %s { --röda-viner    | --vita-viner        |
       %s   --roséviner     | --mousserande-viner |
       %s   --starkvin      | --sprit             |
       %s   --öl            | --cider             |
       %s   --blanddrycker  | --alkoholfritt }
       %s [{--beställningssortimentet |
       %s   --ordinariesortimentet}]
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
       %s [ --druva=[{-,=}]DRUVA ]
       %s [{--bara-varunr | --kort | --fullständig}]
    """ % ((sys.argv[0],) + (" " * len(sys.argv[0]),)*20)


if __name__ == '__main__':
    main()
    
