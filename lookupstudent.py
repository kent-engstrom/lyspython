#!/usr/bin/python
# lookupstudent.py - A Quick hack to see what courses a person attends, and
# what education he's registrered on.
# Copyright (c) 2002 Erik Forsberg <forsberg@lysator.liu.se>
# Released under the GNU GPL

import ldap
import sys
import string

l = ldap.open("ldap.student.liu.se")
l.simple_bind("", "")
r = l.search_st("o=student.liu.se, o=liu.se",
                ldap.SCOPE_SUBTREE, "uid=%s" % sys.argv[1])
data = r[0][1]


print "Gecos: %s" % data["gecos"][0]
print "Utbildning:"
print "*"*80
for utbildning in data["programcode"]:
    print utbildning
print "Kurskoder:"
print "*"*80
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

print "*"*80
try:
    if 0 < len(data["mailforwardingaddress"]):
        print "Vidarebefordrar mail till: %s" % data["mailforwardingaddress"][0]
except KeyError:
    pass
    
