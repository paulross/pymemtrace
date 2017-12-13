# -*- coding: utf-8 -*-

"""Main module."""
import array
import bisect
import collections
import inspect
import re
import sys
import time

import psutil

class ExceptionPyMemTraceBase(Exception):
    pass

class CallReturnSequenceError(ExceptionPyMemTraceBase):
    pass

FunctionLocation = collections.namedtuple(
    'FunctionLocation', 'filename, function, lineno'
)
FunctionLocation.__doc__ += ': Function location.'
FunctionLocation.filename.__doc__ = 'Absolute file path as a string.' 
FunctionLocation.function.__doc__ = 'Function (unqualified) name as a string.' 
FunctionLocation.lineno.__doc__ = 'Line number of the event as an int.'

class FunctionEncoder:
    """
    Gives a space saving encoding/decoding of (file, function, lineno) to
    a single integer.
    """
    def __init__(self):
        """Constructor, just initialises internal state."""
        # {(file_path, function, lineno) : int, ...}
        # Where lineno is the first call event, subsequent call events
        # might have greater line numbers (e.g. generators).
        # lineno of function declaration can be obtained from
        # frame.f_code.co_firstlineno  
        self.id_lookup = {}
        # Reverse lookup.
        # {int : (file_path, function, lineno), ...}
        self.id_rev_lookup = {}
    
    def __len__(self):
        return len(self.id_lookup)
    
    def encode(self, file_path, function_name, lineno):
        """
        Encode the ``(file_path, function_name, lineno)`` to a single integer
        ID in the cache. ``lineno`` must be the function declaration line
        which can be obtained from ``frame.f_code.co_firstlineno``.
        ``lineno`` must be >= 1.
        
        This will add to the encoding cache if the function has not been seen
        before.
        """
        if lineno < 1:
            raise ValueError(
                'FunctionEncoder.encode(): line number must be >=1 not {!r:s}'.format(lineno)
            )
        loc = FunctionLocation(file_path, function_name, lineno)
        try:
            val = self.id_lookup[loc]
        except KeyError:
            # Insert into the cache
            val = len(self.id_lookup)
            self.id_lookup[loc] = val
            assert val not in self.id_rev_lookup
            self.id_rev_lookup[val] = loc
        return val
    
    def decode(self, function_id):
        """
        Decode the int function_id to the original:
        FunctionLocation(file_path, function_name, lineno).
        
        Will raise KeyError if function_id unseen.
        """
        return self.id_rev_lookup[function_id]
    
    def integrity(self):
        """
        Aggressive integrity checking that self._ref_id_lookup is the mirror of
        self.id_lookup.
        """
        if len(self.id_lookup) != len(self.id_rev_lookup):
            return False
        for k, v in self.id_lookup.items():
            if v not in self.id_rev_lookup:
                return False
            if self.id_rev_lookup[v] != k:
                return False
        return True

# CallReturnData = collections.namedtuple(
#     'CallReturnData', 'time, memory'
# )
class CallReturnData(collections.namedtuple('CallReturnData', ['time', 'memory'])):
    """Data obtained at cal and return points."""
    __slots__ = ()
    
    def __sub__(self, other):
        return CallReturnData(self.time - other.time, self.memory - other.memory)
    
    def __isub__(self, other):
        return self - other

CallReturnData.time.__doc__ = 'Wall clock time as a float.' 
CallReturnData.memory.__doc__ = 'Total memory usage in bytes as an int.' 


DepthEventFunctionData = collections.namedtuple(
    'DepthEventFunctionData', ['depth', 'event', 'function_id', 'data']
)
DepthEventFunctionData.__doc__ += ': Function call depth data.'
DepthEventFunctionData.depth.__doc__ = 'Call depth is an int (starting at 0).' 
DepthEventFunctionData.event.__doc__ = 'Event: (\'call\', \'return\').' 
DepthEventFunctionData.function_id.__doc__ = 'Function ID an int.' 
DepthEventFunctionData.data.__doc__ = 'Call/return point data as a CallReturnData object' 

WidthDepthEventFunctionData = collections.namedtuple(
    'WidthDepthEventFunctionData',
    ['width', 'depth', 'event', 'function_id', 'data']
)
WidthDepthEventFunctionData.__doc__ += ': Function call depth data.'
WidthDepthEventFunctionData.width.__doc__ = 'Call width is an int (starting at 0).' 
WidthDepthEventFunctionData.depth.__doc__ = 'Call depth is an int (starting at 0).' 
WidthDepthEventFunctionData.event.__doc__ = 'Event: (\'call\', \'return\').' 
WidthDepthEventFunctionData.function_id.__doc__ = 'Function ID an int.' 
WidthDepthEventFunctionData.data.__doc__ = 'Call/return point data as a CallReturnData object' 

