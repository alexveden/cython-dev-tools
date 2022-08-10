"""
Experimenting setting breakpoints right in C CODE, equivalent to python breakpoint() functin

This is about debugging low level / cdef functions or other C code which can be compiled with Cython.

Cython Tools run command:
cytool debug cy_tools_samples/debugging/assertions.pyx@main
"""
from libc.errno cimport errno, ENOENT
from libc.stdio cimport printf, FILE, fopen, stderr, perror, fprintf
from libc.signal cimport raise_, SIGTRAP

# We need to define *cpdef* to make it able to run via python,
#   i.e. technically it's a C function with python wrapper
cpdef main():
    # Try to open non-existing file and get an error type and message
    cdef char * file_name = '__NoT_eXists__.txt'

    # This will trigger programmable breakpoint on Linux GDB, and allow step next without crashing the program
    #     On Windows you can try research __debugbreak() function.
    raise_(SIGTRAP)

    printf('Trying to open non-existing file: %s\n', file_name)
    printf('Current errno is %d\n', errno)

    cdef FILE *fh = fopen(file_name, 'r')
