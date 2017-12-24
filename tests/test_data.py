#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `pymemtrace` package."""
import inspect
import pprint
import sys
import time

try:
    import hypothesis
except ImportError:
    pass

import pytest

from pymemtrace import data

def test_CallReturnData():
    crd = data.CallReturnData(1.2, 14)
    assert crd.time == 1.2
    assert crd.memory == 14

def test_CallReturnData__sub__():
    crd_0 = data.CallReturnData(0.0, 8)
    crd_1 = data.CallReturnData(16.0, 32)
    diff = crd_1 - crd_0
    assert diff.time == 16.0
    assert diff.memory == 24
    diff = crd_0 - crd_1
    assert diff.time == -16.0
    assert diff.memory == -24

def test_CallReturnData__isub__():
    crd = data.CallReturnData(16.0, 32)
    crd -= data.CallReturnData(0.0, 8)
    assert crd.time == 16.0
    assert crd.memory == 24
    crd = data.CallReturnData(0.0, 8)
    crd -= data.CallReturnData(16.0, 32)
    assert crd.time == -16.0
    assert crd.memory == -24

def test_CallReturnData__str__():
    crd = data.CallReturnData(1.2, 14)
    assert str(crd) == '1,200,000 (us) 0.014 (kb)'
    assert '{!s:s}'.format(crd) == '1,200,000 (us) 0.014 (kb)'

def test_CallReturnData__repr__():
    crd = data.CallReturnData(1.2, 14)
    assert repr(crd) == 'CallReturnData(time=1.2, memory=14)'
    assert '{!r:s}'.format(crd) == 'CallReturnData(time=1.2, memory=14)'

#---- Test FunctionEncoder ----
def test_FunctionEncoder_mt():
    fe = data.FunctionEncoder()
    assert len(fe) == 0

def test_FunctionEncoder_encode():
    fe = data.FunctionEncoder()
    assert fe.encode('file', 'function', 12) == 0

def test_FunctionEncoder_encode_same():
    fe = data.FunctionEncoder()
    assert fe.encode('file', 'function', 12) == 0
    assert fe.encode('file', 'function', 12) == 0
    assert len(fe) == 1
    assert fe.integrity()

def test_FunctionEncoder_encode_diff_file():
    fe = data.FunctionEncoder()
    assert fe.encode('file', 'function', 12) == 0
    assert fe.encode('file_two', 'function', 12) == 1
    assert len(fe) == 2
    assert fe.integrity()

def test_FunctionEncoder_encode_diff_function():
    fe = data.FunctionEncoder()
    assert fe.encode('file', 'function', 12) == 0
    assert fe.encode('file', 'function_two', 12) == 1
    assert len(fe) == 2
    assert fe.integrity()

def test_FunctionEncoder_encode_diff_line():
    fe = data.FunctionEncoder()
    assert fe.encode('file', 'function', 12) == 0
    assert fe.encode('file', 'function', 14) == 1
    assert len(fe) == 2
    assert fe.integrity()

def test_FunctionEncoder_encode_raises_lineno():
    fe = data.FunctionEncoder()
    with pytest.raises(ValueError):
        fe.encode('file', 'function', -12)
    assert len(fe) == 0
    assert fe.integrity()

def test_FunctionEncoder_encode_decode():
    fe = data.FunctionEncoder()
    assert fe.encode('file', 'function', 12) == 0
    assert fe.decode(0) == ('file', 'function', 12)
    assert len(fe) == 1
    assert fe.integrity()

@pytest.mark.skipif('hypothesis' not in sys.modules, reason='hypothesis not installed')
@hypothesis.given(
    hypothesis.strategies.text(),
    hypothesis.strategies.text(),
    hypothesis.strategies.integers(min_value=1, max_value=None),
)
def test_hypothesis_FunctionEncoder_encode_decode(file_path, function, lineno):
    fe = data.FunctionEncoder()
    function_id = fe.encode(file_path, function, lineno)
    assert len(fe) == 1
    assert fe.integrity()
    assert fe.decode(function_id) == (file_path, function, lineno)
