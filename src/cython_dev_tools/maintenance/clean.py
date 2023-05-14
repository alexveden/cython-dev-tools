import glob
import os.path
import shutil
import sys
from cython_dev_tools.logs import log
from cython_dev_tools.common import check_project_initialized, parse_input
from cython_dev_tools.settings import CYTHON_TOOLS_DIRNAME
from cython_dev_tools.building.build import RE_IS_CYTHON


def clean_command(args):
    """
    Main entry point for shell command
    """
    log.setup('cython_dev_tools__clean', verbosity=args.verbose)

    clean(
            project_root=args.project_root,
            confirm=args.yes,
            delete_build=args.delete_build,
    )


def clean(project_root: str = None,
          confirm = False,
          delete_build = False):
    """
    Cleanup all **/*<module>.pyx related files with the same name (i.e. <module>.c, <module>.html, <module>.cpython*.so|dll)

    :param project_root:
    :param confirm: if True, deletes all files without confirmation
    :param delete_build: delete build directory in project root
    :return:
    """

    # Check if cython tools in a good state in the project root
    project_root, cython_dev_tools_path = check_project_initialized(project_root)
    log.info(f'Starting annotation at {project_root}')

    if sys.platform == 'win32':
        so_ext = '.dll'
    elif sys.platform == 'darwin':
        # Probably MacOS also is .so, but need test
        so_ext = '.so'
    else:
        so_ext = '.so'

    files_to_delete = []

    build_dir = os.path.join(project_root, 'build')

    if os.path.exists(os.path.join(project_root, CYTHON_TOOLS_DIRNAME, 'cython_debug')):
        shutil.rmtree(os.path.join(project_root, CYTHON_TOOLS_DIRNAME, 'cython_debug'))

    if os.path.exists(os.path.join(project_root, CYTHON_TOOLS_DIRNAME, '.coverage_cytools.db')):
        os.unlink(os.path.join(project_root, CYTHON_TOOLS_DIRNAME, '.coverage_cytools.db'))

    if os.path.exists(os.path.join(project_root, CYTHON_TOOLS_DIRNAME, 'src')):
        shutil.rmtree(os.path.join(project_root, CYTHON_TOOLS_DIRNAME, 'src'))

    for pyx in glob.glob(os.path.join(project_root, '**', '**.pyx'), recursive=True):
        base_name = pyx[:-4]

        c_file = base_name + '.c'
        html_file = base_name + '.html'

        if os.path.exists(c_file):
            with open(c_file, 'r') as fh:
                source = fh.read()
                if RE_IS_CYTHON.match(source) or '#error Do not use this file, it is the result of a failed Cython compilation.' in source:
                    files_to_delete.append(c_file)
                else:
                    log.warning(f'{c_file} is not Cython generated, skipping')
        if os.path.exists(html_file):
            files_to_delete.append(html_file)

        for so_module in glob.glob(os.path.join(base_name + f'.*{so_ext}')):
            files_to_delete.append(so_module)

    if not files_to_delete:
        log.trace('Nothing to cleanup')
        return

    if not confirm:
        print('Candidates for deletion')
        for f in files_to_delete:
            print(f'[f] {f}')

        if delete_build:
            if os.path.exists(build_dir):
                print(f'[d] {build_dir}')
        confirm = parse_input(bool, prompt='Please confirm deletion of files above')

    if confirm:
        for f in files_to_delete:
            if os.path.exists(f):
                log.trace(f'deleting: {f}')
                os.unlink(f)

        if delete_build:
            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)
            else:
                log.trace(f'Build dir not exists: {build_dir}')
        else:
            log.trace('No build deletion')
    else:
        print('Cancelled cleanup')

