#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `pymemtrace` package."""
import pprint
import sys

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
    assert list(fe.gen_call_return_data()) == expected
    assert fe.integrity()

def test_FunctionCallTree_call_and_return():
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
    assert list(fe.gen_call_return_data()) == expected
    assert fe.integrity()

def test_FunctionCallTree_call_and_return_depth_two():
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
    expected = [
        pymemtrace.DepthEventFunctionData(0, 'call', function_id, call_data[0]),
        pymemtrace.DepthEventFunctionData(1, 'call', function_id + 1, call_data[1]),
        pymemtrace.DepthEventFunctionData(1, 'return', function_id + 1, return_data[1]),
        pymemtrace.DepthEventFunctionData(0, 'return', function_id, return_data[0]),
    ]
    result = list(fe.gen_call_return_data())
#     print()
#     pprint.pprint(result)
    assert result == expected
    assert fe.integrity()

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
    with pytest.raises(pymemtrace.CallReturnSequenceError):
        # Can not call when not open
        fe.add_call(function_id + 1, call_data[1])
    assert fe.integrity()

#     assert fe.is_open
#     fe.add_return(function_id + 1, return_data[1])
#     assert not fe.is_open
#     
#     assert len(fe.children) == 2
#     expected = [
#         ('call', function_id, call_data[0]),
#         ('call', function_id + 1, call_data[1]),
#         ('return', function_id + 1, return_data[1]),
#         ('return', function_id, return_data[0]),
#     ]
#     result = list(fe.gen_call_return_data())
#     print()
#     pprint.pprint(result)
#     assert result == expected

#---- END: Test FunctionCallTree ----

#---- Test FunctionCallTreeSequence ----
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
    expected = [
        pymemtrace.WidthDepthEventFunctionData(0, 0, 'call', function_id, call_data[0]),
        pymemtrace.WidthDepthEventFunctionData(0, 1, 'call', function_id + 1, call_data[1]),
        pymemtrace.WidthDepthEventFunctionData(0, 1, 'return', function_id + 1, return_data[1]),
        pymemtrace.WidthDepthEventFunctionData(0, 0, 'return', function_id, return_data[0]),
    ]
    result = list(fes.gen_call_return_data())
#     print()
#     pprint.pprint(result)
    assert result == expected
    assert fes.integrity()

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
    expected = [
        pymemtrace.WidthDepthEventFunctionData(0, 0, 'call', function_id, call_data[0]),
        pymemtrace.WidthDepthEventFunctionData(0, 0, 'return', function_id, return_data[0]),
        pymemtrace.WidthDepthEventFunctionData(1, 0, 'call', function_id + 1, call_data[1]),
        pymemtrace.WidthDepthEventFunctionData(1, 0, 'return', function_id + 1, return_data[1]),
    ]
    result = list(fes.gen_call_return_data())
#     print()
#     pprint.pprint(result)
    assert result == expected
    assert fes.integrity()

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
    expected = [
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
    result = list(fes.gen_call_return_data())
#     print()
#     pprint.pprint(result)
    assert result == expected
    assert fes.integrity()

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
    pprint.pprint(list(mt.function_tree_seq.gen_call_return_data()))
    print('Initial:', mt.data_initial)
    print('  Final:', mt.data_final)
    print('  Range:', mt.data_final - mt.data_initial)
    print('Minimum:', mt.data_min)
    print('Maximum:', mt.data_max)
    print('  Range:', mt.data_max - mt.data_min)



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
