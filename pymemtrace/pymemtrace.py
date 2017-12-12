# -*- coding: utf-8 -*-

"""Main module."""
import array
import bisect
import collections
import sys
import time

import psutil

pid = psutil.Process()
mem_info = pid.mem_info()
# "Resident Set Size", non-swapped physical memory a process has used.
# On UNIX it matches 'top's RES column.
# On Windows this is an alias for wset field and it matches "Mem Usage" column
# of taskmgr.exe.
rss = mem_info.rss
# "Virtual Memory Size", this is the total amount of virtual memory used by the
# process.
# On UNIX it matches top's VIRT column.
# On Windows this is an alias for pagefile field and it matches "Mem Usage"
# "VM Size" column of taskmgr.exe.
vms = mem_info.vms

mem_full_info = pid.mem_full_info()
# uss (Linux, OSX, Windows): aka "Unique Set Size", this is the memory which is
# unique to a process and which would be freed if the process was terminated
# right now.
mem_full_info.uss

class FunctionCallSites:
    """
    Tracks function call sites during a process.
    
    Given a call/return site (file_path, lineno) this can identify the
    function ID that lineno must belong to.
    
    Als gives a space saving encoding/decoding of (file, function, lineno) to
    a single integer.
    """
    def __init__(self):
        """Constructor, just initialises internal state."""
        # {(file_path, function, lineno) : int, ...}
        # Where lineno is the first call event, subsequent call events
        # might have greater line numbers (e.g. generators), in that case
        # self.function_call_sites can be used to find the first call. 
        self.id_lookup = {}
        # Reverse lookup.
        # {int : (file_path, function, lineno), ...}
        self.id_rev_lookup = {}
#         # dict value is an always ordered list of line numbers of first call.
#         # {file_path : [function_first_call_lineno, ...])
#         self.function_call_sites = collections.defaultdict(list)
        
# #     def has_call(self, function_id, lineno):
# #         """
# #         Returns true if ``function_id`` has been seen.
# #         """
# #         return function_id in self.id_lookup
#     
#     def _add_first_call(self, file_path, lineno):
#         """
#         Adds the first call of a function at lineno.
#         """
#         first_calls = self.function_call_sites[file_path]
#         index = bisect.bisect_left(first_calls, lineno)
#         if index < len(first_calls) and first_calls[index] == lineno:
#             raise ValueError(
#                 'File {:s} already has a first call at a lineno of {:d}'.format(file_path, lineno)
#             )
#         first_calls.insert(index, lineno)
#     
#     def first_call_lineno(self, file_path, lineno):
#         """
#         This is pretty much the sole reason for this class: to identify, from
#         a call/return line number which function that must be in by its first
#         call lineno.
#         """
#         if file_path not in self.function_call_sites:
#             raise ValueError('Do not have information on file "{:s}"'.format(file_path))
#         first_calls, IDs = self.function_call_sites[file_path]
#         # bisect_right - 1 gives the index of the largest value in first_calls
#         # that is <= lineno
#         index = bisect.bisect_right(first_calls, lineno) - 1
#         assert index != len(first_calls)
#         if index < 0:
#             raise ValueError(
#                 'File {:s} can not see lineno prior to {:d}'.format(file_path, lineno)
#             )
#         return first_calls[index]
#     
#     def add_call(self, file_path, function_name, lineno):
#         """
#         Adds a call event. If this does not exist it will be treated as a first
#         call event.
#         """
#         function_key = (file_path, function_name, lineno)
#         if function_key not in self.id_lookup:
#             # First call
#             val = len(self.id_lookup)
#             self.id_lookup[(file_path, function_name, first_call_lineno)] = val
#             assert val not in self.id_rev_lookup
#             self.id_rev_lookup[val] = (file_path, function_name, first_call_lineno)
#             self.add_first_call(file_path, lineno)
    
    def encode(self, file_path, function_name, lineno):
        """
        Encode the ``(file_path, function_name, lineno)`` to a single integer
        ID in the cache. ``lineno`` must be the function declaration line,
        this can be obtained from frame.f_code.co_firstlineno.
        """
        first_call_lineno = self.first_call_lineno(file_path, lineno)
        try:
            val = self.id_lookup[(file_path, function_name, first_call_lineno)]
        except KeyError:
            # Insert into the cache
            val = len(self.id_lookup)
            self.id_lookup[(file_path, function_name, first_call_lineno)] = val
            assert val not in self.id_rev_lookup
            self.id_rev_lookup[val] = (file_path, function_name, first_call_lineno)
        return val
    
    def decode(self, int_val):
        """
        Decode the integer to the original (file_path, function_name, lineno).
        """
        return self.id_rev_lookup[val]
    
    def integrity(self):
        """
        Aggressive integrity checking that self._ref_id_lookup is the mirror of
        self.id_lookup, self.function_call_sites holds sorted values.
        """
        if len(self.id_lookup) != len(self.id_rev_lookup):
            return False
        for k, v in self.id_lookup.items():
            if v not in self.id_rev_lookup:
                return False
            if self.id_rev_lookup[v] != k:
                return False
