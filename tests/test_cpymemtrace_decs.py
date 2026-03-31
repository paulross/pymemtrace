import random
import sys

import pytest

from pymemtrace import cpymemtrace_decs


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


if sys.version_info >= (3, 13):
    @cpymemtrace_decs.reference_tracing(
        message='_reference_tracing_decorator_inner_function_kwargs()',
    )
    def _reference_tracing_decorator_inner_function_kwargs():
        create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


    @cpymemtrace_decs.reference_tracing(
        message='test_reference_tracing_decorator_outer_function_kwargs()',
    )
    def test_reference_tracing_decorator_outer_function_kwargs():
        _reference_tracing_decorator_inner_function_kwargs()


    @cpymemtrace_decs.trace(
        message='Trace the inner function',
    )
    def trace_inner_function():
        pass


    @cpymemtrace_decs.reference_tracing(
        message='Reference trace the outer function that calls the inner function',
    )
    def reference_trace_outer_function():
        trace_inner_function()


    def test_mixed_decorators():
        reference_trace_outer_function()
