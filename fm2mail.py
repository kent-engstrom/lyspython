#!/sw/local/bin/python

# Code to import Freshmeat from NNTP to LysKOM via email.
# Could be used to import to any e-mail address.

# Creates two kinds of imports. One raw and one "corned", where frequent
# releases are imported only once for a certain period.

# State is saved using a pickled file and a textfile.

import nntplib
from smtplib import SMTP
import string
import time
import os
import pickle
import re
import httplib

CORNEDINTERVAL=32140800
# Note: De-spamify addressed below before using.
FMADDR = "sju sex åtta tre@lys kom.lysator.liu.se"
CORNEDADDR = "sju sju två fem5@lys kom.lysator.liu.se"
# This should be a valid mail address, so bounces don't become double-bounces
# that disturb the postmaster.
FROMADDR = "valid email@example.com"

def getlastrun():
    try:
        lrf = open("lastrun", 'r')
        lastrun = lrf.readline()
        lrf.close()
        return lastrun.strip().split(' ', 1)
    except IOError:
        return [time.strftime("%y%m%d", time.gmtime(time.time()-86400)),
                time.strftime("%H%M%S GMT" ,time.gmtime(time.time()-86400))]


def setlastrun(now):
    lrf = open("lastrun.new", 'w')
    lrf.write(time.strftime("%y%m%d %H%M%S GMT\n", time.gmtime(now)))
    lrf.close()
    os.rename('lastrun.new', 'lastrun')

def getlastnum():
    try:
        lnf = open("lastnum", 'r')
        lastnum = lnf.readline()
        lnf.close()
        return int(lastnum)
    except IOError:
        return 0

def setlastnum(num):
    lnf = open("lastnum.new", 'w')
    lnf.write(num+"\n")
    lnf.close()
    os.rename("lastnum.new", "lastnum")
            
        
def unpicklecorned():
    try:
        cb = open("cornedbeef.pickled", 'r')
        return pickle.load(cb)
    except IOError:
        return {}

def picklecorned(beef):
    cb = open("cornedbeef.pickled.new", 'w')
    pickle.dump(beef, cb)
    cb.close()
    os.rename('cornedbeef.pickled.new', 'cornedbeef.pickled')
    
fmn = nntplib.NNTP('news.freshmeat.net')
num = getlastnum()
new = []
resp, count, first, last, name = fmn.group('fm.announce')

if num < int(first):
    num = int(last) - 30
for article in fmn.xover(str(num), last)[1]:
    if num < int(article[0]):
        new.append(article[4])

beef = unpicklecorned()

# now = time.time()
# new = fmn.newnews('fm.announce', d, t)
smtp = SMTP('mail.lysator.liu.se')
redirre = re.compile("(http://freshmeat.net/redir/)(.*?/[0-9]*?/)url_(.*)/")

for article in new:
    try:
        response, number, id, headerlist = fmn.head(article)
        response, number, id, linelist =  fmn.body(article)
    except nntplib.NNTPTemporaryError:
        print "No such article, ", article
        continue

    msg = ""
    msgfrom = ""
    for header in headerlist:
        if 0 == header.find('Subject'):
            msg+=header+"\n"
        elif 0 == header.find("Message-ID"):
            msg+=header+"\n"
	elif 0 == header.find("References"):
            if -1 != header.find("<0@freshmeat.net"):
                continue
            msg+=header+"\n"
        elif 0 == header.find("From"):
            msgfrom = header.split(": ")[1]
    recipients = [FMADDR]
    if beef.has_key(msgfrom):
        if (time.time() - beef[msgfrom]) > CORNEDINTERVAL:
            recipients.append(CORNEDADDR)
            beef["msgfrom"] = time.time()
    else:
        recipients.append(CORNEDADDR)
        beef[msgfrom] = time.time()        
        
    msg+="\n"
    for line in linelist:
        mo = redirre.search(line)
        if None != mo:
            h = httplib.HTTP("freshmeat.net")
            h.putrequest('HEAD', mo.group(0))
            h.endheaders()
            replycode, message, headers = h.getreply()
            try:
                msg+=redirre.sub(headers['Location'], line)+"\n"
            except KeyError:
                msg+=line
        else:
            msg+=line+"\n"
    msg=re.sub(r'&amp;', '&', msg)
    msg=re.sub(r'&quot;', '"', msg)

    smtp.sendmail(FROMADDR, recipients,  msg)    

fmn.quit()
setlastnum(last)
picklecorned(beef)



    
