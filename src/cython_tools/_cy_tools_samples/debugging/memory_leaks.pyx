"""
Experimenting with valgrind

This is about debugging low level / cdef functions or other C code which can be compiled with Cython.

Cython Tools run command:
cytool debug cy_tools_samples/debugging/memory_leaks.pyx@main
"""
from libc.stdlib cimport malloc, free

# We need to define *cpdef* to make it able to run via python,
#   i.e. technically it's a C function with python wrapper

cdef sum(n, v):
    cdef int *int_ptr = <int *> malloc(n * sizeof(int))
    cdef int sum = 0
    for i in range(n):
        int_ptr[i] = v
        sum += int_ptr[i]
    return sum


cpdef main():
    cdef int sum_ = sum(10000, 1)
    print(sum_)
    # free() was not called memory leak!
    # free(int_ptr)
