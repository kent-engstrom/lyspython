"""select-based FD multiplexing.

THIS IS AN EARLY COMMIT OF WORK IN PROGRESS FOR BACKUP PURPOSES.  ALL
API:s SUBJECT TO CHANGE.

Copyright (C) 2000 Per Cederqvist.
"""

import select
import socket
import os
import errno
import string

class parser_base:
    input_line_end = "\n"

    def __init__(self, parent):
        self.__read_queue = ""
        # EOF flag.  0: normal.  1: eof seen, but not yet reported.
        # 2: eof reported to handle_read_eof().
        self.__eof = 0
        self.parent = parent

    def __len__(self):
        return len(self.__read_queue)

    def append(self, data):
        if data != "":
            self.__read_queue = self.__read_queue + data
        res, left = self.handle_read(self.__read_queue)
        # FIXME: error!
        if left == self.__read_queue and self.__eof == 1:
            self.handle_read_eof(left)
            self.__eof = 2
        self.__read_queue = left
        return res
        
    def append_eof(self):
        self.__eof = 1

    def eof_seen(self):
        return not not self.__eof

    def handle_read(self, s):
        """Handle read data.  May be overridden.

        Argument: the incoming buffer.
        Return value: a tuple with two values:
          0: a flag that indicates that a complete command may be present
             in the unparsed buffer.
          1: the part of the incoming buffer that wasn't handled.

        The default implementation extracts the first line, and sends
        it to handle_input_line.  The line is terminated with the
        string input_line_end (which defaults to "\n").
        """

        lineend = string.find(s, self.input_line_end)
        if lineend == -1:
            return 0, s
        self.handle_input_line(s[:lineend])
        s = s[lineend + len(self.input_line_end):]
        if len(s) < len(self.input_line_end):
            return 0, s
        else:
            return 1, s

    def handle_read_eof(self, unparsed):
        self.parent.deferred_close()


def too_large(s, limit):
    if limit is None:
        return 0
    if len(s) < limit:
        return 0
    return 1

class fd_base:
    maxreadbuf = 8192
    readchunk = 8192
    maxwritebuf = None

    def __init__(self, dispatcher, parser, rfd, wfd=None):
        self.rfd = rfd
        self.wfd = wfd
        self.__write_queue = ""
        self.__write_eof = 0
        if parser is not None:
            self.__parser = parser(self)
        self.__deferred_close = 0
        self.dispatcher = dispatcher
        self.dispatcher.register(self)

    def read_fd(self):
        if self.__parser.eof_seen():
            return None
        if too_large(self.__parser, self.maxreadbuf):
            return None
        if too_large(self.__write_queue, self.maxwritebuf):
            return None
        return self.rfd

    def write_fd(self):
        if self.__write_eof:
            return None
        if len(self.__write_queue) == 0:
            return None
        return self.wfd

    def read_event(self):
        try:
            data = os.read(self.rfd, self.readchunk)
        except os.error, (e, emsg):
            if e in [errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK]:
                return 0
            return self.read_error(e)
        if data == "":
            self.__parser.append_eof()
        return self.__parser.append(data)

    def synthetic_read_event(self):
        return self.__parser.append("")

    def write_event(self):
        try:
            sz = os.write(self.wfd, self.__write_queue)
        except os.error, (e, emsg):
	    if e in [errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK]:
		return
	    elif e == errno.EPIPE:
                self.__write_eof = 1
                self.__write_queue = ""
                self.handle_epipe(self.__parser)
		return
	    else:
		self.write_error(e)
                return
        self.__write_queue = self.__write_queue[sz:]
        if len(self.__write_queue) == 0 and self.__deferred_close:
            self.close()

    def write(self, s):
        if not self.__write_eof and not self.__deferred_close:
            self.__write_queue = self.__write_queue + s

    def deferred_close(self):
        self.__deferred_close = 1
        if self.__write_eof or len(self.__write_queue) == 0:
            self.close()

    def close(self):
        self.dispatcher.unregister(self)

    def error(self):
        self.close()

    def read_error(self, eno):
        self.error()

    write_error = read_error

    def handle_epipe(self, unparsed):
        self.close()


