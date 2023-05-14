"""
Simple example how to allocate and resize dynamic 2D arrays

Cython Tools run command:
cytool run cy_tools_samples/low_level/arrays_resize.pyx@main
"""
from libc.stdio cimport printf
from libc.stdlib cimport malloc, realloc, free

# We need to define *cpdef* to make it able to run via python,
#   i.e. technically it's a C function with python wrapper

cdef void fill_matrix(int **array, int rows, int cols) nogil:
    cdef int i, j
    for i in range(rows):
        for j in range(cols):
            array[i][j] = (i * 10) + j

cdef void print_matrix(int **array, int rows, int cols) nogil:
    cdef int i, j
    for i in range(rows):
        for j in range(cols):
            printf("%02d ", array[i][j])
        printf("\n")
    printf("\n")

cpdef main():
    # This is a kind of fixed size array, we can edit, but we can't resize it
    cdef int[4][4] int_array = [[1, 2, 3, 4],
                                [11, 12, 13, 14],
                                [21, 22, 23, 24],
                                [31, 32, 33, 34]]


    # Python print works with C-arrays too, but with overhead
    print(f'int_array: {int_array}')

    print(f'int_array row0: {int_array[0]}')
    print(f'int_array row[0][1]: {int_array[1][1]}')

    # Alter the row, via copy
    int_array[0][:] = [51, 52, 53, 54]
    print(f'int_array row0: {int_array[0]}')

    # Alter the row via direct set
    int_array[1][0] = 61
    int_array[1][1] = 62
    int_array[1][2] = 63
    int_array[1][3] = 64
    print(f'int_array row1: {int_array[1]}')

    #
    # Let's create a dynamic 2D array
    #
    cdef int cols = 4
    cdef int rows = 4
    # array - is array of int pointers
    cdef int **array = <int **>malloc(sizeof(int*) * rows)

    # Allocate memory for rows
    for i in range(rows):
        array[i] = <int*>malloc(sizeof(int) * cols)
    printf("Initial dynamic memory matrix %dx%d\n", rows, cols)
    fill_matrix(array, rows, cols)
    print_matrix(array, rows, cols)

    # Dynamically resize the arrays

    cdef int add_cols = 2
    cols += add_cols
    for i in range(rows):
        # pointer address may not change after realloc
        printf("array[%d] - before - addr: %p\n", i, array[i])
        array[i] = <int *> realloc(array[i], sizeof(int) * cols)
        printf("array[%d] - after - addr: %p\n", i, array[i])

    printf("Added columns to matrix %dx%d\n", rows, cols)
    fill_matrix(array, rows, cols)
    print_matrix(array, rows, cols)


    cdef int add_rows = 3
    rows += add_rows

    # first we need to reallocate the array itself
    array = <int **> realloc(array, sizeof(int *) * rows)

    for i in range(rows-add_rows, rows):
        # Allocate new row first time
        array[i] = <int*>malloc(sizeof(int) * cols)

    printf("Added columns to matrix %dx%d\n", rows, cols)
    fill_matrix(array, rows, cols)
    print_matrix(array, rows, cols)

    #
    # Free the memory!
    #
    for i in range(rows):
        free(array[i])
    free(array)

    printf('array address %p\n', array)