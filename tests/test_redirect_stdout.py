import ctypes
import io
import sys

import pytest

from pymemtrace import redirect_stdout


def test_stdout_redirector_python():
    stream = io.StringIO()
    with redirect_stdout.stdout_redirector(stream):
        sys.stdout.write('Foo')
    result = stream.getvalue()
    assert result == 'Foo'


if __name__ == '__main__':
    test_stdout_redirector_python()
