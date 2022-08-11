import os
import re
from typing import List

from cython_tools.settings import CYTHON_TOOLS_DIRNAME
import sys
from cython_tools.logs import log


RE_PY_FILE = re.compile(r"[A-Za-z\d\._\/\\]+\.py[x]?$", re.MULTILINE)
RE_PY_PACKAGE = re.compile(r"^[A-Za-z\d\._]+$", re.MULTILINE)
RE_ANY_CLASS = re.compile(r"(^cdef +|^)class +[A-Za-z\d_]+(:|\()", re.MULTILINE)


def make_run_args(code_file, package, entry_method, escape=False, pytest=False) -> List[str]:
    """
    Simple python arguments to run package by path

    :param code_file:
    :param package:
    :param entry_method:
    :return:
    """
    assert os.path.exists(code_file), f'{code_file} not exists'

    if entry_method is None:
        if pytest:
            return ['-m', 'pytest', f'{code_file}']
        else:
            return ['-m', f'{package}']
    else:
        if pytest:
            assert not code_file.endswith('.py'), f'Debug test entry point must be a python file!'
            return ['-m', 'pytest', f'{code_file}', '-k', entry_method]
        else:
            if escape:
                return ['-c', f'"import {package}; {package}.{entry_method}();"']
            else:
                return ['-c', f'import {package}; {package}.{entry_method}();']


def check_method_args(args_str: str):
    """
    Parses primitive arguments and decide if they are OK for passing as entry point function
    """
    if not args_str:
        # Empty args / kwargs
        return (), {}
    args_str = args_str.strip()

    if not args_str.startswith('(') or not args_str.endswith(')'):
        raise ValueError(f'Arguments must start with "(" and end with ")"')

    def __test_args(*args, **kwargs):
        return args, kwargs
    try:
        return eval(f"__test_args{args_str}")
    except Exception as exc:
        raise ValueError(f'Error parsing arguments `{args_str}`, it must only contain primitive or builtin types, err: {exc}')


def check_method_exists(code_file, method_def, as_entry=False) -> bool:
    """
    Check is the file contains method in its source code, raises ValueError on failure

    :param code_file: path to python or cython source
    :param method_def: two types methods
        - top level method when method_def='main'
        - class level methods when method_def='SomeClass.some_method'
    :param as_entry: force checks if method_def is a good for entry point into a program

    :return: True if found
    """
    if as_entry and '.' in method_def:
        raise ValueError(f'Class methods are not allowed to use as entry points')
    if method_def.count('.') > 1:
        raise ValueError(f'Too deep level of method, use `method` for top method or `SomeClass.some_method` for class methods')

    with open(code_file, 'r') as fh:
        lines = fh.readlines()
        re_bp_class = None
        _func_found = False
        _class_found = False

        if '.' in method_def:
            bp_class_name, bp_func_name = method_def.split('.')
            if not bp_class_name or not bp_func_name:
                raise ValueError(f'Incorrect class: {method_def}, expected @ClassName.class_method')
            #
            re_bp_class = re.compile(rf"(^cdef +|^)class +{bp_class_name}(:|\()", re.MULTILINE)

            # # When in class we must search indented functions
            re_bp_func = re.compile(rf" +[c|cp]*def( +| .* ){bp_func_name}\(", re.MULTILINE)
        else:
            bp_func_name = method_def
            # When in __main__ we must search NOT-indented functions
            re_bp_func = re.compile(rf"^[c|cp]*def( +| .* ){bp_func_name}\(", re.MULTILINE)

        _class_idx = None
        _curr_class_idx = None
        for i, l in enumerate(lines):
            if RE_ANY_CLASS.match(l):
                _curr_class_idx = i

            if re_bp_class is not None:
                if re_bp_class.match(l):
                    _class_found = True
                    _class_idx = i

                if _class_found and re_bp_func.match(l) and _class_idx == _curr_class_idx:
                    _func_found = True
            else:
                if re_bp_func.match(l):
                    _func_found = True
                    if as_entry and not re.match(rf"^(cpdef|def)( +| .* ){bp_func_name}\(.*", l):
                        raise ValueError(f'Found entry point, it must be def/cpdef'
                                         f'in file://{code_file}, line: {i + 1}, code: `{l}` ')

        if re_bp_func is not None and not _func_found:
            raise ValueError(f'Method not found: no such function ({bp_func_name}) in file://{code_file}')
        if re_bp_class is not None and not _class_found:
            raise ValueError(f'Class  not found: not such class ({bp_class_name}) in file://{code_file}')

    return True


