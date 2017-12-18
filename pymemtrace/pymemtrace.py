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

class PyMemTraceCallReturnSequenceError(ExceptionPyMemTraceBase):
    pass

class PyMemTraceMaxDepthOnEmptyTree(ExceptionPyMemTraceBase):
    """Raised when max_depth() is called on an empty tree.
    max() of an empty sequence raises a generic ValueError.
    This specialises that error."""
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

class CallReturnData(collections.namedtuple('CallReturnData', ['time', 'memory'])):
    """Data obtained at cal and return points."""
    __slots__ = ()
    
    def __sub__(self, other):
        return CallReturnData(self.time - other.time, self.memory - other.memory)
    
    def __isub__(self, other):
        return self - other
    
    def __str__(self):
        return '{:0,.0f} (us) {:0,.3f} (kb)'.format(self.time * 1e6, self.memory / 1024)

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
    
    def max_depth(self):
        """
        Returns the maximum call depth in this tree.
        A single function would return 1 so that the depths reported by
        ``gen_depth_first()`` are 0 <= d < max_depth(). 
        """
        depth = 1
        for child in self.children:
            depth = max([depth, child._max_depth(depth)])
        return depth
    
    def _max_depth(self, depth):
        """
        Returns the maximum call depth in this tree, recursive call.
        A single function would return 1 so that the depths reported by
        ``gen_depth_first()`` are 0 <= d < max_depth(). 
        """
        depth += 1
        for child in self.children:
            depth = max([depth, child._max_depth(depth)])
        return depth
    
    def max_width(self):
        """
        Returns the maximum call width in this tree.
        A single function would return 1 so that the widths reported by
        ``gen_depth_first()`` are 0 <= w < max_width(). 
        """
        if len(self.children) == 0:
            return 1
        return sum([child.max_width() for child in self.children])
    
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
            raise PyMemTraceCallReturnSequenceError(
                'FunctionCallTree.add_call() when not open for calls.'
            )
        if len(self.children) and self.children[-1].is_open:
            self.children[-1].add_call(function_id, data_call)
        else:
            self.children.append(FunctionCallTree(function_id, data_call))
               
    def add_return(self, function_id, data_return):
        """
        Set the return data, this closes this function.
        """
        if not self.is_open:
            raise PyMemTraceCallReturnSequenceError(
                'FunctionCallTree.add_return() when not open for calls.'
            )
        if len(self.children) and self.children[-1].is_open:
            self.children[-1].add_return(function_id, data_return)
        else:
            if self.function_id != function_id:
                raise ValueError(
                    'Returning from open function {!r:s} but given ID of {!r:s}'.format(
                        self.function_id, function_id
                    )
                )
            self.data_return = data_return
        
    def gen_depth_first(self):
        """
        Yields all the data points recursively, depth first, as a named tuple::
        
            DepthEventFunctionData(depth, event, function_id, data)
            
        Where depth is an int (starting at 0), event ('call', 'return'),
        function_id an int, data as a CallReturnData object.
        """
        for child_data in self._gen_depth_first(0):
            yield child_data

    def _gen_depth_first(self, depth):
        """
        Recursive call to generate data points.
        Yields all the data points recursively as a named tuple::
        
            DepthEventFunctionData(depth, event, function_id, data)
            
        Where depth is an int (starting at 0), event ('call', 'return'),
        function_id an int, data as a CallReturnData object.
        """
        yield DepthEventFunctionData(depth, 'call', self.function_id, self.data_call)
        for child in self.children:
