#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `pymemtrace` package."""

import pytest

from pymemtrace import pymemtrace

def test_FunctionCallSites_mt():
    fcs = pymemtrace.FunctionCallSites()
    assert fcs.integrity()


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
