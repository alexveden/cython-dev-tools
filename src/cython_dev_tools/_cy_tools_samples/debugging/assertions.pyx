"""
Experimenting with assertions.

This is about debugging low level / cdef functions or other C code which can be compiled with Cython.

Cython Tools run command:
cytool debug cy_tools_samples/debugging/assertions.pyx@main
"""
from libc.errno cimport errno, ENOENT
from libc.stdio cimport printf, FILE, fopen, stderr, perror, fprintf
from libc.string cimport strerror

cdef extern from "assert.h":
    # Replacing name to avoid conflict with python assert keyword!
    void cassert "assert"(bint)

# We need to define *cpdef* to make it able to run via python,
#   i.e. technically it's a C function with python wrapper
cpdef main():
    # Try to open non-existing file and get an error type and message
    cdef char * file_name = '__NoT_eXists__.txt'

    # Don't forget \n to pring new line
    printf('Trying to open non-existing file: %s\n', file_name)
    printf('Current errno is %d\n', errno)

    cdef FILE *fh = fopen(file_name, 'r')
    # This will show error, but doesn't provide any meaningful breakpoint in GDB
    #assert fh != NULL, f'File not open python'

    # Python breakpoint drop into Pdb but useless too!
    #breakpoint()

    # C-assert is useful
    # cassert(0 or 1)
    # In run mode it shows the error like:
    # python: cy_tools_samples/debugging/assertions.c:1579: __pyx__16cyions_main: Assertion `(__pyx_v_fh != NULL)' failed.
    # In debug mode it drops nearby assertion frame
    #
    # To get into the problematic line in CyGDB, use following commands
    # (gdb) > cy up [or cy u]
    #  (until you see the last line something like:
    # #25 0x00007ffff7fc0221 in main() at ..... /cy_tools_samples/debugging/assertions.pyx:40
    #         40        cassert(fh != NULL)
    #
    # To get a current line listing
    # (gdb) > cy list [or cy l]
    #
    # To get local variables
    # (gdb) > cy locals
    #    fh        = (FILE *) 0x0
    #    file_name = (char *) 0x7ffff7fc10cf "__NoT_eXists__.txt"

    # IMPORTANT! In C assert will fail only if argument is 0!
    #     Make sure that condition count this.
    # These will pass!!!
    cassert(-10000)
    cassert(100000)
    cassert(2)

    # This one will fail
    cassert(fh != NULL)



