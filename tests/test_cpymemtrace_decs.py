import datetime
import os
import random
import string
import sys

import pytest

from pymemtrace import cpymemtrace_decs
from pymemtrace import cPyMemTrace


@cpymemtrace_decs.profile()
def test_profile_file_path():
    assert os.path.isfile(cPyMemTrace.profile_log_path())


@cpymemtrace_decs.trace()
def test_trace_file_path():
    assert os.path.isfile(cPyMemTrace.trace_log_path())


# cpymemtrace_decs.profile
def create_list_of_strings(num: int, min_size: int, max_size: int) -> None:
    l = []
    for i in range(num):
        l.append(' ' * random.randint(min_size, max_size))
    while len(l):
        l.pop()


@cpymemtrace_decs.profile()
def test_profile_decorator_basic():
    create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


@cpymemtrace_decs.profile(
    d_rss_trigger=0, message='test_profile_decorator_kwargs()',
)
def test_profile_decorator_kwargs():
    create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


@cpymemtrace_decs.profile(
    d_rss_trigger=0, message='_profile_decorator_inner_function_kwargs()',
)
def _profile_decorator_inner_function_kwargs():
    create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


@cpymemtrace_decs.profile(
    d_rss_trigger=0, message='test_profile_decorator_outer_function_kwargs()',
)
def test_profile_decorator_outer_function_kwargs():
    _profile_decorator_inner_function_kwargs()


# cpymemtrace_decs.trace 
@cpymemtrace_decs.trace()
def test_trace_decorator_basic():
    create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


@cpymemtrace_decs.trace(
    d_rss_trigger=0, message='test_trace_decorator_kwargs()',
)
def test_trace_decorator_kwargs():
    create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


@cpymemtrace_decs.trace(
    d_rss_trigger=0, message='_trace_decorator_inner_function_kwargs()',
)
def _trace_decorator_inner_function_kwargs():
    create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


@cpymemtrace_decs.trace(
    d_rss_trigger=0, message='test_trace_decorator_outer_function_kwargs()',
)
def test_trace_decorator_outer_function_kwargs():
    _trace_decorator_inner_function_kwargs()


# cpymemtrace_decs.reference_tracing
if sys.version_info >= (3, 13):
    @cpymemtrace_decs.reference_tracing()
    def test_reference_tracing_decorator_basic():
        create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)

if sys.version_info >= (3, 13):
    @cpymemtrace_decs.reference_tracing(
        message='test_reference_tracing_decorator_kwargs()',
    )
    def test_reference_tracing_decorator_kwargs():
        create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


    @cpymemtrace_decs.reference_tracing()
    def test_reference_tracing_file_path():
        assert os.path.isfile(cPyMemTrace.reference_tracing_log_path())


class StringAndTime:
    def __init__(self, size: int):
        self.now = datetime.datetime.now()
        self.str = ''.join(random.choices(string.printable, k=size))


if sys.version_info >= (3, 13):
    @cpymemtrace_decs.reference_tracing(
        message='_reference_tracing_decorator_inner_function_kwargs()',
    )
    def _reference_tracing_decorator_inner_function_kwargs():
        create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


    @cpymemtrace_decs.reference_tracing(
        message='test_reference_tracing_decorator_write_messages()',
    )
    def test_reference_tracing_decorator_write_messages():
        l = []
        for i in range(4):
            length = random.randint(20 * 1024 ** 2, 50 * 1024 ** 2)
            cPyMemTrace.reference_tracing_write_message_to_log(f'Appending index {i} length {length}')
            l.append(' ' * length)
        while len(l):
            l.pop()
        assert os.path.isfile(cPyMemTrace.reference_tracing_log_path())
        with open(cPyMemTrace.reference_tracing_log_path()) as f:
            print(f.read())


    @cpymemtrace_decs.reference_tracing(
        message='test_reference_tracing_decorator_write_message_example()',
        include_builtins=True,
    )
    def test_reference_tracing_decorator_write_message_example():
        l = []
        for i in range(1):
            length = random.randint(20 * 1024 ** 2, 50 * 1024 ** 2)
            cPyMemTrace.reference_tracing_write_message_to_log(f'Entering critical section')
            l.append(' ' * length)
            cPyMemTrace.reference_tracing_write_message_to_log(f'Exiting critical section')
        while len(l):
            cPyMemTrace.reference_tracing_write_message_to_log(f'Before pop()')
            l.pop()
            cPyMemTrace.reference_tracing_write_message_to_log(f'After pop()')
        assert os.path.isfile(cPyMemTrace.reference_tracing_log_path())
        with open(cPyMemTrace.reference_tracing_log_path()) as f:
            print(f.read())


    @cpymemtrace_decs.reference_tracing(
        message='test_example_ref_trace()',
    )
    def test_example_ref_trace():
        list_of_str_and_time = []
        for i in range(2):
            str_len = random.randint(1024, 2048)
            v = StringAndTime(str_len)
            list_of_str_and_time.append(v)
        while len(list_of_str_and_time):
            list_of_str_and_time.pop()
        assert os.path.isfile(cPyMemTrace.reference_tracing_log_path())
        with open(cPyMemTrace.reference_tracing_log_path()) as f:
            print(f.read())


    @cpymemtrace_decs.reference_tracing(
        message='test_example_ref_trace_msg()',
    )
    def test_example_ref_trace_msg():
        list_of_str_and_time = []
        for i in range(2):
            str_len = random.randint(1024, 2048)
            cPyMemTrace.reference_tracing_write_message_to_log(f'Entering critical section')
            v = StringAndTime(str_len)
            list_of_str_and_time.append(v)
            cPyMemTrace.reference_tracing_write_message_to_log(f'Exiting critical section')
        while len(list_of_str_and_time):
            cPyMemTrace.reference_tracing_write_message_to_log(f'Before pop()')
            list_of_str_and_time.pop()
            cPyMemTrace.reference_tracing_write_message_to_log(f'After pop()')
        assert os.path.isfile(cPyMemTrace.reference_tracing_log_path())
        with open(cPyMemTrace.reference_tracing_log_path()) as f:
            print(f.read())


    @cpymemtrace_decs.reference_tracing(
        message='test_reference_tracing_decorator_outer_function_kwargs()',
    )
    def test_reference_tracing_decorator_outer_function_kwargs():
        _reference_tracing_decorator_inner_function_kwargs()


    @cpymemtrace_decs.trace(
        message='Trace the inner function',
    )
    def trace_inner_function():
        # pass
        create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


    @cpymemtrace_decs.reference_tracing(
        message='Reference trace the outer function that calls the inner function',
    )
    def reference_trace_outer_function_A():
        trace_inner_function()


    # Skip this as pytest is calling abort() on x86 machine.
    def _mixed_decorators_A():
        reference_trace_outer_function_A()


    @cpymemtrace_decs.reference_tracing(
        message='Reference trace the inner function',
    )
    def reference_trace_inner_function():
        pass


    @cpymemtrace_decs.reference_tracing(
        message='Reference trace the outer function that calls the inner function',
    )
    def reference_trace_outer_function_B():
        reference_trace_inner_function()


    # Skip this as pytest is calling abort() on x86 machine.
    def _reference_tracing_decorators_B():
        reference_trace_outer_function_B()


def main():
    if sys.version_info >= (3, 13):
        # _mixed_decorators_A()
        # _reference_tracing_decorators_B()
        # test_reference_tracing_decorator_write_messages()
        # test_reference_tracing_decorator_write_message_example()
        test_example_ref_trace()
        # test_example_ref_trace_msg()
    # test_trace_decorator_outer_function_kwargs()


if __name__ == '__main__':
    exit(main())
