"""
Simple example how to get low level C pointers

# More Cython includes available here:
https://github.com/cython/cython/blob/master/Cython/Includes/libc/

Cython Tools run command:
cytool run cy_tools_samples/low_level/pointers.pyx@main
"""
from libc.stdio cimport printf

ctypedef struct MyStructType:
    int x
    int y

cpdef main():
    cdef int i = 777
    cdef int *int_ptr = &i

    printf('i value: %d\n', i)
    printf('int_ptr address: %p\n', int_ptr)

    # In Cython we can't dereference with *int_ptr, we must use array[0] notation
    # See: https://cython.readthedocs.io/en/latest/src/userguide/language_basics.html#types
    printf('int_ptr de-referenced value: %d\n', int_ptr[0])

    # Setting i value via pointer
    int_ptr[0] = 888
    printf('int_ptr address: %p\n', int_ptr)
    printf('int_ptr de-referenced value: %d\n', int_ptr[0])
    printf('i value: %d\n', i)

    # This possibly may cause segmentation fault or unpredictable program results
    # However this will compile, and sometimes or most of the time work
    # int_ptr[1] = 888

    cdef MyStructType s;
    s.x = 200
    s.y = 100
    cdef MyStructType *s_ptr = &s

    printf('MyStructType x=%d y=%d\n', s.x, s.y)
    printf('MyStructType ptr %p\n', s_ptr)
    # The same with structs, instead of s_ptr->x, use array notation at first element s_ptr[0].x
    printf('MyStructType ptr value x=%d y=%d\n', s_ptr[0].x, s_ptr[0].y)
    s_ptr[0].x = 400
    s_ptr[0].y = 200

    printf('MyStructType CHG ptr value x=%d y=%d\n', s_ptr[0].x, s_ptr[0].y)
    printf('MyStructType CHG x=%d y=%d\n', s.x, s.y)




