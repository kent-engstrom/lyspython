# filetree.py -- manipulate file hierarchies.

# Copyright (C) 1998 Per Cederqvist.  Released under GNU GPL.

# mv -- recursively move a directory tree.

# Acknowledgement: I looked at fileutils-3.16/src/mv.c from GNU
# fileutils while writing the code that copies a regular file.
# However, don't blame the authors of that code (Mike Parker and David
# MacKenzie) for any errors I (Per Cederqvist) may have introduced
# while transforming the algoritm from C to Python.

import os
import sys
import posix
import errno
from stat import *

mismatch = 'mismatch'

def mv(src, dst, keep_root, overwrite, verbosity):
    """Move the tree SRC to DST.

    SRC is the name of a file or directory.  The directory hierarchy
    rooted at SRC may contain regular files, directories and symbolic
    links.  They will be moved to DST.

    If KEEP_ROOT is true and SRC is a directory the directory SRC (but
    not its contents) will remain unaltered.  This can be useful if
    you want to move all files from one directory into another, but
    want to keep the base source directory.

    The OVERWRITE argument determines what will happen if a regular
    file or symbolic link in SRC already exists in DST.  It can take
    several values:

        0: Don't touch either SRC or DST.
	1: Ask for confirmation before moving SRC to DST. (This is not
	   yet implemented.)
	2: Overwrite DST with SRC without asking for confirmation.

    The function will print status messages if VERBOSITY is non-zero.

        0: Be silent.
	1: Print one line for each object that is moved.
	2: Also print one line each time something is removed or created.

    Upon normal return SRC will no longer exist, and the integer 0
    will be returned.  If any file was left in SRC the integer 1 will
    be returned instead (this can only happen if OVERWRITE is
    non-zero).

    An error is raised if anything but regular files, directories and
    symbolic links are found in SRC.  An error is also raised if there
    is a mismatch between the type of objects found in SRC and DST
    (for instance if SRC is a file and DST is a directory).
    """

    src_l = os.lstat(src)

    try:
	dst_l = os.lstat(dst)
    except os.error, (eno, msg):
	if eno != errno.ENOENT:
	    raise os.error, (eno, msg)
	dst_l = None

    if (dst_l != None and dst_l[ST_DEV] == src_l[ST_DEV] \
	and dst_l[ST_INO] == src_l[ST_INO]):
	raise mismatch, "same file: %s and %s" % (src, dst)

    if dst_l != None and S_ISLNK(dst_l[ST_MODE]):
	if verbosity >= 2:
	    print "unlink(%s)" % dst
	os.unlink(dst)
	dst_l = None

    if S_ISDIR(src_l[ST_MODE]):
	# Move a directory.
	if dst_l == None:
	    if not keep_root:
		try:
		    # If we can move the entire directory at once, do
		    # so and return immediately.  Do the job with the
		    # least effort possible.  Extra bonus: the mode of all
		    # subdirectories are retained.
		    os.rename(src, dst)
		    if verbosity >= 1:
			print "%s -> %s" % (src, dst)
		    return 0
		except os.error, (eno, msg):
		    # Handle cross-device moving.
		    if eno != errno.EXDEV:
			raise os.error, (eno, msg)
	    if verbosity >= 2:
		print "mkdir(%s)" % dst
		# We lose the mode and time of the directory.  That is OK.
		os.mkdir(dst, 0755)
	else:
	    if not S_ISDIR(dst_l[ST_MODE]):
		raise mismatch, "dir/nodir mismatch: " + src + " and " + dst

	# We could not move the entire directory, for one of several
	# reasons:
	#  * the destination was already present
	#  * src and dst are on different devices
	#  * keep_root is true.
	# Do a recursive move of all the contents.

	retval = 0
	for child in os.listdir(src):
	    if child != "." and child != "..":
		retval = retval or mv(os.path.join(src, child),
				      os.path.join(dst, child),
				      0, overwrite, verbosity)
	if retval == 0 and not keep_root:
	    if verbosity >= 2:
		print "rmdir(%s)" % src
	    os.rmdir(src)
	return retval
    else:

	# Handle regular files and symbolic links.
	mode = src_l[ST_MODE]
	if not (S_ISREG(mode) or S_ISLNK(mode)):
	    raise mismatch, "not dir, link or file: " + src

	if dst_l != None:
	    # The destination exists.
	    mode = dst_l[ST_MODE]
	    if not (S_ISREG(mode) or S_ISLNK(mode)):
		raise mismatch, "not link or file: " + dst

	    # Which file to you want to destroy today?
	    if overwrite == 0:
		return 1
	    elif overwrite == 1:
		response = raw_input("Overwrite `%s'? (y/n)" % dst)
		while response != "y" and response != "n":
		    response = raw_input(
			"Please answer `y' or `n'. Overwrite `%s'? (y/n)" %
			dst)
		if response == "n":
		    return 1
	    elif overwrite == 2:
		pass
	    else:
		raise error, ("bad value for overwrite parameter", overwrite)
		    
	    if verbosity >= 2:
		print "unlink(%s)" % dst
	    os.unlink(dst)

	# Copy the file (or symbolic link).
	if verbosity >= 1:
	    print "%s -> %s" % (src, dst)
	try:
	    os.rename(src, dst)
	except os.error, (eno, msg):
	    # Handle cross-device moving.
	    if eno != errno.EXDEV:
		raise os.error, (eno, msg)

	    if S_ISREG(mode):
		# Copy regular file with all attributes.
		sfp = open(src, "rb")
		dfp = open(dst, "wb")
		buf = sfp.read(64 * 1024)
		while buf != '':
		    dfp.write(buf)
		    buf = sfp.read(64 * 1024)
		sfp.close()
		dfp.close()
		os.utime(dst, (src_l[ST_ATIME], src_l[ST_MTIME]))
		try:
		    os.chown(dst, src_l[ST_UID], src_l[ST_GID])
		except os.error, (eno, msg):
		    # Ignore failures for non-root users to call chown.
		    if eno != errno.EPERM or os.geteuid() == 0:
			raise os.error, (eno, msg)
		os.chmod(dst, S_IMODE(src_l[ST_MODE]))

	    elif S_ISLNK(mode):
		# Copy symbolic link (sans attributes).
		lnk = os.readlink(src)
		os.symlink(lnk, dst)

	    else:
		assert(0)

	    if verbosity >= 2:
		print "unlink(%s)" % src
	    os.unlink(src)

	return 0
