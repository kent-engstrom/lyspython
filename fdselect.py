"""select-based FD multiplexing.

THIS IS AN EARLY COMMIT OF WORK IN PROGRESS FOR BACKUP PURPOSES.  ALL
API:s SUBJECT TO CHANGE.

Copyright (C) 2000 Per Cederqvist.

Shutdown/EOF actions:

Type of application     Wanted behaviour

telnet-client socket    Shut down the application
telnet-client user-tty  Shut down the application
telnetd socket          Shut down the socket and pty; keep telnetd running
telnetd pty             Shut down the socket and pty; keep telnetd running
cdparanoia stdout       if all three: shut down socket and process
cdparanoia stderr       -"-
cdparanoia process      -"-

"""

import select
import socket
import os
import errno
import string
import signal

class eof_policy_deferred_close:
    def __init__(self, callback = None):
        self.__client = None
        self.__cb = callback

    def register(self, client):
        assert self.__client == None
        assert callable(client.deferred_close)
        self.__client = client

    def report_eof(self, client):
        assert self.__client == client
        self.__client.deferred_close()

    def report_close(self, client):
        assert self.__client == client
        if self.__cb is not None:
            self.__cb(client)
        # Break the circular dependency
        self.__client = None

class eof_policy_deferred_shutdown(eof_policy_deferred_close):
    def report_close(self, client):
        eof_policy_deferred_close.report_close(client)
        client.dispatcher.close()

class eof_policy_first_close:
    def __init__(self):
        self.__clients = {}

    def register(self, client):
        self.__clients[client] = None

    def report_eof(self, client):
        for cl in self.__clients.keys():
            cl.close()

    def report_close(self, client):
        del self.__clients[client]

class eof_policy_first_close_shutdown(eof_policy_first_close):
    def report_close(self, client):
        eof_policy_first_close.report_close(self, client)
        client.dispatcher.close()

class eof_policy_process_close:
    def __init__(self):
        self.__clients = {}
        self.__closed = {}
        self.__pids = {}

    def register(self, client):
        assert self.__closed == {}
        self.__clients[client] = None

    def register_pid(self, pid):
        self.__pids[pid] = None

    def report_eof(self, client):
        assert self.__clients.has_key(client)
        assert not self.__closed.has_key(client)
        self.__closed[client] = None
        self.__check()

    def report_dead_child(self, pid):
        del self.__pids[pid]
        self.__check()

    def __check(self):
        if len(self.__closed) == len(self.__clients) \
           and len(self.__pids) == 0:

            for cl in self.__closed.keys():
                cl.close()

    def report_close(self, client):
        self.__clients = {}
        self.__closed = {}

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

    def handle_input_line(self, s):
        """Handle a line.  May be overridden.

        Argument: a complete line (without the trailing line end).
        This default implementation splits the line
        whitespace-separated words.  It the calls a method named
        self.line_WORD where WORD is the first word of the line.  That
        method receives all the words as a list.
        """

        words = string.split(s)
        if len(words):
            method = getattr(self, "line_" + words[0])
            method(words)

    def handle_read_eof(self, unparsed):
        self.parent.parser_eof()

    def write(self, s):
        self.parent.write(s)


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

    def __init__(self, dispatcher, parser, eof_policy, rfd, wfd=None):
        self.rfd = rfd
        self.wfd = wfd
        self.__write_queue = ""
        self.__write_eof = 0
        self.eof_policy = eof_policy
        if parser is not None:
            self.__parser = parser(self)
            assert self.__parser is not None
        self.__deferred_close = 0
        self.dispatcher = dispatcher
        self.dispatcher.register(self)
        if self.eof_policy is not None:
            self.eof_policy.register(self)

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

    def parser_eof(self):
        self.eof_policy.report_eof(self)

    def close(self):
        if self.eof_policy is not None:
            self.eof_policy.report_close(self)
        self.dispatcher.unregister(self)

    def error(self):
        self.close()

    def read_error(self, eno):
        self.error()

    write_error = read_error

    def handle_epipe(self, unparsed):
        self.close()

    def child_pids(self):
        return []

