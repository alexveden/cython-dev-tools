"""
A sample for including Cythonized tests file
"""
import unittest

# cdef-classes require cimport and .pxd file!
from bp_cython.bp_cython_class cimport SomeCythonClass


class CythonTestCase(unittest.TestCase):

    # IMPORTANT: in some reason Nose test doesn't recognize this module as a test
    def test_cytoolzz_class_init(self):
        c = SomeCythonClass(4, 3)
        self.assertEqual(12, c.square())

    def test_cytoolzz_class_static(self):
        self.assertEqual(3, SomeCythonClass.add(1, 2))
