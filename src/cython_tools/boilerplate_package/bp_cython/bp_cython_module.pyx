"""
Samples cython Module
"""
cdef bp_cython_cdeffunc(int a, int b):
    return a + b

cpdef bp_cython_cpdeffunc(int a, int b):
    return a + b

def bp_cython_deffunc(int a, int b):
    return a + b
