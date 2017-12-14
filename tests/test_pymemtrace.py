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

from pymemtrace import pymemtrace

def test_CallReturnData():
    crd = pymemtrace.CallReturnData(1.2, 14)
    assert crd.time == 1.2
    assert crd.memory == 14

def test_CallReturnData__sub__():
    crd_0 = pymemtrace.CallReturnData(0.0, 8)
    crd_1 = pymemtrace.CallReturnData(16.0, 32)
    diff = crd_1 - crd_0
    assert diff.time == 16.0
    assert diff.memory == 24
    diff = crd_0 - crd_1
    assert diff.time == -16.0
    assert diff.memory == -24

def test_CallReturnData__isub__():
    crd = pymemtrace.CallReturnData(16.0, 32)
    crd -= pymemtrace.CallReturnData(0.0, 8)
    assert crd.time == 16.0
    assert crd.memory == 24
    crd = pymemtrace.CallReturnData(0.0, 8)
    crd -= pymemtrace.CallReturnData(16.0, 32)
    assert crd.time == -16.0
    assert crd.memory == -24

def test_CallReturnData__str__():
    crd = pymemtrace.CallReturnData(1.2, 14)
    assert str(crd) == '1,200,000 (us) 0.014 (kb)'
    assert '{!s:s}'.format(crd) == '1,200,000 (us) 0.014 (kb)'

def test_CallReturnData__repr__():
    crd = pymemtrace.CallReturnData(1.2, 14)
    assert repr(crd) == 'CallReturnData(time=1.2, memory=14)'
    assert '{!r:s}'.format(crd) == 'CallReturnData(time=1.2, memory=14)'

#---- Test FunctionEncoder ----
def test_FunctionEncoder_mt():
    fe = pymemtrace.FunctionEncoder()
    assert len(fe) == 0

def test_FunctionEncoder_encode():
    fe = pymemtrace.FunctionEncoder()
    assert fe.encode('file', 'function', 12) == 0

def test_FunctionEncoder_encode_same():
    fe = pymemtrace.FunctionEncoder()
    assert fe.encode('file', 'function', 12) == 0
    assert fe.encode('file', 'function', 12) == 0
    assert len(fe) == 1
    assert fe.integrity()

def test_FunctionEncoder_encode_diff_file():
    fe = pymemtrace.FunctionEncoder()
    assert fe.encode('file', 'function', 12) == 0
    assert fe.encode('file_two', 'function', 12) == 1
    assert len(fe) == 2
    assert fe.integrity()

def test_FunctionEncoder_encode_diff_function():
    fe = pymemtrace.FunctionEncoder()
    assert fe.encode('file', 'function', 12) == 0
    assert fe.encode('file', 'function_two', 12) == 1
    assert len(fe) == 2
    assert fe.integrity()

def test_FunctionEncoder_encode_diff_line():
    fe = pymemtrace.FunctionEncoder()
    assert fe.encode('file', 'function', 12) == 0
    assert fe.encode('file', 'function', 14) == 1
    assert len(fe) == 2
    assert fe.integrity()

def test_FunctionEncoder_encode_raises_lineno():
    fe = pymemtrace.FunctionEncoder()
    with pytest.raises(ValueError):
        fe.encode('file', 'function', -12)
    assert len(fe) == 0
    assert fe.integrity()

def test_FunctionEncoder_encode_decode():
    fe = pymemtrace.FunctionEncoder()
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
    fe = pymemtrace.FunctionEncoder()
    function_id = fe.encode(file_path, function, lineno)
    assert len(fe) == 1
    assert fe.integrity()
    assert fe.decode(function_id) == (file_path, function, lineno)
#---- END: Test FunctionEncoder ----