#---- END: Test FunctionEncoder ----

#---- Test FunctionCallTree ----
def test_FunctionCallTree_call_only():
    function_id = 0
    call_data = data.CallReturnData(0.0, 1)
    fe = data.FunctionCallTree(function_id, call_data)
    assert fe.is_open
    assert fe.function_id == function_id
    assert fe.data_call == call_data
    assert fe.data_return is None
    assert len(fe.children) == 0
    expected = [
        data.DepthEventFunctionData(0, 'call', function_id, call_data),
        data.DepthEventFunctionData(0, 'return', function_id, None),
    ]
    assert list(fe.gen_depth_first()) == expected
    assert list(fe.gen_width_first(0)) == expected
    assert fe.integrity()

def test_FunctionCallTree_call_return():
    function_id = 0
    call_data = data.CallReturnData(0.0, 1)
    fe = data.FunctionCallTree(function_id, call_data)
    assert fe.is_open
    return_data = data.CallReturnData(0.1, 2)
    fe.add_return(function_id, return_data)
    assert not fe.is_open
    assert fe.function_id == function_id
    assert fe.data_call == call_data
    assert fe.data_return == return_data
    assert len(fe.children) == 0
    expected = [
        data.DepthEventFunctionData(0, 'call', function_id, call_data),
        data.DepthEventFunctionData(0, 'return', function_id, return_data),
    ]
    assert list(fe.gen_depth_first()) == expected
    assert list(fe.gen_width_first(0)) == expected
    assert fe.integrity()

def test_FunctionCallTree_call_return_raised_on_ID():
    function_id = 0
    call_data = data.CallReturnData(0.0, 1)
    fe = data.FunctionCallTree(function_id, call_data)
    return_data = data.CallReturnData(0.1, 2)
    with pytest.raises(ValueError):
        fe.add_return(function_id + 1, return_data)

def test_FunctionCallTree_call_return_2():
    function_id = 0
    call_data = [
        data.CallReturnData(0.0, 1),
        data.CallReturnData(0.1, 2),
    ]
    return_data = [
        data.CallReturnData(0.2, 3),
        data.CallReturnData(0.3, 4),
    ]
    
    fe = data.FunctionCallTree(function_id, call_data[0])
    assert fe.is_open
    fe.add_call(function_id + 1, call_data[1])
    assert fe.is_open
    fe.add_return(function_id + 1, return_data[1])
    assert fe.is_open
    fe.add_return(function_id, return_data[0])
    assert not fe.is_open
    
    assert len(fe.children) == 1
    assert fe.integrity()
    # Depth first.
    expected_depth = [
        data.DepthEventFunctionData(0, 'call', function_id, call_data[0]),
        data.DepthEventFunctionData(1, 'call', function_id + 1, call_data[1]),
        data.DepthEventFunctionData(1, 'return', function_id + 1, return_data[1]),
        data.DepthEventFunctionData(0, 'return', function_id, return_data[0]),
    ]
    result = list(fe.gen_depth_first())
#     print()
#     pprint.pprint(result)
    assert result == expected_depth
    # Width first.
    expected_width = [
        [
            data.DepthEventFunctionData(0, 'call', function_id, call_data[0]),
            data.DepthEventFunctionData(0, 'return', function_id, return_data[0]),
        ],
        [
            data.DepthEventFunctionData(1, 'call', function_id + 1, call_data[1]),
            data.DepthEventFunctionData(1, 'return', function_id + 1, return_data[1]),
        ],
    ]
    assert list(fe.gen_width_first(0)) == expected_width[0]
#     print()
#     pprint.pprint(list(fe.gen_width_first(1)))
    assert list(fe.gen_width_first(1)) == expected_width[1]

