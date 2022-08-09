import os
import sys
from typing import List

from cython_tools.logs import log
from cython_tools.common import check_project_initialized
from setuptools import Extension, setup
import numpy as np
from Cython.Build import cythonize
import importlib.util
import glob
from unittest import mock
import re
import json


RE_CYTHON_SRC = re.compile(r".*\/\* BEGIN: Cython Metadata((?P<cython_meta>.*))END: Cython Metadata \*\/.*", re.DOTALL)
RE_IS_CYTHON = re.compile(r".*\/\*\sGenerated\sby\sCython\s.*\*\/.*", re.DOTALL)

def build_command(args):
    """
    Main entry point for shell command
    """
    log.setup('cython_tools__build', verbosity=args.verbose)

    build(args.project_root,
          is_debug=args.debug,
          force=args.force,
          annotate=args.annotate,
          )


def build(project_root: str = None,
          is_debug=False,
          force=False,
          annotate=False,
          ):

    log.trace(f'project root: {project_root}')

    # Check if cython tools in a good state in the project root
    project_root, cython_tools_path = check_project_initialized(project_root)

    # Changing dir to project root
    prev_dir = os.path.abspath(os.getcwd())
    os.chdir(os.path.abspath(project_root))
    log.trace(os.getcwd())

    if project_root not in sys.path:
        log.trace(f'Adding {project_root} to PYTHONPATH')
        sys.path.append(project_root)

    project_extensions = None
    cythonize_kwargs = None

    if os.path.exists(os.path.join(project_root, 'setup.py')):
        project_extensions, cythonize_kwargs = load_extensions_from_setup()

    if project_extensions is None:
        # No setup.py or nothing for building it in python
        project_extensions = [
            Extension("*", ["**/*.pyx"],
                      # get rid of weird Numpy API warnings
                      define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
                      ),
        ]
        cythonize_kwargs = dict(
                include_path=[np.get_include()],
                # Skip cython language level warnings by default!
                language_level="3",
        )

    if is_debug:
        log.debug('Adding debug flags')
        debug_macros = ("CYTHON_TRACE_NOGIL", 1), ("CYTHON_TRACE", 1)
        debug_cythonize_kw = dict(gdb_debug=True,
                                  # cython_debug files output for GDB mapping
                                  output_dir=cython_tools_path,
                                  compiler_directives={'linetrace': True, 'profile': True, 'binding': True})
        log.trace(f'debug_macros: {debug_macros}')
        log.trace(f'debug_cythonize_kw: {debug_cythonize_kw}')

        for ext in project_extensions:
            log.trace(f'Patching extension macros: {ext.name}')

            if ext.define_macros is None:
                ext.define_macros = []
            log.trace(f'\tbefore: {ext.define_macros}')
            for dbg_m in debug_macros:
                has_found = False
                for i, m in enumerate(ext.define_macros):
                    assert len(m) == 2, f'Extension macros expected to be a tuple of 2 elements'
                    if m[0].upper() == dbg_m[0]:
                        # Already has a macros, rewrite value
                        has_found = True
                        ext.define_macros[i] = (m[0], dbg_m[1])
                        break
                if not has_found:
                    ext.define_macros.append(dbg_m)
            log.trace(f'\tafter: {ext.define_macros}')

        # Updating cythonize kw
        cythonize_kwargs.update(debug_cythonize_kw)

    if not force:
        for ext in project_extensions:
            force = check_force_rebuild(ext.name, ext.sources, requested_is_debug=is_debug)
            if force:
                # Something triggered force, no need to loop through everything
                log.info(f'Debug<->release version switch detected, forcing rebuild')
                break

    # Ready to compile
    log.debug('Compiling and building')
    log.trace(f'cythonize_kwargs: {cythonize_kwargs}')

    cythonize_kwargs['force'] = force
    cythonize_kwargs['annotate'] = annotate

    ext_modules = cythonize(project_extensions, **cythonize_kwargs)

    setup(name='Cython tools virtual ext',
          ext_modules=ext_modules,
          script_args=['build_ext', '--inplace'])

    os.chdir(prev_dir)
    log.info(f'Build completed')