#         for file_path in self.function_call_sites:
#             if sorted(self.function_call_sites[file_path]) != self.function_call_sites[file_path]:
#                 return False
        return True

# class FunctionCall:
#     """
#     Temporary representation of a function call.
#     This is created with a call even and completed with a return event.
#     """
#     # TODO: Add time and memory here
#     def __init__(self, file_path, function_name, lineno, data):
#         if lineno < 1:
#             raise ValueError('FunctionCall.__init__(): Line numbers >= 1 not {:d}'.format(lineno))
#         self.time_call = time.time()
#         self.file_path = file_path
#         self.function_name = function_name
#         self.lineno_call = lineno
#         self.data = data
#         self.lineno_return = -1
#         self.time_return = None
#     
#     def add_return(self, file_path, function_name, lineno):
#         if self.file_path != file_path:
#             raise ValueError('FunctionCall.add_return(): file_path was {:s} now {:s}'.format(
#                 self.file_path, file_path
#             ))
#         if self.function_name != function_name:
#             raise ValueError('FunctionCall.add_return(): function_name was {:s} now {:s}'.format(
#                 self.function_name, function_name
#             ))
#         if lineno < 1:
#             raise ValueError('FunctionCall.add_return(): Line numbers >= 1 not {:d}'.format(lineno))
#         if self.lineno_call > lineno:
#             raise ValueError('FunctionCall.add_return(): call lineno {:d} > return lineno {:d}'.format(
#                 self.lineno_call, lineno
#             ))
#         self.lineno_return = lineno
#         self.time_return = time.time()
# 
#     def id_args(self):
#         return self.file_path, self.function_name, self.lineno_call
#     
#     def line_span(self):
#         return self.lineno_call, self.lineno_return

class FunctionCallTree:
    # TODO: Remodel this, use a temporary stack of FunctionCall then
    # as each is popped then append the encoded one into this tree (it being
    # the final result).
    def __init__(self, function_id, *args):
        """Constructor is when a function (function_id) is called.
        args is the data available at call time such as (time, memory_usage)."""
        # This node:
        self.function_id = function_id
        self.data_call = args
        self.data_return = None
        # Child nodes, each is a FunctionCallTree:
        self._children = []
        
    @property
    def is_open(self):
        return self.data_return is None 
        
    def addCall(self, function_id, *args):
        """
        Initialise the call with the function ID, time of call and memory
        usage at the call.
        """
        if len(self._children) and self._children[-1].is_open:
            self._children[-1].addCall(function_id, *args)
        else:
            self._children.append(FunctionCallTree(function_id, *args))
               
    def addReturn(self, function_id, *args):
        """
        Initialise the call with the function ID, time of call and memory
        usage at the call.
        """
        if len(self._children) and self._children[-1].is_open:
            self._children[-1].addReturn(function_id, *args)
        else:
            self.data_return = args
               
class MemTrace:
    """
    Keeps track of overall memory usage at each function entry and exit point.
    """
    RE_TEMPORARY_FILE = re.compile(r'<(.+)>')
    FALSE_FUNCTION_NAMES = ('<dictcomp>', '<genexpr>', '<listcomp>', '<module>', '<setcomp>')
    def __init__(self):
        self._pid = psutil.Process()
        # Don't really need these, or could create them in _finalise()
        self._time_start = time.time()
        self._mem_start = self.memory()
        self._function_tree = FunctionCallTree()
        
    def memory(self):
        mem_info = self._pid.mem_info()
        # "Resident Set Size", non-swapped physical memory a process has used.
        # On UNIX it matches 'top's RES column.
        # On Windows this is an alias for wset field and it matches "Mem Usage" column
        # of taskmgr.exe.
        return mem_info.rss

    def __call__(self, frame, event, arg):
        """Handle a trace event."""
        self.event_counter.update({event : 1})
        # A named tuple: Traceback(filename, lineno, function, code_context, index)
        frame_info = inspect.getframeinfo(frame)