#             for child_data in child._gen_call_return_data(depth + 1):
            for child_data in child._gen_depth_first(depth + 1):
                yield child_data
        yield DepthEventFunctionData(depth, 'return', self.function_id, self.data_return)
    
    def gen_width_first(self, depth):
        """
        Yields all the data points recursively, width first, as a named tuple::
        
            DepthEventFunctionData(depth, event, function_id, data)
            
        Where depth is an int (starting at 0), event ('call', 'return'),
        function_id an int, data as a CallReturnData object.
        """
        for value in self._gen_width_first(depth, 0):
            yield value
                
    def _gen_width_first(self, desired_depth, current_depth):
        """
        Recursive call to generate data points.
        Yields all the data points recursively, width first, as a named tuple::
        
            DepthEventFunctionData(depth, event, function_id, data)
            
        Where depth is an int (starting at 0), event ('call', 'return'),
        function_id an int, data as a CallReturnData object.
        """
        assert desired_depth >= 0
        assert current_depth >= 0
        if current_depth == desired_depth:
            # TODO: depth is always 0 in the data rather than true depth.
            yield DepthEventFunctionData(current_depth, 'call',
                                         self.function_id, self.data_call)
            yield DepthEventFunctionData(current_depth, 'return',
                                         self.function_id, self.data_return)
        else:
            for child in self.children:
                for child_data in child._gen_width_first(desired_depth,
                                                         current_depth + 1):
                    yield child_data
                
class FunctionCallTreeSequence:
    """
    This contains the current and historic call information from a sequence
    of function calls.
    """
    def __init__(self):
        # List of FunctionCallTree objects.
        self.function_trees = []
        
    def __len__(self):
        """Returns the number of top level functions."""
        return len(self.function_trees)
        
    def max_depth(self):
        """
        Returns the maximum call depth in this tree.
        A single function would return 1 so that the depths reported by
        ``gen_depth_first()`` are 0 <= d < max_depth(). 
        
        If empty will raise ValueError: 'max() arg is an empty sequence'
        """
        if len(self.function_trees) == 0:
            raise PyMemTraceMaxDepthOnEmptyTree(
                'FunctionCallTreeSequence.max_depth() on empty tree'
            )
        return max([tree.max_depth() for tree in self.function_trees])
    
    def max_width(self):
        """
        Returns the maximum call width as sum of all trees.
        A single function would return 1 so that the widths reported by
        ``gen_depth_first()`` are 0 <= w < max_width(). 
        
        If empty this returns 0.
        """
        return sum([tree.max_width() for tree in self.function_trees])
    
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

    def gen_depth_first(self):
        """
        Yields all the data points recursively, depth first, as a named tuple::
        
            WidthDepthEventFunctionData(width, depth, event, function_id, data)
            
        Where width is an int (starting at 0), depth is an int (starting at 0),
        event is one of ``('call', 'return')``, function_id an int, data as a
        named tuple ``CallReturnData(time, memory)`` object.
        """
        for width, ft in enumerate(self.function_trees):
            for value in ft.gen_depth_first():
                yield WidthDepthEventFunctionData(width, *value)

    def gen_width_first(self):
        """
        Yields all the data points recursively, width first, as a named tuple::
        
            WidthDepthEventFunctionData(width, depth, event, function_id, data)
            
        Where width is an int (starting at 0), depth is an int (starting at 0),
        event is one of ``('call', 'return')``, function_id an int, data as a
        named tuple ``CallReturnData(time, memory)`` object.
        """
        depth = 0
        try:
            max_depth = self.max_depth()
        except PyMemTraceMaxDepthOnEmptyTree:
            max_depth = 0 # Implicitly makes this function a NOP
        for depth in range(max_depth):
            width = 0
            for ft in self.function_trees:
                for value in ft.gen_width_first(depth):
                    # Function events are in pairs (call/return) so // 2
                    yield WidthDepthEventFunctionData(width // 2, *value)
                    width += 1

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
        # Created by finalise() as CallReturnData objects.
        self.data_final = None
        # These are maintained dynamically as a list of fields but then
        # converted to a CallReturnData in finalise()
        self.data_min = {f : None for f in CallReturnData._fields}
        self.data_max = {f : None for f in CallReturnData._fields}
        # Create initial and final conditions
        # NOTE: self.data_initial and self.data_final are obtained by polling
        # the OS.
        # self.data_min/self.data_max are min/max seen by add_data_point() and
        # these will ne be the same, particularly if synthetic call/return data
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
        return CallReturnData(self.time(), self.memory())
    
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
        self.data_min = CallReturnData(**self.data_min)
        self.data_max = CallReturnData(**self.data_max)

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
