import os
import subprocess
import sys
from cython_dev_tools.logs import log
from cython_dev_tools.common import check_project_initialized, check_method_exists, find_package_path, make_run_args
import re
import signal


def run_command(args):
    log.setup('cython_dev_tools__run', verbosity=args.verbose)

    run(run_target=args.run_target,
        project_root=args.project_root,
        )


def run(run_target,
        project_root=None):
    log.debug(f'Running: {run_target}')
    # Check if cython tools in a good state in the project root
    project_root, cython_dev_tools_path = check_project_initialized(project_root)

    # Getting run target
    source_file, package, entry_method = find_package_path(project_root, run_target, as_entry=True)

    # Building python args
    run_instruct = make_run_args(source_file, package, entry_method)

    log.trace(f'Python args: {run_instruct}')



    my_env = os.environ.copy()
    if "PYTHONPATH" in my_env:
        my_env["PYTHONPATH"] = f"{project_root}:" + my_env["PYTHONPATH"]
    else:
        my_env["PYTHONPATH"] = f"{project_root}"

    p = subprocess.Popen(['python'] + run_instruct, env=my_env)
    #p = subprocess.Popen(['python'] + ['-c', 'import sys; print(sys.path)'], env=my_env)
    log.trace("Python spawned (pid %d)", p.pid)

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

    #os.spawnlp(os.P_NOWAIT, 'python', 'python', *run_instruct)
    #os.spawnlp(os.P_NOWAIT, 'python', 'python')