def load_extensions_from_setup():
    """
    A hacky extension loader from the existing setup.py, when it presents in project root

    :return:
    """
    project_extensions = cythonize_kwargs = None
    log.trace('Loading setup.py')
    # Prevent setup() function running!
    with mock.patch('setuptools.setup') as mock_setup:
        with mock.patch('Cython.Build.cythonize') as mock_cythonize:
            # Gently mock setup initialization call to get cythonize call args
            import setup
            log.trace(f'setup.py: cythonize call: {mock_cythonize.call_args}')
            if mock_cythonize.call_count == 0:
                # No cythonize called / non-cython setup.py or something
                # Fall back to built-in extensions compilation
                log.debug(f'No cython building in setup.py, falling back to cython tools internal building')
            elif mock_cythonize.call_count > 1:
                raise RuntimeError(f'setup.py calls cythonize multiple times, possibly unsupported case. '
                                   f'Or try to build your extension with one cythonize call (i.e. multiple extensions -> one cythonize)')
            else:
                if len(mock_cythonize.call_args[0]) != 1:
                    raise RuntimeError(f'setup(ext_modules=cythonize(...) has more than 1 positional arguments, consider rewriting setup.py'
                                       f' to call only one argument (extension lists) and pass other optional arguments and explicit kwargs')
                project_extensions = mock_cythonize.call_args[0][0]
                cythonize_kwargs = mock_cythonize.call_args[1]

                if len(project_extensions) == 0:
                    raise RuntimeError(f'setup(ext_modules=cythonize(...) empty extensions list has passed as argument')
    log.trace('Done setup.py')
    return project_extensions, cythonize_kwargs


def check_force_rebuild(ext_name: str, ext_sources: List[str], requested_is_debug: bool) -> bool:
    """
    Checks all Cython .c sources to figure out their compilation instructions and compare with current build requirements.

    This one is a simple helper, that forces rebuild when no cython code is changed but debug->release. Without forcing Cython would not rebuild when
    we change from debug to release and vice versa. But always forcing is also burdensome, because rebuilding whole project may be time consuming.
    """
    log.debug(f'check_force_rebuild: Check if extension: {ext_name} needs rebuild')
    for src_pattern in ext_sources:
        if not src_pattern.endswith('.pyx'):
            log.trace(f'extension pattern excludes .pyx, skipping')
            continue

        for fn in glob.glob(src_pattern):
            c_src = fn[:-4] + '.c'
            if not os.path.exists(c_src):
                # .c file is not created, but this doesn't mean that we need to force
                continue

            log.trace(f'check_force_rebuild: {c_src}')

            with open(c_src, 'r') as fh:
                source = fh.read()

                reg = RE_CYTHON_SRC.match(source)
                if reg:
                    cython_meta = json.loads(reg['cython_meta'])

                    has_trace = False
                    has_trace_nogil = False
                    for m in cython_meta.setdefault('distutils', {}).setdefault('define_macros', []):
                        if len(m) == 2:
                            if m[0] == 'CYTHON_TRACE' and m[1] == 1:
                                has_trace = True
                            elif m[0] == 'CYTHON_TRACE_NOGIL' and m[1] == 1:
                                has_trace_nogil = True

                    src_is_debug = has_trace and has_trace_nogil
                    if requested_is_debug != src_is_debug:
                        if requested_is_debug:
                            log.debug(f'{c_src} is built with no debug flags, forcing rebuilt all to get debug version')
                        else:
                            log.debug(f'{c_src} is built with debug flags, forcing rebuilt all to get production version')
                        return True
                else:
                    if not RE_IS_CYTHON.match(source):
                        log.error(f'{c_src} is not generated by cython, but with the same name as .pyx')
                        return True
                    else:
                        log.error(f'{c_src} is Cython generated but does not contain valid metadata or probably new format')
                        return True

    log.trace(f'check_force_rebuild: All files match the {"debug" if requested_is_debug else "production"} compilation flags')
    return False
