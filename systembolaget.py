#!/local/pkg/python/bin/python

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
    

# Generic matcher class

class Matcher:
    def __init__(self, name, pattern, advance=1):
        self.name = name
        self.pattern = self.elaborate_pattern(pattern)
        self.re = re.compile(self.pattern)
        self.advance = advance
        self.data = None
        
    def match(self, data, start_pos):
        m = self.re.search(data, start_pos)
        if m:
            #print "Found", self.name, "=", m.group(1)
            self.data = self.clean(m.group(1))
            if self.advance:
                return m.end(0)
            else:
                return start_pos
        else:
            #print "NOT FOUND", self.name
            return start_pos

    def clean(self, data):
        return data

    def elaborate_pattern(self, pattern):
        return pattern

class StripMatcher(Matcher):
    def clean(self, data):
        return string.join(string.split(string.strip(data)), " ")

class TFMatcher(StripMatcher):
    def elaborate_pattern(self, pattern):
        return r"<B>%s</B></td>\n<td valign=top>(.*)</td></tr>" % pattern

class ClockMatcher(StripMatcher):
    pass

class DeHTMLMatcher(StripMatcher):
    def clean(self, data):
        return re.sub("<.*?>", "",
                      string.join(string.split(string.strip(data)), " "))


class ContainerMatcher(Matcher):
    def __init__(self, name, pattern, advance=1):
        Matcher.__init__(self, name, pattern, advance)

    def clean(self, data):
        res = []
        while 1:
            c = Container(data)
            if not c.valid(): break
            res.append(c)
            data = c.remaining_data()
        return res

class SearchMatcher(Matcher):
    def __init__(self, name, pattern, advance=1):
        Matcher.__init__(self, name, pattern, advance)

    def clean(self, data):
        res = []
        while 1:
            c = SearchLine(data)
            if not c.valid(): break
            res.append(c)
            data = c.remaining_data()
        return res

    
# Generic MatchSet

class MatchSet:
    def __init__(self, data):
        self.data = data
        self.matchers = []
        self.dict = {}
        self.pos = 0
        
    def match(self):
        # Execution
        for matcher in self.matchers:
            self.pos = matcher.match(self.data, self.pos)
            if matcher.data is not None:
                self.dict[matcher.name] = matcher.data

    def remaining_data(self):
        return self.data[self.pos:]

    def add_field(self, f, title, key):
        if self.dict.has_key(key):
            f.write(format_titled(title, self.dict[key]))

    def valid(self):
        return len(self.dict) > 0

# Product class
    