def test_FunctionCallTree_call_return_3():
    function_id = 0
    call_data = [
        data.CallReturnData(1.0, 1),
        data.CallReturnData(1.1, 2),
        data.CallReturnData(1.2, 3),
    ]
    return_data = [
        data.CallReturnData(10.0, 10),
        data.CallReturnData(20.0, 20),
        data.CallReturnData(30.0, 30),
    ]
    
    fe = data.FunctionCallTree(function_id, call_data[0])
    assert fe.is_open
    fe.add_call(function_id + 1, call_data[1])
    assert fe.is_open
    fe.add_call(function_id + 2, call_data[2])
    assert fe.is_open
    fe.add_return(function_id + 2, return_data[2])
    assert fe.is_open
    fe.add_return(function_id + 1, return_data[1])
    assert fe.is_open
    fe.add_return(function_id, return_data[0])
    assert not fe.is_open
    
    assert len(fe.children) == 1
    assert fe.integrity()
    expected_depth = [
        data.DepthEventFunctionData(0, 'call', function_id, call_data[0]),
        data.DepthEventFunctionData(1, 'call', function_id + 1, call_data[1]),
        data.DepthEventFunctionData(2, 'call', function_id + 2, call_data[2]),
        data.DepthEventFunctionData(2, 'return', function_id + 2, return_data[2]),
        data.DepthEventFunctionData(1, 'return', function_id + 1, return_data[1]),
        data.DepthEventFunctionData(0, 'return', function_id, return_data[0]),
    ]
    result = list(fe.gen_depth_first())
#     print()
#     pprint.pprint(result)
    assert result == expected_depth
    expected_width = [
        [
            data.DepthEventFunctionData(0, 'call', function_id, call_data[0]),
            data.DepthEventFunctionData(0, 'return', function_id, return_data[0]),
        ],
        [
            data.DepthEventFunctionData(1, 'call', function_id + 1, call_data[1]),
            data.DepthEventFunctionData(1, 'return', function_id + 1, return_data[1]),
        ],
        [
            data.DepthEventFunctionData(2, 'call', function_id + 2, call_data[2]),
            data.DepthEventFunctionData(2, 'return', function_id + 2, return_data[2]),
        ],
    ]
    assert list(fe.gen_width_first(0)) == expected_width[0]
    assert list(fe.gen_width_first(1)) == expected_width[1]
    assert list(fe.gen_width_first(2)) == expected_width[2]

def test_FunctionCallTree_call_return_call_raises():
    function_id = 0
    call_data = [
        data.CallReturnData(0.0, 1),
        data.CallReturnData(0.1, 2),
    ]
    return_data = [
        data.CallReturnData(0.2, 3),
        data.CallReturnData(0.3, 4),
    ]
    
    fe = data.FunctionCallTree(function_id, call_data[0])
    assert fe.is_open
    fe.add_return(function_id, return_data[0])
    assert not fe.is_open
    with pytest.raises(data.PyMemTraceCallReturnSequenceError):
        # Can not call when not open
        fe.add_call(function_id + 1, call_data[1])
    assert fe.integrity()

def test_FunctionCallTree_call_return_return_raises():
    function_id = 0
    call_data = data.CallReturnData(0.0, 1)
    fe = data.FunctionCallTree(function_id, call_data)
    return_data = data.CallReturnData(0.1, 2)
    fe.add_return(function_id, return_data)
    assert not fe.is_open
    with pytest.raises(data.PyMemTraceCallReturnSequenceError):
        # Can not return when not open
        fe.add_return(function_id, return_data)
    assert fe.integrity()

def test_FunctionCallTree_max_depth_2():
    function_id = 0
    call_data = [
        data.CallReturnData(0.0, 1),
        data.CallReturnData(0.1, 2),
    ]
    return_data = [
        data.CallReturnData(0.2, 3),
        data.CallReturnData(0.3, 4),
    ]
    
    fe = data.FunctionCallTree(function_id, call_data[0])
    assert fe.is_open
    fe.add_call(function_id + 1, call_data[1])
    assert fe.is_open
    fe.add_return(function_id + 1, return_data[1])
    assert fe.is_open
    fe.add_return(function_id, return_data[0])
    assert not fe.is_open
    
    assert fe.max_depth() == 2

