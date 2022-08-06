"""
Cython Tools Management script
"""
import argparse
import sys
import os
import cython_tools.building
import cython_tools.testing
from cython_tools.settings import CYTHON_TOOLS_DIRNAME


def main(argv=None):
    # create the top-level parser
    parser = argparse.ArgumentParser(description='Cython development toolkit (debugger, profiler, coverage, unit tests)\n'
                                                 f'To get more help run: {os.path.basename(sys.argv[0])} <COMMAND> --help/-h')
    parser.add_argument('--verbose', '-v', action='count', default=0)
    subparsers = parser.add_subparsers(title='COMMAND')

    #
    # `initialize` command arguments
    #
    parser_initialize = subparsers.add_parser('initialize',
                                              description='Initializes cython tools project root')
    parser_initialize.add_argument('project-root', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
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
    parser_build.add_argument('--annotate', '-a', action='store_true', help='add HTML Cython annotations')
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
                                            description='Build .pyx files HTML annotations, and returns HTML file link')
    parser_annotate.add_argument('annotate_target', help=f'Individual .pyx file, or folder relative to project root path (finds all .pyx in subfolders also).'
                                                         f'Examples: "." - all in project, "package_name/" - all in package, including subpackages ')
    parser_annotate.add_argument('--force', '-f', action='store_true', help='Force replacing HTML annotation files')
    parser_annotate.add_argument('--append', '-a', action='store_true', help='Instead of cleaning up previous annotation, appends new to the structure')
    parser_annotate.add_argument('--project-root', '-p', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_annotate.add_argument('--browser', '-b', action='store_true',  help='Open url in browser when annotation is ready')
    parser_annotate.set_defaults(func=cython_tools.building.annotate_command)


    args = parser.parse_args(argv)
    if argv is None and len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    else:
        args.func(args)


if __name__ == '__main__':
    #main()
    main('initialize a -h'.split())

