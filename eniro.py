#!/usr/bin/env python

# TODO: Check modules
import sys
import re
import cStringIO
import urllib
import getopt
from regexpmatcher import M, MS, MSDeH, MSet, MList, MLimit

# Exceptions
class NoResults(Exception): pass

# Help functions

def search_args(name):
    search_type = "exact"
    if name[-1:] == "*":
        name = name[:-1]
        search_type = "trunc"
    elif name[-1:] == "~":
        name = name[:-1]
        search_type = "fuzzy"
        
    return (urllib.quote(name), search_type)

def all_numeric(str):
    # An empty string is not all numeric!
    return re.match("^[0-9]+$", str)

def split_area_phone(str):
    m = re.match("^([0-9]+)-([0-9]+)$", str)
    if m:
        return m.group(1,2)
    else:
        return None
    
# Search class

search_m =MSet([("resultat",
                 MList('<TD align="left" bgcolor="#CCCCCC">',
                       MSet([("name_title",
                              MSDeH(r"<(?s).*<b>(.*?)</b>")),
                             ("address",
                              MSDeH(r'(?s)<TD align="left">(.*?)</TD>')),
                             ("phone",
                              MSDeH(r'(?s)<TD align="right" width="100">(.*?)</B>')),
                             ]))),
                ("maxvisas", MS(r">1-([0-9]+)")),
                ("totalt", MS(r"(?s).*visas av totalt:.*?([0-9]+)"))
                ])

class Search:
    def __init__(self, webpage):
        (self.dict, pos) = search_m.match(webpage, 0, len(webpage))
        
    def valid(self):
        return self.dict.has_key("resultat")

    def to_string(self):
        if not self.valid(): raise NoResults
        f = cStringIO.StringIO()
        for p in self.dict["resultat"]:
            f.write(p["name_title"] + "\n")
            f.write("  " + p["address"] + "\n")
            f.write("  " + p["phone"] + "\n")
            f.write("\n")
        if self.dict["maxvisas"] != self.dict["totalt"]:
            f.write("(%s av %s träffar)\n" % (self.dict["maxvisas"],
                                              self.dict["totalt"]))
        return f.getvalue()

    def to_list_of_dicts(self): 
        if not self.valid(): raise NoResults
        l = []
        for p in self.dict["resultat"]:
            d = {}
            for field in ["name_title", "address", "phone"]:
                d[field] = p[field]
            l.append(d)
        return l       
    
class SearchNameFromWeb(Search):
    def __init__(self,
                 firstname = "",
                 lastname = "",
                 address = "",
                 zipcode = "",
                 area = "",
                 title = "",
                 max = 25):
        (firstname, firstname_type) = search_args(firstname)
        (lastname, lastname_type) = search_args(lastname)
        (address, address_type) = search_args(address)
        zipcode = urllib.quote(zipcode)
        area = urllib.quote(area)
        (title, title_type) = search_args(title)
        
        url = "http://www.privatpersoner.gulasidorna.se/search/hits.asp?" +\
              "firstname=" + firstname + "&" +\
              "firstnameType=" + firstname_type + "&" +\
              "lastname=" + lastname + "&" +\
              "lastnameType=" + lastname_type +"&" +\
              "region=0&" +\
              "address=" + address + "&" +\
              "addressType=" + address_type + "&" +\
              "zipcode=" + zipcode + "&" +\
              "area=" + area + "&" +\
              "title=" + title + "&" +\
              "titleType=" + title_type + "&" +\
              "first=1&" +\
              ("last=%d" % max)

        u = urllib.urlopen(url)
        webpage = u.read()

        Search.__init__(self, webpage)

class SearchNumberFromWeb(Search):
    def __init__(self,
                 areacode = "",
                 phone = ""):
        areacode = urllib.quote(areacode)
        phone = urllib.quote(phone)
        
        url = "http://www.privatpersoner.gulasidorna.se/search/hits.asp?" +\
              "areacode=" + areacode + "&" +\
              "phone=" + phone + "&" +\
              "first=1&" +\
              "last=25"

        u = urllib.urlopen(url)
        webpage = u.read()

        Search.__init__(self, webpage)


# MAIN
if __name__ == "__main__":
    firstname = ""
    lastname = ""
    address = ""
    zipcode = ""
    area = ""
    title = ""
    areacode = ""
    phone = ""
    max = 25
    
    F_HELP = 0
    F_NAME = 1
    F_NUMBER = 2
    function = F_HELP

    # Options parsing:
    options, arguments = getopt.getopt(sys.argv[1:],
                                       "",
                                       ["förnamn=",
                                        "efternamn=",
                                        "adress=",
                                        "postnr=",
                                        "område=",
                                        "titel=",
                                        "riktnr=",
                                        "telefonnr=",
                                        "max=",
                                        ])

    for (opt, optarg) in options:
        if opt == "--förnamn":
            function = F_NAME
            firstname = optarg
        elif opt == "--efternamn":
            function = F_NAME
            lastname = optarg
        elif opt == "--adress":
            function = F_NAME
            address = optarg
        elif opt == "--postnr":
            function = F_NAME
            zipcode = optarg
        elif opt == "--område":
            function = F_NAME
            area = optarg
        elif opt == "--titel":
            function = F_NAME
            title = optarg
        elif opt == "--riktnr":
            function = F_NUMBER
            areacode = optarg
        elif opt == "--telefonnr":
            function = F_NUMBER
            phone = optarg
        elif opt == "--max":
            max = int(optarg)
        else:
            sys.stderr.write("Internt fel (%s ej behandlad)" % opt)
            sys.exit(1)

    # Argument parsing:
    
    # Areacode-Phone
    if function == F_HELP and len(arguments) == 1:
        area_phone = split_area_phone(arguments[0])
        if area_phone:
            function = F_NUMBER
            (areacode, phone) = area_phone

    # Areacode Phone
    if function == F_HELP and len(arguments) == 2 and \
       all_numeric(arguments[0]) and all_numeric(arguments[1]):
        function = F_NUMBER
        (areacode, phone) = arguments

    # Firstname [Lastname [Area]] 
    if function in [F_HELP, F_NAME] and len(arguments) > 0:
        function = F_NAME
        firstname = arguments[0]
        if len(arguments) > 1:
            lastname = arguments[1]
            if len(arguments) > 2:
                area = arguments[2]
                

    if function == F_NAME:
        # Namnsökning
        s = SearchNameFromWeb(firstname = firstname,
                              lastname = lastname,
                              address = address,
                              zipcode = zipcode,
                              area = area,
                              title = title,
                              max = max,
                              )
        if s.valid():
            print s.to_string(),
        else:
            print "Sökningen gav inga svar."

    elif function == F_NUMBER:
        # Nummersökning
        s = SearchNumberFromWeb(areacode = areacode,
                                phone = phone)
        if s.valid():
            print s.to_string(),
        else:
            print "Sökningen gav inga svar."

    else:
        print "Hjälptext saknas."
        
