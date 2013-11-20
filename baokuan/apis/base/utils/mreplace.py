import string

oldchars = '1234567890'
newchars = 'zyxwvutsrq'

def mreplace(text):
    if not hasattr(mreplace, 'trans'):
        mreplace.trans = string.maketrans(oldchars, newchars)
    return text.translate(mreplace.trans)

def str2intid(s):
    s = s.translate(string.maketrans(newchars,oldchars))
    return int(s, 26) >> 16

def int2str(num, base=16, sbl=None, minwidth=5):
    if not sbl:
        sbl = '0123456789abcdefghijklmnopqrstuvwxyz'
    if len(sbl) < 2:
        raise ValueError, 'size of symbols should be >= 2'
    if base < 2 or base > len(sbl):
        raise ValueError, 'base must be in range 2-%d' % (len(sbl))

    neg = False
    if num < 0:
        neg = True
        num = -num

    num, rem = divmod(num, base)
    ret = ''
    while num:
        ret = sbl[rem] + ret
        num, rem = divmod(num, base)
    ret = ('-' if neg else '') + sbl[rem] + ret

    padding_zeros =  minwidth - len(ret)
    if padding_zeros > 0:
        ret = 'q'*padding_zeros + ret

    return ret

if __name__ == '__main__':
    import time
    n = 12345
    intid = int(n) << 16 | int(time.time()) & 0xffff
    strid = mreplace(int2str(intid,26))
    intstrid = str2intid(strid) 
    print n
    print strid
    print intstrid
