#!/sw/kom++/bin/python

# LysKOM statistics gatherer.  Requires kom++

# Written by Peter Liljenberg 1998
# Public Domain, no guarantees

import getopt
from string import *
import komxx
from time import *
import sys

class Data:
   def __init__(self, author):
      self.author = author
      self.texts = 0
      self.chars = 0
      self.lines = 0

   def addtext(self, text):
      str = text.body()
      self.texts = self.texts + 1
      self.chars = self.chars + text.num_chars()
      self.lines = self.lines + text.num_lines()

   def format(self):
      formatstr = '%-30.30s %6d %6d %7d %7.2f %8.2f\n'

      if self.texts != 0:
	 return formatstr % (self.author, self.texts, self.lines, self.chars,
			     float(self.lines) / self.texts,
			     float(self.chars) / self.texts)
      else:
	 return formatstr % (self.author, self.texts, self.lines, self.chars, 0, 0)


   def __cmp__(self, obj):
      if self.texts == obj.texts:
	 return cmp(self.lines, obj.lines)
      else:
         return cmp(self.texts, obj.texts)

   
class Statistik:
   def __init__(self, session, conf, post, start, end):
      self.s = session
      self.conf = conf
      self.post = post
      self.total = Data('TOTALT')
      self.start = start
      self.end = end
      self.authors = {}

   def addtext(self, text):
      try:
	 self.total.addtext(text)
#	 print text.text_no(), text.author(), text.subject()
	 
	 if self.authors.has_key(text.author()):
	    d = self.authors[text.author()]
	 else:
	    try:
	       d = Data(s.pers(text.author()).name())
	    except komxx.err_undef_pers:
	       d = Data('Person %d (finns inte)' % text.author())
	       
	    self.authors[text.author()] = d
	 d.addtext(text)
      except komxx.err_text_zero:
	 pass
      except komxx.errno_error, msg:
	 print 'Kan inte läsa inlägg:', msg

   def printdata(self):
      subject = 'Statistik för ' + self.conf.name()
      body = strftime('Statistikperioden är %Y-%m-%d till ',
			   self.start)
      body = body + strftime('%Y-%m-%d\n\n', self.end)

      body = body + '                               Inlägg  Rader  Tecken     R/I      T/I\n'
      body = body + '---------------------------------------------------------------------\n'
      body = body + self.total.format() + '\n'

      as = self.authors.values()
      as.sort()
      as.reverse()
      for a in as:
	 body = body + a.format()

      if self.post:
	 tno = self.s.create_text(subject, body, [self.conf.conf_no()], [], [], [])
	 print 'Skapade text', tno, 'i', self.conf.name()
      print body

def dostat(s, confs, start, end, post):
   # Add 24 hs to end, to make it the day after end-day.
   tot = mktime(end)
   tot = tot + 86400
   nto = localtime(tot)
   
   for c in confs:
      ts = s.last_local_before(c, start) + 1
      te = s.last_local_before(c, nto) + 1
      tmap = s.text_mapping(c)
      conf = s.conf(c)
      stat = Statistik(s, conf, post, start, end)
      for n in range(ts, te):
	 try:
	    tno = tmap[n]
	 except komxx.err_no_such_local_text:
	    print 'Missing local text', n, 'in', conf.name()
	 else:
	    text = s.text(tno)
	    stat.addtext(text)

      stat.printdata()
      
   
def getconflist(s, okconfs, exclude):
   confs = []
   for c, min, max in s.confs_with_unread():
      conf = s.conf(c)
      try:
	 okconfs.index(c)
	 ok = 1
      except ValueError:
	 ok = 0

      if (ok ^ exclude) == 0:
	 print 'Hoppar över', conf.name()
      else:
	 print 'Gräver igenom', conf.name()
	 confs.append(c)

   return confs

def parse_date(date):
   d = split(date, '-')
   today = localtime(time())

   year = today[0]
   month = today[1]

   if len(d) == 1:
      day = atoi(d[0])
   elif len(d) == 2:
      month = atoi(d[0])
      day = atoi(d[1])
   elif len(d) == 3:
      year = atoi(d[0])
      month = atoi(d[1])
      day = atoi(d[2])
   else:
      raise ValueError, 'Malformed date'

   return (year, month, day, 0, 0, 0, 0, 0, -1)

def getpass(prompt = "Password: "):
   sys.stdout.flush()
   passwd = raw_input(prompt)
   sys.stdout.write('\x1b[1A\x1b[2K')
   sys.stdout.flush()
   return passwd

usage = """Usage: komstat [options] persno start [end]
       komstat -l persno

start and end are dates on the form YEAR-MONTH-DAY, where YEAR and MONTH
defaults to the current year and month, respectively.
end default is today.  All the texts in the inclusive interval
[start, end] will be counted.

Note: 'All confs' below refer to all the confs persno is a member of and
has unread texts in.

Options:
  -l  --list         List all confs with unread texts
  -c <conflist> --confs=<conflist>
                     Only collect statistic for these confs.
		     conflist is a commaseparated list of confnos.
		     This option can be given more than once.
  -x  --exclude      Process all confs except those given by -c
  -p  --post         Send statistics data to the processed conf
"""


if __name__ == '__main__':
   try:
      opts, args = getopt.getopt(sys.argv[1:], "c:xlp",
				 ["confs=", "exclude", "list", "post"])

      exclude = 0
      okconfs = []
      listconfs = 0
      post = 0
      persno = atoi(args[0])

      for op, val in opts:
	 if op == '-x' or op == '--exclude':
	    exclude = 1
	 elif op == '-c' or op == '--confs':
	    val = split(val, ',')
	    for v in val:
	       okconfs.append(atoi(v, 10))
	 elif op == '-l' or op == '--list':
	    listconfs = 1
	 elif op == '-p' or op == '--post':
	    post = 1

      if not listconfs:
	 if len(args) < 2:
	    raise 'Ledsen Error', 'Missing arguments'
	 start = parse_date(args[1])
	 try:
	    end = parse_date(args[2])
	 except IndexError:
	    end = localtime(time())

   except 'foo': pass
#   except (getopt.error, 'Ledsen Error', ValueError), val:
#      print usage
      
   else:
      s = komxx.new_session("kom.lysator.liu.se", "4894",
			    "Ctrl-Cs statistisksork", "*pip*")
      if s.login(persno, getpass(), 1) == komxx.st_ok:
	 if listconfs:
	    for c, min, max in s.confs_with_unread():
	       print c, s.conf(c).name()
	 else:
	    if len(okconfs) == 0:
	       confs = getconflist(s, [], 1)
	    elif exclude:
	       confs = getconflist(s, okconfs, exclude)
	    else:
	       confs = okconfs

	    dostat(s, confs, start, end, post)
	 s.logout()
      else:
	 print '*smakk*'
