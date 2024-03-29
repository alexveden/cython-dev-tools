"""
GDB extension that adds Cython support.

Based on Cython project cygdb
https://github.com/cython/cython/blob/master/Cython/Debugger/libcython.py


IMPORTANT: The following python code is only viable inside GDB python interpreter (it's a built-in python wired deep in the GDB)
"""
from __future__ import print_function

import traceback

try:
    input = raw_input
except NameError:
    pass


import sys
import os
import textwrap
import functools
import itertools
import collections

import gdb

try:  # python 2
    UNICODE = unicode
    BYTES = str
except NameError:  # python 3
    UNICODE = str
    BYTES = bytes

try:
    from lxml import etree
    have_lxml = True
except ImportError:
    have_lxml = False
    try:
        # Python 2.5
        from xml.etree import cElementTree as etree
    except ImportError:
        try:
            # Python 2.5
            from xml.etree import ElementTree as etree
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
            except ImportError:
                # normal ElementTree install
                import elementtree.ElementTree as etree

try:
    import pygments.lexers
    import pygments.formatters
except ImportError:
    pygments = None
    sys.stderr.write("Install pygments for colorized source code.\n")

if hasattr(gdb, 'string_to_argv'):
    from gdb import string_to_argv
else:
    from shlex import split as string_to_argv

from cython_dev_tools.debugger.gbd import libpython
from cython_dev_tools.debugger.gbd.libpython import TRACE, DEBUG_TRACE


# C or Python type
CObject = 'CObject'
PythonObject = 'PythonObject'

_data_types = dict(CObject=CObject, PythonObject=PythonObject)
_filesystemencoding = sys.getfilesystemencoding() or 'UTF-8'

import re
RE_WRAPPER_F = re.compile(r"^static .*(?P<func>__pyx_pw_[A-Za-z\d_]+)\(.*\).*$", re.MULTILINE)
RE_C_FUNC = re.compile(r"^\s*__pyx_r\s+=.*(?P<c_func>__pyx_pf_[A-Za-z\d_]+)\(.*;", re.MULTILINE)
RE_C_DEALLOC = re.compile(r"^\s*(?P<c_func>__pyx_pf_[A-Za-z\d_]+__dealloc__)\(.*\);$", re.MULTILINE)
RE_RETURN_F = re.compile(r"^\s*return\s+__pyx_r;$", re.MULTILINE)

def get_cython_wrappers(src_file):
    """
    Parses source files to get core Cython function from Cython wrapper
    '__pyx_pw_13MemPoolQuotes_1__init__' -> '__pyx_pf_13MemPoolQuotes___init__'
    """
    wrapper_map = {}
    if not os.path.exists(src_file):
        TRACE(f'No source file: {src_file} or abandoned files in .cython_dev_tools/cython_debug/ folder')
        return wrapper_map

    with open(src_file, 'r') as fh:
        lines = fh.readlines()

        proto_name = None
        wrapped_func = None
        is_dealloc = False
        has_entry = False

        for l in lines:
            if not has_entry:
                reg = RE_WRAPPER_F.match(l)
                if reg:
                    # print(f'#: {l}')
                    if not proto_name:
                        if ';' in l and '/*proto*/' in l:
                            proto_name = reg['func']
                            if proto_name.endswith('__dealloc__'):
                                is_dealloc = True;
                            continue
                    else:
                        if reg['func'] == proto_name and '{' in l:
                            #print(l)
                            has_entry = True
                        else:
                            has_entry = False
                            proto_name = None
                            wrapped_func = None
                            is_dealloc = False;
                            # print(f'invalid proto: {l}')
            else:
                if is_dealloc:
                    reg = RE_C_DEALLOC.match(l)
                    if reg:
                        wrapped_func = reg['c_func']
                else:
                    reg = RE_C_FUNC.match(l)
                    if reg:
                        wrapped_func = reg['c_func']

            if RE_RETURN_F.match(l) or wrapped_func:
                if proto_name and wrapped_func:
                    wrapper_map[proto_name] = wrapped_func

                # Func return
                proto_name = None
                has_entry = False
                wrapped_func = None
                is_dealloc = False;
    return wrapper_map

# decorators

def default_selected_gdb_frame(err=True):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, frame=None, *args, **kwargs):
            try:
                frame = frame or gdb.selected_frame()
            except RuntimeError:
                raise gdb.GdbError("No frame is currently selected.")

            if err and frame.name() is None:
                raise NoFunctionNameInFrameError()

            return function(self, frame, *args, **kwargs)
        return wrapper
    return decorator


def require_cython_frame(function):
    @functools.wraps(function)
    @require_running_program
    def wrapper(self, *args, **kwargs):
        frame = kwargs.get('frame') or gdb.selected_frame()
        if not self.is_cython_function(frame):
            raise gdb.GdbError('Selected frame does not correspond with a '
                               'Cython function we know about.')
        return function(self, *args, **kwargs)
    return wrapper


def dispatch_on_frame(c_command, python_command=None):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, *args, **kwargs):
            is_cy = self.is_cython_function()
            is_py = self.is_python_function()

            if is_cy or (is_py and not python_command):
                function(self, *args, **kwargs)
            elif is_py:
                gdb.execute(python_command)
            elif self.is_relevant_function():
                gdb.execute(c_command)
            else:
                raise gdb.GdbError("Not a function cygdb knows about. "
                                   "Use the normal GDB commands instead.")

        return wrapper
    return decorator


