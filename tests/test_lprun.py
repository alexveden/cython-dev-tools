import unittest
from cython_tools.testing import lprun


class LPRunTestCase(unittest.TestCase):
    def test_profile_cython_func_same(self):
        #
        # All in cython file
        #
        lprun('cy_tools_samples/profiler/cy_module.pyx@approx_pi2(10)',
              functions=['recip_square2'],
              project_root='./init_project')

    def test_profile_python_func_with_class(self):
        #
        # Python file with class
        #
        lprun('cy_tools_samples/profiler/py_module.py@approx_pi2(10)',
              functions=['SQ.recip_square2'],
              project_root='./init_project')

    def test_profile_cross_import(self):
        #
        # Cross import
        #
        lprun('cy_tools_samples/profiler/py_module.py@approx_pi2(10)',
              functions=['cy_tools_samples/profiler/cy_module.pyx@recip_square2'],
              project_root='./init_project')

    def test_profile_module_python(self):
        #
        # Cross import
        #
        lprun('cy_tools_samples/profiler/py_module.py@approx_pi2(10)',
              modules=['cy_tools_samples/profiler/py_module.py'],
              project_root='./init_project')

    def test_profile_module_cython(self):
        #
        # Cross import
        #
        lprun('cy_tools_samples/profiler/cy_module.pyx@approx_pi2(10)',
              modules=['cy_tools_samples/profiler/cy_module.pyx'],
              project_root='./init_project')

if __name__ == '__main__':
    unittest.main()
