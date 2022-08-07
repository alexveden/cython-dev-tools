import os
import glob
import subprocess
import sys
import tempfile
import textwrap
from .gbd.gdb_command_template import GDB_TEMPLATE
from cython_tools.logs import log
from ..common import check_project_initialized, check_method_exists, find_package_path, make_run_args
import re


def debug_command(args):
    log.setup('cython_tools__debugger', verbosity=args.verbose)

    debug(debug_target=args.debug_target,
          project_root=args.project_root,
          cygdb_verbosity=args.cygdb_verbosity,
          breakpoints_list=args.breakpoint,
          )
def debug(
        debug_target,
        project_root: str = None,
        cygdb_verbosity=0,
        breakpoints_list=None,
        ):

    # Check if cython tools in a good state in the project root
    project_root, cython_tools_path = check_project_initialized(project_root)

    tempfilename = make_command_file(debug_target, project_root, cython_tools_path, cygdb_verbosity, breakpoints_list or [])

    with open(tempfilename) as tempfile:
        p = subprocess.Popen(['gdb', '-command', tempfilename])
        log.info("GDB Spawned (pid %d)", p.pid)
        while True:
            try:
                ret = p.wait()
            except KeyboardInterrupt:
                pass
            else:
                break
    os.remove(tempfilename)


def validate_breakpoint(project_root, break_point_definition: str):
    if break_point_definition is None:
        # Simply no breakpoint
        return ''
    if break_point_definition.count(':') != 1:
        raise ValueError(f'Incorrect breakpoint, it must contain one `:`, got {break_point_definition}')

    bp_target, break_point = break_point_definition.split(':')

    if '@' in bp_target:
        raise ValueError(f'You must not use @ in breakpoints.')

    code_file, package_qualname, _ = find_package_path(project_root, bp_target, as_entry=False)

    if len(break_point) == 0:
        raise ValueError(f'Empty breakpoint given, {break_point_definition}')
    else:
        try:
            # Parses as integer, looks like line breakpoint
            break_point = int(break_point)
        except:
            # looks like a function
            assert isinstance(break_point, str), 'expected string'

    if isinstance(break_point, int):
        if code_file.endswith('.py'):
            raise ValueError(f'Python line number breakpoints are not supported, use [Class.]method breakpoints')

        with open(code_file, 'r') as fh:
            lines = fh.readlines()
            if break_point <= 0 or break_point > len(lines):
                raise ValueError(f'Breakpoint: #lineno: {break_point} is out of file line range [1; {len(lines)}]')

            for i, l in enumerate(lines):
                if i + 1 == break_point:
                    code_line = l.strip()
                    if not code_line:
                        raise ValueError(f'Breakpoint: #lineno: {break_point} is pointing at empty line in file file://{code_file}')
                    if code_line.startswith('#'):
                        raise ValueError(f'Breakpoint: #lineno: {break_point} is pointing at commented line in file file://{code_file}')

            return f"cy break {package_qualname}:{break_point}"
    elif isinstance(break_point, str):
        # Check if the breakpoint method really exists
        check_method_exists(code_file, break_point, as_entry=False)

        if code_file.endswith('.pyx'):
            return f'cy break {package_qualname}.{break_point}'
        else:
            return f'cy break -p {package_qualname}.{break_point}'

    else:
        raise NotImplementedError(f'Unsupported breakpoint type :{type(break_point)} -> {break_point}')


def make_command_file(debug_target, project_root, cython_tools_path, cygdb_verbosity, break_points_list):
    log.trace(f'Preparing GDB debug command file')

    if debug_target.count('@') > 1:
        raise ValueError(f'Only one @ entry point character is allowed, got {debug_target}')
    if debug_target.count(':') > 1:
        raise ValueError(f'Only one : break point character is allowed, got {debug_target}')

    toks = debug_target.split(':')
    bp_target = toks[0].split('@')[0]
    break_list = []
    if len(toks) == 2:
        break_list.append(bp_target + ':' + toks[1])
    for b in break_points_list:
        if ':' not in b:
            # Possibly entry file breakpoint
            break_list.append(bp_target + ':' + b)
        else:
            break_list.append(b)

    log.trace(f'Breakpoints passed: {break_list}')

    source_file, package, entry_method = find_package_path(project_root, toks[0])
    log.trace(f'Entry point: file://{source_file} package: {package} entry_method: {entry_method}')

    cy_breakpoint = '\n'.join([validate_breakpoint(project_root, bp) for bp in break_list if bp])

    run_instruct = ' '.join(make_run_args(source_file, package, entry_method, escape=True))

    pattern = os.path.join(cython_tools_path,
                           'cython_debug',
                           'cython_debug_info_*')
    debug_files = glob.glob(pattern)

    if not debug_files:
        sys.exit(f'No debug files were found in `{os.path.abspath(cython_tools_path)}/cython_debug`. Aborting.')

    fd, tempfilename = tempfile.mkstemp()
    f = os.fdopen(fd, 'w')
    try:
        path = os.path.join(cython_tools_path, "cython_debug", "interpreter")

        with open(path) as interpreter_file:
            interpreter = interpreter_file.read()

        cy_debug_interpreter = f"file {interpreter}"
        cy_debug_imports = '\n'.join(f'cy import {fn}\n' for fn in debug_files)
        cy_extra_gdbinit_list = []
        if os.path.exists(os.path.join(cython_tools_path, '.cygdbinit')):
            cy_extra_gdbinit_list.append(os.path.join(cython_tools_path, '.cygdbinit'))

        if os.path.exists(os.path.join(project_root, '.cygdbinit')):
            cy_extra_gdbinit_list.append(os.path.join(project_root, '.cygdbinit'))

        cy_extra_gdbinit = '\n'.join(f'source {fn}\n' for fn in cy_extra_gdbinit_list)

        f.write(GDB_TEMPLATE.substitute(
                project_root=project_root,
                cy_debug_interpreter=cy_debug_interpreter,
                cy_debug_imports=cy_debug_imports,
                cy_extra_gdbinit=cy_extra_gdbinit,
                cy_breakpoint=cy_breakpoint,
                run_instruct=run_instruct,
                cygdb_verbosity=cygdb_verbosity,
        ))
    finally:
        f.close()

    log.debug(f'gdb command file path: file://{tempfilename}')

    return tempfilename