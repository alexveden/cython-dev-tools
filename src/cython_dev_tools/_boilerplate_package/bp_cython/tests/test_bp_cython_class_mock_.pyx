
"""
A black-magic approach for Mocking Cython cdef class functions calls 
"""
import unittest

# cdef-classes require cimport and .pxd file!
from bp_cython.bp_cython_class cimport SomeCythonClass

from libc.stdlib cimport malloc, free
from libc.string cimport memset
from cython.operator cimport dereference

#
# Mocking SomeCythonClass
#   Global state (don't mix up different instances!)
cdef struct MockCyState:
    bint __mock_lock
    int _rand_next_inc_cntr
    int _rand_next_size
    double * _rand_next_ret_val
    double _volume_ret_val

cdef MockCyState _mock_cy_state 
memset(&_mock_cy_state, 0, sizeof(MockCyState))

cdef class MockSomeCythonClass:
    """
    Dangerous! Cython class mock! Used for cdef method mocking and side effects. 
    Use only per 1 CyClass instance of the same type at time, this class alters CyClass' vtable, and may lead to unpredicted consequencies!
    """
    cdef SomeCythonClass parent 
    # All original (mockable) functions here
    cdef void* _random_next_ptr
    cdef void* _volume_ptr

    def __cinit__(self, SomeCythonClass c):
        """
        IMPORTANT: add all mockable functions and save them as pointers before start!
        """

        self.parent = c
        # IMPORTANT: Mocking Cython class functions lead to changes in global vtable
        #  this will mutate all other instances of this class in place 
        #
        # All class mockable methods goes here
        self._random_next_ptr = <void*>self.parent.random_next
        self._volume_ptr = <void*>self.parent.volume
    
    def reset(self):
        """
        IMPORTANT: implement casting back all original func pointers to the vtable
        """
        self.parent.random_next = dereference(<double (*)(SomeCythonClass)>self._random_next_ptr)
        self.parent.volume = dereference(<double (*)(SomeCythonClass, double)>self._volume_ptr)
        
        self.reset_state()
    
    def __dealloc__(self):
        """
        Reset at deallocation
        """
        self.reset()
        
    def __enter__(self):        
        """
        with MockFVMCBT(mc) as mock_mc: ...
        """
        # Secure concurrent access to the state to avoid veird stuff
        assert _mock_cy_state.__mock_lock == 0, f'Lock already acquired, using concurrent Mocks?'
        _mock_cy_state.__mock_lock = 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        with MockFVMCBT(mc) as mock_mc: ...
        """
        self.reset()
        _mock_cy_state.__mock_lock = 0
   
    cdef reset_state(self):
        """
        Resets shared states, and frees memory
        """
        if _mock_cy_state._rand_next_ret_val != NULL:
            free(_mock_cy_state._rand_next_ret_val)
            _mock_cy_state._rand_next_ret_val = NULL

        _mock_cy_state._rand_next_inc_cntr = 0
        _mock_cy_state._rand_next_size = 0
        _mock_cy_state._volume_ret_val = 0

    @staticmethod
    cdef double __mock_random_next__returns(SomeCythonClass self):
        """
        implementation random_next -> return_value
        """
        assert _mock_cy_state.__mock_lock == 1, f'Lock not acquired, using outside context manager?'
        assert _mock_cy_state._rand_next_ret_val != NULL
        assert _mock_cy_state._rand_next_inc_cntr == 0
        assert _mock_cy_state._rand_next_size == 1
        return _mock_cy_state._rand_next_ret_val[0]
    
    def mock_random_next__returns(self, value: float):
        """
        Set random_next() return value (fixed number always)
        """
        assert _mock_cy_state.__mock_lock == 1, f'Lock not acquired, using outside context manager?'
        assert value >= 0 and value <= 1, f'Random value must be in [0;1], got {value}'
        self.reset_state()
        self.parent.random_next = MockSomeCythonClass.__mock_random_next__returns
        _mock_cy_state._rand_next_ret_val = <double*>malloc(sizeof(double))
        _mock_cy_state._rand_next_ret_val[0] = value
        _mock_cy_state._rand_next_size = 1
        _mock_cy_state._rand_next_inc_cntr = 0
    
    @staticmethod
    cdef double __mock_random_next__sideeffect_list(SomeCythonClass self):
        """
        implementation random_next() -> side effect by list
        """
        assert _mock_cy_state.__mock_lock == 1, f'Lock not acquired, using outside context manager?'
        assert _mock_cy_state._rand_next_inc_cntr < _mock_cy_state._rand_next_size, f'side effect calls overflow'
        assert _mock_cy_state._rand_next_size > 0, 'zero size'
        assert _mock_cy_state._rand_next_inc_cntr >= 0 and _mock_cy_state._rand_next_inc_cntr < 1000000
        
        result = _mock_cy_state._rand_next_ret_val[_mock_cy_state._rand_next_inc_cntr]
        _mock_cy_state._rand_next_inc_cntr += 1

        return result

    def mock_random_next__sideeffect_list(self, values):
        """
        Sets mock for random_next() -> using sequence of values

        Args:
            values (iterable): array of floats
        """
        assert _mock_cy_state.__mock_lock == 1, f'Lock not acquired, using outside context manager?'
        assert len(values) > 0, 'zero lengh'

        self.reset_state()
        _mock_cy_state._rand_next_ret_val = <double*>malloc(sizeof(double)  * len(values))
        for i, v in enumerate(values):
            assert isinstance(v, (float, int)), f'Values must be float, got {v}'
            assert v >= 0 and v <= 1, f'Random value must be in [0;1], got {v}'
            _mock_cy_state._rand_next_ret_val[i] = v

        _mock_cy_state._rand_next_size = len(values)
        _mock_cy_state._rand_next_inc_cntr = 0

        self.parent.random_next = MockSomeCythonClass.__mock_random_next__sideeffect_list
    
    @staticmethod
    cdef double __mock_volume__returns(SomeCythonClass self, double h):
        return _mock_cy_state._volume_ret_val

    def mock_volume_returns(self, value: float): 
        _mock_cy_state._volume_ret_val = value
        self.parent.volume = MockSomeCythonClass.__mock_volume__returns


class CythonTestCaseMock(unittest.TestCase):

    def test_cytoolzz_class_mocks_and_side_effects(self):
        #     def __init__(self, int width, int lengh):
        cdef SomeCythonClass c = SomeCythonClass(2, 3)
        self.assertEqual(6, c.square())
        
        # Volume is h*l*w
        self.assertEqual(12, c.volume(2))

        # Random value
        self.assertTrue(c.random_next() < 1)
        self.assertTrue(c.random_next() >= 0)

        # Mocking random value
        with MockSomeCythonClass(c) as mock_c:
            # Original random is never >= 1
            mock_c.mock_random_next__returns(1.0)
            mock_c.mock_volume_returns(100)

            # Mocked c.volume() too
            self.assertEqual(100, c.volume(2))
            
            for _ in range(1000):
                # Always !
                self.assertEqual(c.random_next(), 1)

            # If we reset it, it's still valid random
            mock_c.reset()

            # Random value
            self.assertTrue(c.random_next() < 1)
            self.assertTrue(c.random_next() >= 0)

            # We can mock by sequence, each element passed by subsequent call of random_next()
            mock_c.mock_random_next__sideeffect_list([0., .1, .2, .3, .4, .5])
            for i in range(6):
                self.assertEqual(i/10, c.random_next())
        
        # After leaving context manager (with ...)
        # the function reverted to usual            
        self.assertTrue(c.random_next() < 1)
        self.assertTrue(c.random_next() >= 0)
        
        # c.volume() is also restored
        self.assertEqual(12, c.volume(2))

