# Cython Dev Tools: toolkit for efficient Cython development

## Key features
- Keeping all development tools in one place with minimal efforts
- Built-in Cython debugger (including low-level cdef / C code, based on GDB)
- Cython code unit testing with coverage reports
- Cython code unit test with cdef class mocks / side-effects
- Line-profiler
- Easy running .pyx files by entry-point functions
- Cython annotations and index file for all project
- Cython project boilerplate
- Cython snippets for low-level C-code and debugging tricks
- Makefile for running command shortcuts, also don't let you forget to build changed files (for example `make test`, `make test-debug p=path/to_test.py`)

## Requirements
- Python 3.6+ (including debug version for CyGDB)
- GDB 7+ (tested with ver 10 and 13)
- Cython 0.29

## Getting started
```bash
pip install cython-dev-tools

# Create a new directory for a project
mkdir init_project
cd init_project

# Initialize cython tools project files
cytool initialize . --include-samples --include-boilerplate --boilerplate-name=cytoolz 

# The initialize commands will setup a simple package with core code and tests at ./cytools dir
# also at `cy_tools_sample` directory you can find samples
```

## Initialize command
Cython tools require each project root to be initialized, the folder `.cython_dev_tools` 
will be created at the project root. There you can find all temporary files, like annotations,
coverage data, debug files, etc.

The main purpose of initialization also is keeping the all project paths relative to 
its project root, because most of Cython utils are sensitive to relative paths, and
require appropriate project structure.

To get more help run:
```bash
cytool initialize --help
```

## Building cython code
Cython tools does the building automatically even if the module code doesn't use any
automatic `pyximport`, the compiled `.c` source and modules `.so|.dll` will be placed
near each `.pyx` file in the project.

Building debug version of project is a mandatory for cython tools functions:
```
cytool build --debug
```

**IMPORTANT:** If you have the `setup.py` that somehow compiles Cython code the `cytool`
will gracefully use it, but you will have to add new code/modules for compilation manually.

## Debugging
Cython debugging is a hard fork of CyGDB, however I refactored its core to make it simply 
work. 

The **critical** requirement for functioning of the debugger is having a `python-dbg` as 
the interpreter, that runs/compiles cython. There is no Anaconda python version with 
debug symbols, so I ended with Linux built-in Python 3.9d `sudo apt-get install python-dbg`
and PipEnv. 

To figure out whether your modules compiled with debug info check the `d` in the file name, 
like this: cy_memory_unsafe.cpython-39**d**-x86_64-linux-gnu.so, python interpreter should
be like `python3.6-dbg` or `python3.6d`.


### Launching debug session
```
# cytool build --debug  (required)
#
# Both .py / .pyx entry points are suported 
#

# Can be called by file path relative to project root 
cytool debug cy_tools_samples/debugging/abort.pyx@main

# Also by package name with breakpoint at line 24 (only Cython!)
cytool debug cy_tools_samples.debugging.assertions@main:24

# Can contain default breakpoint at line 24 (only Cython!)
cytool debug cy_tools_samples/debugging/assertions.pyx@main:24

# Can break at segmentation fault too (at line 13 at the entry module)
cytool debug cy_tools_samples/debugging/segfault.pyx@main -b 13

# Can break at class method
cytool debug cy_tools_samples/cy_memory_unsafe.pyx@main:TestClass.hello_add

# Many breakpoints allowed
cytool debug cy_tools_samples/debugging/segfault.pyx@main -b 13 -b 21
```

