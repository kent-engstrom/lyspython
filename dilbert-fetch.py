#!/usr/bin/python

import urllib,socket,sys,regex,os

# Configuration

server="www.unitedmedia.com:80"
indexurl="http://"+server+"/comics/dilbert/archive/"

# Connect and get archive index page

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

rx=regex.compile("archive/images/dt\([0-9]+\)_\([0-9]+\)\.gif")

for date in dates:
    filename="dilbert-%s.gif"%date
    htmlurl="http://"+server+"/comics/dilbert/archive/dilbert%s.html"%date
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

    (date,rnd)=rx.group(1,2)

    picurl="http://"+server+"/comics/dilbert/archive/images/dt%s_%s.gif"%(date,rnd)

    f=urllib.urlopen(picurl)
    picture=f.read()
    f.close()

    f=open(filename,"w")
    f.write(picture)
    f.close()

    print "%s: fetched"%filename
