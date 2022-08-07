cdef class CyClass:
    cdef void* method_void(self):
        pass
        # some comment

        return 1

    cpdef int method_cpdef(self):
        pass

    def method_def(self):
        pass

    def method_withargs(self, a, b):
        pass

cdef class CyClassDerived(CyClass):
    cdef void * method_void_derived(self):
        pass

class PyClass:
    def method_pydef(self):
        pass


def main():
    pass
    # some comment

    return 1

cpdef int valid_entry1():
    pass

def valid_entry2():
    pass

cdef void* invalid_entry1():
    pass

cdef invalid_entry2(a, b):
    pass

cpdef invalid_entry3(
        a,
        b,
    ):
    pass

def invalid_entry3(
        a,
        b,
    ):
    pass

def valid_entry3():
    cdef invalid_entry4():
        pass

cdef void* cy_main_with_args(a, b):
    pass
