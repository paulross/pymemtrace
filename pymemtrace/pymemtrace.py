# -*- coding: utf-8 -*-

"""Main module."""
import argparse
# import array
# import bisect
import collections
import inspect
import logging
# import os
import re
import sys
import time

import psutil

try:
    from pymemtrace.plot import PlotMemTrace
except ImportError:
    from plot import PlotMemTrace
try:
    from pymemtrace import data
except ImportError:
    import data
    
class MemTrace:
    """
    Keeps track of overall memory usage at each function entry and exit point.
    """
    RE_TEMPORARY_FILE = re.compile(r'<(.+)>')
    FALSE_FUNCTION_NAMES = set(['<dictcomp>', '<genexpr>', '<listcomp>', '<module>', '<setcomp>'])
    TRACE_FUNCTION_GET = sys.getprofile
    TRACE_FUNCTION_SET = sys.setprofile
    TRACE_EVENTS = False
    def __init__(self):
        self.pid = psutil.Process()
        self.function_encoder = data.FunctionEncoder()
        # Wraps a ist of FunctionCallTree objects.
        self.function_tree_seq = data.FunctionCallTreeSequence()
        # Event number, for the curious.
        self.eventno = 0
        # Event counters for different events, for the curious.
        self.event_counter = collections.Counter()
        # Allow re-entrancy with sys.settrace(function)
        self._trace_fn_stack = []
        # Created by finalise() as CallReturnData objects.
        self.data_final = None
        # These are maintained dynamically as a list of fields but then
        # converted to a CallReturnData in finalise()
        self.data_min = {f : None for f in data.CallReturnData._fields}
        self.data_max = {f : None for f in data.CallReturnData._fields}
        # Create initial and final conditions
        # NOTE: self.data_initial and self.data_final are obtained by polling
        # the OS.
        # self.data_min/self.data_max are min/max seen by add_data_point() and
        # these will not be the same, particularly if synthetic call/return data
        # is being injected with add_data_point().
        self.data_initial = self.create_data_point()

    def decode_function_id(self, function_id):
        """
        Given a function ID as an int this returns a named tuple::
        
            FunctionLocation(filename, function, lineno)
        
        Will raise a KeyError if the ``function_id`` is unknown.
        """
        return self.function_encoder.decode(function_id)

    def _update_min_max_dicts(self, field, value):
        """
        Updates the pair of dicts ``{field : value, ...}`` with the
        minimum and maximum value for the field.
        """
        assert field in self.data_min
        assert field in self.data_max
        if self.data_min[field] is None:
            self.data_min[field] = value
        else:
            self.data_min[field] = min([value, self.data_min[field]])
        if self.data_max[field] is None:
            self.data_max[field] = value
        else:
            self.data_max[field] = max([value, self.data_max[field]])

    def memory(self):
        """
        Returns our estimate of the process memory usage, options::
        
            >>> pid = psutil.Process()
            >>> mem_info = pid.mem_info()
            # "Resident Set Size", non-swapped physical memory a process has used.
            # On UNIX it matches 'top's RES column.
            # On Windows this is an alias for wset field and it matches "Mem Usage" column
            # of taskmgr.exe.
            >>> rss = mem_info.rss
            # "Virtual Memory Size", this is the total amount of virtual memory used by the
            # process.
            # On UNIX it matches top's VIRT column.
            # On Windows this is an alias for pagefile field and it matches "Mem Usage"
            # "VM Size" column of taskmgr.exe.
            >>> vms = mem_info.vms
            # Or:
            >>> mem_full_info = pid.mem_full_info()
            # uss (Linux, OSX, Windows): aka "Unique Set Size", this is the memory which is
            # unique to a process and which would be freed if the process was terminated
            # right now.
            >>> mem_full_info.uss
        """
        memory_info = self.pid.memory_info()
        # "Resident Set Size", non-swapped physical memory a process has used.
        # On UNIX it matches 'top's RES column.
        # On Windows this is an alias for wset field and it matches "Mem Usage" column
        # of taskmgr.exe.
        m = memory_info.rss