#---- Test FunctionCallTree ----
def test_FunctionCallTree_call_only():
    function_id = 0
    call_data = pymemtrace.CallReturnData(0.0, 1)
    fe = pymemtrace.FunctionCallTree(function_id, call_data)
    assert fe.is_open
    assert fe.function_id == function_id
    assert fe.data_call == call_data
    assert fe.data_return is None
    assert len(fe.children) == 0
    expected = [
        pymemtrace.DepthEventFunctionData(0, 'call', function_id, call_data),
        pymemtrace.DepthEventFunctionData(0, 'return', function_id, None),
    ]
    assert list(fe.gen_depth_first()) == expected
    assert list(fe.gen_width_first(0)) == expected
    assert fe.integrity()

def test_FunctionCallTree_call_return():
    function_id = 0
    call_data = pymemtrace.CallReturnData(0.0, 1)
    fe = pymemtrace.FunctionCallTree(function_id, call_data)
    assert fe.is_open
    return_data = pymemtrace.CallReturnData(0.1, 2)
    fe.add_return(function_id, return_data)
    assert not fe.is_open
    assert fe.function_id == function_id
    assert fe.data_call == call_data
    assert fe.data_return == return_data
    assert len(fe.children) == 0
    expected = [
        pymemtrace.DepthEventFunctionData(0, 'call', function_id, call_data),
        pymemtrace.DepthEventFunctionData(0, 'return', function_id, return_data),
    ]
    assert list(fe.gen_depth_first()) == expected
    assert list(fe.gen_width_first(0)) == expected
    assert fe.integrity()

def test_FunctionCallTree_call_return_raised_on_ID():
    function_id = 0
    call_data = pymemtrace.CallReturnData(0.0, 1)
    fe = pymemtrace.FunctionCallTree(function_id, call_data)
    return_data = pymemtrace.CallReturnData(0.1, 2)
    with pytest.raises(ValueError):
        fe.add_return(function_id + 1, return_data)

def test_FunctionCallTree_call_return_2():
    function_id = 0
    call_data = [
        pymemtrace.CallReturnData(0.0, 1),
        pymemtrace.CallReturnData(0.1, 2),
    ]
    return_data = [
        pymemtrace.CallReturnData(0.2, 3),
        pymemtrace.CallReturnData(0.3, 4),
    ]
    
    fe = pymemtrace.FunctionCallTree(function_id, call_data[0])
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
        pymemtrace.DepthEventFunctionData(0, 'call', function_id, call_data[0]),
        pymemtrace.DepthEventFunctionData(1, 'call', function_id + 1, call_data[1]),
        pymemtrace.DepthEventFunctionData(1, 'return', function_id + 1, return_data[1]),
        pymemtrace.DepthEventFunctionData(0, 'return', function_id, return_data[0]),
    ]
    result = list(fe.gen_depth_first())
#     print()
#     pprint.pprint(result)
    assert result == expected_depth
    # Width first.
    expected_width = [
        [
            pymemtrace.DepthEventFunctionData(0, 'call', function_id, call_data[0]),
            pymemtrace.DepthEventFunctionData(0, 'return', function_id, return_data[0]),
        ],
        [
            pymemtrace.DepthEventFunctionData(1, 'call', function_id + 1, call_data[1]),
            pymemtrace.DepthEventFunctionData(1, 'return', function_id + 1, return_data[1]),
        ],
    ]
    assert list(fe.gen_width_first(0)) == expected_width[0]
#     print()
#     pprint.pprint(list(fe.gen_width_first(1)))
    assert list(fe.gen_width_first(1)) == expected_width[1]

def test_FunctionCallTree_call_return_3():
    function_id = 0
    call_data = [
        pymemtrace.CallReturnData(1.0, 1),
        pymemtrace.CallReturnData(1.1, 2),
        pymemtrace.CallReturnData(1.2, 3),
    ]
    return_data = [
        pymemtrace.CallReturnData(10.0, 10),
        pymemtrace.CallReturnData(20.0, 20),
        pymemtrace.CallReturnData(30.0, 30),
    ]
    
    fe = pymemtrace.FunctionCallTree(function_id, call_data[0])
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
        pymemtrace.DepthEventFunctionData(0, 'call', function_id, call_data[0]),
        pymemtrace.DepthEventFunctionData(1, 'call', function_id + 1, call_data[1]),
        pymemtrace.DepthEventFunctionData(2, 'call', function_id + 2, call_data[2]),
        pymemtrace.DepthEventFunctionData(2, 'return', function_id + 2, return_data[2]),
        pymemtrace.DepthEventFunctionData(1, 'return', function_id + 1, return_data[1]),
        pymemtrace.DepthEventFunctionData(0, 'return', function_id, return_data[0]),
    ]
    result = list(fe.gen_depth_first())
