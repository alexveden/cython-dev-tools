cpdef double recip_square2(long i):
    return 1. / (i * i)

cdef class SQ:
    cpdef double recip_square_(self, long i):
        return 1. / (i * i)

def approx_pi2(int n=1000):
    cdef double val = 0.
    cdef int k
    sq = SQ()
    for k in range(1, n + 1):
        if k > n*0.5:
            val += recip_square2(k)
        else:
            val += sq.recip_square_(k)
    return (6 * val) ** .5