import unittest
from cython_tools.debugger import debug
from cython_tools.debugger.debug import validate_breakpoint
import os

class DebugTestCase(unittest.TestCase):
    # def test_debug(self):
    #     debug(debug_target="cy_tools_samples.cy_memory_unsafe@main:66",
    #           project_root='./init_project',
    #           cygdb_verbosity=0)

    def test_validate_breakpoint(self):
        proj_root = os.path.dirname(__file__)
        fn = os.path.join(proj_root, 'test_inputs/class_search.pyx')
        assert os.path.exists(fn)

        self.assertEqual('cy break -p test_inputs.python_class.main',
                         validate_breakpoint(proj_root, 'test_inputs/python_class.py:main'))
        self.assertEqual('cy break -p test_inputs.python_class.PySomeClass.test_main',
                         validate_breakpoint(proj_root, 'test_inputs/python_class.py:PySomeClass.test_main'))

        self.assertEqual('cy break test_inputs.class_search:51',
                         validate_breakpoint(proj_root, 'test_inputs/class_search.pyx:51'))
        self.assertEqual('cy break test_inputs.class_search:51',
                         validate_breakpoint(proj_root, 'test_inputs.class_search:51'))
        self.assertEqual('cy break test_inputs.class_search:51',
                         validate_breakpoint(proj_root, 'test_inputs.class_search:51'))

        self.assertEqual('cy break test_inputs.class_search.CyClass.method_void',
                         validate_breakpoint(proj_root, 'test_inputs.class_search:CyClass.method_void'))
        self.assertEqual('cy break test_inputs.class_search.CyClass.method_void',
                         validate_breakpoint(proj_root, 'test_inputs/class_search.pyx:CyClass.method_void'))
        self.assertEqual('cy break test_inputs.class_search.CyClass.method_cpdef',
                         validate_breakpoint(proj_root, 'test_inputs.class_search:CyClass.method_cpdef'))
        self.assertEqual('cy break test_inputs.class_search.CyClass.method_cpdef',
                         validate_breakpoint(proj_root, 'test_inputs/class_search.pyx:CyClass.method_cpdef'))
        self.assertEqual('cy break test_inputs.class_search.CyClass.method_cpdef',
                         validate_breakpoint(proj_root, 'test_inputs/class_search.pyx:CyClass.method_cpdef'))

        # Invalid entries are still feasible for breakpoints
        self.assertEqual('cy break test_inputs.class_search.invalid_entry3',
                         validate_breakpoint(proj_root, 'test_inputs.class_search:invalid_entry3'))

    def test_validate_errors(self):
        proj_root = os.path.dirname(__file__)
        fn = os.path.join(proj_root, 'test_inputs/class_search.pyx')
        assert os.path.exists(fn)

        with self.assertRaises(ValueError) as exc:
            validate_breakpoint(proj_root, 'test_inputs/class_search.pyx:CyClass:method_cpdef')
        self.assertTrue('Incorrect breakpoint, it must contain one `:`' in str(exc.exception), str(exc.exception))

        with self.assertRaises(ValueError) as exc:
            validate_breakpoint(proj_root, 'test_inputs/class_search.pyx@main:CyClass')
        self.assertTrue('You must not use @ in breakpoints' in str(exc.exception), str(exc.exception))

        with self.assertRaises(ValueError) as exc:
            validate_breakpoint(proj_root, 'test_inputs/class_search.pyx:')
        self.assertTrue('Empty breakpoint given' in str(exc.exception), str(exc.exception))

        with self.assertRaises(ValueError) as exc:
            validate_breakpoint(proj_root, 'test_inputs/python_class.py:21')
        self.assertTrue('Python line number breakpoints are not supported' in str(exc.exception), str(exc.exception))

        with self.assertRaises(ValueError) as exc:
            validate_breakpoint(proj_root, 'test_inputs/class_search.pyx:0')
        self.assertTrue('Breakpoint: #lineno: 0 is out of file line range' in str(exc.exception), str(exc.exception))
        with self.assertRaises(ValueError) as exc:
            validate_breakpoint(proj_root, 'test_inputs/class_search.pyx:62')
        self.assertTrue('Breakpoint: #lineno: 62 is out of file line range' in str(exc.exception), str(exc.exception))

        with self.assertRaises(ValueError) as exc:
            validate_breakpoint(proj_root, 'test_inputs/class_search.pyx:5')
        self.assertTrue('Breakpoint: #lineno: 5 is pointing at empty line in file' in str(exc.exception), str(exc.exception))

        with self.assertRaises(ValueError) as exc:
            validate_breakpoint(proj_root, 'test_inputs/class_search.pyx:4')
        self.assertTrue('Breakpoint: #lineno: 4 is pointing at commented line' in str(exc.exception), str(exc.exception))




if __name__ == '__main__':
    unittest.main()
