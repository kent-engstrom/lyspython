#!/usr/bin/env python
# lookupstudent.py - A Quick hack to see what courses a person attends, and
# what education he's registrered on.
# Copyright (c) 2002 Erik Forsberg <forsberg@lysator.liu.se>
# Released under the GNU GPL

import ldap
import sys
import string

if len(sys.argv) < 2:
    print "Usage: %s <studentmailuserid>" % sys.argv[0]
    print "Example: %s abcde123" % sys.argv[0]
    print
    sys.exit(0)

l = ldap.open("ldap.student.liu.se")
l.simple_bind("", "")
r = l.search_st("o=student.liu.se, o=liu.se",
                ldap.SCOPE_SUBTREE, "uid=%s" % sys.argv[1])
data = r[0][1]


print "Gecos: %s" % unicode(data["gecos"][0], "utf-8").encode("latin-1")
print
if data.has_key("programcode"):
    print "Utbildning:"
    print "==========="
    filter = '(|'
    for utbildning in data["programcode"]:
        filter+='(cn='+utbildning+')'
    filter+=')'

    utbildningar = l.search_st("ou=groups, o=student.liu.se, o=liu.se",
                               ldap.SCOPE_SUBTREE,
                               filter,
                               ['cn', 'description'])
    for utb in utbildningar:
        utbkod = utb[1]['cn'][0]
        utbnamn = unicode(utb[1]['description'][0], 'utf8').encode('latin-1')
        print "%s" % utbkod + " "*(25-len(utbkod)) + "%s" % utbnamn
else:
    print "Ej registrerad på någon utbildning"

print

if data.has_key("coursecode"):
    print "Kurskoder:"
    print "=========="
    filter = '(|'
    for kurskod in data["coursecode"]:
        filter+='(cn='+kurskod+')'
    filter+=')'

    kurser = l.search_st("ou=groups, o=student.liu.se, o=liu.se",
                         ldap.SCOPE_SUBTREE,
                         filter,
                         ['cn', 'description'])
    for kurs in kurser:
        kurskod = kurs[1]['cn'][0]
        kursnamn = unicode(kurs[1]['description'][0], 'utf8').encode('latin-1')
        print "%s" % kurskod + " "*(25-len(kurskod)) + "%s" % kursnamn
else:
    print "Ej registrerad på någon kurs"

print
try:
    if 0 < len(data["mailforwardingaddress"]):
        print "Vidarebefordrar mail till: %s" % data["mailforwardingaddress"][0]
except KeyError:
    pass
    
