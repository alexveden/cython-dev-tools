import random

cdef class SomeCythonClass:
    def __init__(self, int w, int l):
        self.width = w
        self.length = l

    cdef int square(self):
        return self.width * self.length

    @staticmethod
    cdef int add(int a, int b):
        return a + b

    cdef double volume(self, double h):
        return self.square() * h

    cdef double random_next(self):
        return <double>random.random()
