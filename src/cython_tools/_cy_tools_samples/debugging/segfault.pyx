"""
Experimenting with catching segmentation faults in debugger

This is about debugging low level / cdef functions or other C code which can be compiled with Cython.

Cython Tools run command:
cytool debug cy_tools_samples/debugging/segfault.pyx@main
"""

# We need to define *cpdef* to make it able to run via python,
#   i.e. technically it's a C function with python wrapper
cpdef main():
    cdef int *int_ptr = NULL

    # De-referencing NULL pointer
    # Run it in the debugger
    # (gdb) > cy locals
    # int_ptr = (int *) 0x0

    # Debugger will break at this line automatically
    int_ptr[0] = 1