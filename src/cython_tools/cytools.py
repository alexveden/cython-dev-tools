"""
Cython Tools Management script
"""
import argparse
import os
import sys
from argparse import RawTextHelpFormatter

import cython_tools.building
import cython_tools.debugger
import cython_tools.testing
import cython_tools.maintenance

from cython_tools.settings import CYTHON_TOOLS_DIRNAME


def main(argv=None):
    # create the top-level parser
    parser = argparse.ArgumentParser(description='Cython development toolkit (debugger, profiler, coverage, unit tests)\n'
                                                 f'To get more help run: {os.path.basename(sys.argv[0])} <COMMAND> --help/-h',
                                     )
    parser.add_argument('--verbose', '-v', action='count', default=0)
    subparsers = parser.add_subparsers(title='COMMAND')

    #
    # `initialize` command arguments
    #
    parser_initialize = subparsers.add_parser('initialize',
                                              description='Initializes cython tools project root')
    parser_initialize.add_argument('project_root', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_initialize.add_argument('--force', '-f', action='store_true', help='Force replacing cython tools project files (can be dangerous)')
    parser_initialize.add_argument('--include-samples', '-s', action='store_true', help='Copy sample files for experimenting')
    parser_initialize.add_argument('--include-boilerplate', '-b', action='store_true', help='Make typical cython project')
    parser_initialize.add_argument('--boilerplate-name', '-n', help='Boilerplate package name')
    parser_initialize.add_argument('--log-name', help='custom log name', default='cython_tools__initialize')
    parser_initialize.set_defaults(func=cython_tools.building.initialize_command)

    #
    # `build` command arguments
    #
    parser_build = subparsers.add_parser('build',
                                         description='Build cython extensions')
    parser_build.add_argument('--project-root', '-p', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_build.add_argument('--debug', '-d', action='store_true', help='build debug version for coverage and GDB')
    parser_build.add_argument('--annotate', '-a', action='store_true', help='create HTML annotation file nearby .pyx')
    parser_build.add_argument('--force', '-f', action='store_true', help='force rebuilding all cython files')
    parser_build.set_defaults(func=cython_tools.building.build_command)

    #
    # `cover` command arguments
    #
    parser_cover = subparsers.add_parser('cover',
                                         description='Runs unit tests on cython files and produces code coverage')
    parser_cover.add_argument('tests_target', help=f'Tests target path relative to project root')
    parser_cover.add_argument('--coverage-engine', help=f'Test runner package (pytest only tested so far)', default='pytest')
    parser_cover.add_argument('--project-root', '-p', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_cover.add_argument('--browser', '-b', action='store_true',  help='Open url in browser when coverage is ready')
    parser_cover.set_defaults(func=cython_tools.testing.coverage_command)

    #
    # `annotate` command arguments
    #
    parser_annotate = subparsers.add_parser('annotate',
                                            description='Build .pyx files HTML annotations, and returns HTML file link',
                                            formatter_class=RawTextHelpFormatter)
    parser_annotate.add_argument('annotate_target', help=f'Individual .pyx file, or folder relative to project root path (finds all .pyx in subfolders also).\n'
                                                         f'Examples: \n'
                                                         f'"." - all in project \n'
                                                         f'"package_name/" - all in package including subpackages ')
    parser_annotate.add_argument('--append', '-a', action='store_true', help='Instead of cleaning up previous annotation index, appends new to the structure')
    parser_annotate.add_argument('--project-root', '-p', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_annotate.add_argument('--browser', '-b', action='store_true',  help='Open url in browser when annotation is ready')
    parser_annotate.set_defaults(func=cython_tools.building.annotate_command)

    #
    # `debug` command arguments
    #
    parser_debug = subparsers.add_parser('debug',
                                         description='Starts cython debugger',
                                         formatter_class=RawTextHelpFormatter)
    parser_debug.add_argument('debug_target',
                              help=f'A python/cython module path or initial breakpoint (must be relative to project root!)\n'
                                   f'Examples:\n'
                                   f'package/sub_package/module.py - starts __main__ in Python module\n'
                                   f'package.sub_package.module - starts __main__ in Python module\n'
                                   f'package/sub_package/cy_module.pyx@main - starts main() in Cython module, entry point is mandatory\n'
                                   f'package.sub_package.cy_module@main - starts main() in Cython module, entry point is mandatory\n'
                                   f'package.sub_package.cy_module@main:23 - starts main() in Cython module, entry point is mandatory, break at line 23\n'
                                   f'package.sub_package.cy_module@main:test_break - starts main() in Cython module, break at test_break() of this module\n'
                              )
    parser_debug.add_argument('--breakpoint', '-b',
                              action='append',
                              help=f'Set initial breakpoint for the debugger (can be used multiple times, must be relative to project root!)\n'
                                   f'Examples:\n'
                                   f'-b 10 - sets line 10 breakpoint at `debug_target` (only Cython)\n'
                                   f'-b SomeClass.meth - class/method breakpoint inside `debug_target`\n'
                                   f'-b another_pkg:SomeClass.meth - class method breakpoint somewhere is project root\n'
                                   f'-b another_pkg:meth - method breakpoint somewhere in project root\n'
                                   f'-b package/sub_package/module.pyx:23 - line breakpoint by path (only Cython)\n'
                                   f'-b package/sub_package/module.pyx:SomeClass.meth - class method breakpoint by path\n'
                              )
    parser_debug.add_argument('--pytest', '-t', action='store_true', help='Run tests in pytest environment')
    parser_debug.add_argument('--project-root', '-p', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_debug.add_argument('--cygdb-verbosity', type=int, default=0,
                              help=f'Print more debug information when in GDB, integer [0, 4]. Typically only used to debug the debugger')
    parser_debug.set_defaults(func=cython_tools.debugger.debug_command)

    #
    # `valgrind` command arguments
    #
    parser_valgrind = subparsers.add_parser('valgrind',
                                            description='Checks memory leaks with Valgrind tool',
                                            formatter_class=RawTextHelpFormatter)
    parser_valgrind.add_argument('run_target',
                            help=f'A python/cython module path (must be relative to project root!)\n'
                                 f'Examples:\n'
                                 f'package/sub_package/module.py - starts __main__ in Python module\n'
                                 f'package.sub_package.module - starts __main__ in Python module\n'
                                 f'package/sub_package/cy_module.pyx@main - starts main() in Cython module, entry point is mandatory\n'
                                 f'package.sub_package.cy_module@main - starts main() in Cython module, entry point is mandatory\n'
                            )
    parser_valgrind.add_argument('--project-root', '-p', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_valgrind.add_argument('--pytest', '-t', action='store_true', help='Run module as in pytest')
    parser_valgrind.add_argument('--no-filter', '-n', action='store_false', help='Include all functions calls in call stacks')
    parser_valgrind.add_argument('--no-replace', '-r', action='store_false', help='Don\'t replace Cython raw c-functions names by mapping pyx code')
    parser_valgrind.set_defaults(func=cython_tools.debugger.valgrind_command)

    #
    # `run` command arguments
    #
    parser_run = subparsers.add_parser('run',
                                       description='Runs Cython/Python script',
                                       formatter_class=RawTextHelpFormatter)
    parser_run.add_argument('run_target',
                            help=f'A python/cython module path (must be relative to project root!)\n'
                                 f'Examples:\n'
                                 f'package/sub_package/module.py - starts __main__ in Python module\n'
                                 f'package.sub_package.module - starts __main__ in Python module\n'
                                 f'package/sub_package/cy_module.pyx@main - starts main() in Cython module, entry point is mandatory\n'
                                 f'package.sub_package.cy_module@main - starts main() in Cython module, entry point is mandatory\n'
                            )
    parser_run.add_argument('--project-root', '-p', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_run.set_defaults(func=cython_tools.debugger.run_command)

    #
    # `tests` command arguments
    #
    parser_tests = subparsers.add_parser('tests',
                                         description='Runs all or selected tests by file or directory path',
                                         formatter_class=RawTextHelpFormatter)
    parser_tests.add_argument('tests_target',
                              help=f'A python/cython module path or directory (only python entry points!)\n'
                                   f'Examples:\n'
                                   f'. - runs all tests in current directory\n'
                                   f'mymodule/tests - runs all tests `mymodule/tests` directory\n'
                                   f'package/test/test_module.py - starts tests in a specific module\n'
                              )
    parser_tests.add_argument('--project-root', '-p', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_tests.add_argument('--quiet', '-q', action='store_true', help=f'Reduces test suite verbosity to minimum')
    parser_tests.add_argument('--disable-warnings', '-w', action='store_true', help=f'Ignore all warnings')
    parser_tests.add_argument('--lf', '-l', action='store_true', help=f'Run only last failed')
    parser_tests.set_defaults(func=cython_tools.testing.tests_command)

    #
    # `clean` command arguments
    #
    parser_clean = subparsers.add_parser('clean',
                                         description='Clean Cython project structure form all non <module>.pyx '
                                                     '(i.e. <module>.c, <module>.html, <module>*.so/dll)\n',
                                         formatter_class=RawTextHelpFormatter)

    parser_clean.add_argument('--yes', '-y', action='store_true',
                                 help='Confirm deletion all files without prompt')
    parser_clean.add_argument('--project-root', '-p', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_clean.add_argument('--delete-build', '-b', action='store_true', help=f'deletes a build directory in project root')
    parser_clean.set_defaults(func=cython_tools.maintenance.clean_command)


    #
    # `lprun` command arguments
    #
    parser_lprun = subparsers.add_parser('lprun',
                                         description='Run line profiler on Cython/Python code',
                                         formatter_class=RawTextHelpFormatter)

    parser_lprun.add_argument('profile_target',
                            help=f'A python/cython module path (must be relative to project root!)\n'
                                 f'Profiled functin must support simple args, kwargs of primitive Python types\n'
                                 f'Examples:\n'
                                 f'cy_tools_samples/profiler/cy_module.pyx@approx_pi2(10)\n'
                                 f'some_module.py@some_func(10.1, [1, 2.2, 3], kwarg1="test")\n'
                            )

    parser_lprun.add_argument('--function', '-f',
                              action='append',
                              help=f'Add function to the profiler report\n'
                                   f'Examples:\n'
                                   f'-f cy_tools_samples/profiler/cy_module.pyx@recip_square2 - by path\n'
                                   f'-f cy_tools_samples.profiler.cy_module@recip_square2 - by package\n'
                                   f'-f recip_square2 - another function in `profile_target` module`\n'
                                   f'-f SomeClass.class_method - class method profile\n'
                                   f'-f cy_tools_samples.profiler.cy_module.pyx@SQ.recip_square_ - another package with class\n'
                              )

    parser_lprun.add_argument('--module', '-m',
                              action='append',
                              help=f'Add all module methods and classes to profiler report\n'
                                   f'Examples:\n'
                                   f'-m cy_tools_samples/profiler/cy_module.pyx - by path\n'
                                   f'-m cy_tools_samples.profiler.cy_module - by package\n'
                              )

    parser_lprun.add_argument('--project-root', '-p', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_lprun.set_defaults(func=cython_tools.testing.lprun_command)
    
    #
    # `template` command arguments
    #
    parser_template = subparsers.add_parser('template',
                                              description='Creates template Cython class/module with tests')
    parser_template.add_argument('module_full_package', help='New module path from project root, i.e. mypackage.subpackage.my_new_module')
    parser_template.add_argument('--project_root', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_template.add_argument('--template-type', '-t', help=f'Template type: class|module')
    parser_template.add_argument('--include-tests', '-i', help='Makes test files inside new module dir', type=bool)
    parser_template.add_argument('--log-name', help='custom log name', default='cython_tools__template')
    parser_template.set_defaults(func=cython_tools.maintenance.template_command)

    args = parser.parse_args(argv)
    if (argv is None and len(sys.argv) == 1) or 'func' not in args:
        parser.print_help()
        sys.exit(0)
    else:
        #print(args)
        args.func(args)


if __name__ == '__main__':
    #main()
    main('initialize a -h'.split())

