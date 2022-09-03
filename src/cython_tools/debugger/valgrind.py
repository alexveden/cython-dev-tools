import os
import subprocess
import sys
from cython_tools.logs import log
from cython_tools.common import check_project_initialized, check_method_exists, find_package_path, make_run_args
import re
import signal
import xml.etree.ElementTree as ET
import os
import glob


def valgrind_command(args):
    log.setup('cython_tools__valgrind', verbosity=args.verbose)

    valgrind(run_target=args.run_target,
             project_root=args.project_root,
             pytest=args.pytest,
        )


def valgrind(run_target,
             project_root=None,
             pytest = False):
    log.debug(f'Running: {run_target}')

    # Check if cython tools in a good state in the project root
    project_root, cython_tools_path = check_project_initialized(project_root)

    # Building python args
    run_path = os.path.join(project_root, run_target)

    if not os.path.isdir(run_target):
        # Getting run target
        source_file, package, entry_method = find_package_path(project_root, run_target, as_entry=False)
        if pytest and entry_method is not None:
            raise RuntimeError(f'Only python entry methods allowed, with -t / --pytest flags')
        run_instruct = make_run_args(source_file, package, entry_method, pytest=pytest)
    else:
        run_instruct = ['-m', 'pytest', f'{run_path}']

    if pytest:
        # Get rid of annoying ".pytest_cache" folder in the root dir!
        run_instruct.insert(-1, f'--override-ini=cache_dir={os.path.join(cython_tools_path, ".pytest_cache")}')

    log.trace(f'Python args: {run_instruct}')

    my_env = os.environ.copy()
    if "PYTHONPATH" in my_env:
        my_env["PYTHONPATH"] = f"{project_root}:" + my_env["PYTHONPATH"]
    else:
        my_env["PYTHONPATH"] = f"{project_root}"

    # Suppressing valgrind errors
    my_env['PYTHONMALLOC'] = 'malloc'

    valgrind_log_fn = os.path.join(cython_tools_path, 'valgrind.log')
    if os.path.exists(valgrind_log_fn):
        os.unlink(valgrind_log_fn)
    p = subprocess.Popen(['valgrind',
                          f'--log-file={valgrind_log_fn}',
                          '--leak-check=full',
                          'python'
                          ] + run_instruct, env=my_env)

    log.trace("Python spawned (pid %d)", p.pid)
    ret = -1
    while True:
        try:
            ret = p.wait()
            if ret == 0:
                log.trace(f'python correctly finished')
            elif ret == -11:
                # Segmentation fault
                log.critical(f'Python SEGMENTATION FAULT during running: {run_target} ErrCode: {ret}, try to run with `debug` command')
            elif  ret == -5:
                log.critical(f'Python POSSIBLE unhandled breakpoint during running: {run_target} ErrCode: {ret}, try to run with `debug` command')
            else:
                log.error(f'Python returned error while running: {run_target} ErrCode: {ret}')
        except KeyboardInterrupt:
            pass
        except:
            log.exception(f'Exception during running python: {run_instruct}')
        else:
            break

    if os.path.exists(valgrind_log_fn):
        # All good let's check
        if not os.path.exists(valgrind_log_fn):
            raise RuntimeError(f'No valgrind log found at {os.path.join(cython_tools_path, "valgrind.log")}')

        result = parse_valgrind_logs(cython_tools_path, valgrind_log_fn)
        for l in result:
            print(l, end='')
    else:
        log.error("Failed to run valgrind!")