#         if self.trace_frame_event and (self.events_to_trace is None or event in self.events_to_trace):
#             # The tuple contains the filename, the line number of the current line, the function name, a list of lines
#             # of context from the source code, and the index of the current line within that list.
#             # Traceback(filename='.../3.6/lib/python3.6/_sitebuiltins.py', lineno=19, function='__call__',
#             #           code_context=['    def __call__(self, code=None):\n'], index=0)
#             # Or:
#             # Traceback(filename='<string>', lineno=12, function='__new__', code_context=None, index=None)
#             try:
#                 repr_arg = repr(arg)
#             except Exception:# AttributeError: # ???
#                 repr_arg = 'repr(arg) fails'
#             # Order of columns is an attempt to make this very verbose output readable
#             print('[{:8d}] {:9s} {!r:s}: arg="{:s}"'.format(self.eventno, event, frame_info, repr_arg), flush=True)
#         try:
#             self._debug(
#                 'TypeInferencer.__call__(): file: {:s}#{:d} function: {:s} event:{:s} arg: {:s}'.format(
#                     frame_info.filename,
#                     frame_info.lineno,
#                     frame_info.function,
#                     repr(event),
#                     repr(arg)
#                 )
#             )
#         except Exception: # Or just AttributeError ???
#             # This can happen when calling __repr__ on partially constructed objects
#             # For example with argparse:
#             # AttributeError: 'ArgumentParser' object has no attribute 'prog'
#             self._warn(
#                 'TypeInferencer.__call__(): failed, function: {:s} file: {:s}#{:d}'.format(
#                     frame_info.function, frame_info.filename, frame_info.lineno
#                 )
#             )
#         self._trace('TRACE: self.exception_in_progress', self.exception_in_progress)
        if self.RE_TEMPORARY_FILE.match(frame_info.filename) \
        or frame_info.function in self.FALSE_FUNCTION_NAMES:
            # Ignore these.
            pass
        else:
            # Only look at 'real' files and functions
            lineno = frame_info.lineno
            lineno_decl = frame.f_code.co_firstlineno
            if event in ('call', 'return', 'exception'):# and frame_info.filename != '<module>':
                file_path = os.path.abspath(frame_info.filename)
                # TODO: For methods use __qualname__
                #             function_name = frame_info.function
                q_name, bases, signature = self._qualified_name_bases_signature(frame)
                self._debug(
                    'TypeInferencer.__call__(): q_name="{:s}", bases={!r:s})'.format(
                        q_name, bases
                ))
                if q_name != '':
                    try:
                        self._set_bases(file_path, lineno, q_name, bases)
                        # func_types is a types.FunctionTypes object
                        func_types = self._get_func_data(file_path, q_name, signature)
                        self._process_call_return_exception(frame, event, arg,
                                                            frame_info, func_types)
                        if self.trace_frame_event and (self.events_to_trace is None or event in self.events_to_trace):
                            print('[{:8d}] func_types now: {!r:s}'.format(self.eventno, func_types), flush=True)
                    except Exception as err:
                        self._error(
                            'ERROR: Could not add event "{:s}" Function: {:s} File: {:s}#{:d}'.format(
                                event,
                                frame_info.function,
                                frame_info.filename,
                                frame_info.lineno,
                            )
                        )
                        self._error('ERROR: Type error: {!r:s}, message: {:s}'.format(type(err), str(err)))
                        self._error(''.join(traceback.format_exception(*sys.exc_info())))
                else:
                    self._error('Could not find qualified name in frame: {!r:s}'.format(frame_info))
            elif event == 'line':
                # Deferred decision about the exception reveals that
                # this exception is caught within the function.
                if self.exception_in_progress is not None:
                    self._trace('TRACE: Exception in flight followed by line event', frame_info.filename, frame_info.function, lineno)
                    # The exception has been caught within the function
                    self._assert_exception_caught(event, arg, frame_info)
                    self.exception_in_progress = None
        self.eventno += 1
        self._trace()
        return self

    def _cleanup(self):
        """
        This does any spring cleaning once tracing has stopped.
        """
        pass
    
    def _finalise(self):
        """
        This extracts any overall data such as max memory usage, start/finish
        time etc.
        """
        pass

    def __enter__(self):
        """
        Context manager sets the profiling function. This saves the existing
        tracing function.
        
        We use ``sys.setprofile()`` as we only want the granularity of
        call and return in functions, not line events.
        """
        self._trace_fn_stack.append(sys.getprofile())
        sys.setprofile(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context manager. This performs some cleanup and then
        restores the tracing function to that prior to ``__enter__``.
        """
        # TODO: Check what is sys.gettrace(), if it is not self then someone has
        # monkeyed with the tracing.
        sys.setprofile(self._trace_fn_stack.pop())
        self._cleanup()
        self._finalise()
