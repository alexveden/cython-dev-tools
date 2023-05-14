"""
Initializes Cython project root
"""
import os
import shutil
from cython_dev_tools.logs import log
from cython_dev_tools.settings import CYTHON_TOOLS_DIRNAME
from cython_dev_tools.common import parse_input
import glob
import re

RE_VALID_NAME = re.compile(r'^[a-z_\d]+$', re.MULTILINE)
RE_VALID_PY_EX = re.compile(r'.*\.p[y|yx|xd]+$', re.MULTILINE)
RE_FILE_BP_MODULE = re.compile(r'.*_module[_]*\.p[y|yx|xd]+$', re.MULTILINE)
RE_FILE_BP_CLASS = re.compile(r'.*_class[_]*\.p[y|yx|xd]+$', re.MULTILINE)
RE_FILE_BP_TEST = re.compile(r'.*[\\\/]tests[\/\\].*\.p[y|yx|xd]+$', re.MULTILINE)



def initialize_command(args):
    """
    Main entry point for shell command
    """
    log.setup('cython_dev_tools__initialize', verbosity=args.verbose)
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
               log_name='cython_dev_tools__initialize',
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

    cy_tools_dir_path = os.path.join(project_root, CYTHON_TOOLS_DIRNAME)

    if os.path.exists(cy_tools_dir_path):
        if not force:
            raise FileExistsError(f'CYTHON_TOOLS_DIR={CYTHON_TOOLS_DIRNAME} already exists in project root')
        else:
            shutil.rmtree(cy_tools_dir_path)

    boiler_plate_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '_boilerplate_package'))

    if not os.path.exists(os.path.join(project_root, 'Makefile')):
        shutil.copy(os.path.join(boiler_plate_dir, 'Makefile'),
                    os.path.join(project_root, 'Makefile'))

    os.makedirs(cy_tools_dir_path)
    if include_samples:
        make_samples(project_root)

    if include_boilerplate:
        if boilerplate_name is not None:
            # Possibly called via script
            make_boilerplate(project_root, boilerplate_name, include_class=True, include_module=True, include_tests=True)
        else:
            # Make more interactive
            make_boilerplate(project_root)


def make_samples(project_root):
    samples_project_source = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '_cy_tools_samples')

    assert os.path.exists(samples_project_source), f'samples_project_source path does not exist: {samples_project_source}'
    assert os.path.exists(project_root), f'project root does not exist: {project_root}'

    samples_project_dest = os.path.join(project_root, 'cy_tools_samples')

    if os.path.exists(samples_project_dest):
        raise FileExistsError(f'samples_project_dest already exists: {samples_project_dest}')

    log.info(f'Creating sample project at: {samples_project_dest}')
    shutil.copytree(samples_project_source, samples_project_dest)




def make_boilerplate(project_root, boiler_plate_name, include_class=None, include_module=None, include_tests=None):
    boiler_plate_root = 'bp_cython'
    boiler_plate_package_source = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '_boilerplate_package', boiler_plate_root))

    assert os.path.exists(boiler_plate_package_source), f'boiler_plate_package_source path does not exist: {boiler_plate_package_source}'
    assert os.path.exists(project_root), f'project root does not exist: {project_root}'

    boiler_plate_name = parse_input(str, boiler_plate_name, 'Package name: ', regex=RE_VALID_NAME)

    boiler_plate_project_dest = os.path.abspath(os.path.join(project_root, boiler_plate_name))
    log.trace(f'boiler_plate_package_source: {boiler_plate_package_source}')
    log.info(f'Saving boiler plate package as: {boiler_plate_project_dest}')

    if os.path.exists(boiler_plate_project_dest):
        raise FileExistsError(f'{boiler_plate_project_dest} already exists, try another name')

    include_class = parse_input(bool, include_class, 'Include class? ')
    include_module = parse_input(bool, include_module, 'Include module? ')
    include_tests = parse_input(bool, include_tests, 'Include tests? ')

    log.trace(f'include_class={include_class} include_module={include_module} include_tests={include_tests}')
    if not include_tests and not include_module:
        raise ValueError(f'You must include at least one type of boiler plate code, class or module')

    for fn in glob.glob(boiler_plate_package_source + '/**', recursive=True):
        fn_source = fn
        fn_dest = fn.replace(boiler_plate_package_source, '')
        fn_dest = fn_dest.replace(boiler_plate_root, boiler_plate_name)
        if os.path.isdir(fn):
            # Skip directories
            continue
        if not RE_VALID_PY_EX.match(fn_source):
            log.trace(f'Skipping (not valid python/cython file): {fn_source}')
            continue
        if (RE_FILE_BP_TEST.match(fn_dest)) and not include_tests:
            log.trace(f'Test excluded: {fn_dest}')
            continue
        if RE_FILE_BP_CLASS.match(fn_dest) and not include_class:
            log.trace(f'Class excluded: {fn_dest}')
            continue
        if RE_FILE_BP_MODULE.match(fn_dest) and not include_module:
            log.trace(f'Module excluded: {fn_dest}')
            continue

        fn_dest = boiler_plate_project_dest + fn_dest
        dest_dir = os.path.abspath(os.path.dirname(fn_dest))
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)

        log.trace(f'Copying boilerplate project: \n Source: {fn_source}\n Destination: {fn_dest}')

        if RE_VALID_PY_EX.match(fn_source):
            # Copy only python / cython files
            with open(fn_source, 'r') as fh:
                source_test = fh.read()
                dest_source = source_test.replace(boiler_plate_root, boiler_plate_name)

                with open(fn_dest, 'w') as fh_dest:
                    fh_dest.write(dest_source)





