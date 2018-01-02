'''
Data structures used by pymemtrace
'''
# import argparse
# import array
# import bisect
import collections
# import inspect
# import logging
# import os
# import re
import sys
# import time

class ExceptionPyMemTraceBase(Exception):
    pass

class PyMemTraceCallReturnSequenceError(ExceptionPyMemTraceBase):
    pass

class PyMemTraceMaxDepthOnEmptyTree(ExceptionPyMemTraceBase):
    """Raised when max_depth() is called on an empty tree.
    max() of an empty sequence raises a generic ValueError.
    This specialises that error."""
    pass

class FunctionLocation(collections.namedtuple('FunctionLocation',
                                              ['filename', 'function', 'lineno'])):
    __slots__ = ()
    
    def __sizeof__(self):
        return sys.getsizeof(tuple()) + sys.getsizeof(self.filename) \
            + sys.getsizeof(self.function) + sys.getsizeof(self.lineno)

FunctionLocation.__doc__ = 'Function location.'
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
        # {FunctionLocation(file_path, function, lineno) : int, ...}
        # Where lineno is the first call event, subsequent call events
        # might have greater line numbers (e.g. generators).
        # lineno of function declaration can be obtained from
        # frame.f_code.co_firstlineno  
        self.id_lookup = {}
        # Reverse lookup.
        # {int : FunctionLocation(file_path, function, lineno), ...}
        self.id_rev_lookup = {}
    
    def __len__(self):
        return len(self.id_lookup)
    
    def __sizeof__(self):
        # Will raise a RuntimeError if this is called within a trace function
        # as the dict will be mutated whilst iterated.
        s = sys.getsizeof(dict())
        for k, v in self.id_lookup.items():
            s += sys.getsizeof(k)
            s += sys.getsizeof(v)
        return 2 * s
    
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
        Decode the int function_id to the original as a named tuple::
        
            FunctionLocation(filename, function, lineno)
        
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
    
    def __sizeof__(self):
        return sys.getsizeof(tuple()) + sys.getsizeof(self.time) + sys.getsizeof(self.memory)
    
    def __str__(self):
#         return '{:0,.0f} (us) {:0,.3f} (kb)'.format(self.time * 1e6, self.memory / 1024)
        return '{:s} {:s}'.format(*self.str_pair())

    def str_pair(self):
        """Returns the data nicely formated as a tuple of strings."""
        return (
            '{:0,.0f} (ms)'.format(self.time * 1e3),
            '{:0,.0f} (kb)'.format(self.memory / 1024)
        )

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
        # An int
        self.function_id = function_id
        # namedtuple CallReturnData
        self.data_call = data_call
        # None or namedtuple CallReturnData
        self.data_return = None
        # Child nodes, each is a FunctionCallTree.
        self.children = []
    
    def __sizeof__(self):
        s = sys.getsizeof(self.function_id)
        s += sys.getsizeof(self.data_call) 
        s += sys.getsizeof(self.data_return)
        s += sum([sys.getsizeof(c) for c in self.children])
        return s 
    
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
            # TODO: Event filtering: self.children.pop() if data_return is small?   
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
        
    def __sizeof__(self):
        s = sys.getsizeof(list())
        s += sum([sys.getsizeof(t) for t in self.function_trees])
        return s 

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
        # TODO: Have a filter function to filter data value so that small
        # values are not accumulated.
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
        # TODO: Could filter data here, or at acquisition time.
        for width, ft in enumerate(self.function_trees):
            for value in ft.gen_depth_first():
                # value is a a named tuple:
                # DepthEventFunctionData(depth, event, function_id, data)
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
