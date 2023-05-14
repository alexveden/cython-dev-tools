cdef class SomeCythonClass:
    cdef int width
    cdef int length

    cdef int square(self)

    @staticmethod
    cdef int add(int a, int b)

    cdef double random_next(self)
    cdef double volume(self, double h)