def test_FunctionCallTree_max_depth_3():
    function_id = 0
    call_data = [
        data.CallReturnData(1.0, 1),
        data.CallReturnData(1.1, 2),
        data.CallReturnData(1.2, 3),
    ]
    return_data = [
        data.CallReturnData(10.0, 10),
        data.CallReturnData(20.0, 20),
        data.CallReturnData(30.0, 30),
    ]
    
    fe = data.FunctionCallTree(function_id, call_data[0])
    assert fe.is_open
    fe.add_call(function_id + 1, call_data[1])
    assert fe.is_open
    fe.add_call(function_id + 2, call_data[2])
    assert fe.is_open
    fe.add_return(function_id + 2, return_data[2])
    assert fe.is_open
    fe.add_return(function_id + 1, return_data[1])
    assert fe.is_open
    fe.add_return(function_id, return_data[0])
    assert not fe.is_open
    assert fe.max_depth() == 3

def test_FunctionCallTree_max_width_1():
    function_id = 0
    call_data = [
        data.CallReturnData(0.0, 1),
        data.CallReturnData(0.1, 2),
    ]
    return_data = [
        data.CallReturnData(0.2, 3),
        data.CallReturnData(0.3, 4),
    ]
    
    fe = data.FunctionCallTree(function_id, call_data[0])
    assert fe.is_open
    fe.add_call(function_id + 1, call_data[1])
    assert fe.is_open
    fe.add_return(function_id + 1, return_data[1])
    assert fe.is_open
    fe.add_return(function_id, return_data[0])
    assert not fe.is_open
    
    assert fe.max_width() == 1

def test_FunctionCallTree_max_width_2():
    function_id = 0
    call_data = [
        data.CallReturnData(1.0, 1),
        data.CallReturnData(1.1, 2),
        data.CallReturnData(1.2, 3),
    ]
    return_data = [
        data.CallReturnData(10.0, 10),
        data.CallReturnData(20.0, 20),
        data.CallReturnData(30.0, 30),
    ]
    
    fe = data.FunctionCallTree(function_id, call_data[0])
    assert fe.is_open
    fe.add_call(function_id + 1, call_data[1])
    assert fe.is_open
    fe.add_return(function_id + 1, return_data[1])
    assert fe.is_open
    fe.add_call(function_id + 2, call_data[2])
    assert fe.is_open
    fe.add_return(function_id + 2, return_data[2])
    assert fe.is_open
    fe.add_return(function_id, return_data[0])
    assert not fe.is_open
    
    assert fe.max_width() == 2
#---- END: Test FunctionCallTree ----

#---- Test FunctionCallTreeSequence ----
def test_FunctionCallTreeSequence_empty():
    fes = data.FunctionCallTreeSequence()
    assert len(fes) == 0
    assert fes.integrity()

def test_FunctionCallTreeSequence_empty_depth_first():
    fes = data.FunctionCallTreeSequence()
    assert list(fes.gen_depth_first()) == []

def test_FunctionCallTreeSequence_empty_width_first():
    fes = data.FunctionCallTreeSequence()
    assert list(fes.gen_width_first()) == []

def test_FunctionCallTreeSequence_empty_max_depth_raises():
    fes = data.FunctionCallTreeSequence()
    with pytest.raises(data.PyMemTraceMaxDepthOnEmptyTree) as err:
        fes.max_depth()
    assert err.value.args[0] == 'FunctionCallTreeSequence.max_depth() on empty tree'

