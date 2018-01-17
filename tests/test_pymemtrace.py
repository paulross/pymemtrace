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

@pytest.mark.parametrize("filter_fn", [
    None,
    lambda data_call, data_return: True,
])
def test_MemTrace_ctor(filter_fn):
    mt = pymemtrace.MemTrace(filter_fn)
    assert mt is not None

@pytest.mark.parametrize("filter_fn", [
    None,
    lambda data_call, data_return: True,
])
def test_MemTrace_synthetic_events_single_call(filter_fn):
    mt = pymemtrace.MemTrace(filter_fn)
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

def test_MemTrace_synthetic_events_single_call_filtered_out():
    def filter_on_time(data_call, data_return):
        diff = data_return - data_call
        if diff.time < 0.1:
            return False
        return True
    mt = pymemtrace.MemTrace(filter_on_time)
    mt.add_data_point('filename', 'function', 12, 'call', data.CallReturnData(0.1, 1000))
    mt.add_data_point('filename', 'function', 12, 'return', data.CallReturnData(0.15, 2000))
    mt.finalise()
    results_depth = list(mt.function_tree_seq.gen_depth_first())
    assert results_depth == []
    assert mt.data_min == data.CallReturnData(0.1, 1000)
    assert mt.data_max == data.CallReturnData(0.15, 2000)

@pytest.mark.parametrize("filter_fn", [
    None,
    lambda data_call, data_return: True,
])
def test_MemTrace_synthetic_events_double_call_depth(filter_fn):
    mt = pymemtrace.MemTrace(filter_fn)
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

def test_MemTrace_synthetic_events_double_call_depth_one_filtered_out():
    def filter_on_time(data_call, data_return):
        diff = data_return - data_call
        if diff.time < 0.1:
            return False
        return True
    mt = pymemtrace.MemTrace(filter_on_time)
    # Line number is firstlineno
    mt.add_data_point('filename', 'parent', 12, 'call', data.CallReturnData(0.1, 1000))
    mt.add_data_point('filename', 'child', 15, 'call', data.CallReturnData(0.2, 2000))
    mt.add_data_point('filename', 'child', 15, 'return', data.CallReturnData(0.25, 3000))
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
            width=0, depth=0, event='return', function_id=0,
            data=data.CallReturnData(0.4, 4000)),
    ]
    assert mt.data_min == data.CallReturnData(0.1, 1000)
    assert mt.data_max == data.CallReturnData(0.4, 4000)

@pytest.mark.parametrize("filter_fn", [
    None,
    lambda data_call, data_return: True,
])
def test_MemTrace_synthetic_events_double_call_width(filter_fn):
    mt = pymemtrace.MemTrace(filter_fn)
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

def test_MemTrace_synthetic_events_double_call_width_filter_first_on_time():
    def filter_on_time(data_call, data_return):
        diff = data_return - data_call
        if diff.time < 0.1:
            return False
        return True
    mt = pymemtrace.MemTrace(filter_on_time)
    # First call should get filtered out
    mt.add_data_point('filename', 'parent', 12, 'call', data.CallReturnData(0.1, 1000))
    mt.add_data_point('filename', 'parent', 12, 'return', data.CallReturnData(0.15, 2000))
    mt.add_data_point('filename', 'child', 15, 'call', data.CallReturnData(0.15, 3000))
    mt.add_data_point('filename', 'child', 15, 'return', data.CallReturnData(0.4, 4000))
    mt.finalise()
    results_depth = list(mt.function_tree_seq.gen_depth_first())
    print()
    pprint.pprint(results_depth)
    assert results_depth == [
        data.WidthDepthEventFunctionData(
            width=0, depth=0, event='call', function_id=1,
            data=data.CallReturnData(0.15, 3000)),
        data.WidthDepthEventFunctionData(
            width=0, depth=0, event='return', function_id=1,
            data=data.CallReturnData(0.4, 4000)),
    ]
    assert mt.data_min == data.CallReturnData(0.1, 1000)
    assert mt.data_max == data.CallReturnData(0.4, 4000)

def test_MemTrace_synthetic_events_double_call_width_filter_second_on_time():
    def filter_on_time(data_call, data_return):
        diff = data_return - data_call
        if diff.time < 0.1:
            return False
        return True
    mt = pymemtrace.MemTrace(filter_on_time)
    mt.add_data_point('filename', 'parent', 12, 'call', data.CallReturnData(0.1, 1000))
    mt.add_data_point('filename', 'parent', 12, 'return', data.CallReturnData(0.35, 2000))
    # Second call should get filtered out
    mt.add_data_point('filename', 'child', 15, 'call', data.CallReturnData(0.35, 3000))
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
            data=data.CallReturnData(0.35, 2000)),
    ]
    assert mt.data_min == data.CallReturnData(0.1, 1000)
    assert mt.data_max == data.CallReturnData(0.4, 4000)

@pytest.mark.parametrize("filter_fn", [
    None,
    lambda data_call, data_return: True,
])
def test_MemTrace_single_function(filter_fn):
    def single_function(n):
        return n * 2
    
    with pymemtrace.MemTrace(filter_fn) as mt:
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