### More help
```
cytool debug --help
```
[CyGDB commands](https://cython.readthedocs.io/en/latest/src/userguide/debugging.html#using-the-debugger)

Check the `cy_tools_samples/debugging/` for more tricks on how to set breakpoints,
c-style (not python!) asserts and debug them.

### Troubleshooting the debugger
This functionality is still under development, so expect bugs everywhere. However, there are some
common issues with the Cython debugger: 

1. Make sure that you are using **debug** version of python
2. Make sure that the current build is debug, try to force rebuild
```
cytool build --debug --force
```
3. Ramp up verbosity
```
cytool -vvvv debug cy_tools_samples/debugging/abort.pyx@main --cygdb-verbosity=3
```
4. Don't hesitate to fill an issue on GitHub!

## Unit Testing
Running unit tests on Cython low-level cdef functions or even classes is also possible task, but requires some 
code preparation.
To run unit tests on low-level code you must do the following steps:
1. Implement unit test class in `test_cython_.pyx` file:
```python
import unittest
# cdef-classes require cimport and .pxd file!
from bp_cython.bp_cython_class cimport SomeCythonClass

class CythonTestCase(unittest.TestCase):
    # IMPORTANT: in some reason, NoseTest doesn't recognize this module as a test
    def test_cytoolzz_class_init(self):
        cdef double * ptr = NULL # You can also use all low-level C-like stuff
        c = SomeCythonClass(4, 3)
        # c.square() is cdef method and not accessible via Python
        self.assertEqual(12, c.square())  
```
2. Implement python file which includes `test_cython_.pyx` (don't use `pyximport`!) But it's literally 1 line!
```python
from my_proj.tests.test_cython_ import *
```
3. Re-build project in debug mode and run test suite. Only `pytest` works for me, BUT you still have to write `unittest.TestCase` classes, 
`pytest` fancy fixtures are not supported for Cython tests.
```
> cytool build --debug 
> cytool tests .

# Or alternatively via make (no extra build step required)
> make tests
```
[See Cython code with tests examples](https://github.com/alexveden/cython-dev-tools/tree/main/src/cython_dev_tools/_boilerplate_package/bp_cython)

## Unit Test Mocks for Cython cdef classes 
Sometimes it's crucial to have fast cdef code, but occasionally it could have undetermined functions like random or datetime.now(), so I found an approach
for implementing unit test mocks for Cython class methods. Unfortunately it's not so elegant as Python one, and require implementing special class. But in 
some cases it's better than nothing.

[Cython UnitTest Mocks example](https://github.com/alexveden/cython-dev-tools/tree/main/src/cython_dev_tools/_boilerplate_package/bp_cython/tests/test_bp_cython_class_mock_.pyx)

## Code coverage
Install the boilerplate project `cytool initialize --include-boilerplate`, this package
contains unit-tests, so you can play with it.

This command will run all tests in project root and open coverage report in the browser.
```
# More help
# cytool cover --help
# cytool build --debug  (required)
cytool cover . --browser
```

## Annotate
For developing high performance Cython code it's crucial to run annotations to see
potential bottlenecks. Cython tools provides this functionality, you can build one file or
all files in the folder/project.

This command will run all tests in project root and open coverage report in the browser.
```
# More help
# cytool annotate  --help
cytool annotate . --browser
cytool annotate cy_tools_samples/debugging/segfault.pyx --browser
```

## Running
A simple command for running the Cython code by entry point
```
# More help
# cytool run --help
 
cytool run cy_tools_samples/debugging/segfault.pyx@main
cytool run cy_tools_samples.debugging.segfault@main
cytool run python/works/too.py
```

## Line Profiler
Line profiler uses https://github.com/pyutils/line_profiler project, and uses the similar
logic as `%lprun` Jupyter magic
```
# More help
# cytool lprun --help
# cytool build --debug  (required)
 
# Profile approx_pi2"(10)" -- equals to launching this function as approx_pi2(n=10) 
cytool lprun cy_tools_samples/profiler/cy_module.pyx@approx_pi2"(10)"

# Profile extra functions in the entry-point module 
cytool lprun cy_tools_samples/profiler/cy_module.pyx@approx_pi2"(10)" -f recip_square2

# Profile class mehtod in entry-module
cytool lprun cy_tools_samples/profiler/py_module.py@approx_pi2"(10)" -f SQ.recip_square2

# Profile function in another module
cytool lprun cy_tools_samples/profiler/py_module.py@approx_pi2"(10)" -f cy_tools_samples/profiler/cy_module.pyx@recip_square2

# Profile entire module
cytool lprun cy_tools_samples/profiler/cy_module.pyx@approx_pi2"(10)" -m cy_tools_samples/profiler/cy_module.pyx

```

## Cleanup
Cleanup all compilation junk 
```
# For more help
# cytool clean --help
cytool clean
```

## Templates
Creates Cython cdef module or class using boilerplate templates relative to project root.
Optionally it can include tests in new package directory.

```
# For more help
# cytool template --help
cytool template subpkg.my_template
```