def test_FunctionCallTreeSequence_call_and_return_depth_two():
    function_id = 0
    call_data = [
        data.CallReturnData(0.0, 1),
        data.CallReturnData(0.1, 2),
    ]
    return_data = [
        data.CallReturnData(0.2, 3),
        data.CallReturnData(0.3, 4),
    ]
    fes = data.FunctionCallTreeSequence()
    fes.add_call_return_event('call', function_id, call_data[0])
    fes.add_call_return_event('call', function_id + 1, call_data[1])
    fes.add_call_return_event('return', function_id + 1, return_data[1])
    fes.add_call_return_event('return', function_id, return_data[0])
    
    assert len(fes) == 1
    assert fes.integrity()
    expected_depth = [
        data.WidthDepthEventFunctionData(0, 0, 'call', function_id, call_data[0]),
        data.WidthDepthEventFunctionData(0, 1, 'call', function_id + 1, call_data[1]),
        data.WidthDepthEventFunctionData(0, 1, 'return', function_id + 1, return_data[1]),
        data.WidthDepthEventFunctionData(0, 0, 'return', function_id, return_data[0]),
    ]
    result = list(fes.gen_depth_first())
#     print()
#     pprint.pprint(result)
    assert result == expected_depth
    expected_width = [
        data.WidthDepthEventFunctionData(0, 0, 'call', function_id, call_data[0]),
        data.WidthDepthEventFunctionData(0, 0, 'return', function_id, return_data[0]),
        data.WidthDepthEventFunctionData(0, 1, 'call', function_id + 1, call_data[1]),
        data.WidthDepthEventFunctionData(0, 1, 'return', function_id + 1, return_data[1]),
    ]
#     print()
#     pprint.pprint(list(fes.gen_width_first()))
    assert list(fes.gen_width_first()) == expected_width

def test_FunctionCallTreeSequence_call_and_return_width_two():
    function_id = 0
    call_data = [
        data.CallReturnData(0.0, 1),
        data.CallReturnData(0.1, 2),
    ]
    return_data = [
        data.CallReturnData(0.2, 3),
        data.CallReturnData(0.3, 4),
    ]
    
    fes = data.FunctionCallTreeSequence()
    fes.add_call_return_event('call', function_id, call_data[0])
    fes.add_call_return_event('return', function_id, return_data[0])
    fes.add_call_return_event('call', function_id + 1, call_data[1])
    fes.add_call_return_event('return', function_id + 1, return_data[1])
    
    assert len(fes) == 2
    assert fes.integrity()
    expected = [
        data.WidthDepthEventFunctionData(0, 0, 'call', function_id, call_data[0]),
        data.WidthDepthEventFunctionData(0, 0, 'return', function_id, return_data[0]),
        data.WidthDepthEventFunctionData(1, 0, 'call', function_id + 1, call_data[1]),
        data.WidthDepthEventFunctionData(1, 0, 'return', function_id + 1, return_data[1]),
    ]
    result = list(fes.gen_depth_first())
#     print()
#     pprint.pprint(result)
    assert result == expected
    assert list(fes.gen_width_first()) == expected

def test_FunctionCallTreeSequence_call_and_return_depth_width_two():
    function_id = 0
    call_data = [
        data.CallReturnData(0.0, 1),
        data.CallReturnData(0.1, 2),
        data.CallReturnData(0.2, 3),
        data.CallReturnData(0.3, 4),
    ]
    return_data = [
        data.CallReturnData(1.0, 10),
        data.CallReturnData(2.0, 20),
        data.CallReturnData(3.0, 30),
        data.CallReturnData(4.0, 40),
    ]
    
    fes = data.FunctionCallTreeSequence()
    # Width[0], depth 0, 1
    fes.add_call_return_event('call', function_id, call_data[0])
    fes.add_call_return_event('call', function_id + 1, call_data[1])
    fes.add_call_return_event('return', function_id + 1, return_data[1])
    fes.add_call_return_event('return', function_id, return_data[0])
    # Width[1], depth 0, 1
    fes.add_call_return_event('call', function_id + 2, call_data[2])
    fes.add_call_return_event('call', function_id + 3, call_data[3])
    fes.add_call_return_event('return', function_id + 3, return_data[3])
    fes.add_call_return_event('return', function_id + 2, return_data[2])
    
    assert len(fes) == 2
    assert fes.integrity()
    expected_depth = [
        data.WidthDepthEventFunctionData(
            0, 0, 'call', 0, data.CallReturnData(time=0.0, memory=1)),
        data.WidthDepthEventFunctionData(
            0, 1, 'call', 1, data.CallReturnData(time=0.1, memory=2)),
        data.WidthDepthEventFunctionData(
            0, 1, 'return', 1, data.CallReturnData(time=2.0, memory=20)),
        data.WidthDepthEventFunctionData(
            0, 0, 'return', 0, data.CallReturnData(time=1.0, memory=10)),
        data.WidthDepthEventFunctionData(
            1, 0, 'call', 2, data.CallReturnData(time=0.2, memory=3)),
        data.WidthDepthEventFunctionData(
            1, 1, 'call', 3, data.CallReturnData(time=0.3, memory=4)),
        data.WidthDepthEventFunctionData(
            1, 1, 'return', 3, data.CallReturnData(time=4.0, memory=40)),
        data.WidthDepthEventFunctionData(
            1, 0, 'return', 2, data.CallReturnData(time=3.0, memory=30)),
    ]
    result = list(fes.gen_depth_first())
