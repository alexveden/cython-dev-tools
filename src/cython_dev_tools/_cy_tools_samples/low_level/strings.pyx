"""
Simple example how to get low level C string management

Cython Tools run command:
cytool run cy_tools_samples/low_level/strings.pyx@main
"""
from libc.string cimport strlen, strcpy, strcat, strcmp, strtok
from libc.stdio cimport printf
from libc.stdlib cimport malloc, free

cpdef main():
    cdef char * cost_string = "I'm a constant string"

    # len(cost_string) also calls `strlen(cost_string)` when compiled
    # 1 step assign: __pyx_v_length = strlen(__pyx_v_cost_string);
    cdef size_t length = strlen(cost_string)

    # Assign via temp var
    # size_t __pyx_t_1;
    # __pyx_t_1 = strlen(__pyx_v_cost_string);
    #  __pyx_v_py_length = __pyx_t_1;
    cdef size_t py_length = len(cost_string)

    # Still need the %s, to format the string
    # Note: len()/strlen() return size_t is long unsigned int, and possible overflow on larger data (2+GB), and
    #       also gcc warnings -> use %lu instead of %d.
    printf("`%s`, my length is: strlen(%lu) len(%lu)\n", cost_string, length, py_length)

    # CRITICAL: we are not allowed to write to the memory of const stings -> SEGMENTATION FAULT
    # cost_string[:] = 'another string'
    # cost_string[0] = 98
    # cost_string[1] = 98

    # Python will treat this sting as b'I'm a constant string', i.e. byte array!
    print(cost_string)

    #
    # Figuring out how to edit the string
    #
    # Method 1: using fixed buffer of constant size (must be greater than expected string length)
    cdef char[50] buf_string
    strcpy(buf_string, cost_string)
    printf("buf_string: %s, len(%lu)\n", buf_string, len(buf_string))

    # Set initial values to letter 'c'
    for i in range(50):
        buf_string[i] = b'c'
    # It's a mandatory to all string in C to be null-terminated!
    buf_string[49] = b'\0'

    # Length must be 49, because 50th char is '\0' special non-printable char
    printf("buf_string: %s, len(%lu)\n", buf_string, len(buf_string))

    # Let's copy const into a buffer again, and try to edit the buffer
    strcpy(buf_string, cost_string)
    buf_string[0] = b'W'
    buf_string[1] = b'e'
    buf_string[2] = b'\''
    buf_string[3] = b'r'
    buf_string[4] = b'e'
    buf_string[5] = b' '
    printf("Edited buf_string: %s, len(%lu)\n", buf_string, len(buf_string))

    printf("Buffer alignment:\n")
    #
    #  At index=21 there is \0, which makes strlen() think that the string is 21 chars len
    #
    for i in range(50):
        printf("  %2d", i)
    printf("\n")
    for i in range(50):
        if buf_string[i] == b'\0':
            printf("  \\%d", 0)
        else:
            printf("  %2c", buf_string[i])
    printf("\n")

    #
    # Method 2: dynamic allocation
    #
    # Method 1: using fixed buffer of constant size (must be greater than expected string length)
    cdef char *buf_string2 = <char*>malloc( sizeof(char) * (len(cost_string) + 1)) # Add +1 because of \0
    strcpy(buf_string2, cost_string)

    # Also editable
    buf_string2[0] = b'W'
    buf_string2[1] = b'e'

    printf("buf_string2: %s, len(%lu)\n", buf_string2, len(buf_string2))

    # Must release the memory!
    free(buf_string2)







