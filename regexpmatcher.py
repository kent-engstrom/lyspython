# (C) 2001-2002 Kent Engström. Released under the GNU GPL.

import string
import re

# Debugging
debug = 0 # Set to 1 to enable debug output

# Auxiliary functions

def findall_pos(pattern, data, s_pos, e_pos):
    """Find all positions where a pattern matches in data[s_pos:e_pos]."""

    l = []
    pos = s_pos
    patre = re.compile(pattern)
    while 1:
        m = patre.search(data, pos, e_pos)
        if m:
            l.append(m.start(0))
            pos = m.end(0)
        else:
            return l
        
class GetMixin:
    def get(self, data, s_pos=0, e_pos=None):
        """Match the pattern. Return string/None.
        
        FIXME: Will we use this interface???"""
        
        (res, pos) = self.match(data, s_pos, e_pos)
        return res

class M(GetMixin):
    """Match a pattern, return a string or None."""

    def __init__(self, pattern = None, advance=1):
        self.pattern = self.elaborate_pattern(pattern)
        if self.pattern:
            self.re = re.compile(self.pattern)
        self.advance = advance
        
    def match(self, data, s_pos=0, e_pos=None):
        """Match the pattern. Return string/None + start for next search."""

        if e_pos is None: e_pos = len(data)
        if self.pattern:
            m = self.re.search(data, s_pos, e_pos)
            if m:
                if debug: print "Found", m.group(1)
                data = m.group(1)
                match_end = m.end(1)
                found = 1
            else:
                found = 0
        else:
            match_end = e_pos
            data = data[s_pos:e_pos]
            found = 1

        if found:
            data = self.clean(data)
            if self.advance:
                return (data, match_end)
            else:
                return (data, s_pos)
        else:
            if debug: print "Not found"
            return (None, s_pos)

    def clean(self, data):
        """Clean the data.

        You may override this method in derived classes."""

        return data

    def elaborate_pattern(self, pattern):
        """Elaborate the pattern.

        You may override this method in derived classes."""

        return pattern

class MS(M):
    """Match as M, but strip the data of extra whitespace."""
    
    def clean(self, data):
        """Clean the data.

        This means removing whitespace at beginning and end,
        plus replacing internal whitespace with single spaces."""
        
        return string.join(string.split(string.strip(data)), " ")

class MSDeH(MS):
    """Match as M, but strip away HTML tags. Convert &bnsp; to normal space.
       Also convert &amp; to a normal ampersand."""
    
    def clean(self, data):
        return re.sub("&amp;", "&", 
                      re.sub("&nbsp;", " ",
                             re.sub("<.*?>", "",
                                    string.join(string.split(\
            string.strip(data)), " "))))


class MSet(GetMixin):
    """Match a set of patterns. Return a dictionary."""
    
    def __init__(self, matchers):
        self.matchers = matchers
        
    def match(self, data, s_pos=0, e_pos=None):
        # Execution
        if e_pos is None: e_pos = len(data)
        dict = {}
        for (name, m) in self.matchers:
            if debug:
                print "Looking for",name,"between",s_pos,"and",e_pos
                print "--> %s" % data[s_pos:min(s_pos+110,e_pos)]
            (found, s_pos) = m.match(data, s_pos, e_pos)
            if found: # Subtle: empty dict or list is also false!
                dict[name] = found
        return (dict, s_pos)

# Class matching a list of data, producing a list

class MList(GetMixin):
    """Match a single pattern repeatedly. Return a list."""
    
    def __init__(self, begin, matcher):
        self.begin = begin
        self.matcher = matcher
        
    def match(self, data, s_pos=0, e_pos=None):
        # Execution
        if e_pos is None: e_pos = len(data)
        list = []
        pos = findall_pos(self.begin, data, s_pos, e_pos) + [e_pos]
        entry_end_pos = s_pos
        if debug: print "Positions for", self.begin,":", pos
        for i in range(0,len(pos)-1):
            if debug:
                print "Looking for list entry between",pos[i],"and",pos[i+1]
                if (pos[i+1] - pos[i]) < 400:
                    print "Entry is:", data[pos[i]:pos[i+1]]
            (found, entry_end_pos) = self.matcher.match(data, pos[i], pos[i+1])
            list.append(found)
        return (list, entry_end_pos)


class MLimit(GetMixin):
    """Narrow the allowable search range without matching."""
    
    def __init__(self, pattern, matcher):
        self.pattern = pattern
        self.re = re.compile(self.pattern)
        self.matcher = matcher
        
    def match(self, data, s_pos=0, e_pos=None):
        if e_pos is None: e_pos = len(data)
        #print "Before limit", s_pos,"to", e_pos
        #print "--> %s" % data[s_pos:s_pos+60]
        
        m = self.re.search(data, s_pos, e_pos)
        if m:
            (s_pos, e_pos) = m.span(1)
            #print "After limit", s_pos,"to", e_pos
            #print "--> %s" % data[s_pos:s_pos+40]
            return self.matcher.match(data, s_pos, e_pos)
        else:
            #print "Limit failed"
            return (None, s_pos) # or should we call the matcher with empty data?
