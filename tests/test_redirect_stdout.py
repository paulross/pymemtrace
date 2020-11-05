import ctypes
import io
import sys

import pytest

from pymemtrace import redirect_stdout


def test_stdout_redirector_python_bytes():
    stream = io.BytesIO()
    with redirect_stdout.stdout_redirector(stream):
        sys.stdout.write('Foo')
    result = stream.getvalue()
    assert result == b'Foo', f'Result: {result!r}'


# def test_stdout_redirector_python_text():
#     stream = io.StringIO()
#     with redirect_stdout.stdout_redirector(stream):
#         sys.stdout.write('Foo')
#     result = stream.getvalue()
#     assert result == b'Foo', f'Result: {result!r}'


def test_stdout_redirector_c_bytes():
    libc = ctypes.CDLL(None)
    stream = io.BytesIO()
    with redirect_stdout.stdout_redirector(stream):
        libc.puts(b'This comes from C')
    result = stream.getvalue()
    assert result == b'This comes from C\n', f'Result: {result!r}'


def test_stdout_redirector_python_c_bytes():
    libc = ctypes.CDLL(None)
    stream = io.BytesIO()
    with redirect_stdout.stdout_redirector(stream):
        print('foobar')
        sys.stdout.write('sys.stdout.write()\n')
        libc.puts(b'This comes from C')
    result = stream.getvalue()
    assert result == b'This comes from C\nfoobar\nsys.stdout.write()\n', f'Result: {result!r}'


def test_stdout_redirector_python_c_bytes_flush():
    libc = ctypes.CDLL(None)
    stream = io.BytesIO()
    with redirect_stdout.stdout_redirector(stream):
        print('foobar')
        sys.stdout.write('sys.stdout.write()\n')
        sys.stdout.flush()
        libc.puts(b'This comes from C')
    result = stream.getvalue()
    assert result == b'foobar\nsys.stdout.write()\nThis comes from C\n', f'Result: {result!r}'


if __name__ == '__main__':
    test_stdout_redirector_python_bytes()
    # test_stdout_redirector_python_text()
    test_stdout_redirector_c_bytes()
    test_stdout_redirector_python_c_bytes()
    test_stdout_redirector_python_c_bytes_flush()
