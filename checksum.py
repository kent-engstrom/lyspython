#
# Checksum calculations
# - ISBN
# - Personnummer (and other data using the same algorithm)
# (C) 1998 Kent Engstrˆm. Released under GNU GPL.

import sys, string

# Auxiliary functions

def strip_separators(str, data_chars, sep_chars):
    """Strip separators and other non-data characters from a string.

    Arguments:
    str        -- string to check
    data_chars -- characters that should be considered as data
    sep_chars  -- characters that should be considered as separators

    Return a tuple containing:
    - data string (containing only characters in data_chars)
    - number of separators removed
    - number of other characters removed
    """

    data = []
    sep_count = 0
    other_count = 0
    for c in str:
	if c in data_chars:
	    data.append(c)
	elif c in sep_chars:
	    sep_count = sep_count + 1
	else:
	    other_count = other_count + 1

    return (string.join(data, ""), sep_count, other_count)

def digit_string_sum(digits, weights, sum_init=0, adder=None):
    """Calculate the sum of a string of digits.

    Arguments:
    digits -- string of digits to sum
    weights -- vector of weights OR a function calculating the weight
    sum_init -- starting value for the sum (default 0)
    adder -- function used to add each term to the sum (default normal "+")

    If weights are specified as a vector, it must be the same length as
    the digit string. If it is specified as a function, it should accept
    two arguments (position starting at 0, length of digits string) and
    return the weight at that position.

    Returns the sum as an integer.
    """

    sum = sum_init
    ord0 = ord('0')
    digits_length = len(digits)

    if adder == None:
	adder = lambda x,y: x+y

    if type(weights) == type([]):
	wfun = lambda i, l, w=weights: w[i]
    else:
	wfun = weights

    for i in range(digits_length):
	d = digits[i]
	if d >=  '0' and d <= '9':
	    incr = wfun(i,digits_length) * (ord(d) - ord0)
	    sum = adder(sum, incr)
	else:
	    return None
    return sum

#
# ISBN
#

def calculate_isbn_checksum(digits):
    """Calculate the ISBN check digit from a string of 9 digits.

    Return a single character (the check digit 0-9 or X),
    or None in case of error.
    """

    if len(digits) <> 9:
	return None

    sum = digit_string_sum(digits, [10, 9, 8, 7, 6, 5, 4, 3, 2])
    if sum == None:
	return None
    checksum = 11 - (sum % 11)
    if checksum == 11:
	checksum = 0
    if checksum < 10:
	return chr(ord('0') + checksum)
    else:
	return 'X'

def valid_isbn(isbn, hyphens_optional=0):
    """Check if an ISBN is valid.

    Arguments:
    isbn -- string containing ISBN to check
    hyphens_optional -- set if a non-hyphenated ISBN is OK

    Returns 1 if the ISBN is correct, 0 otherwise.
    """

    (stripped_isbn, hyphen_count, other_count) = \
		    strip_separators(isbn, "0123456789X", "-")
    if other_count <> 0:
	return 0
    elif not ((hyphen_count == 0 and hyphens_optional) or hyphen_count == 3):
	return 0
    elif len(stripped_isbn) <> 10:
	return 0
    else:
	checkdigit = calculate_isbn_checksum(stripped_isbn[0:9])
	if checkdigit == None or checkdigit <> stripped_isbn[9]:
	    return 0
	else:
	    return 1

#
# PNRALG - Same basic algorithm as swedish "personnummer"
#

def pnralg_weight(i, l):
    """Return the weight at position 'i' in an 'l' long string""" 
    return (l-i)%2+1

def pnralg_adder(sum, incr):
    """Add to sum for personnummer-like checksums."""

    if incr<10:
	return sum + incr
    else:
	return sum + incr - 9

def calculate_pnralg_checksum(digits, min_length=1, max_length=None):
    """Calculate the personnummer-like check digit from a string of digits.

    Return a single character (the check digit 0-9) or None in case of error.
    """

    digits_length = len(digits)

    if digits_length < min_length:
	return None
    elif max_length <> None and digits_length > max_length:
	return None

    sum = digit_string_sum(digits, pnralg_weight, adder = pnralg_adder)
    if sum == None:
	return None
    else:
	return (chr(ord('0') + 10 - (sum % 10)))

def valid_pnralg(digits, min_length=1, max_length=None):
    """Check if a personnummer-like string is valid.

    Arguments:
    digits -- string of digits to check
    min_length -- minimum length of the string (default 1)
    max_length -- maximum length of the string (defalt None, i.e. no limit)

    Returns 1 if it is correct, 0 otherwise.
    """

    # Lengths without check digit
    min_length = min_length - 1
    if max_length <> None:
	max_length = max_length - 1

    check_digit = calculate_pnralg_checksum(digits[:-1], \
					    min_length, max_length)
    if check_digit == None or check_digit <> digits[-1:]:
	return 0
    else:
	return 1

#
# PERSONNUMMER - Swedish "Social Security Number"
#

def calculate_personnummer_checksum(digits):
    """Calculate the personnummer check digit from a string of 9 digits.

    Return a single character (the check digit 0-9),
    or None in case of error.
    """

    return calculate_pnralg_checksum(digits, min_length=9, max_length=9)

def valid_personnummer(pnr, hyphen_allowed=1, hyphen_required=0):
    """Check if a personnummer is valid.

    Arguments:
    pnr -- string containing personnummer to check
    hyphen_allowed -- set if a hyphen (as in ≈≈MMDD-XXXY) is allowed
    hyphen_required -- set if a hyphen is required

    The default setting is that a hyphen is allowed but not required.
    It is an error to call this function with hyphen_required true and
    hyphen_allowed false.

    Returns 1 if it is correct, 0 otherwise.
    """
    
    # Check length and hyphen status
    pnr_length = len(pnr)
    if pnr_length == 10:
	if hyphen_required:
	    return 0
    elif pnr_length == 11:
	if hyphen_allowed:
	    if pnr[6] == "-":
		pnr = pnr[:6]+pnr[7:]
	    else:
		return 0
	else:
	    return 0
    else:
	return 0
    
    # Now check the check digit
    return valid_pnralg(pnr, min_length=10, max_length=10)

# Test
def test():
    for arg in sys.argv[1:]:
	print arg,valid_pnralg(arg)
#	print arg,valid_isbn(arg)

if __name__ == '__main__':
    test()
