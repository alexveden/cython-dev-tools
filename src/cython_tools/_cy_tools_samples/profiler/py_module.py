from .cy_module import recip_square2

def recip_square3(z):
    return 1. / (z * z)

class SQ:
    def recip_square2(self, i):
        return recip_square3(i)

def approx_pi2(n=1000):
    val = 0.
    s = SQ()
    for k in range(1, n + 1):
        if k > n*0.5:
            val += s.recip_square2(k)
        else:
            val += recip_square2(k)
    return (6 * val) ** .5

