"""
Simple example how to get low level C errno

Equivalent of C code:

    #include <errno.h>
    extern int errno;

# More Cython includes available here:
https://github.com/cython/cython/blob/master/Cython/Includes/libc/

Cython Tools run command:
cytool run cy_tools_samples/low_level/errors.pyx@main
"""
from libc.errno cimport errno, ENOENT
from libc.stdio cimport printf, FILE, fopen, stderr, perror, fprintf
from libc.string cimport strerror

# We need to define *cpdef* to make it able to run via python,
#   i.e. technically it's a C function with python wrapper
cpdef main():

    # Try to open non-existing file and get an error type and message
    cdef char * file_name = '__NoT_eXists__.txt'

    # Don't forget \n to pring new line
    printf('Trying to open non-existing file: %s\n', file_name)
    printf('Current errno is %d\n', errno)

    cdef FILE *fh = fopen(file_name, 'r')
    if fh == NULL:
        printf('file open error. errno: %d\n', errno)

        # We can also get string representation of this errno
        printf('errno message: %s\n', strerror(errno))

        # Print another way, also this message is output into stderr stream!
        perror('This msg print by perr')

        # Print to stderr directly
        fprintf(stderr, 'My error in the stderr: %s\n', strerror(errno))

        # Trying to figure out by errno constants
        # ENOENT 2 No such file or directory
        # More info https://man7.org/linux/man-pages/man3/errno.3.html
        # Or run in terminal `errno -l`
        if errno == ENOENT:
            printf("It's definitely ENOENT=%d\n", errno)


