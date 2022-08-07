import os
import unittest
from cython_tools.common import *

class CyToolsCommonTestCase(unittest.TestCase):
    def test_find_entry_point(self):
        project_root = './init_project'

        self.assertRaises(FileNotFoundError, find_package_path, project_root, 'cy_tools_samples/cy_memory_unsafe_debug_unknown.py')
        self.assertRaises(ValueError, find_package_path, project_root, '/cy_tools_samples/cy_memory_unsafe_debug_unknown.py')
        self.assertRaises(ValueError, find_package_path, project_root, '.cy_tools_samples/cy_memory_unsafe_debug_unknown.py')
        self.assertRaises(ValueError, find_package_path, project_root, 'cy_tools_samples/cy_memory_unsafe_debug_unknown.')
        self.assertRaises(ValueError, find_package_path, project_root, 'cy_tools_samples/cy_memory_unsafe_debug_unknown/')

        self.assertRaises(ValueError, find_package_path, project_root, 'cy_tools_samples.cy!_memory_unsafe_debug_unknown')

        self.assertRaises(ValueError, find_package_path, project_root, '/cy_tools_samples/cy_memory_unsafe_debug_unknown.py@ads@as22')

        ep_file, ep_pkg, ep_meth = find_package_path(project_root, 'cy_tools_samples/cy_memory_unsafe_debug.py')
        self.assertEqual(ep_file, os.path.abspath(os.path.join(project_root, 'cy_tools_samples/cy_memory_unsafe_debug.py')))
        self.assertEqual(ep_pkg, 'cy_tools_samples.cy_memory_unsafe_debug')
        self.assertEqual(ep_meth, None)

        ep_file, ep_pkg, ep_meth = find_package_path(project_root, 'cy_tools_samples.cy_memory_unsafe_debug')
        self.assertEqual(ep_file, os.path.abspath(os.path.join(project_root, 'cy_tools_samples/cy_memory_unsafe_debug.py')))
        self.assertEqual(ep_pkg, 'cy_tools_samples.cy_memory_unsafe_debug')
        self.assertEqual(ep_meth, None)

        self.assertRaises(FileNotFoundError, find_package_path, project_root, 'cy_tools_samples.cy_memory_unsafe_debug.test')
        self.assertRaises(ValueError, find_package_path, project_root, 'cy_tools_samples.cy_memory_unsafe@')

        ep_file, ep_pkg, ep_meth = find_package_path(project_root, 'cy_tools_samples/cy_memory_unsafe.pyx@main')
        self.assertEqual(ep_file, os.path.abspath(os.path.join(project_root, 'cy_tools_samples/cy_memory_unsafe.pyx')))
        self.assertEqual(ep_pkg, 'cy_tools_samples.cy_memory_unsafe')
        self.assertEqual(ep_meth, 'main')

        with self.assertRaises(ValueError):
            # Method not found
            ep_file, ep_pkg, ep_meth = find_package_path(project_root, 'cy_tools_samples/cy_memory_unsafe.pyx@main2')

        with self.assertRaises(ValueError):
            # Class not allowed
            ep_file, ep_pkg, ep_meth = find_package_path(project_root, 'cy_tools_samples/cy_memory_unsafe.pyx@main.asd')

    def test_check_method_exists(self):
        fn = os.path.join(os.path.dirname(__file__), 'test_inputs/class_search.pyx')
        assert os.path.exists(fn)

        self.assertEqual(True, check_method_exists(fn, 'main'))
        self.assertRaises(ValueError, check_method_exists, fn, 'main.main.main')
        self.assertRaises(ValueError, check_method_exists, fn, 'main.main', True)
        self.assertRaises(ValueError, check_method_exists, fn, '.main')
        self.assertRaises(ValueError, check_method_exists, fn, 'main.')

        self.assertEqual(True, check_method_exists(fn, 'cy_main_with_args'))
        self.assertEqual(True, check_method_exists(fn, 'PyClass.method_pydef'))
        self.assertEqual(True, check_method_exists(fn, 'CyClass.method_void'))
        self.assertEqual(True, check_method_exists(fn, 'CyClass.method_cpdef'))
        self.assertEqual(True, check_method_exists(fn, 'CyClass.method_def'))
        self.assertEqual(True, check_method_exists(fn, 'CyClass.method_withargs'))
        self.assertEqual(True, check_method_exists(fn, 'CyClassDerived.method_void_derived'))
        self.assertRaises(ValueError, check_method_exists, fn, 'CyClassDerived.method_def')
        self.assertRaises(ValueError, check_method_exists, fn, 'CyClass.method_pydef')
        self.assertRaises(ValueError, check_method_exists, fn, 'PyClass.method_def')

        self.assertEqual(True, check_method_exists(fn, 'valid_entry1', as_entry=True))
        self.assertEqual(True, check_method_exists(fn, 'valid_entry2', as_entry=True))
        self.assertEqual(True, check_method_exists(fn, 'valid_entry3', as_entry=True))
        self.assertRaises(ValueError, check_method_exists, fn, 'invalid_entry1', as_entry=True)
        self.assertRaises(ValueError, check_method_exists, fn, 'invalid_entry2', as_entry=True)
        self.assertRaises(ValueError, check_method_exists, fn, 'invalid_entry3', as_entry=True)
        self.assertRaises(ValueError, check_method_exists, fn, 'invalid_entry4', as_entry=True)







if __name__ == '__main__':
    unittest.main()
