import logging
import sys

from pymemtrace import trace_malloc

def create_string(l: int) -> str:
    return ' ' * l


COUNT = 16


def test_under_512(list_of_strings):
    print(f'test_under_512 count={COUNT}')
    for i in range(COUNT):
        list_of_strings.append(create_string(256))
    # while len(list_of_strings):
    #     list_of_strings.pop()


def test_over_512(list_of_strings):
    print(f'test_over_512 count={COUNT}')
    for i in range(COUNT):
        list_of_strings.append(create_string(1024))
    # while len(list_of_strings):
    #     list_of_strings.pop()


def test_well_over_512(list_of_strings):
    print(f'test_well_over_512 count={COUNT}')
    for i in range(COUNT):
        list_of_strings.append(create_string(1024**2))
    # while len(list_of_strings):
    #     list_of_strings.pop()


def example_trace_malloc_for_documentation(list_of_strings):
    """An example of using the trace_malloc.trace_malloc_report decorator for logging memory usage.
    Typical output::

        example_trace_malloc_for_documentation()
        pymemtrace/pymemtrace/examples/example_trace_malloc.py:0: size=8194 KiB (+8193 KiB), count=16 (+10), average=512 KiB
        /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/tracemalloc.py:0: size=6720 B (+552 B), count=43 (+11), average=156 B
        pymemtrace/pymemtrace/trace_malloc.py:0: size=3076 B (-468 B), count=10 (-1), average=308 B
        /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/logging/__init__.py:0: size=16.3 KiB (-176 B), count=49 (-3), average=340 B
        /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/abc.py:0: size=3169 B (+0 B), count=30 (+0), average=106 B
        /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/posixpath.py:0: size=480 B (+0 B), count=1 (+0), average=480 B
        /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/threading.py:0: size=168 B (+0 B), count=2 (+0), average=84 B
        /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/_weakrefset.py:0: size=72 B (+0 B), count=1 (+0), average=72 B
    """
    print(f'example_trace_malloc_for_documentation()')
    with trace_malloc.TraceMalloc('filename') as tm:
        for i in range(8):
            list_of_strings.append(create_string(1024**2))
    print(f'tm.memory_start={tm.memory_start}')
    print(f'tm.memory_finish={tm.memory_finish}')
    for stat in tm.statistics:
        print(stat)


@trace_malloc.trace_malloc_report(logging.ERROR)
def example_decorator_for_documentation(list_of_strings):
    """An example of using the trace_malloc.trace_malloc_report decorator for logging memory usage.
    Typical output::

        ERROR:root:TraceMalloc memory usage: 8390030
    """
    print(f'example_decorator_for_documentation()')
    for i in range(8):
        list_of_strings.append(create_string(1024**2))


def example():
    for function in (test_under_512, test_over_512, test_well_over_512):
        print(f'Function: {function}')
        list_of_strings = []
        # with trace_malloc.TraceMalloc('filename') as tm:
        with trace_malloc.TraceMalloc('lineno') as tm:
            function(list_of_strings)
        print(f'tm.memory_start={tm.memory_start}')
        print(f'tm.memory_finish={tm.memory_finish}')
        for stat in tm.net_statistics():
            print(stat)
        print()


def main():
    example_decorator_for_documentation([])
    print()
    example_trace_malloc_for_documentation([])
    print()
    example()
    return 0


if __name__ == '__main__':
    sys.exit(main())

