"""
A sample for including Cythonized tests file
"""
import unittest
from bp_cython.bp_cython_module import bp_cython_cpdeffunc, bp_cython_deffunc

# cdef-functions require cimport and .pxd file!
from bp_cython.bp_cython_module cimport bp_cython_cdeffunc


class CythonTestCase(unittest.TestCase):

    # IMPORTANT: in some reason Nose test doesn't recognize this module as a test
    def test_bp_cython_deffunc(self):
        self.assertEqual(3, bp_cython_deffunc(1, 2), 'simple addition')

    def test_bp_cython_cpdeffunc(self):
        self.assertEqual(3, bp_cython_cpdeffunc(1, 2), 'simple addition')

    def test_bp_cython_cdeffunc(self):
        self.assertEqual(3, bp_cython_cdeffunc(1, 2), 'simple addition')