class socket_base(fd_base):
    af = socket.AF_INET
    pf = socket.SOCK_STREAM
    
    def __init__(self, dispatcher, parser, s=None):
        if s is None:
            self.sock = socket.socket(self.af, self.pf)
        else:
            self.sock = s
        self.sock.setblocking(0)
        fd = self.sock.fileno()
        fd_base.__init__(self, dispatcher, parser, fd, fd)

    def close(self):
        fd_base.close(self)
        self.sock.close()

class server_socket(socket_base):

    maxwritebuf = 8192

    def __init__(self, dispatcher, parser, addr, client_class):
        socket_base.__init__(self, dispatcher, None)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(addr)
        self.sock.listen(3)
        self.__client_class = client_class
        self.__client_parser = parser

    def write_fd(self):
        return None

    def read_fd(self):
        return self.rfd

    def read_event(self):
        (s, remoteaddr) = self.sock.accept()
        self.__client_class(self.dispatcher, self.__client_parser, s)
        return 0
    
class client_socket(socket_base):
    def __init__(self, dispatcher, parser, addr):
        socket_base.__init__(self, dispatcher, parser)
        try:
            self.sock.connect(addr)
        except socket.error, (e, emsg):
	    if e == errno.EINPROGRESS:
                pass
            else:
                raise

class process_handler(fd_base):
    def __init__(self, dispatcher, rfd, wfd=None):
        pass # FIXME
        
    def close(self):
        if self.rfd != None:
            os.close(self.rfd)
        if self.wfd != None:
            os.close(self.wfd)

class process:
    def __init__(self, dispatcher, path, args):
        (in_r, in_w) = os.pipe()
        (out_r, out_w) = os.pipe()
        (err_r, err_w) = os.pipe()
        child = os.fork()
        if child == 0:
            # in the child
            os.close(in_w)
            os.close(out_r)
            os.close(err_r)
            os.dup2(in_r, 0)
            os.dup2(out_w, 1)
            os.dup2(err_w, 2)
            os.close(in_r)
            os.close(out_w)
            os.close(err_w)
            os.execvp(path, args)
            os._exit(1)
        else:
            # in the parent
            os.close(in_r)
            os.close(out_w)
            os.close(err_w)
            return (child, fd_owner(dispatcher, out_r, in_w), fd_owner(dispatcher, err_r, None))
        

class dispatcher:
    def __init__(self):
        self.__clients = {}
        self.__pending_r = {}
        self.__closing = 0

    def register(self, client):
        self.__clients[client] = None

    def unregister(self, client):
        del self.__clients[client]

    def close(self):
        self.__closing = 1

    def main_iteration(self, maxtimeout=None, r_set=[], w_set=[]):
        if self.__closing:
            for cl in self.__clients.keys():
                cl.close()
        rset = r_set[:]
        wset = w_set[:]
        rmap = {}
        wmap = {}
        rpend_set = []
        for cl in self.__clients.keys():
            if self.__pending_r.has_key(cl):
                rpend_set.append(cl)
            else:
                fd = cl.read_fd()
                if fd is not None:
                  rmap[fd] = cl
                  rset.append(fd)
            fd = cl.write_fd()
            if fd is not None:
                wmap[fd] = cl
                wset.append(fd)

        if rpend_set != [] or (wset == [] and self.__closing):
            maxtimeout = 0
        rset, wset, eset = select.select(rset, wset, [], maxtimeout)

        self.__pending_r = {}

        for fd in wset:
            wmap[fd].write_event()
        for cl in rpend_set:
            if cl.synthetic_read_event():
                self.__pending_r[cl] = None
        for fd in rset:
            cl = rmap[fd]
            if cl.read_event():
                self.__pending_r[cl] = None

    def toploop(self):
        while not self.__closing or len(self.__clients) > 0:
            self.main_iteration()
