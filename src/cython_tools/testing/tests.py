import os
import subprocess
import sys
from cython_tools.logs import log
from cython_tools.common import check_project_initialized, check_method_exists, find_package_path, make_run_args
import re
import signal


def tests_command(args):
    log.setup('cython_tools__tests', verbosity=args.verbose)

    tests(tests_target=args.tests_target,
          project_root=args.project_root,
          )


def tests(tests_target,
          project_root=None):
    log.debug(f'Running: {tests_target}')
    # Check if cython tools in a good state in the project root
    project_root, cython_tools_path = check_project_initialized(project_root)

    # Building python args
    tests_path = os.path.join(project_root, tests_target)

    if not os.path.exists(tests_path):
        raise FileNotFoundError(f'tests_target = {tests_path} not exists')

    if not os.path.isdir(tests_path):
        # Getting run target
        source_file, package, entry_method = find_package_path(project_root, tests_target, as_entry=False)
        if entry_method is not None:
            raise RuntimeError(f'Only python entry methods allowed')

        run_instruct = make_run_args(source_file, package, entry_method, pytest=True)
    else:
        run_instruct = ['-m', 'pytest', f'{tests_path}']

    # Get rid of annoying ".pytest_cache" folder in the root dir!
    run_instruct.insert(-1, f'--override-ini=cache_dir={os.path.join(cython_tools_path, ".pytest_cache")}')

    log.trace(f'Python args: {run_instruct}')

    my_env = os.environ.copy()
    if "PYTHONPATH" in my_env:
        my_env["PYTHONPATH"] = f"{project_root}:" + my_env["PYTHONPATH"]
    else:
        my_env["PYTHONPATH"] = f"{project_root}"

    p = subprocess.Popen(['python'] + run_instruct, env=my_env)
    log.trace("Python spawned (pid %d)", p.pid)

    while True:
        try:
            ret = p.wait()
            if ret == 0:
                log.trace(f'python correctly finished')
            elif ret == -11:
                # Segmentation fault
                log.critical(f'Python SEGMENTATION FAULT during running: {tests_target} ErrCode: {ret}, try to run with `debug` command')
            elif  ret == -5:
                log.critical(f'Python POSSIBLE unhandled breakpoint during running: {tests_target} ErrCode: {ret}, try to run with `debug` command')
            else:
                log.error(f'Python returned error while running: {tests_target} ErrCode: {ret}')
        except KeyboardInterrupt:
            pass
        except:
            log.exception(f'Exception during running python: {run_instruct}')
        else:
            break

