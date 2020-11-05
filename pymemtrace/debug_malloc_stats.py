"""
This is a wrapper around sys._debugmallocstats which writes to C stderr.
We capture this and can diff two calls to sys._debugmallocatats.
"""
import contextlib
import difflib
import io
import sys

import redirect_stdout


def get_debugmallocstats() -> bytes:
    """Invokes sys._debugmallocstats and captures the output as bytes."""
    stream = io.BytesIO()
    with redirect_stdout.stderr_redirector(stream):
        sys._debugmallocstats()
    return stream.getvalue()
    # return stream.getvalue().decode('ascii', 'replace')


@contextlib.contextmanager
def change_in_debugmallocstats():
    before = get_debugmallocstats()
    yield
    after = get_debugmallocstats()
    return before, after


@contextlib.contextmanager
def diff_debugmallocstats():
    before = get_debugmallocstats()
    yield
    after = get_debugmallocstats()
    diffs = list(difflib.diff_bytes(difflib.unified_diff, before.split(b'\n'), after.split(b'\n')))
    return diffs


def main():
    print('sys._debugmallocstats()')
    print(get_debugmallocstats())

    print('diff_debugmallocstats()')
    d = {}
    with diff_debugmallocstats() as diff:
        s = ' ' * 12
        d.update({str(v): v for v in range(1024)})
    print(diff)
    return 0


if __name__ == '__main__':
    sys.exit(main())
