import sys

import pytest

from pymemtrace import cMemLeak


@pytest.mark.parametrize(
    'cls',
    (
            cMemLeak.CMalloc,
            cMemLeak.PyRawMalloc,
            cMemLeak.PyMalloc,
    )
)
def test_cmeleak_object_ctor(cls):
    cobj = cls(1024)
    assert cobj.size == 1024


@pytest.mark.parametrize(
    'cls',
    (
            cMemLeak.CMalloc,
            cMemLeak.PyRawMalloc,
            cMemLeak.PyMalloc,
    )
)
def test_cmeleak_refcnt(cls):
    cobj = cls(1024)
    assert cobj.refcnt() == 2


@pytest.mark.parametrize(
    'cls',
    (
            cMemLeak.CMalloc,
            cMemLeak.PyRawMalloc,
            cMemLeak.PyMalloc,
    )
)
def test_cmeleak_inc_refcnt(cls):
    cobj = cls(1024)
    assert cobj.refcnt() == 2
    cobj.inc_refcnt(1)
    assert cobj.refcnt() == 3
    cobj.inc_refcnt(-1)
    assert cobj.refcnt() == 2
