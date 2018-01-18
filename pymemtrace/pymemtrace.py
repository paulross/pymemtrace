# -*- coding: utf-8 -*-

"""Main module."""
import argparse
# import array
# import bisect
import collections
import inspect
import logging
# import os
import pprint
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
#     TRACE_FUNCTION_GET = sys.gettrace
#     TRACE_FUNCTION_SET = sys.settrace
    # Very verbose tracing of every event
    TRACE_EVENTS = False
    # Verbose printing of events that are recorded
    TRACE_ADD_DATA_POINT = False
    def __init__(self, filter_fn):
        """
        :param filter_fn: A callable that takes two ``CallReturnData`` objects
            and returns a boolean, if True this function record is kept, if
            False it is discarded. If filter_fn is None it is ignored and all
            function records are kept.
            ``filter_fn=None`` means all functions are captured, it is equivalent
            to ``filter_fn=lambda call_data, return_data: True``
        :type filter_fn: A callable that takes two ``CallReturnData`` objects.
        """
        self.pid = psutil.Process()
        self.function_encoder = data.FunctionEncoder()
        # Wraps a list of FunctionCallTree objects.
        self.function_tree_seq = data.FunctionCallTreeSequence(filter_fn)
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
        # Capture sizeof at __inter__ and __exit__
        self.sizeof_enter = 0
        self.sizeof_exit = 0

    def __sizeof__(self):
        # TODO: Could iterate through __dict__
        s = sys.getsizeof(self.function_encoder)
        s += sys.getsizeof(self.function_tree_seq)
        s += sys.getsizeof(self.eventno)
        s += sys.getsizeof(self.event_counter)
        s += sum([sys.getsizeof(f) for f in self._trace_fn_stack])
        s += sys.getsizeof(self.data_initial)
        s += sys.getsizeof(self.data_min)
        s += sys.getsizeof(self.data_max)
        s += sys.getsizeof(self.data_final)
        return s

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
        if self.TRACE_ADD_DATA_POINT:
            print(
                'TRACE add_data_point(): {:12} {:4d} {!s:40s} {:32s} {:s}'.format(
                    event, firstlineno, data,
                    '{:s}()'.format(function), filename,
                )
            )
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
                'TRACE __call__(): {:12} {:4d} {:4d} {:24s} {:s}'.format(
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
        self.sizeof_enter = sys.getsizeof(self)
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
        self.sizeof_exit = sys.getsizeof(self)

def compile_and_exec(script_name, filter_fn, *args, **kwargs):
    """
    Main execution point to trace memory function calls.

    Returns a MemTrace object.
    """
    logging.info('compile_and_exec(): START "{!s:s}"'.format(script_name))
    sys.argv = [script_name] + list(args)
    logging.debug('typein_cli.compile_and_exec({:s})'.format(script_name))
    with open(script_name) as f_obj:
        src = f_obj.read()
        logging.debug('typein_cli.compile_and_exec() read {:d} lines'.format(src.count('\n')))
        code = compile(src, script_name, 'exec')
        with MemTrace(filter_fn) as mt:
            try:
                exec(code, globals())#, locals())
            except SystemExit:
                # Trap CLI code that calls exit() or sys.exit()
                pass
    logging.info('compile_and_exec():  DONE "{!s:s}"'.format(script_name))
    return mt

DEFAULT_FILTER_MIN_TIME = -1
DEFAULT_FILTER_MIN_MEMORY = 0

def create_filter_function(filter_min_time, filter_min_memory):
    """
    Given command line arguments minimum time and memory (ms and kilobytes) this
    returns a function that filters function call data.

    If both are default values this returns None, this is means all functions
    are captured, it is equivalent to
    ``filter_fn=lambda call_data, return_data: True``

    If both values are non-default then this returns a function that filters
    functions where *either*
    """
    if filter_min_memory < 0:
        raise ValueError(
            'filter_min_memory must be >= 0 not {!r:s}'.format(
                filter_min_memory
            )
        )
    if filter_min_time == DEFAULT_FILTER_MIN_TIME \
    and filter_min_memory == DEFAULT_FILTER_MIN_MEMORY:
        # return None which is a speed optimisation as no function call is made by
        # pymemtrace.data.FunctionCallTree.add_return
        return None
    if filter_min_time != DEFAULT_FILTER_MIN_TIME \
    and filter_min_memory != DEFAULT_FILTER_MIN_MEMORY:
        # Filter on either
        def filter_either(data_call, data_return):
            diff = data_return - data_call
<<<<<<< HEAD
            if diff.time * 1e6 >= filter_min_time \
            or abs(diff.memory / 1024) >= filter_min_memory:
                return_value = True
            else:
                return_value = False
#             print('TRACE: filter_either():', diff, return_value)
            return return_value
=======
            if diff.time * 1e3 >= filter_min_time:
                return True
            if abs(diff.memory / 1024) >= filter_min_memory:
                return True
            return False
>>>>>>> origin/master
        return filter_either
    # Filter on one or the other
    if filter_min_time != DEFAULT_FILTER_MIN_TIME:
        # Time only
        assert filter_min_memory == DEFAULT_FILTER_MIN_MEMORY
        def filter_time(data_call, data_return):
            diff = data_return - data_call
            if diff.time * 1e3 >= filter_min_time:
                return True
            return False
        return filter_time
    # Memory only
    assert filter_min_time == DEFAULT_FILTER_MIN_TIME
    def filter_memory(data_call, data_return):
        diff = data_return - data_call
        if abs(diff.memory / 1024) >= filter_min_memory:
            return True
        return False
    return filter_memory

def dump_function_tree_seq(function_tree_seq, data_min, function_encoder):
    """
    Dumps MemTrace function tree sequence data to stdout.

    :param function_tree_seq: The sequence of functions.
    :type function_tree_seq: ``pymemtrace.data.FunctionCallTreeSequence``

    :param data_min: The minimum discovered data value for each function.
        This will be subtracted from each item in the dump as a baseline.
    :type data_min: A named tuple ``pymemtrace.data.CallReturnData(time, memory)``.

    :param function_encoder: The function encoder/decoder.
    :type function_encoder: ``pymemtrace.data.FunctionEncoder``

    :returns: ``None``
    """
    print(' DUMP of MemTrace.function_tree_seq '.center(75, '='))
    # A pymemtrace.data.CallReturnData
    data_previous = data.CallReturnData(0, 0)
    count = 0
    for wdefd in function_tree_seq.gen_depth_first():
        # Each object is a:
        # WidthDepthEventFunctionData(width, depth, event, function_id, data)
        #
        # A FunctionLocation(filename, function, lineno)
        function = function_encoder.decode(wdefd.function_id)
        data_diff = wdefd.data - data_min
        print('{:4d} {:s}{:s} {!s:28s} {!s:28s} {:32s} {:s}#{:d}'.format(
                wdefd.width,
                '  ' * wdefd.depth,
                '>' if wdefd.event == 'call' else '<',
                data_diff,
                data_diff - data_previous,
                function.function,
                function.filename,
                function.lineno,
            )
        )
        data_previous = data_diff
        count += 1
    print(' DUMP of MemTrace.function_tree_seq ENDS [{:d}]'.format(count).center(75, '='))

def dump_function_encoder(function_encoder):
    print(' DUMP of MemTrace.function_encoder [{:d}]'.format(len(function_encoder.id_rev_lookup)).center(75, '='))
    for key in sorted(function_encoder.id_rev_lookup.keys()):
        # {int : FunctionLocation(filename, function, lineno), ...}
        fn_loc = function_encoder.id_rev_lookup[key]
        print('{:4d} {:32s} {:s}#{:d}'.format(key, fn_loc.function, fn_loc.filename, fn_loc.lineno))
    print(' DUMP of MemTrace.function_encoder ENDS '.center(75, '='))

def main():
    """Command line version of pymemtrace which executes arbitrary Python code
    and for each function records all the types called, returned and raised.
    For example::

        python pymemtrace/pymemtrace.py result.svg example.py foo bar baz

    This will execute ``example.py`` with the options ``foo bar baz`` under the
    control of pymemtrace and write an SVG memory representation to
    ``result.svg``.
    """
    start_time = time.time()
    start_clock = time.clock()
    program_version = "v%s" % '0.1.0'
    program_shortdesc = 'pymemtrace - Track memory usage of a Python script.'
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
    parser.add_argument("-d", "--dump", action="store_true", dest="dump",
                        default=False,
                        help="Dump results on stdout after processing. [default: %(default)s]")
    parser.add_argument(
        type=str,
        dest="output",
        help="Output SVG file.",
    )
    parser.add_argument(
        "-t", "--filter-min-time",
        type=int,
        dest="filter_min_time",
        default=DEFAULT_FILTER_MIN_TIME,
        help="Ignore functions that execute in less than this number of"
        " milliseconds. -1 means retain all. [default: %(default)s (milliseconds)]"
    )
    parser.add_argument(
        "-m", "--filter-min-memory",
        type=int,
        dest="filter_min_memory",
        default=DEFAULT_FILTER_MIN_MEMORY,
        help="Ignore functions that have a memory impact (+/-) of this number"
        " of kilobytes. 0 means retain all. [default: %(default)s (kilobytes)]"
    )
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
#     print(dir(PlotMemTrace))
#     print(PlotMemTrace.plot_memtrace_to_path)
    # Create filter function
    if cli_args.filter_min_memory < 0:
        logging.error(
            '--filter-min-memory must be >= 0 not {!r:s}'.format(
                cli_args.filter_min_memory
            )
        )
        return -1
    filter_fn = create_filter_function(cli_args.filter_min_time,
                                       cli_args.filter_min_memory)
    logging.info('Filter function created: {!s:s}'.format(filter_fn))
    # Execution point
    mem_trace = compile_and_exec(cli_args.program, filter_fn, *cli_args.args)
    # Output: SVG.
    logging.info('Plotting SVG')
    pmt = PlotMemTrace.plot_memtrace_to_path(mem_trace, cli_args.output)
    # Dump.
    if cli_args.dump:
        dump_function_tree_seq(
            mem_trace.function_tree_seq,
            mem_trace.data_min,
            mem_trace.function_encoder,
        )
        dump_function_encoder(mem_trace.function_encoder)
    logging.info('All done, summary:')
    # Summary.
    print('MemTrace functions total: {:10d}'.format(mem_trace.function_tree_seq.function_count + mem_trace.function_tree_seq.filtered_function_count))
    print('   MemTrace filtered out: {:10d}'.format(mem_trace.function_tree_seq.filtered_function_count))
    print(' MemTrace functions kept: {:10d}'.format(mem_trace.function_tree_seq.function_count))
    print('   MemTrace total events: {:10d}'.format(mem_trace.eventno))
    print('    MemTrace event count: {:s}'.format(pprint.pformat(mem_trace.event_counter)))
    print('       MemTrace data_min: {!s:s}'.format(mem_trace.data_min))
    print('       MemTrace data_max: {!s:s}'.format(mem_trace.data_max))
    print('              Difference: {!s:s}'.format(mem_trace.data_max - mem_trace.data_min))
    print('   MemTrace data_initial: {!s:s}'.format(mem_trace.data_initial))
    print('     MemTrace data_final: {!s:s}'.format(mem_trace.data_final))
    print('              Difference: {!s:s}'.format(mem_trace.data_final - mem_trace.data_initial))
    print('        Functions in SVG: {!r:s}'.format(pprint.pformat(pmt.function_counter)))
    # sizeof
    print()
    print('sys.getsizeof(MemTrace) starts: {:12,d} (bytes)'.format(mem_trace.sizeof_enter))
    print('sys.getsizeof(MemTrace)   ends: {:12,d} (bytes)'.format(mem_trace.sizeof_exit))
    print('sys.getsizeof(MemTrace)   diff: {:12,d} (bytes)'.format(mem_trace.sizeof_exit - mem_trace.sizeof_enter))
    print('sys.getsizeof(FunctionEncoder): {:12,d} (bytes)'.format(sys.getsizeof(mem_trace.function_encoder)))
    print('sys.getsizeof(FunctionTree)   : {:12,d} (bytes)'.format(sys.getsizeof(mem_trace.function_tree_seq)))
    # Done
    print()
    print(' CPU time = {:8.3f} (S)'.format(time.time() - start_time))
    print('CPU clock = {:8.3f} (S)'.format(time.clock() - start_clock))
    print('Bye, bye!')
    print(' FINISH: typin_cli '.center(75, '='))
    return 0

if __name__ == '__main__':
    sys.exit(main())
