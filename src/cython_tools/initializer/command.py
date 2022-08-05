"""
Initializes Cython project root
"""
import os
import shutil
from cython_tools.logs import log
from cython_tools.settings import CYTHON_TOOLS_DIRNAME
from .boilerplate import make_boilerplate
from .samples import make_samples


def command(args):
    """
    Main entry point for shell command
    """
    initialize(
            project_root=args.project_root,
            force=args.force,
            include_samples=args.include_samples,
            include_boilerplate=args.include_boilerplate,
            boilerplate_name=args.boilerplate_name,
            log_name=args.log_name,
    )


def initialize(project_root: str,
               force=False,
               verbosity=0,
               include_samples=False,
               include_boilerplate=False,
               boilerplate_name=None,
               log_name='cython_tools__initialize',
               ):
    """
    `initialize` shell command initialization, also may be called via pure python

    :param project_root:
    :param force:
    :param verbosity:
    :param include_samples:
    :param include_boilerplate:
    :param boilerplate_name:
    :param log_name:
    :return:
    """
    log.setup(log_name, verbosity=verbosity)

    if not os.path.exists(project_root):
        os.makedirs(project_root)
    elif not force:
        raise ValueError(f'Project root already exists: {project_root}, try with `force` flag')
    if os.path.exists(os.path.join(project_root, 'setup.py')):
        if not force:
            raise FileExistsError(f'setup.py already exists in project root, try with `force` flag to rewrite')
    if os.path.exists(os.path.join(project_root, 'Makefile')):
        if not force:
            raise FileExistsError(f'Makefile already exists in project root, try with `force` flag to rewrite')

    cy_tools_dir_path = os.path.join(project_root, CYTHON_TOOLS_DIRNAME)

    if os.path.exists(cy_tools_dir_path):
        if not force:
            raise FileExistsError(f'CYTHON_TOOLS_DIR={CYTHON_TOOLS_DIRNAME} already exists in project root')
        else:
            shutil.rmtree(cy_tools_dir_path)

    boiler_plate_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '_boilerplate_package'))

    shutil.copy(os.path.join(boiler_plate_dir, 'setup.py'),
                os.path.join(project_root, 'setup.py'))
    shutil.copy(os.path.join(boiler_plate_dir, 'Makefile'),
                os.path.join(project_root, 'Makefile'))

    os.makedirs(cy_tools_dir_path)
    if include_samples:
        make_samples(project_root)

    if include_boilerplate:
        make_boilerplate(project_root, boilerplate_name)




