from setuptools import Extension, setup
from Cython.Build import cythonize
import numpy as np
import os
IS_DEBUG = os.getenv('CYTHON_TOOLS_BUILD_DEBUG', False)
CYTHON_TOOLS_DIRNAME = os.getenv("CYTHON_TOOLS_DIRNAME", '.cython_tools')

debug_macros = []
debug_cythonize_kw = dict(force=True)
debug_include_path = []

if IS_DEBUG:
    cython_tools_dir = gdb_out_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), CYTHON_TOOLS_DIRNAME)
    if not os.path.exists(cython_tools_dir):
        print(f'{CYTHON_TOOLS_DIRNAME} doesn\'t exist in current project root, missing configuration?!')
        gdb_out_dir = os.getcwd()
    print('Extension IS_DEBUG=True!')
    # Adding cython line trace for coverage report
    debug_macros += ("CYTHON_TRACE_NOGIL", 1), ("CYTHON_TRACE", 1)
    # Adding upper directory for supporting code coverage when running tests inside the cython package
    debug_include_path += ['..']
    # Some extra info for cython compilator
    debug_cythonize_kw.update(dict(gdb_debug=True,
                                   output_dir=gdb_out_dir,
                              force=True,
                              annotate=True,
                              compiler_directives={'linetrace': True, 'profile': True, 'binding': True}))

extensions = [
    Extension("*", ["**/*.pyx"],
              # get rid of weird Numpy API warnings
              define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")] + debug_macros,
              #include_dirs=["cy_debug/"],
              #library_dirs=[...]
              ),
]


setup(
    name="Cython Tools Template App",
    ext_modules=cythonize(extensions,
                          # include_path='..' for making Cython coverage work, when tests are inside the Cython package
                          include_path=[np.get_include()] + debug_include_path,
                          language_level="3",
                          **debug_cythonize_kw
                          )
)