import unittest
from cython_tools.building import annotate

class AnnotateTestCase(unittest.TestCase):
    def test_annotate(self):
        project_root = './init_project'
        annotate('.', project_root=project_root)


if __name__ == '__main__':
    unittest.main()
