"""
Simple example how to run low level printf

Cython Tools run command:
cytool run cy_tools_samples/low_level/hello_world.pyx@main
"""
from libc.stdio cimport printf

# We need to define *cpdef* to make it able to run via python,
#   i.e. technically it's a C function with python wrapper
cpdef main():
    cdef int i = 777
    cdef double pi = 3.14159
    cdef char * hello_world = "Hello world!"

    # We must set `\n` explicitly to print a line of text
    printf("%s Number of the day: %d Pi: %f\n", hello_world, i, pi)




