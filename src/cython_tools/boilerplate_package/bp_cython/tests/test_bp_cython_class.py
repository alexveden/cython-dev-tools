"""
A sample for including Cythonized tests into test suite

Works with pytest, MAY NOT WORK WITH  nose
"""

import unittest
from bp_cython.tests.test_bp_cython_class_ import *

if __name__ == '__main__':
    unittest.main()
