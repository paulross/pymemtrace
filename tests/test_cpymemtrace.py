"""
At the moment these produce a log file per test.
TODO: Would be handy if we could specify a temporary file or file path, inspect it and clean up.
"""

import pytest

from pymemtrace import cPyMemTrace


def test_basic():
    with cPyMemTrace.Profile(0) as foo:
        print(foo)
        print(dir(foo))
        b' ' * (1024 ** 2)
