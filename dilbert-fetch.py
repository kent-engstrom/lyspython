#!/local/pkg/python1.5/bin/python

import urllib,socket,sys,regex,os

# Configuration

server="www.unitedmedia.com:80"
server2="umweb1.unitedmedia.com:80"
indexurl="http://"+server+"/comics/dilbert/archive/"

# Connect and get archive index page

print "- fetching main page"
f=urllib.urlopen(indexurl)
index=f.read()
f.close()

# Search archive index page for references to html files for days

pos=0
dates=[]
rx=regex.compile("archive/dilbert\([0-9]+\)\.html")

while pos<>-1:
    pos=rx.search(index,pos+1)
    if pos<>-1:
	dates.append(rx.group(1))

# Now see  if we need to download any of them

rx=regex.compile("archive/images/dilbert\([0-9]+\)\.gif")

for date in dates:
    filename="dilbert-%s.gif"%date
    htmlurl="http://"+server2+"/comics/dilbert/archive/dilbert%s.html"%date
    try:
	lf=open(filename,"r")
	lf.close()
	print "%s: present, skipping."%filename
	skip=1
    except:
	skip=0
    if skip: continue

    f=urllib.urlopen(htmlurl)
    html=f.read()
    f.close()

    if rx.search(html)==-1:
	print "%s: no image reference found"%filename
	continue

    (rnd)=rx.group(1)

    picurl="http://"+server2+"/comics/dilbert/archive/images/dilbert%s.gif"%(rnd)

    print "%s: fetching..."%filename
    f=urllib.urlopen(picurl)
    picture=f.read()
    f.close()

    f=open(filename,"w")
    f.write(picture)
    f.close()

    print "%s: fetched"%filename