#         self._update_min_max_dicts('memory', m)
        return m
    
    def time(self):
        """
        Returns our estimate of the process 'time'. We use time.time(), the
        wall clock time.
        """
        t = time.time()
#         self._update_min_max_dicts('time', t)
        return t
    
    def create_data_point(self):
        """Snapshot a data point. Returns a CallReturnData named tuple.""" 
        return data.CallReturnData(self.time(), self.memory())
    
    def add_data_point(self, filename, function, firstlineno, event, data):
        """
        Adds a data point. Test code can drive this to create synthetic
        time/memory events.
        
        data is a CallReturnData object.
        """
        assert event in ('call', 'return')
        # Update the function encoder if necessary.
        function_id = self.function_encoder.encode(filename, function, firstlineno)
        self.function_tree_seq.add_call_return_event(event, function_id, data)
        # Update max and min
        self._update_min_max_dicts('time', data.time)
        self._update_min_max_dicts('memory', data.memory)


    def __call__(self, frame, event, arg):
        """Handle a trace event."""
        # frame_info is a named tuple:
        # Traceback(filename, lineno, function, code_context, index)
        # From the documentation:
        # "The tuple contains the frame object, the filename, the line number of
        # the current line, the function name, a list of lines of context from
        # the source code, and the index of the current line within that list."
        frame_info = inspect.getframeinfo(frame)
        firstlineno = frame.f_code.co_firstlineno
        if self.TRACE_EVENTS:
            print(
                'TRACE: {:12} {:4d} {:4d} {:24s} {:s}'.format(
                    event, frame_info.lineno, firstlineno,
                    '{:s}()'.format(frame_info.function), frame_info.filename,
                )
            )
        is_return_from_self_enter = event == 'return' \
            and frame_info.filename == __file__ \
            and firstlineno == self.__enter__lineno
        is_call_self_exit = event == 'call' \
            and frame_info.filename == __file__ \
            and firstlineno == self.__exit__lineno
        is_non_decl_function = self.RE_TEMPORARY_FILE.match(frame_info.filename) \
            or frame_info.function in self.FALSE_FUNCTION_NAMES
        if is_return_from_self_enter or is_call_self_exit or is_non_decl_function:
            # Ignore artifacts of context manager and non-declared functions.
            pass
        elif event in ('call', 'return'):
            # Only look at 'real' files and functions
            self.add_data_point(
                frame_info.filename,
                frame_info.function,
                firstlineno,
                event,
                self.create_data_point(),
            )
        self.event_counter.update({event : 1})
        self.eventno += 1
        return self

    def _cleanup(self):
        """
        This does any spring cleaning once tracing has stopped.
        """
        pass
    
    def finalise(self):
        """
        This extracts any overall data such as max memory usage, start/finish
        time etc.
        """
        self._cleanup()
        self.data_final = self.create_data_point()
        for ft in self.function_tree_seq.function_trees:
            assert not ft.is_open
        # Convert data min/max frm dynamic dicts to immutable named tuples.
        self.data_min = data.CallReturnData(**self.data_min)
        self.data_max = data.CallReturnData(**self.data_max)

    __enter__lineno = inspect.currentframe().f_lineno + 1
    def __enter__(self):
        """
        Context manager sets the profiling function. This saves the existing
        tracing function.
        
        We use ``sys.setprofile()`` as we only want the granularity of
        call and return in functions, not line events.
        """
        self._trace_fn_stack.append(self.TRACE_FUNCTION_GET())
        self.TRACE_FUNCTION_SET(self)
        return self

    __exit__lineno = inspect.currentframe().f_lineno + 1
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context manager. This performs some cleanup and then
        restores the tracing function to that prior to ``__enter__``.
        """
        # TODO: Check what is sys.gettrace(), if it is not self then someone has
        # monkeyed with the tracing.
        self.TRACE_FUNCTION_SET(self._trace_fn_stack.pop())
        self.finalise()

def compile_and_exec(script_name, *args, **kwargs):
    """
    Main execution point to trace memory function calls.
    
    Returns a MemTrace object.
    """
#     print('TRACE: compile_and_exec()', script_name, args, kwargs)
    sys.argv = [script_name] + list(args)
#     logging.debug('typein_cli.compile_and_exec({:s})'.format(script_name))
    with open(script_name) as f_obj:
        src = f_obj.read()
#         logging.debug('typein_cli.compile_and_exec() read {:d} lines'.format(src.count('\n')))
        code = compile(src, script_name, 'exec')
        with MemTrace() as mt:
            try:
                exec(code, globals())#, locals())
            except SystemExit:
                # Trap CLI code that calls exit() or sys.exit()
                pass
    return mt

def main():
    """Command line version of pymemtrace which executes arbitrary Python code
    and for each function records all the types called, returned and raised.
    For example::

        python typin_cli.py --stubs=stubs -- example.py 'foo bar baz'

    This will execute ``example.py`` with the options ``foo bar baz`` under the
    control of typin and write all the type annotations to the stubs/ directory.
    """
    start_time = time.time()
    start_clock = time.clock()
    program_version = "v%s" % '0.1.0'
    program_shortdesc = 'typin_cli - Infer types of Python functions.'
    program_license = """%s
  Created by Paul Ross on 2017-10-25. Copyright 2017. All rights reserved.
  Version: %s Licensed under MIT License
