import unittest
from cython_tools.testing import coverage


class CoverTestCase(unittest.TestCase):
    def test_something(self):
        coverage(tests_target='.',
                 project_root='./init_project')


if __name__ == '__main__':
    unittest.main()
