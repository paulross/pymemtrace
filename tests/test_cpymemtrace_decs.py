import random

import pytest

from pymemtrace import cpymemtrace_decs


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


@cpymemtrace_decs.trace()
def test_trace_decorator_basic():
    create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


@cpymemtrace_decs.trace(
    d_rss_trigger=0, message='test_trace_decorator_kwargs()',
)
def test_trace_decorator_kwargs():
    create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


@cpymemtrace_decs.reference_tracing()
def test_reference_tracing_decorator_basic():
    create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)


@cpymemtrace_decs.reference_tracing(
    message='test_reference_tracing_decorator_kwargs()',
)
def test_reference_tracing_decorator_kwargs():
    create_list_of_strings(4, 20 * 1024 ** 2, 50 * 1024 ** 2)
