from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free

cdef struct Header:
    int magic
    int count
    char end

cdef struct Rec:
    char b
    int v
    char e

cdef class TestClass:
    cdef hello_add(self, int a, int b):
        return a + b

    def main(self):
        print('World')


cpdef main_add(int a, int b):
    return b + a

cdef sub_c(int a, int b):
    return a - b

def hello():
    i = 0

    print('Hello cydbg')

    j = 5

cpdef main():
    main_add(1, 2)
    sub_c(3, 5)
    buf_count = 50
    cy_cl = TestClass()

    cy_cl.main()
    cy_cl.hello_add(10, 20)
    # Works
    cdef void * _data = <void *> PyMem_Malloc(buf_count)
    cdef char * data = <char *> _data

    hello()

    for i in range(buf_count):
        if i < buf_count - 1:
            data[i] = b'b'
        else:
            data[i] = b'z'
    #cdef char[:] buf = data

    print(data)

    cdef Header * h = <Header *> data
    h.magic = 2222
    h.count = 999
    h.end = b'z'
    print(f'sizeof(Header): {sizeof(Header)}')
    print(f'sizeof(Rec): {sizeof(Rec)}')

    cdef Rec * r = <Rec *> (data + sizeof(Header))
    r[0].b = 11
    r[0].v = 33
    r[0].e = 12

    r[1].b = 22
    r[1].v = 44
    r[1].e = 22

    for i in range(buf_count):
        ltr = str(data[i])
        print(ltr, end=' '),
    #print(data)

    cdef Header * h2 = <Header *> data
    print('\nH2')
    print(h2.magic)
    print(h2.count)
    print(h2.end)

    cdef Rec * r_ptr = <Rec *> (data + sizeof(Header))
    print('Rec1')
    print(r_ptr[0].b)
    print(r_ptr[0].v)
    print(r_ptr[0].e)
    # make debug-file p=examples/cy_memory_unsafe_debug.py
    # cy break examples.cy_memory_unsafe:40
    print('Rec2')
    print(r_ptr[1].b)
    print(r_ptr[1].v)
    print(r_ptr[1].e)

    PyMem_Free(data)

if __name__ == '__main__':
    main()