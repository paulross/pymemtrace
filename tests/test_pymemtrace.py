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
from pymemtrace import data

#---- Test MemTrace ----

def test_MemTrace_ctor():
    mt = pymemtrace.MemTrace()

def test_MemTrace_synthetic_events_single_call():
    mt = pymemtrace.MemTrace()
    mt.add_data_point('filename', 'function', 12, 'call', data.CallReturnData(0.1, 1000))
    mt.add_data_point('filename', 'function', 12, 'return', data.CallReturnData(0.2, 2000))
    mt.finalise()
    results_depth = list(mt.function_tree_seq.gen_depth_first())
#     print()
#     pprint.pprint(results_depth)
#     print()
#     print('mt.data_initial:', mt.data_initial)
#     print('    mt.data_min:', mt.data_min)
#     print('    mt.data_max:', mt.data_max)
#     print('  mt.data_final:', mt.data_final)
    assert results_depth == [
        data.WidthDepthEventFunctionData(
            width=0, depth=0, event='call', function_id=0,
            data=data.CallReturnData(0.1, 1000)),
        data.WidthDepthEventFunctionData(
            width=0, depth=0, event='return', function_id=0,
            data=data.CallReturnData(0.2, 2000)),
    ]
    assert mt.data_min == data.CallReturnData(0.1, 1000)
    assert mt.data_max == data.CallReturnData(0.2, 2000)

def test_MemTrace_synthetic_events_double_call_depth():
    mt = pymemtrace.MemTrace()
    # Line number is firstlineno
    mt.add_data_point('filename', 'parent', 12, 'call', data.CallReturnData(0.1, 1000))
    mt.add_data_point('filename', 'child', 15, 'call', data.CallReturnData(0.2, 2000))
    mt.add_data_point('filename', 'child', 15, 'return', data.CallReturnData(0.3, 3000))
    mt.add_data_point('filename', 'parent', 12, 'return', data.CallReturnData(0.4, 4000))
    mt.finalise()
    results_depth = list(mt.function_tree_seq.gen_depth_first())
#     print()
#     pprint.pprint(results_depth)
    assert results_depth == [
        data.WidthDepthEventFunctionData(
            width=0, depth=0, event='call', function_id=0,
            data=data.CallReturnData(0.1, 1000)),
        data.WidthDepthEventFunctionData(
            width=0, depth=1, event='call', function_id=1,
            data=data.CallReturnData(0.2, 2000)),
        data.WidthDepthEventFunctionData(
            width=0, depth=1, event='return', function_id=1,
            data=data.CallReturnData(0.3, 3000)),
        data.WidthDepthEventFunctionData(
            width=0, depth=0, event='return', function_id=0,
            data=data.CallReturnData(0.4, 4000)),
    ]
    assert mt.data_min == data.CallReturnData(0.1, 1000)
    assert mt.data_max == data.CallReturnData(0.4, 4000)

def test_MemTrace_synthetic_events_double_call_width():
    mt = pymemtrace.MemTrace()
    # Line number is firstlineno
    mt.add_data_point('filename', 'parent', 12, 'call', data.CallReturnData(0.1, 1000))
    mt.add_data_point('filename', 'parent', 12, 'return', data.CallReturnData(0.2, 2000))
    mt.add_data_point('filename', 'child', 15, 'call', data.CallReturnData(0.3, 3000))
    mt.add_data_point('filename', 'child', 15, 'return', data.CallReturnData(0.4, 4000))
    mt.finalise()
    results_depth = list(mt.function_tree_seq.gen_depth_first())
    print()
    pprint.pprint(results_depth)
    assert results_depth == [
        data.WidthDepthEventFunctionData(
            width=0, depth=0, event='call', function_id=0,
            data=data.CallReturnData(0.1, 1000)),
        data.WidthDepthEventFunctionData(
            width=0, depth=0, event='return', function_id=0,
            data=data.CallReturnData(0.2, 2000)),
        data.WidthDepthEventFunctionData(
            width=1, depth=0, event='call', function_id=1,
            data=data.CallReturnData(0.3, 3000)),
        data.WidthDepthEventFunctionData(
            width=1, depth=0, event='return', function_id=1,
            data=data.CallReturnData(0.4, 4000)),
    ]
    assert mt.data_min == data.CallReturnData(0.1, 1000)
    assert mt.data_max == data.CallReturnData(0.4, 4000)

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
    expected = data.FunctionLocation(__file__, 'single_function', single_function_lineno)
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
