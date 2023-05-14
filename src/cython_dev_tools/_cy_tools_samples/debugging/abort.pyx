"""
Experimenting with handling abort() right in the Cython code

This is about debugging low level / cdef functions or other C code which can be compiled with Cython.

Cython Tools run command:
cytool debug cy_tools_samples/debugging/abort.pyx@main
"""
from libc.stdio cimport  printf
from libc.stdlib cimport abort

# We need to define *cpdef* to make it able to run via python,
#   i.e. technically it's a C function with python wrapper
cpdef main():
    printf('Sending abort')

    abort()