class socket_base(fd_base):
    af = socket.AF_INET
    pf = socket.SOCK_STREAM
    
    def __init__(self, dispatcher, parser, eof_policy, s=None):
        if s is None:
            self.sock = socket.socket(self.af, self.pf)
        else:
            self.sock = s
        self.sock.setblocking(0)
        fd = self.sock.fileno()
        fd_base.__init__(self, dispatcher, parser, eof_policy, fd, fd)

    def close(self):
        fd_base.close(self)
        if self.sock != None:
            self.sock.close()
            self.sock = None

class server_socket(socket_base):

    maxwritebuf = 8192

    def __init__(self, dispatcher, parser, eof_policy, addr, client_class):
        socket_base.__init__(self, dispatcher, None, None)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(addr)
        self.sock.listen(3)
        self.__client_class = client_class
        self.__client_parser = parser
        self.__client_eof_policy = eof_policy

    def write_fd(self):
        return None

    def read_fd(self):
        return self.rfd

    def read_event(self):
        (s, remoteaddr) = self.sock.accept()
        self.__client_class(self.dispatcher, self.__client_parser,
                            self.__client_eof_policy(), s)
        return 0
    
class client_socket(socket_base):
    def __init__(self, dispatcher, parser, eof_policy, addr):
        socket_base.__init__(self, dispatcher, parser, eof_policy)
        try:
            self.sock.connect(addr)
        except socket.error, (e, emsg):
	    if e == errno.EINPROGRESS:
                pass
            else:
                raise

class fd_owner(fd_base):
    def close(self):
        fd_base.close(self)
        if self.rfd != None:
            os.close(self.rfd)
            self.rfd = None
        if self.wfd != None:
            os.close(self.wfd)
            self.wfd = None

class process(fd_owner):
    def __init__(self, dispatcher, stdout_parser, stderr_parser, eof_policy,
                 path, args):
        (in_r, in_w) = os.pipe()
        (out_r, out_w) = os.pipe()
        (err_r, err_w) = os.pipe()
        self.__child_pid = os.fork()
        if self.__child_pid == 0:
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
        # in the parent
        os.close(in_r)
        os.close(out_w)
        os.close(err_w)
        assert stdout_parser is not None
        fd_owner.__init__(self, dispatcher, stdout_parser, eof_policy,
                          out_r, in_w)
        self.stderr_object = fd_owner(dispatcher, stderr_parser,
                                      eof_policy, err_r)
        eof_policy.register_pid(self.__child_pid)

    def child_pids(self):
        return [self.__child_pid]

    def child_status(self, pid, status):
        assert pid == self.__child_pid
        if os.WIFEXITED(status):
            self.child_exited(pid, os.WEXITSTATUS(status))
        elif os.WIFSTOPPED(status):
            self.child_stopped(pid, os.WSTOPSIG(status))
        elif os.WIFSIGNALED(status):
            self.child_signaled(pid, os.WTERMSIG(status))
        else:
            assert 0

    def child_exited(self, pid, status):
        assert pid == self.__child_pid
        self.child_dead(pid)
        if status != 0:
            self.error()

    def child_stopped(self, pid, sig):
        assert pid == self.__child_pid
        os.kill(pid, signal.SIGCONT)

    def child_signaled(self, pid, sig):
        assert pid == self.__child_pid
        self.child_dead(pid)
        self.error()

    def child_dead(self, pid):
        assert pid == self.__child_pid
        self.__child_pid = None
        self.eof_policy.report_dead_child(pid)

class dispatcher:
    def __init__(self):
        self.__clients = {}
        self.__pending_r = {}
        self.__closing = 0

    def register(self, client):
        self.__clients[client] = None

    def unregister(self, client):
        if self.__clients.has_key(client):
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
        pidmap = {}
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
            for pid in cl.child_pids():
                pidmap[pid] = cl

        if rpend_set != [] or (wset == [] and self.__closing):
            maxtimeout = 0
        if pidmap != {}:
            maxtimeout = min(maxtimeout, 5)
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
        while len(pidmap) > 0:
            try:
                (pid, status) = os.waitpid(-1, os.WNOHANG)
            except os.error, e:
                if e.errno == errno.ECHILD:
                    break
                raise
            if pid == 0:
                break
            pidmap[pid].child_status(pid, status)

    def toploop(self):
        while not self.__closing or len(self.__clients) > 0:
            self.main_iteration()
