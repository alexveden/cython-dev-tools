import os
import shutil
from datetime import datetime

import cython_tools.building
from cython_tools.common import check_project_initialized, open_url_in_browser
from cython_tools.logs import log


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
    cython_tools.building.build(project_root, is_debug=True)

    # Step 2: make a .coveragerc file with Cython plugin record
    # include = {project_root}/*.pyx
    with open(cy_tools_coverage_rc, 'w') as fh:
        fh.write(f"""
[run]
plugins = cython_tools.testing.coverage_plugin
#source = {project_root}
#source_pkgs = uberhf.datafeed.mem_pool_quotes
#debug = plugin, trace, dataio
        """)

    # Step 3: run a bunch of tests
    # Equivalent to console 'coverage run ...'
    log.trace(f'Running coverage with coverage engine: {coverage_engine}')

    # Run tests relative to project root!
    os.chdir(project_root)

    # Place this junk into cython tools dir
    # TODO: add it to the test runner too
    pytest_cache_dir = os.path.join(cython_tools_path, '.pytest_cache')

    coverage_main(['run', f'--data-file={cy_tools_coverage_data}', f'--rcfile={cy_tools_coverage_rc}',
                   '-m', coverage_engine, f'--override-ini=cache_dir={pytest_cache_dir}', '-q', tests_target])

    log.trace(f'Producing HTML file: {cy_tools_coverage_html}')
    title = f'Cython Tools Coverage at {datetime.now()}'
    coverage_main(['html', f'--data-file={cy_tools_coverage_data}', f'--rcfile={cy_tools_coverage_rc}', f'--title="{title}"', '-i', '-d', cy_tools_coverage_html])

    return os.path.join(cy_tools_coverage_html, 'index.html')