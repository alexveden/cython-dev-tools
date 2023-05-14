"""
Command for creating Cython class/modules/tests templates
"""

import glob
import os.path
import shutil
import sys
from cython_dev_tools.logs import log
from cython_dev_tools.common import check_project_initialized, parse_input
from cython_dev_tools.settings import CYTHON_TOOLS_DIRNAME
from cython_dev_tools.building.build import RE_IS_CYTHON
from cython_dev_tools.building.initialize import RE_FILE_BP_CLASS, RE_FILE_BP_MODULE, RE_FILE_BP_TEST, RE_VALID_PY_EX
import re

RE_VALID_NAME = re.compile(r'^[A-Za-z_\d\.]+$', re.MULTILINE)
RE_VALID_TEMPLATE_TYPE = re.compile(r'(^class$)|(^module$)', re.MULTILINE)

def template_command(args):
    """
    Main entry point for shell command
    """
    log.setup('cython_dev_tools__template', verbosity=args.verbose)

    template(
            project_root=args.project_root,
            module_full_package=args.module_full_package,
            include_tests=args.include_tests,
            template_type=args.template_type,

    )


def template(module_full_package: str = None,
             template_type: str = None,
             include_tests: bool = None,
             project_root: str = None,
             ):

    project_root, cython_dev_tools_path = check_project_initialized(project_root)

    boiler_plate_root = 'bp_cython'
    boiler_plate_package_source = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '_boilerplate_package', boiler_plate_root))

    assert os.path.exists(boiler_plate_package_source), f'boiler_plate_package_source path does not exist: {boiler_plate_package_source}'
    assert os.path.exists(project_root), f'project root does not exist: {project_root}'

    module_full_package = parse_input(str, module_full_package, 'Full package module from proj-root (i.e. mypkg.mysub2.mymodule): ', regex=RE_VALID_NAME)
    module_name = module_full_package.split('.')[-1]
    if module_name != module_full_package:
        module_sub_name = '.'.join(module_full_package.split('.')[:-1]) + '.'
    else:
        module_sub_name = ''
    module_full_path = '/'.join(module_full_package.split('.')[:-1])

    boiler_plate_project_dest = os.path.abspath(os.path.join(project_root, module_full_path))
    log.trace(f'boiler_plate_package_source: {boiler_plate_package_source}')
    log.info(f'Saving boiler plate package as: {boiler_plate_project_dest}/{module_name}.pyx')

    if os.path.exists(boiler_plate_project_dest) and os.path.exists(os.path.join(boiler_plate_project_dest, f'{module_name}.pyx')):
        raise FileExistsError(f'{boiler_plate_project_dest}/{module_name}.pyx already exists, try another name')

    template_type = parse_input(str, template_type, 'Template type? Valid: class, module: ', regex=RE_VALID_TEMPLATE_TYPE)
    include_tests = parse_input(bool, include_tests, 'Include tests? ')

    log.trace(f'template_type={template_type} include_tests={include_tests}')

    re_new_module_name = re.compile(rf'(.*)({boiler_plate_root}_{template_type})([_]?\.p[y|yx|xd]+$)')

    for fn in glob.glob(boiler_plate_package_source + '/**', recursive=True):
        fn_source = fn
        fn_dest = fn.replace(boiler_plate_package_source, '')
        if os.path.isdir(fn):
            # Skip directories
            continue
        if not RE_VALID_PY_EX.match(fn_source):
            log.trace(f'Skipping (not valid python/cython file): {fn_source}')
            continue
        if (RE_FILE_BP_TEST.match(fn_dest)) and not include_tests:
            log.trace(f'Test excluded: {fn_dest}')
            continue
        if not re_new_module_name.match(fn_source):
            log.trace(f'Source excluded: {fn_dest}')
            continue
        
        # Replace name
        fn_dest = re_new_module_name.sub(rf'\1{module_name}\3', fn_dest)
        if fn_dest.startswith('/'):
            fn_dest = fn_dest[1:]

        fn_dest = os.path.join(boiler_plate_project_dest, fn_dest)
        log.trace(f'{boiler_plate_project_dest=} {fn_dest=}')
        dest_dir = os.path.abspath(os.path.dirname(fn_dest))
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)

        if not os.path.exists(os.path.join(dest_dir, '__init__.py')):
            with open(os.path.join(dest_dir, '__init__.py'), 'w'):
                # Just create an empty file
                pass

        log.trace(f'Copying boilerplate project: \n Source: {fn_source}\n Destination: {fn_dest}')

        if RE_VALID_PY_EX.match(fn_source):
            # Copy only python / cython files
            with open(fn_source, 'r') as fh:
                source_test = fh.read()
                dest_source = source_test.replace(boiler_plate_root, module_name)
                dest_source = dest_source.replace(f'from {module_name}.{module_name}_{template_type}', f'from {module_full_package}')
                dest_source = dest_source.replace(f'from {module_name}.tests.test_{module_name}_{template_type}_', f'from {module_sub_name}tests.test_{module_name}_')

                with open(fn_dest, 'w') as fh_dest:
                    fh_dest.write(dest_source)



