# -*- coding: iso-8859-1 -*-
# Quotes a string so that it can be put in a latex-document.
# This is useful for printed reports etc.
#
# Please note that I have failed to find a complete listing of
# latex special characters, so this is generally the result of some
# creative guessing.
#
# This could probably also be done a lot quicker with the re-module.
#
# David Björkevik 2003

def latexquote(st):
    """Quotes a string for use in a latex document"""
    retst = ""
    # Characters that require a backslash before them
    special = "$%&%{}_"
    # A mapping of characters where a simple backslash doesn't do the trick
    veryspecial = {"\\": "\\backslash",
                   "~": "\\~{}",
                   "^": "\\^{}",
                   "<": "$<$",
                   ">": "$>$",
                   "|": "$\mid$",
                   }
    for ch in st:
        if ch in special:
            retst = retst + "\\" + ch
        elif veryspecial.has_key(ch):
            retst = retst + veryspecial[ch]
        else:
            retst = retst + ch
    return retst
 
