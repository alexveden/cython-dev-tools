import os
import shutil
import sys
from cython_tools.common import check_project_initialized, open_url_in_browser
from cython_tools.logs import log
import cython_tools.building
import glob
from unittest import mock
import xml.etree.ElementTree as ET
from datetime import datetime


def coverage_command(args):
    """
    Main entry point for shell command
    """
    log.setup('cython_tools__coverage', verbosity=args.verbose)

    coverage_rep_url = coverage(tests_target=args.tests_target,
             project_root=args.project_root,
             coverage_engine=args.coverage_engine,
             )
    if args.browser:
        open_url_in_browser(f'file://{coverage_rep_url}')
    else:
        print(f'file://{coverage_rep_url}')


def coverage(tests_target: str = '.',
          project_root: str = None,
          coverage_engine='pytest',
          ):

    # Check if cython tools in a good state in the project root
    project_root, cython_tools_path = check_project_initialized(project_root)
    log.info(f'Starting coverage at {project_root}')

    tests_path = os.path.join(project_root, tests_target)

    if not os.path.exists(tests_path):
        raise FileNotFoundError(f'tests_target = {tests_path} not exists')
    if not os.path.isdir(tests_path):
        raise NotADirectoryError(f'tests_target = must be a directory, got {tests_path}')

    try:
        from coverage.cmdline import main as coverage_main
    except ImportError:
        raise RuntimeError(f'coverage package is not available try to `pip install coverage`')

    cy_tools_coverage_rc = os.path.join(cython_tools_path, '.coveragerc_cytools')
    cy_tools_coverage_data = os.path.join(cython_tools_path, '.coverage_cytools.db')
    cy_tools_coverage_xml = os.path.join(cython_tools_path, '.coverage_cytools.xml')
    cy_tools_coverage_html = os.path.join(cython_tools_path, 'coverage_html')
    log.trace(f'cy_tools_coverage_rc={cy_tools_coverage_rc}')
    log.trace(f'cy_tools_coverage_data={cy_tools_coverage_data}')
    log.trace(f'cy_tools_coverage_xml={cy_tools_coverage_xml}')
    log.trace(f'cy_tools_coverage_html={cy_tools_coverage_html}')

    if os.path.exists(cy_tools_coverage_html):
        shutil.rmtree(cy_tools_coverage_html)

    # Step 1: coverage cython cove must be re-build with debug option
    log.debug(f'Force rebuild extension with debug info')
    cython_tools.building.build(project_root, is_debug=True, annotate=False, build_ext=True)

    # Step 2: make a .coveragerc file with Cython plugin record

    with open(cy_tools_coverage_rc, 'w') as fh:
        fh.write("""
[run]
plugins = Cython.Coverage
        """)

    # Step 3: run a bunch of tests
    # Equivalent to console 'coverage run ...'
    log.trace(f'Running coverage with coverage engine: {coverage_engine}')

    # Run tests relative to project root!
    os.chdir(project_root)

    coverage_main(['run', f'--data-file={cy_tools_coverage_data}', f'--rcfile={cy_tools_coverage_rc}', '-m', coverage_engine, tests_target])

    # # Step 4: generate XML file based on those tests
    # # IMPORTANT: Add -i (to ignore coverage errors) (without -i cython full coverage report may silently fail, if any issue in one file)
    # log.trace(f'Producing XML file: {cy_tools_coverage_xml}')
    # coverage_main(['xml', f'--data-file={cy_tools_coverage_data}', f'--rcfile={cy_tools_coverage_rc}', '-i', '-o', cy_tools_coverage_xml])

    log.trace(f'Producing HTML file: {cy_tools_coverage_html}')
    title = f'Cython Tools Coverage at {datetime.now()}'
    coverage_main(['html', f'--data-file={cy_tools_coverage_data}', f'--rcfile={cy_tools_coverage_rc}', f'--title="{title}"', '-i', '-d', cy_tools_coverage_html])

    return os.path.join(cy_tools_coverage_html, 'index.html')
    #
    # all_pyx_files = get_all_covered_pyx(cy_tools_coverage_xml)
    # log.debug(f'#{len(all_pyx_files)} pyx files covered in this run')
    #
    # # Step 5: recompile cython code with annotations (but no rebuilding)
    # #     Make sure that we use the same method as for initial build
    # log.trace(f'Producing cython annotations with coverage')
    # cython_tools.building.build(project_root,
    #                             is_debug=True,
    #                             annotate=True,
    #                             build_ext=False,
    #                             coverage_xml_path=cy_tools_coverage_xml)
    #
    # cython_tools.building.annotate(all_pyx_files,
    #                                project_root=project_root,
    #                                force=False,
    #                                append=False,
    #                                )

def get_all_covered_pyx(coverage_rc_file):
    mytree = ET.parse(coverage_rc_file)
    myroot = mytree.getroot()

    packages = myroot.find('packages')

    all_pyx_files = set()
    if packages:
        package_list = packages.findall('package')
        for p in package_list:
            class_tag = p.find('classes')
            if class_tag is None:
                continue

            all_classes_tag = class_tag.findall('class')
            for c in all_classes_tag:
                try:
                    fn = c.attrib['filename']
                    if fn.lower().endswith('.pyx'):
                        all_pyx_files.add(fn)
                except KeyError:
                    log.error(f'{coverage_rc_file}: missing attr=filename')
    else:
        log.warn(f'{coverage_rc_file}: no packages covered')

    return sorted(list(all_pyx_files))
