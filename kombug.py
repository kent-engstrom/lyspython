#! /usr/local/bin/python

#  This program is a LysKOM protocol A bugging program.  It listens to
#  a port, and when a LysKOM client connects to that port it will
#  connect to a LysKOM server.  All data between the client and the
#  server will be enqueued by this program.
#
#  This bugging program is interactive.  The prompt, which is printed
#  in reverse video, indicates how many pending questions/replies/async 
#  messages there are.  When the user hits "c" one pending question
#  will be forwarded to the server (and printed to stdout in reverse
#  video).  When the user hits "s" one pending reply or async message
#  is forwarded from the server to the client (and printed to stdout).
#
#  Hit "q" to exit kombug.py.
#
#  Sample usage:
#
#     ./kombug.py 5100 kom.lysator.liu.se 4894
#
#  This will listen to port 5100 and forward connections to
#  kom.lysator.liu.se:4894.  The two last arguments may be left out.
#
#  BUGS:
#    The "c" and "s" buttons may wear out.
#    Inverse video assumes that a vt100-compatible output device is used.

import os
import sys
import socket
import select
import string

class kombug:
    def __init__(self, myport, host, port):
	self.clientq=[]
	self.serverq=[]
	self.clientunparsed=""
	self.serverunparsed=""
	self.connect(host, port)
	self.listen(myport)

    def connect(self, host, port):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.connect(host, port)
	print "Reached", host, port
	self.server = s

    def listen(self, port):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind("", port)
	s.listen(3)
	(self.client, addr) = s.accept()
	print "Client connected from", addr

    def prompt(self):
	self.current_prompt=("Client: " + `len(self.clientq)`
			     + " Server: " + `len(self.serverq)` + ": ")
	sys.stdout.write(self.current_prompt)
	sys.stdout.flush()

    def eraseprompt(self):
	sys.stdout.write("\r" + " "*len(self.current_prompt) + "\r")
	sys.stdout.flush()

    def parse(self, str, res):
	"""Parse calls from STR and append them to RES.

	RES is a list of strings.  STR is a string.  Any unparsed data
	are returned.  That happens if an incomplete call exists in STR.
	"""

	linestart=0
	state=0
	i=0
	while i < len(str):
	    c = str[i]
	    if c == '\n':
		res.append(str[linestart:i+1])
		linestart=i+1
		state = 0
	    elif state == 0:
		if c in string.digits:
		    stringstart=i
		    state = 1
	    elif state == 1:
		if c == "H":
		    slen=string.atoi(str[stringstart:i])
		    i = i + slen
		    state = 0
		elif c not in string.digits:
		    state = 0
	    i = i + 1
	return str[linestart:]

    def relay(self):
	try:
	    os.system("stty -echo -icanon min 1 time 0 -opost")
	    while 1:
		self.prompt()
		(rfd, wfd, efd) = select.select([self.server, self.client,
						 sys.stdin.fileno()], [], [])
		self.eraseprompt()
		if self.server in rfd:
		    msg=self.server.recv(10000)
		    self.serverunparsed = self.parse(
		       self.serverunparsed + msg, self.serverq)
		if self.client in rfd:
		    msg=self.client.recv(1000)
		    self.clientunparsed = self.parse(
		       self.clientunparsed + msg, self.clientq)
		if sys.stdin.fileno() in rfd:
		    key=sys.stdin.read(1)
		    if key == "q":
			return
		    elif key == "c":
			if len(self.clientq) > 0:
			    msg=self.clientq[0]
			    self.server.send(msg)
			    self.clientq[0:1]=[]
			    sys.stdout.write("[7m" + msg + "[m")
			    sys.stdout.flush()
			else:
			    sys.stdout.write('\a')
		    elif key == "s":
			if len(self.serverq) > 0:
			    msg=self.serverq[0]
			    self.client.send(msg)
			    self.serverq[0:1]=[]
			    sys.stdout.write(msg + "")
			    sys.stdout.flush()
			else:
			    sys.stdout.write('\a')
		    else:
			sys.stdout.write('\a')

	finally:
	    os.system("stty echo icanon opost");

if __name__ == '__main__':
    local_port = string.atoi(sys.argv[1])
    if len(sys.argv) > 2:
	remote_host = sys.argv[2]
    else:
	remote_host = "kom.lysator.liu.se"
    if len(sys.argv) > 3:
	remote_port = string.atoi(sys.argv[3])
    else:
	remote_port = 4894
    b=kombug(local_port, remote_host, remote_port)
    b.relay()