def require_running_program(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            gdb.selected_frame()
        except RuntimeError:
            raise gdb.GdbError("No frame is currently selected.")

        return function(*args, **kwargs)
    return wrapper


def gdb_function_value_to_unicode(function):
    @functools.wraps(function)
    def wrapper(self, string, *args, **kwargs):
        if isinstance(string, gdb.Value):
            string = string.string()

        return function(self, string, *args, **kwargs)
    return wrapper


# Classes that represent the debug information
# Don't rename the parameters of these classes, they come directly from the XML

class CythonModule(object):
    def __init__(self, module_name, filename, c_filename):
        self.name = module_name
        self.filename = filename
        self.c_filename = c_filename
        self.globals = {}
        # {cython_lineno: min(c_linenos)}
        self.lineno_cy2c = {}
        # {c_lineno: cython_lineno}
        self.lineno_c2cy = {}
        self.functions = {}

        # We will use this for exclude irrelevant (say C MACTOS) from `cy next`/`cy step`
        # Will be initialized in CyImport class
        self.min_relevant_line_no = 10000000
        self.max_relevant_line_no = 0


class CythonVariable(object):

    def __init__(self, name, cname, qualified_name, type, lineno):
        self.name = name
        self.cname = cname
        self.qualified_name = qualified_name
        self.type = type
        self.lineno = int(lineno)


class CythonFunction(CythonVariable):
    def __init__(self,
                 module,
                 name,
                 cname,
                 pf_cname,
                 qualified_name,
                 lineno,
                 type=CObject,
                 is_initmodule_function="False"):
        super(CythonFunction, self).__init__(name,
                                             cname,
                                             qualified_name,
                                             type,
                                             lineno)
        self.module = module
        self.pf_cname = pf_cname
        self.is_initmodule_function = is_initmodule_function == "True"
        self.locals = {}
        self.arguments = []
        self.step_into_functions = set()


# General purpose classes

class CythonBase(object):

    @default_selected_gdb_frame(err=False)
    def is_cython_function(self, frame):
        return frame.name() in self.cy.functions_by_cname

    @default_selected_gdb_frame(err=False)
    def is_python_function(self, frame):
        """
        Tells if a frame is associated with a Python function.
        If we can't read the Python frame information, don't regard it as such.
        """
        if frame.name() == 'PyEval_EvalFrameEx':
            pyframe = libpython.Frame(frame).get_pyop()
            return pyframe and not pyframe.is_optimized_out()
        return False

    @default_selected_gdb_frame()
    def get_c_function_name(self, frame):
        return frame.name()

    @default_selected_gdb_frame()
    def get_c_lineno(self, frame):
        return frame.find_sal().line

    @default_selected_gdb_frame()
    def get_cython_function(self, frame):
        TRACE(f'CythonBase.get_cython_function(): {frame.name()}', 3)
        result = self.cy.functions_by_cname.get(frame.name())
        if result is None:
            if frame.name() == 'raise':
                # Handling possible C-breakpoints, i.e. raise_(SIGTRAP)
                try:
                    arg_val = frame.read_var('sig')
                    _sig = int(arg_val.format_string(format="d"))
                    if _sig == 5:
                        TRACE(f'cybreakpoint: incode breakpoint triggered')
                        gdb.execute('cy up')
                        gdb.execute('cy list')
                        return None
                except:
                    if DEBUG_TRACE > 4:
                        breakpoint()
                    raise NoCythonFunctionInFrameError(frame.name())
            if DEBUG_TRACE > 4:
                breakpoint()
            raise NoCythonFunctionInFrameError()

        return result

    @default_selected_gdb_frame()
    def get_cython_lineno(self, frame):
        """
        Get the current Cython line number. Returns 0 if there is no
        correspondence between the C and Cython code.
        """
        TRACE(f'CythonBase.get_cython_lineno(): {frame.name()} \n>>>', 3)
        cyfunc = self.get_cython_function(frame)
        frame_line = self.get_c_lineno(frame)

        TRACE(f'CythonBase.get_cython_lineno(): cyfunc={cyfunc.name}, c_line={os.path.basename(cyfunc.module.c_filename)}:{frame_line}', 3)

        fn_and_line_no = cyfunc.module.lineno_c2cy.get(frame_line, None)
        if fn_and_line_no is None:
            # Debug
            TRACE(f'get_cython_lineno: Cython line not found: {cyfunc.name}:{frame_line}', 1)
            return (cyfunc.module.c_filename, frame_line)

        TRACE(f'CythonBase.get_cython_lineno(): fn_and_line_no=({fn_and_line_no})', 3)
        TRACE(f'CythonBase.get_cython_lineno(): \n<<<<', 3)
        return fn_and_line_no

    @default_selected_gdb_frame()
    def get_source_desc(self, frame):

        frame_name = frame.name()
        cython_frame = frame
        TRACE(f'CythonBase.get_source_desc() - frame: `{frame_name}`', 2)
        if frame_name.startswith('__pyx_pf_'):
            # For `def` functions Cython generates 2 types of functions:
            #  __pyx_pf_8examples_16cy_memory_unsafe_2hello  (which is typically in current frame)
            #  __pyx_pw_8examples_16cy_memory_unsafe_3hello  (which registered in debug xml tree as c_func)
            # Check for possible frame wrapper
            if not self.is_cython_function(frame):
                older_frame = gdb.selected_frame().older()
                older_frame_name = older_frame.name()
                # Possibly a wrapper of the same function
                if older_frame_name.startswith('__pyx_pw_') and self.is_cython_function(older_frame):
                    cython_frame = older_frame

        filename = lineno = lexer = None
        if self.is_cython_function(cython_frame):
            TRACE(f'CythonBase.get_source_desc(): is_cython_function', 2)
            filename = self.get_cython_function(frame).module.filename
            filename_and_lineno = self.get_cython_lineno(frame)
            #print(f'get_cython_lineno: {filename_and_lineno}')
            if filename_and_lineno[0].endswith('.c'):
                # Cython code is not mapped, because probably calling internal MACROS
                TRACE(f'CythonBase.get_source_desc(): Got macro call: its safe to do `cy next`', 2)
                filename = filename_and_lineno[0]
                lineno = filename_and_lineno[1]
                if pygments:
                    lexer = pygments.lexers.CLexer(stripall=False)
            else:
                assert filename == filename_and_lineno[0]
                lineno = filename_and_lineno[1]
                if pygments:
                    lexer = pygments.lexers.CythonLexer(stripall=False)
        elif self.is_python_function(frame):
            TRACE(f'CythonBase.get_source_desc(): is_python_function', 2)
            pyframeobject = libpython.Frame(frame).get_pyop()

            if not pyframeobject:
                raise gdb.GdbError(
                            'Unable to read information on python frame')

            filename = pyframeobject.filename()
            lineno = pyframeobject.current_line_num()

            if pygments:
                lexer = pygments.lexers.PythonLexer(stripall=False)
        else:
            TRACE(f'CythonBase.get_source_desc(): is_C_function', 2)
            TRACE(f'CythonBase.get_source_desc(): Available cython func: {self.cy.functions_by_cname.keys()}', 2)
            if DEBUG_TRACE > 4:
                breakpoint()
            filename, lexer, lineno = self.get_c_lexer(frame)

        return SourceFileDescriptor(filename, lexer), lineno

    def get_c_lexer(self, frame):
        lexer = None
        symbol_and_line_obj = frame.find_sal()
        if not symbol_and_line_obj or not symbol_and_line_obj.symtab:
            filename = None
            lineno = 0
        else:
            filename = symbol_and_line_obj.symtab.fullname()
            lineno = symbol_and_line_obj.line
            if pygments:
                lexer = pygments.lexers.CLexer(stripall=False)
        return filename, lexer, lineno

    @default_selected_gdb_frame()
    def get_source_line(self, frame):
        TRACE(f'libcython: get_source_line frame:{frame.name()}', 3)
        source_desc, lineno = self.get_source_desc()
        return source_desc.get_source(lineno)

    @default_selected_gdb_frame()
    def is_relevant_function(self, frame):
        """
        returns whether we care about a frame on the user-level when debugging
        Cython code
        """
        TRACE('libcython: is_relevant_function >>>', 3)
        name = frame.name()
        older_frame = frame.older()
        if self.is_cython_function(frame) or self.is_python_function(frame):

            if not self._is_relevant_c_line(frame):
                TRACE(f'is_relevant_function: {frame.name()} -> but irrelevant C-line (probably MACRO)')
                return True #False
            else:
                #print(f'is_relevant_function: {frame.name()}')
                return True
        elif older_frame and self.is_cython_function(older_frame):
            # check for direct C function call from a Cython function
            cython_func = self.get_cython_function(older_frame)
            is_relevant = name in cython_func.step_into_functions
            if is_relevant:
                is_relevant = self._is_relevant_c_line(frame)
            return is_relevant
        else:
            if frame.name() == 'raise' or frame.name() == '__GI_raise':
                # Handling possible C-breakpoints, i.e. raise_(SIGTRAP) or assert/abort
                try:
                    arg_val = frame.read_var('sig')
                    _sig = int(arg_val.format_string(format="d"))
                    if _sig == 5 or _sig == 6:
                        TRACE(f'libcython: is_relevant_function breakpoint/assert/abort triggered', 3)
                        gdb.execute('cy up')
                        gdb.execute('cy list')
                        return False
                except Exception as exc:
                    TRACE(f'libcython: is_relevant_function -- function looks like raise/breakpoint/assert, but failed with {repr(exc)}', 1)
                    if DEBUG_TRACE > 4:
                        breakpoint()

        return False

    def _is_relevant_c_line(self, frame):
        is_relevant = True

        cython_func = self.get_cython_function(frame)
        if cython_func is None:
            return False
        # Sometimes in weird case Cython calls C_MACROS which are out of normal source range
        #  make debugger to ignore them
        #  for i in range(buf_count):
        symbol_and_line_obj = frame.find_sal()
        if not symbol_and_line_obj or not symbol_and_line_obj.symtab:
            lineno = None
        else:
            lineno = symbol_and_line_obj.line
        if lineno is None or \
            lineno < cython_func.module.min_relevant_line_no or \
            lineno > cython_func.module.max_relevant_line_no:
            is_relevant = False
        return is_relevant

    @default_selected_gdb_frame(err=False)
    def print_stackframe(self, frame, index, is_c=False):
        """
        Print a C, Cython or Python stack frame and the line of source code
        if available.
        """
        TRACE('print_stackframe>>>', 4)
        # do this to prevent the require_cython_frame decorator from
        # raising GdbError when calling self.cy.cy_cvalue.invoke()
        selected_frame = gdb.selected_frame()
        frame.select()

        try:
            source_desc, lineno = self.get_source_desc(frame)
        except NoFunctionNameInFrameError:
            print('#%-2d Unknown Frame (compile with -g)' % index)
            return

        if not is_c and self.is_python_function(frame):
            pyframe = libpython.Frame(frame).get_pyop()
            if pyframe is None or pyframe.is_optimized_out():
                # print this python function as a C function
                return self.print_stackframe(frame, index, is_c=True)

            func_name = pyframe.co_name
            func_cname = 'PyEval_EvalFrameEx'
            func_args = []
        elif self.is_cython_function(frame):
            cyfunc = self.get_cython_function(frame)
            f = lambda arg: self.cy.cy_cvalue.invoke(arg, frame=frame)

            func_name = cyfunc.name
            func_cname = cyfunc.cname
            func_args = []  # [(arg, f(arg)) for arg in cyfunc.arguments]
        else:
            source_desc, lineno = self.get_source_desc(frame)
            func_name = frame.name()
            func_cname = func_name
            func_args = []

        try:
            gdb_value = gdb.parse_and_eval(func_cname)
        except RuntimeError:
            func_address = 0
        else:
            func_address = gdb_value.address
            if not isinstance(func_address, int):
                # Seriously? Why is the address not an int?
                if not isinstance(func_address, (str, bytes)):
                    func_address = str(func_address)
                func_address = int(func_address.split()[0], 0)

        a = ', '.join('%s=%s' % (name, val) for name, val in func_args)
        sys.stdout.write('#%-2d 0x%016x in %s(%s)' % (index, func_address, func_name, a))

        if source_desc.filename is not None:
            sys.stdout.write(' at %s:%s' % (source_desc.filename, lineno))

        sys.stdout.write('\n')

        try:
            sys.stdout.write('    ' + source_desc.get_source(lineno) + '\n')
        except gdb.GdbError:
            pass

        selected_frame.select()
        TRACE('<<<print_stackframe', 4)

    def get_remote_cython_globals_dict(self):
        m = gdb.parse_and_eval('__pyx_m')

        try:
            PyModuleObject = gdb.lookup_type('PyModuleObject')
        except RuntimeError:
            raise gdb.GdbError(textwrap.dedent("""\
                Unable to lookup type PyModuleObject, did you compile python
                with debugging support (-g)?"""))

        m = m.cast(PyModuleObject.pointer())
        return m['md_dict']


    def get_cython_globals_dict(self):
        """
        Get the Cython globals dict where the remote names are turned into
        local strings.
        """
        remote_dict = self.get_remote_cython_globals_dict()
        pyobject_dict = libpython.PyObjectPtr.from_pyobject_ptr(remote_dict)

        result = {}
        seen = set()
        for k, v in pyobject_dict.iteritems():
            result[k.proxyval(seen)] = v

        return result

    def print_gdb_value(self, name, value, max_name_length=None, prefix=''):
        if isinstance(value, str) or libpython.pretty_printer_lookup(value):
            typename = ''
        else:
            typename = '(%s) ' % (value.type,)

        if max_name_length is None:
            print('%s%s = %s%s' % (prefix, name, typename, value))
        else:
            print('%s%-*s = %s%s' % (prefix, max_name_length, name, typename, value))

    def is_initialized(self, cython_func, local_name):
        if local_name not in cython_func.locals:
            return False

        cyvar = cython_func.locals[local_name]
        cur_lineno = self.get_cython_lineno()[1]

        if '->' in cyvar.cname:
            # Closed over free variable
            if cur_lineno > cython_func.lineno:
                if cyvar.type == PythonObject:
                    return int(gdb.parse_and_eval(cyvar.cname))
                return True
            return False

        return cur_lineno > cyvar.lineno


class SourceFileDescriptor(object):
    def __init__(self, filename, lexer, formatter=None):
        self.filename = filename
        self.lexer = lexer
        self.formatter = formatter

    def valid(self):
        return self.filename is not None

    def lex(self, code):
        if pygments and self.lexer and parameters.colorize_code:
            bg = parameters.terminal_background.value
            if self.formatter is None:
                formatter = pygments.formatters.TerminalFormatter(bg=bg)
            else:
                formatter = self.formatter

            return pygments.highlight(code, self.lexer, formatter)

        return code

    def _get_source(self, start, stop, lex_source, mark_line, lex_entire):
        if not os.path.exists(self.filename):
            raise FileNotFoundError(self.filename)

        with open(self.filename) as f:
            # to provide "correct" colouring, the entire code needs to be
            # lexed. However, this makes a lot of things terribly slow, so
            # we decide not to. Besides, it's unlikely to matter.

            if lex_source and lex_entire:
                f = self.lex(f.read()).splitlines()

            slice = itertools.islice(f, start - 1, stop - 1)

            for idx, line in enumerate(slice):
                if start + idx == mark_line:
                    prefix = '>'
                else:
                    prefix = ' '

                if lex_source and not lex_entire:
                    line = self.lex(line)

                yield '%s %4d    %s' % (prefix, start + idx, line.rstrip())

    def get_source(self, start, stop=None, lex_source=True, mark_line=0,
                   lex_entire=False):
        exc = gdb.GdbError('Unable to retrieve source code')

        if not self.filename:
            raise exc

        start = max(start, 1)
        if stop is None:
            stop = start + 1

        try:
            return '\n'.join(
                self._get_source(start, stop, lex_source, mark_line, lex_entire))
        except IOError:
            raise exc


# Errors

class CyGDBError(gdb.GdbError):
    """
    Base class for Cython-command related errors
    """

    def __init__(self, *args):
        args = args or (self.msg,)
        super(CyGDBError, self).__init__(*args)


class NoCythonFunctionInFrameError(CyGDBError):
    """
    raised when the user requests the current cython function, which is
    unavailable
    """
    msg = "Current function is a function cygdb doesn't know about"


class NoFunctionNameInFrameError(NoCythonFunctionInFrameError):
    """
    raised when the name of the C function could not be determined
    in the current C stack frame
    """
    msg = ('C function name could not be determined in the current C stack '
           'frame')


# Parameters

class CythonParameter(gdb.Parameter):
    """
    Base class for cython parameters
    """

    def __init__(self, name, command_class, parameter_class, default=None):
        self.show_doc = self.set_doc = self.__class__.__doc__
        super(CythonParameter, self).__init__(name, command_class,
                                              parameter_class)
        if default is not None:
            self.value = default

    def __bool__(self):
        return bool(self.value)

    __nonzero__ = __bool__  # Python 2



class CompleteUnqualifiedFunctionNames(CythonParameter):
    """
    Have 'cy break' complete unqualified function or method names.
    """


class ColorizeSourceCode(CythonParameter):
    """
    Tell cygdb whether to colorize source code.
    """


class TerminalBackground(CythonParameter):
    """
    Tell cygdb about the user's terminal background (light or dark).
    """


class CythonParameters(object):
    """
    Simple container class that might get more functionality in the distant
    future (mostly to remind us that we're dealing with parameters).
    """

    def __init__(self):
        self.complete_unqualified = CompleteUnqualifiedFunctionNames(
            'cy_complete_unqualified',
            gdb.COMMAND_BREAKPOINTS,
            gdb.PARAM_BOOLEAN,
            True)
        self.colorize_code = ColorizeSourceCode(
            'cy_colorize_code',
            gdb.COMMAND_FILES,
            gdb.PARAM_BOOLEAN,
            True)
        self.terminal_background = TerminalBackground(
            'cy_terminal_background_color',
            gdb.COMMAND_FILES,
            gdb.PARAM_STRING,
            "dark")

parameters = CythonParameters()


# Commands

class CythonCommand(gdb.Command, CythonBase):
    """
    Base class for Cython commands
    """

    command_class = gdb.COMMAND_NONE

    @classmethod
    def _register(cls, clsname, args, kwargs):
        if not hasattr(cls, 'completer_class'):
            return cls(clsname, cls.command_class, *args, **kwargs)
        else:
            return cls(clsname, cls.command_class, cls.completer_class,
                       *args, **kwargs)

    @classmethod
    def register(cls, *args, **kwargs):
        alias = getattr(cls, 'alias', None)
        if alias:
            return cls._register(alias, args, kwargs)
        else:
            return cls._register(cls.name, args, kwargs)

class CyCy(CythonCommand):
    """
    Invoke a Cython command. Available commands are:

        cy import
        cy break
        cy step
        cy next
        cy run
        cy cont
        cy finish
        cy up
        cy down
        cy select
        cy bt / cy backtrace
        cy list
        cy print
        cy set
        cy locals
        cy globals
        cy exec
    """

    name = 'cy'
    command_class = gdb.COMMAND_NONE
    completer_class = gdb.COMPLETE_COMMAND

    def __init__(self, name, command_class, completer_class):
        # keep the signature 2.5 compatible (i.e. do not use f(*a, k=v)
        super(CythonCommand, self).__init__(name, command_class,
                                            completer_class, prefix=True)

        commands = dict(
            # GDB commands
            import_ = CyImport.register(),
            break_ = CyBreak.register(),
            step = CyStep.register(),
            s=CyStepA.register(),
            next = CyNext.register(),
            n=CyNextA.register(),
            run = CyRun.register(),
            cont = CyCont.register(),
            c=CyContA.register(),
            finish = CyFinish.register(),
            up = CyUp.register(),
            u=CyUpA.register(),
            down = CyDown.register(),
            d=CyDown.register(),
            select = CySelect.register(),
            bt = CyBacktrace.register(),
            list = CyList.register(),
            l=CyListA.register(),
            print_ = CyPrint.register(),
            p_=CyPrintA.register(),
            locals = CyLocals.register(),
            globals = CyGlobals.register(),
            exec_ = libpython.FixGdbCommand('cy exec', '-cy-exec'),
            _exec = CyExec.register(),
            set = CySet.register(),

            # GDB functions
            cy_cname = CyCName('cy_cname'),
            cy_cvalue = CyCValue('cy_cvalue'),
            cy_lineno = CyLine('cy_lineno'),
            cy_eval = CyEval('cy_eval'),
        )

        for command_name, command in commands.items():
            command.cy = self

            # TRACE(f'Adding command: {command_name}')
            # alias = getattr(command, 'alias', None)
            # if alias:
            #     assert alias.startswith('cy '), f'Alias must start with `cy `, got {alias}'
            #     alias_command = alias[3:]
            #     assert alias_command, f'Alias empty alias, got {alias}'
            #     assert alias_command not in commands, f'Conflicting alias name with existing commands {alias}'
            #     TRACE(f'Adding alias command: `cy {alias_command}` -> {command.__class__}')
            #     alias_class = command.__class__.register()
            #     print(f'alias_class={alias_class}')
            #     alias_class.cy = self
            #     setattr(self, alias_command, alias_class)

            setattr(self, command_name, command)

        self.cy = self

        # Cython module namespace
        self.cython_namespace = {}

        # maps (unique) qualified function names (e.g.
        # cythonmodule.ClassName.method_name) to the CythonFunction object
        self.functions_by_qualified_name = {}

        # unique cnames of Cython functions
        self.functions_by_cname = {}

        # map function names like method_name to a list of all such
        # CythonFunction objects
        self.functions_by_name = collections.defaultdict(list)


class CyImport(CythonCommand):
    """
    Import debug information outputted by the Cython compiler
    Example: cy import FILE...
    """

    name = 'cy import'
    command_class = gdb.COMMAND_STATUS
    completer_class = gdb.COMPLETE_FILENAME

    @libpython.dont_suppress_errors
    def invoke(self, args, from_tty):
        TRACE(f'`cy import`: Adding file: {args}')
        if isinstance(args, BYTES):
            args = args.decode(_filesystemencoding)
        for arg in string_to_argv(args):
            try:
                f = open(arg)
            except OSError as e:
                raise gdb.GdbError('Unable to open file %r: %s' % (args, e.args[1]))

            t = etree.parse(f)

            for module in t.getroot():
                cython_module = CythonModule(**module.attrib)
                src_path = module.attrib['filename']
                c_src_path = module.attrib['c_filename']
                pw_func_map = get_cython_wrappers(c_src_path)
                TRACE(f'Module src: {src_path}', 3)
                TRACE(f'Module src .c: {c_src_path}', 3)
                TRACE(f'Module wrappers: {pw_func_map}', 3)
                self.cy.cython_namespace[cython_module.name] = cython_module

                for variable in module.find('Globals'):
                    d = variable.attrib
                    cython_module.globals[d['name']] = CythonVariable(**d)
                TRACE(f'`cy import`: Globals added: {len(cython_module.globals)}')

                for function in module.find('Functions'):
                    cython_function = CythonFunction(module=cython_module,
                                                     **function.attrib)

                    # update the global function mappings
                    name = cython_function.name
                    qname = cython_function.qualified_name

                    self.cy.functions_by_name[name].append(cython_function)
                    self.cy.functions_by_qualified_name[cython_function.qualified_name] = cython_function

                    # Map correct code with real C-implementation, exlclude Python wrapper functions!
                    TRACE(f'`cy import`: Function: {name}')
                    TRACE(f'`cy import`: \tQualName: {cython_function.qualified_name}')

                    if cython_function.cname in pw_func_map:
                        mapped_f = pw_func_map[cython_function.cname]
                        self.cy.functions_by_cname[mapped_f] = cython_function
                        TRACE(f'`cy import`: \tCName: {cython_function.cname} -> mapped to : {mapped_f}')
                    else:
                        self.cy.functions_by_cname[cython_function.cname] = cython_function
                        TRACE(f'`cy import`: \tCName: {cython_function.cname}')



                    d = cython_module.functions[qname] = cython_function

                    for local in function.find('Locals'):
                        d = local.attrib
                        cython_function.locals[d['name']] = CythonVariable(**d)

                    for step_into_func in function.find('StepIntoFunctions'):
                        d = step_into_func.attrib
                        cython_function.step_into_functions.add(d['name'])

                    cython_function.arguments.extend(
                        funcarg.tag for funcarg in function.find('Arguments'))

                TRACE(f'`cy import`: \tC source: {src_path}')

                for marker in module.find('LineNumberMapping'):
                    src_lineno = int(marker.attrib['cython_lineno'])
                    c_linenos = list(map(int, marker.attrib['c_linenos'].split()))
                    cython_module.lineno_cy2c[src_path, src_lineno] = min(c_linenos)
                    for c_lineno in c_linenos:
                        cython_module.lineno_c2cy[c_lineno] = (src_path, src_lineno)
                        cython_module.min_relevant_line_no = min(cython_module.min_relevant_line_no, c_lineno)
                        cython_module.max_relevant_line_no = max(cython_module.max_relevant_line_no, c_lineno)


class CyBreak(CythonCommand):
    """
    Set a breakpoint for Cython code using Cython qualified name notation, e.g.:

        cy break cython_modulename.ClassName.method_name...

    or normal notation:

        cy break function_or_method_name...

    or for a line number:

        cy break cython_module:lineno...

    Set a Python breakpoint:
        Break on any function or method named 'func' in module 'modname'

            cy break -p modname.func...

        Break on any function or method named 'func'

            cy break -p func...
    """

    name = 'cy break'
    command_class = gdb.COMMAND_BREAKPOINTS

    def _break_pyx(self, name):
        modulename, _, lineno = name.partition(':')
        lineno = int(lineno)
        if modulename:
            cython_module = self.cy.cython_namespace[modulename]
        else:
            cython_module = self.get_cython_function().module

        if (cython_module.filename, lineno) in cython_module.lineno_cy2c:
            c_lineno = cython_module.lineno_cy2c[cython_module.filename, lineno]
            breakpoint = '%s:%s' % (cython_module.c_filename, c_lineno)
            TRACE(f'`cy breakpoint`: {name} -> {breakpoint}')
            gdb.execute('break ' + breakpoint)
        else:
            TRACE(f'`cy breakpoint`: {cython_module.filename=}')
            TRACE(f'`cy breakpoint`: {cython_module.lineno_cy2c}')
            raise gdb.GdbError("Not a valid line number. "
                               "Does it contain actual code?")

    def _break_funcname(self, funcname):
        func = self.cy.functions_by_qualified_name.get(funcname)

        if func and func.is_initmodule_function:
            func = None

        break_funcs = [func]

        if not func:
            funcs = self.cy.functions_by_name.get(funcname) or []
            funcs = [f for f in funcs if not f.is_initmodule_function]

            if not funcs:
                gdb.execute('break ' + funcname)
                return

            if len(funcs) > 1:
                # multiple functions, let the user pick one
                print('There are multiple such functions:')
                for idx, func in enumerate(funcs):
                    print('%3d) %s' % (idx, func.qualified_name))

                while True:
                    try:
                        result = input(
                            "Select a function, press 'a' for all "
                            "functions or press 'q' or '^D' to quit: ")
                    except EOFError:
                        return
                    else:
                        if result.lower() == 'q':
                            return
                        elif result.lower() == 'a':
                            break_funcs = funcs
                            break
                        elif (result.isdigit() and
                                0 <= int(result) < len(funcs)):
                            break_funcs = [funcs[int(result)]]
                            break
                        else:
                            print('Not understood...')
            else:
                break_funcs = [funcs[0]]

        for func in break_funcs:
            gdb.execute('break %s' % func.cname)
            if func.pf_cname:
                gdb.execute('break %s' % func.pf_cname)

    @libpython.dont_suppress_errors
    def invoke(self, function_names, from_tty):
        if isinstance(function_names, BYTES):
            function_names = function_names.decode(_filesystemencoding)
        argv = string_to_argv(function_names)
        if function_names.startswith('-p'):
            argv = argv[1:]
            python_breakpoints = True
        else:
            python_breakpoints = False

        for funcname in argv:
            if python_breakpoints:
                gdb.execute('py-break %s' % funcname)
            elif ':' in funcname:
                self._break_pyx(funcname)
            else:
                self._break_funcname(funcname)

    @libpython.dont_suppress_errors
    def complete(self, text, word):
        # Filter init-module functions (breakpoints can be set using
        # modulename:linenumber).
        names =  [n for n, L in self.cy.functions_by_name.items()
                  if any(not f.is_initmodule_function for f in L)]
        qnames = [n for n, f in self.cy.functions_by_qualified_name.items()
                  if not f.is_initmodule_function]

        if parameters.complete_unqualified:
            all_names = itertools.chain(qnames, names)
        else:
            all_names = qnames

        words = text.strip().split()
        if not words or '.' not in words[-1]:
            # complete unqualified
            seen = set(text[:-len(word)].split())
            return [n for n in all_names
                          if n.startswith(word) and n not in seen]

        # complete qualified name
        lastword = words[-1]
        compl = [n for n in qnames if n.startswith(lastword)]

        if len(lastword) > len(word):
            # readline sees something (e.g. a '.') as a word boundary, so don't
            # "recomplete" this prefix
            strip_prefix_length = len(lastword) - len(word)
            compl = [n[strip_prefix_length:] for n in compl]

        return compl


class CythonInfo(CythonBase, libpython.PythonInfo):
    """
    Implementation of the interface dictated by libpython.LanguageInfo.
    """

    def lineno(self, frame):
        TRACE(f'CythonInfo.lineno: {frame.name()}', 3)
        # Take care of the Python and Cython levels. We need to care for both
        # as we can't simply dispatch to 'py-step', since that would work for
        # stepping through Python code, but it would not step back into Cython-
        # related code. The C level should be dispatched to the 'step' command.
        if self.is_cython_function(frame):
            fn_and_lineno = self.get_cython_lineno(frame)
            if isinstance(fn_and_lineno, int):
                return fn_and_lineno
            else:
                if fn_and_lineno[0].endswith('.c'):
                    if not self._is_relevant_c_line(frame):
                        return None
                return fn_and_lineno[1]
        return super(CythonInfo, self).lineno(frame)

    def get_source_line(self, frame):
        TRACE(f'CythonInfo.get_source_line: {frame.name()}', 3)
        try:
            line = super(CythonInfo, self).get_source_line(frame)
        except gdb.GdbError:
            return None
        else:
            return line.strip() or None

    def exc_info(self, frame):
        if self.is_python_function:
            return super(CythonInfo, self).exc_info(frame)

    def runtime_break_functions(self):
        if self.is_cython_function():
            return self.get_cython_function().step_into_functions
        return ()

    def static_break_functions(self):
        result = ['PyEval_EvalFrameEx']
        result.extend(self.cy.functions_by_cname)
        return result


class CythonExecutionControlCommand(CythonCommand,
                                    libpython.ExecutionControlCommandBase):

    @classmethod
    def register(cls):
        return cls(cls.name, cython_info)


class CyStep(CythonExecutionControlCommand, libpython.PythonStepperMixin):
    "Step through Cython, Python or C code."

    name = 'cy -step'
    #alias = 'cy s'
    stepinto = True

    @libpython.dont_suppress_errors
    def invoke(self, args, from_tty):
        TRACE('`cy step`', 2)
        if self.is_python_function():
            TRACE('`cy step` python_step', 2)
            self.python_step(self.stepinto)
        elif not self.is_cython_function():
            if self.stepinto:
                command = 'step'
            else:
                command = 'next'

            TRACE('`cy step` C step', 2)
            self.finish_executing(gdb.execute(command, to_string=True))
        else:
            TRACE('`cy step` cython step', 2)
            # Uses special stepover command that silence the C code output
            # Requres the following in command file
            # """
            # # This disables c-line output when `cy next`
            #     define next-silent
            #         set logging file /dev/null
            #         set logging redirect on
            #         set logging on
            #         next
            #         set logging off
            #         display
            #     end
            # """
            self.step(stepinto=self.stepinto)




class CyNext(CyStep):
    "Step-over Cython, Python or C code."

    name = 'cy -next'
    stepinto = False




class CyRun(CythonExecutionControlCommand):
    """
    Run a Cython program. This is like the 'run' command, except that it
    displays Cython or Python source lines as well
    """

    name = 'cy run'
    #alias = 'cy r'

    invoke = libpython.dont_suppress_errors(CythonExecutionControlCommand.run)



class CyCont(CythonExecutionControlCommand):
    """
    Continue a Cython program. This is like the 'run' command, except that it
    displays Cython or Python source lines as well.
    """

    name = 'cy cont'
    #alias = 'cy c'
    invoke = libpython.dont_suppress_errors(CythonExecutionControlCommand.cont)




class CyFinish(CythonExecutionControlCommand):
    """
    Execute until the function returns.
    """
    name = 'cy finish'

    invoke = libpython.dont_suppress_errors(CythonExecutionControlCommand.finish)


class CyUp(CythonCommand):
    """
    Go up a Cython, Python or relevant C frame.
    """
    name = 'cy up'
    #alias = 'cy u'
    _command = 'up'

    @libpython.dont_suppress_errors
    def invoke(self, *args):
        try:
            gdb.execute(self._command, to_string=True)
            while not self.is_relevant_function(gdb.selected_frame()):
                gdb.execute(self._command, to_string=True)
        except RuntimeError as e:
            raise gdb.GdbError(*e.args)

        frame = gdb.selected_frame()
        index = 0
        while frame:
            frame = frame.older()
            index += 1

        self.print_stackframe(index=index - 1)


class CyDown(CyUp):
    """
    Go down a Cython, Python or relevant C frame.
    """

    name = 'cy down'
    #alias = 'cy d'
    _command = 'down'


class CySelect(CythonCommand):
    """
    Select a frame. Use frame numbers as listed in `cy backtrace`.
    This command is useful because `cy backtrace` prints a reversed backtrace.
    """

    name = 'cy select'

    @libpython.dont_suppress_errors
    def invoke(self, stackno, from_tty):
        try:
            stackno = int(stackno)
        except ValueError:
            raise gdb.GdbError("Not a valid number: %r" % (stackno,))

        frame = gdb.selected_frame()
        while frame.newer():
            frame = frame.newer()

        stackdepth = libpython.stackdepth(frame)

        try:
            gdb.execute('select %d' % (stackdepth - stackno - 1,))
        except RuntimeError as e:
            raise gdb.GdbError(*e.args)


class CyBacktrace(CythonCommand):
    'Print the Cython stack'

    name = 'cy bt'
    #alias = 'cy backtrace'
    command_class = gdb.COMMAND_STACK
    completer_class = gdb.COMPLETE_NONE

    @libpython.dont_suppress_errors
    @require_running_program
    def invoke(self, args, from_tty):
        # get the first frame
        frame = gdb.selected_frame()
        while frame.older():
            frame = frame.older()

        print_all = args == '-a'

        index = 0
        while frame:
            try:
                is_relevant = self.is_relevant_function(frame)
            except CyGDBError:
                is_relevant = False

            if print_all or is_relevant:
                self.print_stackframe(frame, index)

            index += 1
            frame = frame.newer()


class CyList(CythonCommand):
    """
    List Cython source code. To disable to customize colouring see the cy_*
    parameters.
    """

    name = 'cy list'
    #alias = 'cy l'
    command_class = gdb.COMMAND_FILES
    completer_class = gdb.COMPLETE_NONE

    @libpython.dont_suppress_errors
    # @dispatch_on_frame(c_command='list')
    def invoke(self, _, from_tty):
        TRACE('`cy list`', 1)
        sd, lineno = self.get_source_desc()

        source = sd.get_source(lineno - 5, lineno + 5, mark_line=lineno,
                               lex_entire=True)
        print(source)


class CyPrint(CythonCommand):
    """
    Print a Cython variable using 'cy-print x' or 'cy-print module.function.x'
    """

    name = 'cy print'
    #alias = 'cy p'
    command_class = gdb.COMMAND_DATA

    @libpython.dont_suppress_errors
    def invoke(self, name, from_tty):
        global_python_dict = self.get_cython_globals_dict()
        module_globals = self.get_cython_function().module.globals

        if name in global_python_dict:
            value = global_python_dict[name].get_truncated_repr(libpython.MAX_OUTPUT_LEN)
            print('%s = %s' % (name, value))
            #This also would work, but beacause the output of cy exec is not captured in gdb.execute, TestPrint would fail
            #self.cy.exec_.invoke("print('"+name+"','=', type(" + name + "), "+name+", flush=True )", from_tty)
        elif name in module_globals:
            cname = module_globals[name].cname
            try:
                value = gdb.parse_and_eval(cname)
            except RuntimeError:
                print("unable to get value of %s" % name)
            else:
                if not value.is_optimized_out:
                    self.print_gdb_value(name, value)
                else:
                    print("%s is optimized out" % name)
        elif self.is_python_function():
            return gdb.execute('py-print ' + name)
        elif self.is_cython_function():
            value = self.cy.cy_cvalue.invoke(name.lstrip('*'))
            for c in name:
                if c == '*':
                    value = value.dereference()
                else:
                    break

            self.print_gdb_value(name, value)
        else:
            gdb.execute('print ' + name)

    def complete(self):
        if self.is_cython_function():
            f = self.get_cython_function()
            return list(itertools.chain(f.locals, f.globals))
        else:
            return []


sortkey = lambda item: item[0].lower()


class CyLocals(CythonCommand):
    """
    List the locals from the current Cython frame.
    """

    name = 'cy locals'
    command_class = gdb.COMMAND_STACK
    completer_class = gdb.COMPLETE_NONE

    @libpython.dont_suppress_errors
    @dispatch_on_frame(c_command='info locals', python_command='py-locals')
    def invoke(self, args, from_tty):
        cython_function = self.get_cython_function()

        if cython_function.is_initmodule_function:
            self.cy.globals.invoke(args, from_tty)
            return

        local_cython_vars = cython_function.locals
        if local_cython_vars:
            max_name_length = len(max(local_cython_vars, key=len))
            for name, cyvar in sorted(local_cython_vars.items(), key=sortkey):
                if self.is_initialized(self.get_cython_function(), cyvar.name):
                    try:
                        value = gdb.parse_and_eval(cyvar.cname)
                        if not value.is_optimized_out:
                            self.print_gdb_value(cyvar.name, value,
                                                 max_name_length, '')
                    except Exception as exc:
                        self.print_gdb_value(cyvar.name, "Err: " + str(exc),
                                             max_name_length, '')
        else:
            print('No locals')


class CyGlobals(CyLocals):
    """
    List the globals from the current Cython module.
    """

    name = 'cy globals'
    command_class = gdb.COMMAND_STACK
    completer_class = gdb.COMPLETE_NONE

    @libpython.dont_suppress_errors
    @dispatch_on_frame(c_command='info variables', python_command='py-globals')
    def invoke(self, args, from_tty):
        global_python_dict = self.get_cython_globals_dict()
        module_globals = self.get_cython_function().module.globals

        max_globals_len = 0
        max_globals_dict_len = 0
        if module_globals:
            max_globals_len = len(max(module_globals, key=len))
        if global_python_dict:
            max_globals_dict_len = len(max(global_python_dict))

        max_name_length = max(max_globals_len, max_globals_dict_len)

        seen = set()
        print('Python globals:')

        for k, v in sorted(global_python_dict.items(), key=sortkey):
            v = v.get_truncated_repr(libpython.MAX_OUTPUT_LEN)
            seen.add(k)
            print('    %-*s = %s' % (max_name_length, k, v))

        print('C globals:')
        for name, cyvar in sorted(module_globals.items(), key=sortkey):
            if name not in seen:
                try:
                    value = gdb.parse_and_eval(cyvar.cname)
                except RuntimeError:
                    pass
                else:
                    if not value.is_optimized_out:
                        self.print_gdb_value(cyvar.name, value,
                                             max_name_length, '    ')


class EvaluateOrExecuteCodeMixin(object):
    """
    Evaluate or execute Python code in a Cython or Python frame. The 'evalcode'
    method evaluations Python code, prints a traceback if an exception went
    uncaught, and returns any return value as a gdb.Value (NULL on exception).
    """

    def _fill_locals_dict(self, executor, local_dict_pointer):
        "Fill a remotely allocated dict with values from the Cython C stack"
        cython_func = self.get_cython_function()

        for name, cyvar in cython_func.locals.items():
            if (cyvar.type == PythonObject
                    and self.is_initialized(cython_func, name)):

                try:
                    val = gdb.parse_and_eval(cyvar.cname)
                except RuntimeError:
                    continue
                else:
                    if val.is_optimized_out:
                        continue

                pystringp = executor.alloc_pystring(name)
                code = '''
                    (PyObject *) PyDict_SetItem(
                        (PyObject *) %d,
                        (PyObject *) %d,
                        (PyObject *) %s)
                ''' % (local_dict_pointer, pystringp, cyvar.cname)

                try:
                    if gdb.parse_and_eval(code) < 0:
                        gdb.parse_and_eval('PyErr_Print()')
                        raise gdb.GdbError("Unable to execute Python code.")
                finally:
                    # PyDict_SetItem doesn't steal our reference
                    executor.xdecref(pystringp)

    def _find_first_cython_or_python_frame(self):
        frame = gdb.selected_frame()
        while frame:
            if (self.is_cython_function(frame)
                    or self.is_python_function(frame)):
                frame.select()
                return frame

            frame = frame.older()

        raise gdb.GdbError("There is no Cython or Python frame on the stack.")

    def _evalcode_cython(self, executor, code, input_type):
        with libpython.FetchAndRestoreError():
            # get the dict of Cython globals and construct a dict in the
            # inferior with Cython locals
            global_dict = gdb.parse_and_eval(
                '(PyObject *) PyModule_GetDict(__pyx_m)')
            local_dict = gdb.parse_and_eval('(PyObject *) PyDict_New()')

            try:
                self._fill_locals_dict(executor,
                                       libpython.pointervalue(local_dict))
                result = executor.evalcode(code, input_type, global_dict,
                                           local_dict)
            finally:
                executor.xdecref(libpython.pointervalue(local_dict))

        return result

    def evalcode(self, code, input_type):
        """
        Evaluate `code` in a Python or Cython stack frame using the given
        `input_type`.
        """
        frame = self._find_first_cython_or_python_frame()
        executor = libpython.PythonCodeExecutor()
        if self.is_python_function(frame):
            return libpython._evalcode_python(executor, code, input_type)
        return self._evalcode_cython(executor, code, input_type)


class CyExec(CythonCommand, libpython.PyExec, EvaluateOrExecuteCodeMixin):
    """
    Execute Python code in the nearest Python or Cython frame.
    """

    name = '-cy-exec'
    command_class = gdb.COMMAND_STACK
    completer_class = gdb.COMPLETE_NONE

    @libpython.dont_suppress_errors
    def invoke(self, expr, from_tty):
        expr, input_type = self.readcode(expr)
        executor = libpython.PythonCodeExecutor()
        executor.xdecref(self.evalcode(expr, executor.Py_file_input))


class CySet(CythonCommand):
    """
    Set a Cython variable to a certain value

        cy set my_cython_c_variable = 10
        cy set my_cython_py_variable = $cy_eval("{'doner': 'kebab'}")

    This is equivalent to

        set $cy_value("my_cython_variable") = 10
    """

    name = 'cy set'
    command_class = gdb.COMMAND_DATA
    completer_class = gdb.COMPLETE_NONE

    @libpython.dont_suppress_errors
    @require_cython_frame
    def invoke(self, expr, from_tty):
        name_and_expr = expr.split('=', 1)
        if len(name_and_expr) != 2:
            raise gdb.GdbError("Invalid expression. Use 'cy set var = expr'.")

        varname, expr = name_and_expr
        cname = self.cy.cy_cname.invoke(varname.strip())
        TRACE(f'`cy set`: varname={varname} cname={cname} expr={expr}')
        gdb.execute("set %s = %s" % (cname, expr))


# Functions

class CyCName(gdb.Function, CythonBase):
    """
    Get the C name of a Cython variable in the current context.
    Examples:

        print $cy_cname("function")
        print $cy_cname("Class.method")
        print $cy_cname("module.function")
    """

    @libpython.dont_suppress_errors
    @require_cython_frame
    @gdb_function_value_to_unicode
    def invoke(self, cyname, frame=None):
        frame = frame or gdb.selected_frame()
        cname = None

        if self.is_cython_function(frame):
            cython_function = self.get_cython_function(frame)
            if cyname in cython_function.locals:
                cname = cython_function.locals[cyname].cname
            elif cyname in cython_function.module.globals:
                cname = cython_function.module.globals[cyname].cname
            else:
                qname = '%s.%s' % (cython_function.module.name, cyname)
                if qname in cython_function.module.functions:
                    cname = cython_function.module.functions[qname].cname

        if not cname:
            cname = self.cy.functions_by_qualified_name.get(cyname)

        if not cname:
            raise gdb.GdbError('No such Cython variable: %s' % cyname)

        return cname


class CyCValue(CyCName):
    """
    Get the value of a Cython variable.
    """

    #@libpython.dont_suppress_errors
    @require_cython_frame
    @gdb_function_value_to_unicode
    def invoke(self, cyname, frame=None):
        globals_dict = self.get_cython_globals_dict()
        cython_function = self.get_cython_function(frame)

        if self.is_initialized(cython_function, cyname):
            cname = super(CyCValue, self).invoke(cyname, frame=frame)
            return gdb.parse_and_eval(cname)
        elif cyname in globals_dict:
            return globals_dict[cyname]._gdbval
        else:
            raise gdb.GdbError("Variable %s is not initialized." % cyname)


class CyLine(gdb.Function, CythonBase):
    """
    Get the current Cython line.
    """

    @libpython.dont_suppress_errors
    @require_cython_frame
    def invoke(self):
        return self.get_cython_lineno()[1]


class CyEval(gdb.Function, CythonBase, EvaluateOrExecuteCodeMixin):
    """
    Evaluate Python code in the nearest Python or Cython frame and return
    """

    @libpython.dont_suppress_errors
    @gdb_function_value_to_unicode
    def invoke(self, python_expression):
        input_type = libpython.PythonCodeExecutor.Py_eval_input
        return self.evalcode(python_expression, input_type)


#
# One letter aliases
#
class CyContA(CyCont):
    name = 'cy c'


class CyStepA(CyStep):
    name = 'cy s'


class CyNextA(CyNext):
    name = 'cy -n'

class CyBreakA(CyBreak):
    name = 'cy b'

class CyUpA(CyUp):
    name = 'cy u'

class CyDnA(CyDown):
    name = 'cy d'

class CyListA(CyList):
    name = 'cy l'

class CyPrintA(CyPrint):
    name = 'cy p'


cython_info = CythonInfo()
cy = CyCy.register()
cython_info.cy = cy


def register_defines():
    libpython.source_gdb_script(textwrap.dedent("""\
        define cy step
        cy -step
        end

        define cy next
        cy -next
        end

        document cy step
        %s
        end

        document cy next
        %s
        end
    """) % (CyStep.__doc__, CyNext.__doc__))

register_defines()