#     print()
#     pprint.pprint(result)
    assert result == expected_depth
    expected_width = [
        [
            pymemtrace.DepthEventFunctionData(0, 'call', function_id, call_data[0]),
            pymemtrace.DepthEventFunctionData(0, 'return', function_id, return_data[0]),
        ],
        [
            pymemtrace.DepthEventFunctionData(1, 'call', function_id + 1, call_data[1]),
            pymemtrace.DepthEventFunctionData(1, 'return', function_id + 1, return_data[1]),
        ],
        [
            pymemtrace.DepthEventFunctionData(2, 'call', function_id + 2, call_data[2]),
            pymemtrace.DepthEventFunctionData(2, 'return', function_id + 2, return_data[2]),
        ],
    ]
    assert list(fe.gen_width_first(0)) == expected_width[0]
    assert list(fe.gen_width_first(1)) == expected_width[1]
    assert list(fe.gen_width_first(2)) == expected_width[2]

def test_FunctionCallTree_call_return_call_raises():
    function_id = 0
    call_data = [
        pymemtrace.CallReturnData(0.0, 1),
        pymemtrace.CallReturnData(0.1, 2),
    ]
    return_data = [
        pymemtrace.CallReturnData(0.2, 3),
        pymemtrace.CallReturnData(0.3, 4),
    ]
    
    fe = pymemtrace.FunctionCallTree(function_id, call_data[0])
    assert fe.is_open
    fe.add_return(function_id, return_data[0])
    assert not fe.is_open
    with pytest.raises(pymemtrace.PyMemTraceCallReturnSequenceError):
        # Can not call when not open
        fe.add_call(function_id + 1, call_data[1])
    assert fe.integrity()

def test_FunctionCallTree_call_return_return_raises():
    function_id = 0
    call_data = pymemtrace.CallReturnData(0.0, 1)
    fe = pymemtrace.FunctionCallTree(function_id, call_data)
    return_data = pymemtrace.CallReturnData(0.1, 2)
    fe.add_return(function_id, return_data)
    assert not fe.is_open
    with pytest.raises(pymemtrace.PyMemTraceCallReturnSequenceError):
        # Can not return when not open
        fe.add_return(function_id, return_data)
    assert fe.integrity()

def test_FunctionCallTree_max_depth_2():
    function_id = 0
    call_data = [
        pymemtrace.CallReturnData(0.0, 1),
        pymemtrace.CallReturnData(0.1, 2),
    ]
    return_data = [
        pymemtrace.CallReturnData(0.2, 3),
        pymemtrace.CallReturnData(0.3, 4),
    ]
    
    fe = pymemtrace.FunctionCallTree(function_id, call_data[0])
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
        pymemtrace.CallReturnData(1.0, 1),
        pymemtrace.CallReturnData(1.1, 2),
        pymemtrace.CallReturnData(1.2, 3),
    ]
    return_data = [
        pymemtrace.CallReturnData(10.0, 10),
        pymemtrace.CallReturnData(20.0, 20),
        pymemtrace.CallReturnData(30.0, 30),
    ]
    
    fe = pymemtrace.FunctionCallTree(function_id, call_data[0])
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
        pymemtrace.CallReturnData(0.0, 1),
        pymemtrace.CallReturnData(0.1, 2),
    ]
    return_data = [
        pymemtrace.CallReturnData(0.2, 3),
        pymemtrace.CallReturnData(0.3, 4),
    ]
    
    fe = pymemtrace.FunctionCallTree(function_id, call_data[0])
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
        pymemtrace.CallReturnData(1.0, 1),
        pymemtrace.CallReturnData(1.1, 2),
        pymemtrace.CallReturnData(1.2, 3),
    ]
    return_data = [
        pymemtrace.CallReturnData(10.0, 10),
        pymemtrace.CallReturnData(20.0, 20),
        pymemtrace.CallReturnData(30.0, 30),
    ]
    
    fe = pymemtrace.FunctionCallTree(function_id, call_data[0])
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
    fes = pymemtrace.FunctionCallTreeSequence()
    assert len(fes) == 0
    assert fes.integrity()