USAGE
""" % (program_shortdesc, program_version)
    parser = argparse.ArgumentParser(description=program_license,
                            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "-l", "--loglevel",
        type=int,
        dest="loglevel",
        default=30,
        help="Log Level (debug=10, info=20, warning=30, error=40, critical=50)" \
        " [default: %(default)s]"
    )
#     parser.add_argument("-d", "--dump", action="store_true", dest="dump",
#                         default=False,
#                         help="Dump results on stdout after processing. [default: %(default)s]")
#     parser.add_argument("-t", "--trace-frame-events", action="store_true", dest="trace_frame_events",
#                         default=False,
#                         help="""Very verbose trace output, one line per frame event. [default: %(default)s]""")
#     parser.add_argument("-e", "--events-to-trace", action='append', default=[], dest="events_to_trace",
#                         help="Events to trace (additive). [default: %(default)s] i.e. every event.")
    parser.add_argument(
#         "-o", "--output",
        type=str,
        dest="output",
        help="Output SVG file.",
    )
#     parser.add_argument(
#         "-w", "--write-docstrings",
#         type=str,
#         dest="write_docstrings",
#         default="",
#         help="Directory to write source code with docstrings. [default: %(default)s]"
#     )
#     parser.add_argument(
#         "-r", "--root",
#         type=str,
#         dest="root",
#         default=".",
#         help="Root path of the Python packages to generate stub files for."
#         " [default: %(default)s]"
#     )
    parser.add_argument(dest="program",
                        help="Python target file to be compiled and executed.")
    parser.add_argument(dest="args",
                        nargs=argparse.REMAINDER,
                        help="Arguments to give to the target.")
    cli_args = parser.parse_args()
    logFormat = '%(asctime)s %(levelname)-8s %(message)s'
    logging.basicConfig(level=cli_args.loglevel,
                        format=logFormat,
                        # datefmt='%y-%m-%d % %H:%M:%S',
                        stream=sys.stdout)
#     print(' START: typin_cli '.center(75, '='))
#     print('typin_cli sys.argv:', sys.argv)
#     print('sys.argv:', sys.argv)
    print('cli_args', cli_args)
    print(dir(PlotMemTrace))
    print(PlotMemTrace.plot_memtrace_to_path)
    return

    # Execution point
    mem_trace = compile_and_exec(cli_args.program, *cli_args.args)
    # Output: SVG.
    PlotMemTrace.plot_memtrace_to_path(mem_trace, cli_args.ouptut)
    # Summary.
    print('MemTrace total events: {:d}'.format(mem_trace.eventno))
    print(' MemTrace event count:', mem_trace.event_counter)
    print(' CPU time = {:8.3f} (S)'.format(time.time() - start_time))
    print('CPU clock = {:8.3f} (S)'.format(time.clock() - start_clock))
    print('Bye, bye!')
    print(' FINISH: typin_cli '.center(75, '='))
    return 0

if __name__ == '__main__':
    sys.exit(main())


