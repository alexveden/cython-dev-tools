"""
Cython Tools Management script
"""
import argparse
import sys
import os
import cython_tools.initializer
import cython_tools.builder
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
    parser_initialize.add_argument('project_root', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_initialize.add_argument('--force', '-f', action='store_true', help='Force replacing cython tools project files (can be dangerous)')
    parser_initialize.add_argument('--include-samples', '-s', action='store_true', help='Copy sample files for experimenting')
    parser_initialize.add_argument('--include-boilerplate', '-b', action='store_true', help='Make typical cython project')
    parser_initialize.add_argument('--boilerplate-name', '-n', help='Boilerplate package name')
    parser_initialize.add_argument('--log-name', help='custom log name', default='cython_tools__initialize')
    parser_initialize.set_defaults(func=cython_tools.initializer.command)

    #
    # `build` command arguments
    #
    parser_build = subparsers.add_parser('build',
                                         description='Build cython extensions')
    parser_build.add_argument('project_root', help=f'A project root path and also `{CYTHON_TOOLS_DIRNAME}` working dir')
    parser_build.add_argument('--debug', '-d', action='store_true', help='build debug version for coverage and GDB')
    parser_build.add_argument('--annotate', '-a', action='store_true', help='add HTML Cython annotations')
    parser_build.set_defaults(func=cython_tools.builder.command)

    args = parser.parse_args(argv)
    if argv is None and len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    else:
        args.func(args)


if __name__ == '__main__':
    #main()
    main('initialize a -h'.split())

