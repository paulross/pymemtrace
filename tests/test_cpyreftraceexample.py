"""
At the moment these produce a log file per test.
"""
import faulthandler
import pprint
import sys

import pytest

from pymemtrace import cPyRefTraceExample

faulthandler.enable()


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_module_dir_post_313():
    pprint.pprint(dir(cPyRefTraceExample))
    assert dir(cPyRefTraceExample) == [
        'RefTraceCount',
        '__doc__',
        '__file__',
        '__loader__',
        '__name__',
        '__package__',
        '__spec__',
    ]


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python > 3.13')
def test_reftracecount_object_dir_post_313():
    print()
    print('test_reftracecount_object_dir_post_313():')
    counter = cPyRefTraceExample.RefTraceCount()
    pprint.pprint(dir(counter))
    assert dir(counter) == [
        '__class__',
        '__delattr__',
        '__dir__',
        '__doc__',
        '__eq__',
        '__format__',
        '__ge__',
        '__getattribute__',
        '__getstate__',
        '__gt__',
        '__hash__',
        '__init__',
        '__init_subclass__',
        '__le__',
        '__lt__',
        '__ne__',
        '__new__',
        '__reduce__',
        '__reduce_ex__',
        '__repr__',
        '__setattr__',
        '__sizeof__',
        '__str__',
        '__subclasshook__',
        'count_del',
        'count_new',
    ]

# @pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
# @pytest.mark.parametrize(
#     'attr',
#     (
#             'profile_log_path',
#             'trace_log_path',
#             'reference_tracing_log_path',
#     )
# )
# def test_module_log_file_path_none_post_313(attr):
#     log_file_path_fn = getattr(cPyMemTrace, attr)
#     assert callable(log_file_path_fn)
#     assert log_file_path_fn() is None


def create_list_of_ints(start: int, stop: int, step: int) -> None:
    l = []
    for i in range(start, stop, step):
        l.append(i)


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reftracecount_object_example_0_8_post_313():
    counter = cPyRefTraceExample.RefTraceCount()
    create_list_of_ints(0, 8, 1)
    assert counter.count_new() == 4
    assert counter.count_del() == 4

@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reftracecount_object_example_1024_1032_post_313():
    counter = cPyRefTraceExample.RefTraceCount()
    create_list_of_ints(1024, 1024+8, 1)
    assert counter.count_new() == 12
    assert counter.count_del() == 12
