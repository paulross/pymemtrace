"""Taken from the excellent blog:
https://eli.thegreenplace.net/2015/redirecting-all-kinds-of-stdout-in-python/

Changes:

* Minor edits.
* Move tfile = tempfile.TemporaryFile(mode='w+b') outside try block.
* Duplicate for stderr

TODO: Unite duplicate code.
"""
from contextlib import contextmanager
import ctypes
import io
import os
import sys
import tempfile

import typing

libc = ctypes.CDLL(None)
if sys.platform == 'darwin':
    c_stdout = ctypes.c_void_p.in_dll(libc, '__stdoutp')
    c_stderr = ctypes.c_void_p.in_dll(libc, '__stderrp')
else:
    c_stdout = ctypes.c_void_p.in_dll(libc, 'stdout')
    c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')


@contextmanager
def stdout_redirector(stream: typing.BinaryIO):
    """A context manager that redirects Python stdout and C stdout to the given binary I/O stream."""
    def _redirect_stdout(to_fd):
        """Redirect stdout to the given file descriptor."""
        # Flush the C-level buffer stdout
        libc.fflush(c_stdout)
        # Flush and close sys.stdout - also closes the file descriptor (fd)
        sys.stdout.close()
        # Make original_stdout_fd point to the same file as to_fd
        os.dup2(to_fd, original_stdout_fd)
        # Create a new sys.stdout that points to the redirected fd
        sys.stdout = io.TextIOWrapper(os.fdopen(original_stdout_fd, 'wb'))

    # The original fd stdout points to. Usually 1 on POSIX systems.
    original_stdout_fd = sys.stdout.fileno()
    # Save a copy of the original stdout fd in saved_stdout_fd
    saved_stdout_fd = os.dup(original_stdout_fd)
    # Create a temporary file and redirect stdout to it
    tfile = tempfile.TemporaryFile(mode='w+b')
    try:
        _redirect_stdout(tfile.fileno())
        # Yield to caller, then redirect stdout back to the saved fd
        yield
        _redirect_stdout(saved_stdout_fd)
        # Copy contents of temporary file to the given stream
        tfile.flush()
        tfile.seek(0, io.SEEK_SET)
        stream.write(tfile.read())
    finally:
        tfile.close()
        os.close(saved_stdout_fd)


@contextmanager
def stderr_redirector(stream: typing.BinaryIO):
    """A context manager that redirects Python stderr and C stderr to the given binary I/O stream."""
    def _redirect_stderr(to_fd):
        """Redirect stderr to the given file descriptor."""
        # Flush the C-level buffer stderr
        libc.fflush(c_stderr)
        # Flush and close sys.stderr - also closes the file descriptor (fd)
        sys.stderr.close()
        # Make original_stderr_fd point to the same file as to_fd
        os.dup2(to_fd, original_stderr_fd)
        # Create a new sys.stderr that points to the redirected fd
        sys.stderr = io.TextIOWrapper(os.fdopen(original_stderr_fd, 'wb'))

    # The original fd stderr points to. Usually 2 on POSIX systems.
    original_stderr_fd = sys.stderr.fileno()
    # Save a copy of the original stderr fd in saved_stderr_fd
    saved_stderr_fd = os.dup(original_stderr_fd)
    # Create a temporary file and redirect stderr to it
    tfile = tempfile.TemporaryFile(mode='w+b')
    try:
        _redirect_stderr(tfile.fileno())
        # Yield to caller, then redirect stderr back to the saved fd
        yield
        _redirect_stderr(saved_stderr_fd)
        # Copy contents of temporary file to the given stream
        tfile.flush()
        tfile.seek(0, io.SEEK_SET)
        stream.write(tfile.read())
    finally:
        tfile.close()
        os.close(saved_stderr_fd)
