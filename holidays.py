# Miscellaneous holiday-related calculations
# Not much here now

import jddate

# Auxiliary function
def divmod(x,y):
    return (x/y,x%y)

# 
def easter_day(year):
    a = year % 19
    (b, c) = divmod(year,100)
    (d, e) = divmod(b,4)
    f = (b + 8) / 25
    g = (b - f + 1) / 3
    h = (19 * a + b - d - g + 15) % 30;
    (i,k) = divmod(c,4)
    l = (32 + 2 * e + 2  * i - h  - k) % 7
    m = (a + 11 * h + 22 * l) / 451
    (n,p) = divmod(h + l - 7 * m + 114, 31)
    return jddate.FromYMD(year,n,p+1)

