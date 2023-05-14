from line_profiler import LineProfiler, show_text
import importlib
import textwrap
import os
import sys
import shutil
from datetime import datetime
import inspect
import cython_dev_tools.building
from cython_dev_tools.common import check_project_initialized, open_url_in_browser, find_package_path, check_method_args
from cython_dev_tools.logs import log


def lprun_command(args):
    log.setup('cython_dev_tools__lprun', verbosity=args.verbose)

    lprun(args.profile_target,
          functions=args.function,
          modules=args.module,
          project_root=args.project_root,
          )


class CythonLineProfiler(LineProfiler):
    def add_module(self, mod):
        """
        Add all the functions in a module and its classes.

        Added implementation of cython module inclusion
        """
        from inspect import isclass, isroutine

        # replaced isfunction to isroutine which works with Cython methods
        nfuncsadded = 0
        for key, item in mod.__dict__.items():
            #if key == 'SQ':
            #    breakpoint()
            if isclass(item):

                for k, v in item.__dict__.items():
                    # Exclude private and built-in methods
                    if isroutine(v) and not k.startswith('__') and not k.endswith('__'):
                        log.trace(f'class: {key}.{k} -> {v}')
                        self.add_function(v)
                        nfuncsadded += 1
            elif isroutine(item):
                if not key.startswith('__') and not key.endswith('__'):
                    log.trace(f'function: {item}')
                    self.add_function(item)
                    nfuncsadded += 1

        return nfuncsadded


def lprun(profile_target,
          functions=None,
          modules=None,
          project_root=None,
          ):
    __cytool_functions = functions or []
    __cytool_modules = modules or []

    # Check if cython tools in a good state in the project root
    project_root, cython_dev_tools_path = check_project_initialized(project_root)
    sys.path.insert(0, project_root)
    log.info(f'Starting coverage at {project_root}')

    if '(' not in profile_target and ')' not in profile_target and '@' not in profile_target:
        raise ValueError(f'profile_target (got {profile_target}) should be a package path with entry point with args, '
                         f'e.g. package/sub_package/module.pyx@main() or package.module@main(1, 2, n=5)')

    log.trace(f'profile_target: {profile_target}')

    arg_i = profile_target.index('(')

    entry_target = profile_target[:arg_i]
    entry_args = profile_target[arg_i:]

    source_file, package, entry_method = find_package_path(project_root, entry_target)
    log.trace((source_file, package, entry_method))

    f_args, f_kwargs = check_method_args(entry_args)
    log.trace(f'Arguments to pass into: {entry_method}(*{f_args}, **{f_kwargs})')

    log.trace(f'Importing {package}')
    entry_module = importlib.import_module(package)

    def get_module_func(m, func_path):
        try:
            if '.' in func_path:
                toks = func_path.split('.')
                o = getattr(m, toks[0])
                return get_module_func(o, '.'.join(toks[1:]))
            else:
                return getattr(m, func_path)
        except AttributeError:
            raise RuntimeError(f'Module/object {m} does no contain visible for Python method {entry_method}')

    entry_func = get_module_func(entry_module, entry_method)

    functions_to_profile = [entry_func]

    for lp_func in __cytool_functions:
        if '(' in lp_func or ')' in lp_func:
            raise f'-f/-func arguments must be a simple path to a function WITHOUT arguments, got `{lp_func}`, i.e. `func` (if func in entry module)' \
                  f' or `package/module.pyx@func` or `package.module@func`'
        if '@' not in lp_func:
            # Func definition related to the main module
            _func = get_module_func(entry_module, lp_func)
            functions_to_profile.append(_func)
        else:
            f_source_file, f_package, f_entry_method = find_package_path(project_root, lp_func, as_entry=False)
            _func_m = importlib.import_module(f_package)
            _func = get_module_func(_func_m, f_entry_method)
            functions_to_profile.append(_func)

        log.trace(f'lprun added profile function: {_func} code: {_func.__code__}')

    modules_to_profile = []
    for lp_module in __cytool_modules:
        if '@' in lp_module:
            raise ValueError(f'You must pass module path without @, got {lp_module}')
        m_source_file, m_package, m_entry_method = find_package_path(project_root, lp_module, as_entry=False)

        m_module = importlib.import_module(m_package)
        modules_to_profile.append(m_module)
        #breakpoint()
        log.trace(f'lprun added module: {m_module} {m_source_file}')

    importlib.invalidate_caches()

    prof = CythonLineProfiler(*functions_to_profile)
    for m in modules_to_profile:
        prof.add_module(m)

    try:
        prof.runcall(entry_func, *f_args, **f_kwargs)
        prof.print_stats(stripzeros=True)
    except TypeError as exc:
        if 'argument' in str(exc):
            full_spec = inspect.getfullargspec(entry_func)
            raise RuntimeError(f'Incorrect arguments passed to entry_func: {entry_method}, got *args={f_args}, **kwargs={f_kwargs}\n\t{full_spec}')
        raise