def test_FunctionCallTreeSequence_empty_depth_first():
    fes = pymemtrace.FunctionCallTreeSequence()
    assert list(fes.gen_depth_first()) == []

def test_FunctionCallTreeSequence_empty_width_first():
    fes = pymemtrace.FunctionCallTreeSequence()
    assert list(fes.gen_width_first()) == []

def test_FunctionCallTreeSequence_empty_max_depth_raises():
    fes = pymemtrace.FunctionCallTreeSequence()
    with pytest.raises(pymemtrace.PyMemTraceMaxDepthOnEmptyTree) as err:
        fes.max_depth()
    assert err.value.args[0] == 'FunctionCallTreeSequence.max_depth() on empty tree'

def test_FunctionCallTreeSequence_call_and_return_depth_two():
    function_id = 0
    call_data = [
        pymemtrace.CallReturnData(0.0, 1),
        pymemtrace.CallReturnData(0.1, 2),
    ]
    return_data = [
        pymemtrace.CallReturnData(0.2, 3),
        pymemtrace.CallReturnData(0.3, 4),
    ]
    fes = pymemtrace.FunctionCallTreeSequence()
    fes.add_call_return_event('call', function_id, call_data[0])
    fes.add_call_return_event('call', function_id + 1, call_data[1])
    fes.add_call_return_event('return', function_id + 1, return_data[1])
    fes.add_call_return_event('return', function_id, return_data[0])
    
    assert len(fes) == 1
    assert fes.integrity()
    expected_depth = [
        pymemtrace.WidthDepthEventFunctionData(0, 0, 'call', function_id, call_data[0]),
        pymemtrace.WidthDepthEventFunctionData(0, 1, 'call', function_id + 1, call_data[1]),
        pymemtrace.WidthDepthEventFunctionData(0, 1, 'return', function_id + 1, return_data[1]),
        pymemtrace.WidthDepthEventFunctionData(0, 0, 'return', function_id, return_data[0]),
    ]
    result = list(fes.gen_depth_first())
#     print()
#     pprint.pprint(result)
    assert result == expected_depth
    expected_width = [
        pymemtrace.WidthDepthEventFunctionData(0, 0, 'call', function_id, call_data[0]),
        pymemtrace.WidthDepthEventFunctionData(0, 0, 'return', function_id, return_data[0]),
        pymemtrace.WidthDepthEventFunctionData(0, 1, 'call', function_id + 1, call_data[1]),
        pymemtrace.WidthDepthEventFunctionData(0, 1, 'return', function_id + 1, return_data[1]),
    ]
#     print()
#     pprint.pprint(list(fes.gen_width_first()))
    assert list(fes.gen_width_first()) == expected_width