@pytest.mark.parametrize("filter_fn", [
    None,
    lambda data_call, data_return: True,
])
def test_MemTrace_function_id(filter_fn):
    single_function_lineno = inspect.currentframe().f_lineno + 1
    def single_function(n):
        return n * 2
    
    with pymemtrace.MemTrace(filter_fn) as mt:
        assert single_function(5) == 10
    expected = data.FunctionLocation(__file__, 'single_function', single_function_lineno)
    assert mt.decode_function_id(0) == expected

@pytest.mark.parametrize("filter_fn", [
    None,
    lambda data_call, data_return: True,
])
def test_MemTrace_function_id_raises(filter_fn):
    mt = pymemtrace.MemTrace(filter_fn)
    with pytest.raises(KeyError):
        mt.decode_function_id(0)

@pytest.mark.parametrize("filter_fn", [
    None,
    lambda data_call, data_return: True,
])
def test_MemTrace_multiple_functions(filter_fn):
    def inner_function(n):
        return n * 2
    
    def outer_function_0(n):
        return inner_function(n) * 2
    
    def outer_function_1(n):
        return inner_function(n) * 4
    
    with pymemtrace.MemTrace(filter_fn) as mt:
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


@pytest.mark.parametrize("filter_fn", [
    None,
    lambda data_call, data_return: True,
])
def test_MemTrace_multiple_functions_real_memory_usage(filter_fn):
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
    with pymemtrace.MemTrace(filter_fn) as mt:
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

@pytest.mark.parametrize("filter_fn", [
    None,
    lambda data_call, data_return: True,
])
def test_MemTrace_function_expected_time(filter_fn):
    DELAY = 0.25
    def timed_function():
        time.sleep(DELAY)
        
    with pymemtrace.MemTrace(filter_fn) as mt:
        assert timed_function() is None
    call_return_data = list(mt.function_tree_seq.gen_depth_first())
    assert len(call_return_data) == 2
    rng = mt.data_final - mt.data_initial
    assert rng.time > DELAY
    assert rng.time < DELAY + 0.010

@pytest.mark.parametrize("filter_fn", [
    None,
    lambda data_call, data_return: True,
])
def test_MemTrace_function_expected_memory(filter_fn):
    SIZE = 1024*1024
    def memory_function():
        long_str = ' ' * SIZE
        return long_str
        
    with pymemtrace.MemTrace(filter_fn) as mt:
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
    assert 0 <= rng.memory < sizeof * 1.005

#---- END: Test MemTrace ----

#---- Test create_filter_function() ----
def test_create_filter_function_none():
    fn = pymemtrace.create_filter_function(
        pymemtrace.DEFAULT_FILTER_MIN_TIME,
        pymemtrace.DEFAULT_FILTER_MIN_MEMORY,
    )
    assert fn is None

def test_create_filter_function_raises_negative_min_memory():
    with pytest.raises(ValueError):
        pymemtrace.create_filter_function(
            pymemtrace.DEFAULT_FILTER_MIN_TIME,
            -1,
        )

@pytest.mark.parametrize("t, m, expected", [
    # Time in seconds, memory in bytes
    (0.000999, 1024, False),
    (0.001000, 1024, True),
    (0.001001, 1024, True),
])
def test_create_filter_function_time(t, m, expected):
    fn = pymemtrace.create_filter_function(
        1000, # time in microseconds
        pymemtrace.DEFAULT_FILTER_MIN_MEMORY,
    )
    assert fn is not None
    assert fn(data.CallReturnData(0, 1024), data.CallReturnData(t, m)) == expected

@pytest.mark.parametrize("t, m, expected", [
    # Time in seconds, memory in bytes
    (0.001, 2048, False),
    (0.001, 1024 + 1, False),
    (0.001, 2048 + 1024 - 1, False),
    (0.001, 1024, True),
    (0.001, 2048 + 1024, True),
    (0.001, 1024 - 1, True),
    (0.001, 2048 + 1024 + 1, True),
])
def test_create_filter_function_memory(t, m, expected):
    fn = pymemtrace.create_filter_function(
        pymemtrace.DEFAULT_FILTER_MIN_TIME,
        1, # Memory in kilobytes
    )
    assert fn is not None
    assert fn(data.CallReturnData(0, 2048), data.CallReturnData(t, m)) == expected

@pytest.mark.parametrize("t, m, expected", [
    # Time in seconds, memory in bytes
    #
    # Tinker with memory
    (0.000999, 2048, False),
    (0.000999, 1024 + 1, False),
    (0.000999, 2048 + 1024 - 1, False),
    (0.000999, 1024, True),
    (0.000999, 2048 + 1024, True),
    (0.000999, 1024 - 1, True),
    (0.000999, 2048 + 1024 + 1, True),
    # Tinker with time
    (0.000999, 2048, False),
    (0.001000, 2048, True),
    (0.001001, 2048, True),
    # Tinker with both
    (0.000999, 2048, False),
    (0.001000, 2048 - 1024, True),
    (0.001001, 2048 + 1024, True),
])
def test_create_filter_function_both(t, m, expected):
    fn = pymemtrace.create_filter_function(
        1000, # time in microseconds
        1, # Memory in kilobytes
    )
    assert fn is not None
    assert fn(data.CallReturnData(0, 2048), data.CallReturnData(t, m)) == expected

#---- END: Test create_filter_function() ----

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
