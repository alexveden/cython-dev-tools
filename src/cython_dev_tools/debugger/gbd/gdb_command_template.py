from string import Template

# Template vars
# project_root - typically project root path
# cy_debug_interpreter - the python interpreter which was used for producing debug cython build
#                        (typically content of .cython_dev_tools/cython_debug/interpreter)
# cy_debug_imports - cython debug information (all files form .cython_dev_tools/cython_debug/cython_debug_info**)
# cy_extra_gdbinit - add extra gdb init files if available

GDB_TEMPLATE = Template("""
# This is a gdb command file
# See https://sourceware.org/gdb/onlinedocs/gdb/Command-Files.html
#
# GDB Setup
#
set breakpoint pending on
set print pretty on
set pagination off

#
# Loading debug simbols for
#     $project_root

# Python interpreter which was used for cython code compilation
$cy_debug_interpreter

#
# The following python code is only viable inside GDB python interpreter (it's a built-in python wired deep in the GDB)
#
python
print('CythonTools: initializing plugin')

import sys
import os
sys.path.insert(0, '/home/ubertrader/cloud/code/cython_dev_tools/src')

print('''CythonTools: adding to PYTHONPATH: ${project_root}''')
sys.path.insert(0, '${project_root}')

try:
    print('CythonTools: loading debugger plugin')
    # Activate virtualenv, if we were launched from one
    import os
    virtualenv = os.getenv('VIRTUAL_ENV')
    if virtualenv:
        path_to_activate_this_py = os.path.join(virtualenv, 'bin', 'activate_this.py')
        print("CythonTools: Activating virtualenv: %s" % (virtualenv))
        with open(path_to_activate_this_py) as f:
            exec(f.read(), dict(__file__=path_to_activate_this_py))
    
    print("CythonTools: GDB Python interpreter" + str(sys.executable))
    
    os.environ['CYGDB_DEBUG_TRACE'] = "${cygdb_verbosity}"
    
    
    import Cython
    print(f"CythonTools: Cython version: {Cython.__version__}")
    
    from cython_dev_tools.debugger.gbd import libcython, libpython
    
    if libpython.DEBUG_TRACE == 0:
        print('CythonTools: Debug tracing disabled')
    else:
        print('CythonTools: Debug tracing enabled level=' + str(libpython.DEBUG_TRACE))
    
    # You actually can run PDB inside GDB to debug internal python code    
    # breakpoint()
            
except Exception as ex:
    from traceback import print_exc
    print('''CythonTools: exception when loading the debugger plugin''')    
    print("It used the Python interpreter " + str(sys.executable))
    print("sys.path: " + str(sys.path))
    print_exc()
    exit(1)
    
try: 
    # Check if python interpreter include any debug symbols
    gdb.lookup_type('PyModuleObject')
    print("CythonTools: Attached to python interpreter: ${cy_debug_interpreter}")
except RuntimeError:
    sys.stderr.write(
        "Python `${cy_debug_interpreter}` was not compiled with debug symbols (or it was "
        "stripped). Some functionality may not work (properly).\\n")
end
   
# Compiled debug metadata files
$cy_debug_imports

# Extra .cygdbinit files (by project root or .cython_dev_tools)
$cy_extra_gdbinit

# Optionally set initial breakpoints here
$cy_breakpoint

# Run initial program
cy run ${run_instruct}
""")