def test_FunctionCallTreeSequence_call_and_return_width_two():
    function_id = 0
    call_data = [
        pymemtrace.CallReturnData(0.0, 1),
        pymemtrace.CallReturnData(0.1, 2),
    ]
    return_data = [
        pymemtrace.CallReturnData(0.2, 3),
        pymemtrace.CallReturnData(0.3, 4),
    ]
    
    fes = pymemtrace.FunctionCallTreeSequence()
    fes.add_call_return_event('call', function_id, call_data[0])
    fes.add_call_return_event('return', function_id, return_data[0])
    fes.add_call_return_event('call', function_id + 1, call_data[1])
    fes.add_call_return_event('return', function_id + 1, return_data[1])
    
    assert len(fes) == 2
    assert fes.integrity()
    expected = [
        pymemtrace.WidthDepthEventFunctionData(0, 0, 'call', function_id, call_data[0]),
        pymemtrace.WidthDepthEventFunctionData(0, 0, 'return', function_id, return_data[0]),
        pymemtrace.WidthDepthEventFunctionData(1, 0, 'call', function_id + 1, call_data[1]),
        pymemtrace.WidthDepthEventFunctionData(1, 0, 'return', function_id + 1, return_data[1]),
    ]
    result = list(fes.gen_depth_first())
#     print()
#     pprint.pprint(result)
    assert result == expected
    assert list(fes.gen_width_first()) == expected

def test_FunctionCallTreeSequence_call_and_return_depth_width_two():
    function_id = 0
    call_data = [
        pymemtrace.CallReturnData(0.0, 1),
        pymemtrace.CallReturnData(0.1, 2),
        pymemtrace.CallReturnData(0.2, 3),
        pymemtrace.CallReturnData(0.3, 4),
    ]
    return_data = [
        pymemtrace.CallReturnData(1.0, 10),
        pymemtrace.CallReturnData(2.0, 20),
        pymemtrace.CallReturnData(3.0, 30),
        pymemtrace.CallReturnData(4.0, 40),
    ]
    
    fes = pymemtrace.FunctionCallTreeSequence()
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
        pymemtrace.WidthDepthEventFunctionData(
            0, 0, 'call', 0, pymemtrace.CallReturnData(time=0.0, memory=1)),
        pymemtrace.WidthDepthEventFunctionData(
            0, 1, 'call', 1, pymemtrace.CallReturnData(time=0.1, memory=2)),
        pymemtrace.WidthDepthEventFunctionData(
            0, 1, 'return', 1, pymemtrace.CallReturnData(time=2.0, memory=20)),
        pymemtrace.WidthDepthEventFunctionData(
            0, 0, 'return', 0, pymemtrace.CallReturnData(time=1.0, memory=10)),
        pymemtrace.WidthDepthEventFunctionData(
            1, 0, 'call', 2, pymemtrace.CallReturnData(time=0.2, memory=3)),
        pymemtrace.WidthDepthEventFunctionData(
            1, 1, 'call', 3, pymemtrace.CallReturnData(time=0.3, memory=4)),
        pymemtrace.WidthDepthEventFunctionData(
            1, 1, 'return', 3, pymemtrace.CallReturnData(time=4.0, memory=40)),
        pymemtrace.WidthDepthEventFunctionData(
            1, 0, 'return', 2, pymemtrace.CallReturnData(time=3.0, memory=30)),
    ]
    result = list(fes.gen_depth_first())
#     print()
#     pprint.pprint(result)
    assert result == expected_depth
    expected_width = [
        pymemtrace.WidthDepthEventFunctionData(
            0, 0, 'call', 0, pymemtrace.CallReturnData(time=0.0, memory=1)),
        pymemtrace.WidthDepthEventFunctionData(
            0, 0, 'return', 0, pymemtrace.CallReturnData(time=1.0, memory=10)),
        pymemtrace.WidthDepthEventFunctionData(
            1, 0, 'call', 2, pymemtrace.CallReturnData(time=0.2, memory=3)),
        pymemtrace.WidthDepthEventFunctionData(
            1, 0, 'return', 2, pymemtrace.CallReturnData(time=3.0, memory=30)),
        pymemtrace.WidthDepthEventFunctionData(
            0, 1, 'call', 1, pymemtrace.CallReturnData(time=0.1, memory=2)),
        pymemtrace.WidthDepthEventFunctionData(
            0, 1, 'return', 1, pymemtrace.CallReturnData(time=2.0, memory=20)),
        pymemtrace.WidthDepthEventFunctionData(
            1, 1, 'call', 3, pymemtrace.CallReturnData(time=0.3, memory=4)),
        pymemtrace.WidthDepthEventFunctionData(
            1, 1, 'return', 3, pymemtrace.CallReturnData(time=4.0, memory=40)),
    ]