def parse_valgrind_logs(cython_tools_path, valgrind_log_fn):
    """
    Parses valgrind logs and maps Cython .c calls to .pyx functions (also filters all python junk)
    """
    func_mapper = make_func_mapper(cython_tools_path)

    with open(valgrind_log_fn, 'r') as fh:
        lines = fh.readlines()

    RE_CYTHON_LINE = re.compile(r"(?P<base>==\d+==.*0x[A-Z0-9]+:*.)(?P<fn_name>__pyx_.*) \((?P<c_file>.*\.c):(?P<c_line>\d+)\)")
    RE_NEW_REC = re.compile(r"==\d+== \n")
    RE_REPORT_START = re.compile(r"==\d+== Parent PID:.*\n")
    RE_LEAK_SUMMARY = re.compile(r"==\d+== LEAK SUMMARY:\n")

    result_lines = []
    last_rec = -1
    report_started = False
    has_cython_calls = False

    def replace_cython_calls(lines, l_start, l_end):
        for i in range(l_start, l_end):
            g = RE_CYTHON_LINE.match(lines[i])
            if g:
                c_file = g['c_file']
                fn_name = g['fn_name']
                c_line_no = int(g['c_line'])
                if c_file in func_mapper and fn_name in func_mapper[c_file]:
                    module_map = func_mapper[c_file][fn_name]
                    _qual_name, _pyx_fn_line_no = module_map['functions'][fn_name]

                    pyx_base_name = os.path.basename(module_map['module_pyx_fn'])
                    pyx_line_number = module_map['line_numbers'].get(c_line_no, _pyx_fn_line_no)

                    result_lines.append(re.sub(RE_CYTHON_LINE, rf"\g<base>{_qual_name} ({pyx_base_name}:{pyx_line_number})", lines[i]))

            else:
                # Not a cython line return as is
                result_lines.append(lines[i])

    for i, l in enumerate(lines):
        if last_rec == -1:
            result_lines.append(l)

        if not report_started:
            if RE_REPORT_START.match(l):
                report_started = True

        if last_rec == -1 and report_started and RE_NEW_REC.match(l):
            # First valgrind record found
            last_rec = i
            continue

        if last_rec != -1:
            # Parsing records
            g = RE_CYTHON_LINE.match(l)
            if g:
                if g['c_file'] in func_mapper and g['fn_name'] in func_mapper[g['c_file']]:
                    has_cython_calls = True

            elif RE_NEW_REC.match(l):
                if has_cython_calls:
                    replace_cython_calls(lines, last_rec, i)
                last_rec = i
                has_cython_calls = False
            elif RE_LEAK_SUMMARY.match(l):
                last_rec = -1
                result_lines.append('\n\n')
                result_lines.append(l)
    return result_lines

def make_func_mapper(cython_tools_path) -> dict:
    """
    Parses cython debug metadata to map c source lines and functions to pyx files/modules
    """
    if not os.path.exists(os.path.join(cython_tools_path, 'cython_debug')):
        raise RuntimeError(f'Cython debug info not found in {cython_tools_path}, missing build --debug?')
    func_mapper = {}

    for fn in glob.glob(os.path.join(cython_tools_path, 'cython_debug', 'cython_debug_info_*')):
        tree = ET.parse(fn)
        root = tree.getroot()

        for m in root:
            module_map = dict(
                    module_name=m.attrib['module_name'],
                    module_c_basename=os.path.basename(m.attrib['c_filename']),
                    module_pyx_fn=m.attrib['filename'],
                    module_c_fn=m.attrib['c_filename'],
                    functions={},
                    line_numbers={}
            )

            for child in m:
                if child.tag == 'Functions':
                    for f in child:
                        if f.attrib['qualified_name'] == '':
                            continue
                        if f.attrib['cname'] != '':
                            module_map['functions'][f.attrib['cname']] = (f.attrib['qualified_name'], int(f.attrib['lineno']))
                        if f.attrib['pf_cname'] != '':
                            module_map['functions'][f.attrib['pf_cname']] = (f.attrib['qualified_name'], int(f.attrib['lineno']))

                if child.tag == 'LineNumberMapping':
                    for lnum in child:
                        for c_lno in lnum.attrib['c_linenos'].split():
                            module_map['line_numbers'][int(c_lno)] = int(lnum.attrib['cython_lineno'])

            # Storing functions map
            fn_map = func_mapper.setdefault(module_map['module_c_basename'], {})
            for f in module_map['functions'].keys():
                fn_map[f] = module_map

    if len(func_mapper) == 0:
        raise RuntimeError(f'Cython debug info not found in {cython_tools_path}, missing build --debug?')

    return func_mapper