#     print()
#     pprint.pprint(result)
    assert result == expected_depth
    expected_width = [
        data.WidthDepthEventFunctionData(
            0, 0, 'call', 0, data.CallReturnData(time=0.0, memory=1)),
        data.WidthDepthEventFunctionData(
            0, 0, 'return', 0, data.CallReturnData(time=1.0, memory=10)),
        data.WidthDepthEventFunctionData(
            1, 0, 'call', 2, data.CallReturnData(time=0.2, memory=3)),
        data.WidthDepthEventFunctionData(
            1, 0, 'return', 2, data.CallReturnData(time=3.0, memory=30)),
        data.WidthDepthEventFunctionData(
            0, 1, 'call', 1, data.CallReturnData(time=0.1, memory=2)),
        data.WidthDepthEventFunctionData(
            0, 1, 'return', 1, data.CallReturnData(time=2.0, memory=20)),
        data.WidthDepthEventFunctionData(
            1, 1, 'call', 3, data.CallReturnData(time=0.3, memory=4)),
        data.WidthDepthEventFunctionData(
            1, 1, 'return', 3, data.CallReturnData(time=4.0, memory=40)),
    ]
#     print()
#     pprint.pprint(list(fes.gen_width_first()))
    assert list(fes.gen_width_first()) == expected_width

def test_FunctionCallTreeSequence_max_depth_two():
    function_id = 0
    call_data = [
        data.CallReturnData(0.0, 1),
        data.CallReturnData(0.1, 2),
    ]
    return_data = [
        data.CallReturnData(0.2, 3),
        data.CallReturnData(0.3, 4),
    ]
    fes = data.FunctionCallTreeSequence()
    fes.add_call_return_event('call', function_id, call_data[0])
    fes.add_call_return_event('call', function_id + 1, call_data[1])
    fes.add_call_return_event('return', function_id + 1, return_data[1])
    fes.add_call_return_event('return', function_id, return_data[0])
    assert fes.integrity()
    assert fes.max_depth() == 2

def test_FunctionCallTreeSequence_max_width_two():
    function_id = 0
    call_data = [
        data.CallReturnData(0.0, 1),
        data.CallReturnData(0.1, 2),
    ]
    return_data = [
        data.CallReturnData(0.2, 3),
        data.CallReturnData(0.3, 4),
    ]
    fes = data.FunctionCallTreeSequence()
    fes.add_call_return_event('call', function_id, call_data[0])
    fes.add_call_return_event('call', function_id + 1, call_data[1])
    fes.add_call_return_event('return', function_id + 1, return_data[1])
    fes.add_call_return_event('return', function_id, return_data[0])
    assert fes.integrity()
    assert fes.max_width() == 1

def test_FunctionCallTreeSequence_max_width_raises():
    fes = data.FunctionCallTreeSequence()
    assert fes.integrity()
    fes.max_width() == 0

#---- END: Test FunctionCallTreeSequence ----