#     print()
#     pprint.pprint(list(fes.gen_width_first()))
    assert list(fes.gen_width_first()) == expected_width

def test_FunctionCallTreeSequence_max_depth_two():
    function_id = 0
    call_data = [
        pymemtrace.CallReturnData(0.0, 1),
        pymemtrace.CallReturnData(0.1, 2),
    ]
    return_data = [
        pymemtrace.CallReturnData(0.2, 3),
        pymemtrace.CallReturnData(0.3, 4),
    ]
    fes = pymemtrace.FunctionCallTreeSequence()
    fes.add_call_return_event('call', function_id, call_data[0])
    fes.add_call_return_event('call', function_id + 1, call_data[1])
    fes.add_call_return_event('return', function_id + 1, return_data[1])
    fes.add_call_return_event('return', function_id, return_data[0])
    assert fes.integrity()
    assert fes.max_depth() == 2

def test_FunctionCallTreeSequence_max_width_two():
    function_id = 0
    call_data = [
        pymemtrace.CallReturnData(0.0, 1),
        pymemtrace.CallReturnData(0.1, 2),
    ]
    return_data = [
        pymemtrace.CallReturnData(0.2, 3),
        pymemtrace.CallReturnData(0.3, 4),
    ]
    fes = pymemtrace.FunctionCallTreeSequence()
    fes.add_call_return_event('call', function_id, call_data[0])
    fes.add_call_return_event('call', function_id + 1, call_data[1])
    fes.add_call_return_event('return', function_id + 1, return_data[1])
    fes.add_call_return_event('return', function_id, return_data[0])
    assert fes.integrity()
    assert fes.max_width() == 1

def test_FunctionCallTreeSequence_max_width_raises():
    fes = pymemtrace.FunctionCallTreeSequence()
    assert fes.integrity()
    fes.max_width() == 0

#---- END: Test FunctionCallTreeSequence ----

#---- Test MemTrace ----

def test_MemTrace_ctor():
    mt = pymemtrace.MemTrace()


def test_MemTrace_single_function():
    def single_function(n):
        return n * 2
    
    with pymemtrace.MemTrace() as mt:
        assert single_function(5) == 10
    print()
#     print(mt.function_tree_seq.function_trees)
    pprint.pprint(list(mt.function_tree_seq.gen_depth_first()))
    print('Initial:', mt.data_initial)
    print('  Final:', mt.data_final)
    print('  Range:', mt.data_final - mt.data_initial)
    print('Minimum:', mt.data_min)
    print('Maximum:', mt.data_max)
    print('  Range:', mt.data_max - mt.data_min)

def test_MemTrace_function_id():
    single_function_lineno = inspect.currentframe().f_lineno + 1
    def single_function(n):
        return n * 2
    
    with pymemtrace.MemTrace() as mt:
        assert single_function(5) == 10
    expected = pymemtrace.FunctionLocation(__file__, 'single_function', single_function_lineno)
    assert mt.decode_function_id(0) == expected

def test_MemTrace_function_id_raises():
    mt = pymemtrace.MemTrace()
    with pytest.raises(KeyError):
        mt.decode_function_id(0)

def test_MemTrace_multiple_functions():
    def inner_function(n):
        return n * 2
    
    def outer_function_0(n):
        return inner_function(n) * 2
    
    def outer_function_1(n):
        return inner_function(n) * 4
    
    with pymemtrace.MemTrace() as mt:
        assert outer_function_0(5) == 20
        assert outer_function_1(10) == 80
    print()
#     print(mt.function_tree_seq.function_trees)
    pprint.pprint(list(mt.function_tree_seq.gen_depth_first()))
    print('Initial:', mt.data_initial)
    print('  Final:', mt.data_final)
    print('  Range:', mt.data_final - mt.data_initial)
    print('Minimum:', mt.data_min)
    print('Maximum:', mt.data_max)
    print('  Range:', mt.data_max - mt.data_min)