def find_package_path(project_root, entry_point_string, as_entry=True):
    """
    Looks into entry points for python/cython files for running or debugging

    :param project_root: project root for look up
    :param entry_point_string: argument with possible formats, relative to project root
         package/sub_package/module.py - uses __main__ by path
         package.sub_package.module - uses __main__ by module name
         package/sub_package/module.py@main - uses main() inside package/sub_package/module.py
         package.sub_package.module@main - uses main() inside package/sub_package/module.py

         package/sub_package/module.pyx@main - for Cython modules must have a `@func_name` for entry point
         package.sub_package.module@main - for Cython modules must have a `@func_name` for entry point
    :param as_entry: checks if the `entry_point_string` is viable entry point for program start
    :return:
    """
    toks = entry_point_string.split('@')
    file_qual_path = toks[0]

    if len(toks) > 2:
        raise ValueError(f'Duplicate entry points `@`, only one/or none allowed in {entry_point_string}')

    if file_qual_path.startswith('.') or file_qual_path.startswith(os.path.sep) or \
            file_qual_path.endswith('.') or file_qual_path.endswith(os.path.sep):
        raise ValueError(f'Project path must not start or end with `.` or `/`, must be relative to project root: {file_qual_path}')

    source_path = None
    package_path = None
    entry_method = None

    if RE_PY_FILE.match(file_qual_path):
        source_path = os.path.join(project_root, file_qual_path)
        # Simple path
        if not os.path.exists(source_path):
            raise FileNotFoundError(f'Source not found: {source_path}')
        if os.path.isdir(source_path):
            raise IsADirectoryError(f'Source must be a file, got dir: {source_path}')

        package_path = re.sub(r"\.py[x]?$", '', file_qual_path).replace(os.path.sep, '.')
    else:
        if not RE_PY_PACKAGE.match(file_qual_path):
            raise ValueError(f'This does not look as valid package path: `{file_qual_path}`, contains incorrect chars')

        package_path = file_qual_path
        source_path = os.path.join(project_root, file_qual_path.replace('.', os.path.sep))
        if os.path.exists(source_path + '.pyx'):
            source_path += '.pyx'
        elif os.path.exists(source_path + '.py'):
            source_path += '.py'
        else:
            raise FileNotFoundError(f'No .py/.pyx files found at {source_path}[.py|.pyx]')

    if len(toks) == 2:
        entry_method = toks[1]
        if entry_method == '':
            raise ValueError(f'Empty entry method name after @')
        check_method_exists(source_path, entry_method, as_entry=as_entry)
    else:
        if as_entry and source_path.endswith('.pyx'):
            raise ValueError(f'Cython packages always must have entry point, i.e. package.pyx@some_main_entry!')

    return os.path.abspath(source_path), package_path, entry_method


def open_url_in_browser(url):
    if sys.platform == 'win32':
        # Not tested!
        log.CRITICAL(f'Not tested!')
        os.startfile(url)
    elif sys.platform == 'darwin':
        os.spawnlp(os.P_NOWAIT, 'open', 'open', url)
    else:
        try:
            os.spawnlp(os.P_NOWAIT, 'xdg-open', 'xdg-open', url)
        except OSError:
            print('Please open a browser on: ' + url)

    sys.stderr.flush()
    sys.stdout.flush()


def check_project_initialized(project_root):
    if project_root is not None:
        if not os.path.exists(project_root):
            raise FileNotFoundError(f'project_root not exists: {project_root}')
        project_root = os.path.abspath(project_root)
        os.chdir(project_root)
    else:
        project_root = os.getcwd()

    if not os.path.exists(os.path.join(project_root, CYTHON_TOOLS_DIRNAME)):
        raise FileNotFoundError(f'{CYTHON_TOOLS_DIRNAME} not exists in project root {project_root}, missing cython tools initialize?')

    return project_root, os.path.join(project_root, CYTHON_TOOLS_DIRNAME)


def parse_input(input_type, default=None, prompt='', regex=None, n_trials=3):
    """
    Parses user input if default value is None, or checks `default` value

    :param input_type: expected variable type: str/float/int
    :param prompt: input prompt
    :param default: if default value is given, the function will skip asking, but will do a type check (but raises immediately without re-asking!)
    :param regex: optional regex for string inputs
    :param n_trials: number of trials before input raises an error
    :return:
    :raise ValueError
    """
    if regex is not None:
        if isinstance(regex, str):
            regex = re.compile(regex, re.MULTILINE)
        else:
            assert isinstance(regex, re.Pattern), f'Expected string or compiled re, got {type(regex)}'

    valid_value = None
    for i in range(n_trials):
        if default is None:
            # Add new line to prompt to make logging output look correct
            if input_type is bool:
                print(prompt + ' [y/n]')
                value = input()
            else:
                print(prompt)
                value = input()
        else:
            value = default

        if input_type is int:
            try:
                valid_value = int(value)
            except ValueError:
                if default is not None:
                    raise ValueError(f'Argument value is incorrect: {default}, expected integer')
                print(f'Type correct int number value')
                continue
            break
        elif input_type is float:
            try:
                valid_value = float(value)
            except ValueError:
                if default is not None:
                    raise ValueError(f'Argument value is incorrect: {default}, expected float')
                print(f'Type correct float number value')
                continue
            break
        elif input_type is bool:
            try:
                if isinstance(value, str):
                    # Given from console
                    _v = value.lower()
                    if _v == 'y' or _v == 'yes' or _v == '1':
                        valid_value = True
                    elif _v == 'n' or _v == 'no' or _v == '0':
                        valid_value = False
                    else:
                        raise ValueError()
                elif isinstance(value, bool):
                    valid_value = value
                else:
                    raise ValueError(f'unsupported')

                break
            except ValueError:
                if default is not None:
                    raise ValueError(f'Argument value is incorrect: {default}, expected bool')
                print(f'Type correct bool value: y/n, yes/no, 1/0')
                continue
        elif input_type is str:
            if not isinstance(value, str):
                raise ValueError(f'Argument value is incorrect: {default}, expected string')
            if len(value) == 0:
                print(f'Empty string, try again')
                continue

            if regex is not None:
                if not regex.match(value):
                    print(f'Incorrect sting input, expected regex={regex}, no match for {value}')
                    continue

            valid_value = value
            break
        else:
            raise NotImplementedError(f'Unsupported input type: {input_type}')

    if valid_value is None:
        raise ValueError(f'Input validation failed')

    return valid_value
