import sys

import pytest

print(sys.path)

import pymemtrace

print(dir(pymemtrace))

import cMemLeak

# from pymemtrace import cMemLeak

def test_cmalloc_object():
    cobj = cMemLeak.mem_leak.CMalloc(1024)
    assert cobj.size == 1024






