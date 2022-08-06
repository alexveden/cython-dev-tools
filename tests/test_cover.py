import unittest
from cython_tools.coverage import cover


class CoverTestCase(unittest.TestCase):
    def test_something(self):
        cover(tests_target='.',
              project_root='./init_project')


if __name__ == '__main__':
    unittest.main()
