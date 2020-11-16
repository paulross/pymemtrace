import sys

import pytest

from pymemtrace import cMemLeak


def test_cmalloc_object():
    cobj = cMemLeak.CMalloc(1024)
    assert cobj.size == 1024