def test_MemTrace_multiple_functions_real_memory_usage():
    KILO = 1024
    MEGA = KILO**2
    MEGA_10 = KILO**2
    def inner_function(lst):
        print('  inner_function():    sys.getsizeof(lst)', sys.getsizeof(lst))
        # Offset by 1024 to avoid interned numbers.
        result = list(range(KILO, len(lst) * 2 + KILO))
        print('  inner_function(): sys.getsizeof(result)', sys.getsizeof(result))
        return result
    
    def outer_function_0():
        lst = list(range(KILO, MEGA + KILO))
        print('outer_function_0():    sys.getsizeof(lst)', sys.getsizeof(lst))
        result = inner_function(lst)
        print('outer_function_0(): sys.getsizeof(result)', sys.getsizeof(result))
        return result
    
    def outer_function_1():
        lst = list(range(KILO, MEGA_10 + KILO))
        print('outer_function_1():    sys.getsizeof(lst)', sys.getsizeof(lst))
        result = inner_function(lst)
        print('outer_function_1(): sys.getsizeof(result)', sys.getsizeof(result))
        return result
    
    print()
    with pymemtrace.MemTrace() as mt:
        assert len(outer_function_0()) == 2 * MEGA
        assert len(outer_function_1()) == 2 * MEGA_10
    call_return_data = list(mt.function_tree_seq.gen_depth_first())
    diff_data = [
        (
            mt.decode_function_id(v.function_id)[1:],
            v.event,
            str(v.data - call_return_data[0].data),
        )
        for v in call_return_data[1:]
    ]
    initial_diff_data = [
        (
            mt.decode_function_id(v.function_id)[1:],
            v.event,
            str(v.data - mt.data_initial),
        )
        for v in call_return_data
    ]
    print()
#     print(mt.function_tree_seq.function_trees)
    print('call_return_data:')
    pprint.pprint(call_return_data)
    print()
    print('diff_data:')
    pprint.pprint(diff_data, width=132)
    print()
    print('initial_diff_data:')
    pprint.pprint(initial_diff_data, width=132)
    print()
    print('Initial:', mt.data_initial)
    print('  Final:', mt.data_final)
    print('  Range:', mt.data_final - mt.data_initial)
    print('Minimum:', mt.data_min)
    print('Maximum:', mt.data_max)
    print('  Range:', mt.data_max - mt.data_min)

def test_MemTrace_function_expected_time():
    DELAY = 0.25
    def timed_function():
        time.sleep(DELAY)
        
    with pymemtrace.MemTrace() as mt:
        assert timed_function() is None
    call_return_data = list(mt.function_tree_seq.gen_depth_first())
    assert len(call_return_data) == 2
    rng = mt.data_final - mt.data_initial
    assert rng.time > DELAY
    assert rng.time < DELAY + 0.010

def test_MemTrace_function_expected_memory():
    SIZE = 1024*1024
    def memory_function():
        long_str = ' ' * SIZE
        return long_str
        
    sizeof = 0
    with pymemtrace.MemTrace() as mt:
        long_str = memory_function()
        assert len(long_str) == SIZE
        sizeof = sys.getsizeof(long_str)
    call_return_data = list(mt.function_tree_seq.gen_depth_first())
    assert len(call_return_data) == 2
    rng = mt.data_final - mt.data_initial
    print()
    print(rng)
    # len: 1048576
    # sizeof: 1048625, +49
    # Memory: 1052672, +4047, or * 1.00385933961
    assert sizeof < rng.memory < sizeof * 1.005

#---- END: Test MemTrace ----

@pytest.fixture
def response():
    """Sample pytest fixture.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/audreyr/cookiecutter-pypackage')


def test_content(response):
    """Sample pytest test function with the pytest fixture as an argument."""
    # from bs4 import BeautifulSoup
    # assert 'GitHub' in BeautifulSoup(response.content).title.string
