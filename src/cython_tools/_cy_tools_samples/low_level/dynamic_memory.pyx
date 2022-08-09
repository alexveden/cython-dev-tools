"""
Simple example how to get low level C dynamic memory allocation

# More Cython includes available here:
https://github.com/cython/cython/blob/master/Cython/Includes/libc/

Cython Tools run command:
cytool run cy_tools_samples/low_level/dynamic_memory.pyx@main
"""
from libc.stdio cimport printf
from libc.stdlib cimport malloc, free
from libc.string cimport memmove, memcpy

ctypedef struct MyStructType:
    int x
    int y

cdef void print_int_array_func(int* array, int size) nogil:
    cdef int i    # set i as int, otherwise it will be set to long (by Cython compiler -> gcc warnings)
    for i in range(size):
        printf("array[%d]=%d\n", i, array[i])

cdef void print_s_array_func(MyStructType* array, int size) nogil:
    cdef int i    # set i as int, otherwise it will be set to long (by Cython compiler -> gcc warnings)
    for i in range(size):
        printf("print_s_array_func: MyStructType[%d] -> x=%d, y=%d\n", i, array[i].x, array[i].y)

cpdef main():
    cdef int i = 777
    cdef int *int_ptr = &i

    cdef int *int_array = <int*>malloc(sizeof(int) * 4)
    # No luck with python `print`, because Cannot convert 'int *' to Python object, must implement custom function
    # print(int_array)

    printf('Uninitialized memory int array\n')
    print_int_array_func(int_array, 4)

    # This notation works with pointers too
    int_array[:] = [21, 22, 23, 24]
    printf('Assigned int array\n')
    print_int_array_func(int_array, 4)

    cdef int[4] const_array = [1, 2, 3, 4]
    # void *memcpy(void *restrict dest, const void *restrict src, size_t n);
    # The memcpy() function copies n bytes from memory area src to
    #        memory area dest.  The memory areas must not overlap.  Use
    #        memmove(3) if the memory areas do overlap.

    # Fully copy one array into another
    memcpy(int_array, const_array, sizeof(int) * 4)
    printf('Copied int array\n')
    print_int_array_func(int_array, 4)

    # Partial copy
    int_array[:] = [21, 22, 23, 24]
    # Copy                  [1,  2]
    # Expected     [21, 22,  1,  2]
    memcpy(int_array+2, const_array, sizeof(int) * 2)
    printf('Partial copy with pointer offset int array\n')
    print_int_array_func(int_array, 4)

    # Copy overlapping (IMPORTANT: use memmove() for overlapping)
    int_array[:] = [21, 22, 23, 24]
    # Copy self            [21, 22]
    # Expected     [21, 22, 21, 22]
    memmove(int_array + 2, int_array, sizeof(int) * 2)
    printf('Overlapping copy of the int_array inself\n')
    print_int_array_func(int_array, 4)

    cdef MyStructType *s_array = <MyStructType *> malloc(sizeof(MyStructType) * 2)

    s_array[0].x = 1
    s_array[0].y = 2
    s_array[1].x = 3
    s_array[1].y = 4

    # No luck with python `print`, because `Cannot convert 'MyStructType *' to Python object`
    # print(s_array)

    # We need to implement low level printing of structs
    cdef int j  # set i as int, otherwise it will be set to long (by Cython compiler -> gcc warnings)
    for j in range(2):
        printf("MyStructType[%d]: x=%d, y=%d\n", j, s_array[j].x, s_array[j].y)

    # Or wrap as a function
    print_s_array_func(s_array, 2)


    # Don't forget to call free after using the dynamic memory
    free(s_array)
    free(int_array)