class Product(MatchSet):
    def __init__(self, webpage):
        MatchSet.__init__(self, webpage)
        # Definition
        self.matchers = [
            StripMatcher("grupp", r"<tr><td width=144> </td><td>\n(.+)\n"),
            StripMatcher("namn", r"<B>([^(]+)\(nr [^)]*\)"),
            TFMatcher("ursprung", "Ursprung"),
            TFMatcher("producent", "Producent"),
            ContainerMatcher("förpackningar", "(?s)<td><table border=1><tr><td><table border=0>(.*)</table></td></tr></table>"),
            TFMatcher("färg", "Färg"),
            TFMatcher("doft", "Doft"),
            TFMatcher("smak", "Smak"),
            ClockMatcher("sötma", r'<td width=70><center><img src="/bilder/klock_([0-9]+).gif"\n><br> *Sötma *</center></td>', advance = 0),
            ClockMatcher("fyllighet", r'<td width=70><center><img src="/bilder/klock_([0-9]+).gif"\n><br> *Fyllighet *</center></td>', advance = 0),
            ClockMatcher("strävhet", r'<td width=70><center><img src="/bilder/klock_([0-9]+).gif"\n><br> *Strävhet *</center></td>', advance = 0),
            ClockMatcher("fruktsyra", r'<td width=70><center><img src="/bilder/klock_([0-9]+).gif"\n><br> *Fruktsyra *</center></td>', advance = 0),
            ClockMatcher("beska", r'<td width=70><center><img src="/bilder/klock_([0-9]+).gif"\n><br> *Beska *</center></td>', advance = 0),
            TFMatcher("användning", "Användning"),
            TFMatcher("hållbarhet", "Hållbarhet"),
            TFMatcher("provad_årgång", "Provad årgång"),
            TFMatcher("provningsdatum", "Provningsdatum"),
            StripMatcher("alkoholhalt", "<B>Alkoholhalt</B></td>\n<td valign=top>(.*\n.*)</td></tr>"),
            ]
        self.match()

    def to_string(self):
        f = cStringIO.StringIO()
        self.add_field(f,"Grupp","grupp")
        self.add_field(f,"Namn","namn")
        self.add_field(f,"Ursprung","ursprung")
        self.add_field(f,"Producent","producent")
        f.write("\n")
        self.add_field(f,"Färg","färg")
        self.add_field(f,"Doft","doft")
        self.add_field(f,"Smak","smak")
        f.write("\n")
        self.add_field(f,"Sötma","sötma")
        self.add_field(f,"Fyllighet","fyllighet")
        self.add_field(f,"Strävhet","strävhet")
        self.add_field(f,"Fruktsyra","fruktsyra")
        self.add_field(f,"Beska","beska")
        f.write("\n")
        self.add_field(f,"Användning","användning")
        self.add_field(f,"Hållbarhet","hållbarhet")
        self.add_field(f,"Provad årgång","provad_årgång")
        self.add_field(f,"Provad","provningsdatum")
        self.add_field(f,"Alkoholhalt","alkoholhalt")
        f.write("\n")
        f.write(format_titled_fixed("Förpackningar",
                                    map(lambda x: x.to_string(),
                                        self.dict["förpackningar"])))
            
        return f.getvalue()

    def valid(self):
        # Should at least contain name to be valid
        return self.dict.has_key("namn") and self.dict["namn"] <> ""

class Container(MatchSet):
    def __init__(self, data):
        MatchSet.__init__(self, data)
        # Definition
        self.matchers = [
            StripMatcher("namn", r"<td>([^<]+)</td>"),
            StripMatcher("storlek", r"<td align=right>([^<]+)</td>"),
            StripMatcher("pris", r"<td align=right>([^<]+)</td>"),
            StripMatcher("anm1", r"<td>([^<]+)</td>"),
            DeHTMLMatcher("anm2", r"<td>(.+?)</td>"),
            ]

        self.match()

    def to_string(self):
        return "%-15s %7s %7s %s %s" % (
            self.dict.get("namn"),
            self.dict.get("storlek"),
            self.dict.get("pris"),
            self.dict.get("anm1"),
            self.dict.get("anm2"))

class ProductFromWeb(Product):
    def __init__(self, prodno):
        url = "http://www.systembolaget.se/pris/owa/xdisplay?p_varunr=" + \
              prodno
        u = urllib.urlopen(url)
        webpage = u.read()
        Product.__init__(self, webpage)


class Search(MatchSet):
    def __init__(self, webpage):
        MatchSet.__init__(self, webpage)
        # Definition
        self.matchers = [
            SearchMatcher("resultat", r"(?s)Kr / liter.*?\n.*?\n(.*)\nDin sökning"),
            ]
        self.match()
        
    def to_string(self):
        f = cStringIO.StringIO()
        if self.valid():
            for sl in self.dict["resultat"]:
                f.write(sl.to_string() + "\n")
                
        return f.getvalue()

        
class SearchLine(MatchSet):
    def __init__(self, data):
        MatchSet.__init__(self, data)
        # Definition
        self.matchers = [
            StripMatcher("varunr", r'<tr valign=top><td bgcolor="#[0-9a-f]+" width=320>\n<tr valign=top><td bgcolor="#[0-9a-f]+" width=275><font face="Arial, Helvetica, sans-serif" size="2">\n<A HREF="/pris/owa/xdisplay\?p_varunr=([0-9]+)'),
            StripMatcher("namn", r"<B>(.*?)</B>"),
            ]

        self.match()

    def to_string(self):
        return "%-8s %s" % (
            self.dict.get("varunr"),
            self.dict.get("namn"))


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
            print prod.to_string()
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
        print s.to_string()
