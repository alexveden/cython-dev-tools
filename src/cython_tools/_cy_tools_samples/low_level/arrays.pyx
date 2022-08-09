"""
Simple example how to get low level C arrays management

# More Cython includes available here:
https://github.com/cython/cython/blob/master/Cython/Includes/libc/

Cython Tools run command:
cytool run cy_tools_samples/low_level/arrays.pyx@main
"""
from libc.stdio cimport printf

# We need to define *cpdef* to make it able to run via python,
#   i.e. technically it's a C function with python wrapper

# Equivalent to #define  in C
DEF STR_CONST = u"spam"
DEF ARR_SIZE = 4
DEF DBL_ARR_SIZE = 2 * ARR_SIZE

ctypedef struct MyStructType:
    int x
    double y


cdef struct MyStruct:
    int x
    double y

cdef print_int_array_func(int[] array, int size):
    cdef int i    # set i as int, otherwise it will be set to long (by Cython compiler -> gcc warnings)
    for i in range(size):
        printf("print_int_array_func: array[%d]=%d\n", i, array[i])

cdef print_int_array_func_ptr(int * array, int size):
    cdef int i    # set i as int, otherwise it will be set to long (by Cython compiler -> gcc warnings)
    for i in range(size):
        printf("print_int_array_func_ptr: array[%d]=%d\n", i, array[i])

cpdef main():
    # Number in array len must be equal to the number of assigning elements
    # Otherwise you will get something line this:
    # arrays.pyx:18:9: Assignment to slice of wrong length, expected 4, got 3
    cdef int[4] int_array = [1, 2, 3, 4]

    # Python print works with C-arrays too, but with overhead
    print(f'int_array: {int_array}')

    int_array[:] = [21, 22, 23, 24]
    print(f'int_array assigned: {int_array}')

    # May not be efficient
    #cdef int[4] int_array = [1, 2, 3, 4]
    #int_array[:] = [21, 22, 23, 24]
    # C does the following
    # int[4] __pyx_t_1;  // Creates temporary array
    # Assign it
    # __pyx_t_1[0] = 1;
    # __pyx_t_1[1] = 2;
    # __pyx_t_1[2] = 3;
    # __pyx_t_1[3] = 4;
    # memcpy from temp array to int_array in cython
    # memcpy(&(__pyx_v_int_array[0]), __pyx_t_1, sizeof(__pyx_v_int_array[0]) * (4));


    # More efficiently to set one by one
    # Array with DEF constant also works
    cdef int[ARR_SIZE] int_array2
    int_array2[0] = 11
    int_array2[1] = 12
    int_array2[2] = 13
    int_array2[3] = 14

    print(int_array2)

    #
    #  Array of structs
    #
    cdef MyStructType[2] v
    v[0] = MyStructType(1, 2)
    v[1] = MyStructType(3, 4)

    cdef MyStruct[2] w
    w[0] = MyStruct(5, 6)
    w[1] = MyStruct(7, 8)

    print('MyStructType array')
    print(v)

    print('MyStruct array')
    print(w)

    #
    # Printing with C
    #
    # We must print each element one-by-one! because printf() is a low-level function
    #for i in range(len(int_array)):   <- this is also viable but will call python code => overhead

    # In C we must store array length separately too
    cdef int i    # set i as int, otherwise it will be set to long (by Cython compiler -> gcc warnings)
    for i in range(ARR_SIZE):
        printf("int_array2[%d]=%d\n", i, int_array2[i])

    # Print via func
    # Still need a size argument, because C does not have any cluse about array sizes
    print_int_array_func(int_array, 4)

    # We also can pass array as pointer
    print_int_array_func_ptr(int_array, 4)
