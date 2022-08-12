# distutils: sources = cy_tools_samples/with_c_code/include/mymath.c
# distutils: include_dirs = cy_tools_samples/with_c_code/include
#     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# IMPORTANT: you must include this line to get mymath.c module compiled in the call_mymath.pyx (path must be relative to project root!)
#            SPACE separated source files are allowed too. (documentation say # distutils: sources = helper.c, another_helper.c, but this doesn't work!)
# Otherwise, you will have to setup dynamic linking https://github.com/cython/cython/tree/master/Demos/libraries

"""
Simple example how to include external .c code

Cython Tools run command:
cytool run cy_tools_samples/with_c_code/call_mymath.pyx@call_sinc
"""

cdef extern from "include/mymath.h":
    double sinc(double)


cpdef call_sinc():
    print('Calling mymath: sinc(10)')
    cdef double res = sinc(10.0)
    print(res)