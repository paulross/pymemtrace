"""
At the moment these produce a log file per test.
TODO: Would be handy if we could specify a temporary file or file path, inspect it and clean up.
"""

import pytest

from pymemtrace import cPyMemTrace


def test_basic():
    with cPyMemTrace.Profile(0) as profiler:
        b' ' * (1024 ** 2)
        print(profiler)
        print(dir(profiler))
        print(profiler.trace_file_wrapper)
        print(dir(profiler.trace_file_wrapper))
        assert profiler.trace_file_wrapper.log_file_path == ''