class FunctionCallTree:
    """This contains the current and historic call information from a single
    function."""
    def __init__(self, function_id, data_call):
        """Constructor is when a function (function_id) is called.
        date_call is the data available at call time as a  CallReturnData
        object, such as (time, memory_usage)."""
        # This node:
        self.function_id = function_id
        self.data_call = data_call
        self.data_return = None
        # Child nodes, each is a FunctionCallTree.
        self.children = []
        
    @property
    def is_open(self):
        """Returns True if this function has not yet seen a return event."""
        return self.data_return is None
    
    def integrity(self):
        """Returns True if the internal representation is OK."""
        if not self.is_open:
            for child in self.children:
                if child.is_open:
                    return False
                if not child.integrity():
                    return False
        return True
        
    def add_call(self, function_id, data_call):
        """
        Initialise the call with the function ID, time of call and memory
        usage at the call.
        """
        if not self.is_open:
            raise CallReturnSequenceError(
                'FunctionCallTree.add_call() when not open for calls.'
            )
        if len(self.children) and self.children[-1].is_open:
            self.children[-1].addCall(function_id, data_call)
        else:
            self.children.append(FunctionCallTree(function_id, data_call))
               
    def add_return(self, function_id, data_return):
        """
        Set the return data, this closes this function.
        """
        if not self.is_open:
            raise CallReturnSequenceError(
                'FunctionCallTree.add_return() when not open for calls.'
            )
        if len(self.children) and self.children[-1].is_open:
            self.children[-1].add_return(function_id, data_return)
        else:
            assert function_id == self.function_id
            self.data_return = data_return
        
    def gen_call_return_data(self):
        """
        Yields all the data points recursively as a named tuple::
        
            DepthEventFunctionData(depth, event, function_id, data)
            
        Where depth is an int (starting at 0), event ('call', 'return'),
        function_id an int, data as a CallReturnData object.
        """
        for child_data in self._gen_call_return_data(0):
            yield child_data

    def _gen_call_return_data(self, depth):
        """
        Recursive call to generate data points.
        Yields all the data points recursively as a named tuple::
        
            DepthEventFunctionData(depth, event, function_id, data)
            
        Where depth is an int (starting at 0), event ('call', 'return'),
        function_id an int, data as a CallReturnData object.
        """
        yield DepthEventFunctionData(depth, 'call', self.function_id, self.data_call)
        for child in self.children:
            for child_data in child._gen_call_return_data(depth + 1):
                yield child_data
        yield DepthEventFunctionData(depth, 'return', self.function_id, self.data_return)

class FunctionCallTreeSequence:
    """
    This contains the current and historic call information from a sequence
    of function calls.
    """
    def __init__(self):
        # List of FunctionCallTree objects.
        self.function_trees = []
        
    def __len__(self):
        return len(self.function_trees)
        
    def integrity(self):
        """Returns True if the internal representation is OK."""
        return all([v.integrity() for v in self.function_trees])
    
    def add_call_return_event(self, event, function_id, data):
        assert event in ('call', 'return'), \
            'Expected "call" or "return" not "{:s}"'.format(event)
        if len(self.function_trees) and self.function_trees[-1].is_open:
            # Pass the event down the stack.
            if event == 'call':
                self.function_trees[-1].add_call(function_id, data)
            else:
                assert event == 'return', 'Expected "return" not "{:s}"'.format(event)
                self.function_trees[-1].add_return(function_id, data)
        else:
            # Create a new stack
            assert event == 'call', 'Expected "call" not "{:s}"'.format(event)
            self.function_trees.append(FunctionCallTree(function_id, data))

    def gen_call_return_data(self):
        """
        Yields all the data points recursively as a named tuple::
        
            WidthDepthEventFunctionData(width, depth, event, function_id, data)
            
        Where width is an int (starting at 0), depth is an int (starting at 0),
        event ('call', 'return'), function_id an int, data as a CallReturnData object.
        """
        for width, ft in enumerate(self.function_trees):
            for value in ft.gen_call_return_data():
                yield WidthDepthEventFunctionData(width, *value)

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
        self.function_encoder = FunctionEncoder()
        # Wraps a ist of FunctionCallTree objects.
        self.function_tree_seq = FunctionCallTreeSequence()
        # Event number, for the curious.
        self.eventno = 0
        # Event counters for different events, for the curious.
        self.event_counter = collections.Counter()
        # Allow re-entrancy with sys.settrace(function)
        self._trace_fn_stack = []
        # Create initial and final conditions
        self.data_initial = self.create_data()
        # Created by finalise() as CallReturnData objects.
        self.data_final = None
        self.data_min = None
        self.data_max = None

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
        return memory_info.rss

    def create_data(self):
        """Snapshot a data point. Returns a CallReturnData named tuple.""" 
        return CallReturnData(time.time(), self.memory())

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
            function_id = self.function_encoder.encode(
                    frame_info.filename,
                    frame_info.function,
                    firstlineno,
            )
            self.function_tree_seq.add_call_return_event(
                event, function_id, self.create_data()
            )
        self.event_counter.update({event : 1})
        self.eventno += 1
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
        self._cleanup()
        self.data_final = self.create_data()
        for ft in self.function_tree_seq.function_trees:
            assert not ft.is_open
        # Find min/max, if available.
        if len(self.function_tree_seq) > 0:
            len_fields = len(CallReturnData._fields)
            data_min = [None,] * len_fields
            data_max = [None,] * len_fields
            for event_data in self.function_tree_seq.gen_call_return_data():
                assert len(event_data.data) == len_fields
                for i in range(len_fields):
                    if data_min[i] is None:
                        data_min[i] = event_data.data[i]
                    else:
                        data_min[i] = min([data_min[i], event_data.data[i]])
                    if data_max[i] is None:
                        data_max[i] = event_data.data[i]
                    else:
                        data_max[i] = max([data_max[i], event_data.data[i]])
            self.data_min = CallReturnData(*data_min)
            self.data_max = CallReturnData(*data_max)

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
        self._finalise()
