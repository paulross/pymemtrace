import logging
import sys
import timeit

from pymemtrace import trace_malloc

def create_string(l: int) -> str:
    return ' ' * l


COUNT = 16


def test_under_512(list_of_strings):
    # print(f'test_under_512 count={COUNT}')
    for i in range(COUNT):
        list_of_strings.append(create_string(256))
    # while len(list_of_strings):
    #     list_of_strings.pop()


def test_over_512(list_of_strings):
    # print(f'test_over_512 count={COUNT}')
    for i in range(COUNT):
        list_of_strings.append(create_string(1024))
    # while len(list_of_strings):
    #     list_of_strings.pop()


def test_well_over_512(list_of_strings):
    # print(f'test_well_over_512 count={COUNT}')
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
            # list_of_strings.append(create_string(128))
    print(f' tm.memory_start={tm.memory_start}')
    print(f'tm.memory_finish={tm.memory_finish}')
    print(f'         tm.diff={tm.diff}')
    for stat in tm.statistics:
        print(stat)
    print()
    for stat in tm.net_statistics():
        print(stat)


@trace_malloc.trace_malloc_log(logging.INFO)
def example_decorator_for_documentation(list_of_strings):
    """An example of using the trace_malloc.trace_malloc_report decorator for logging memory usage.
    Typical output::

        2020-11-15 18:13:06,000 -          trace_malloc.py#82   -  9689 - (MainThread) - INFO     - TraceMalloc memory delta: 8,389,548
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


def example_timeit_under_512():
    list_of_strings = []
    test_under_512(list_of_strings)


def example_timeit_under_512_with_trace_malloc(key_type):
    list_of_strings = []
    with trace_malloc.TraceMalloc(key_type) as tm:
        test_under_512(list_of_strings)


def example_timeit_over_512():
    list_of_strings = []
    test_over_512(list_of_strings)


def example_timeit_over_512_with_trace_malloc(key_type):
    list_of_strings = []
    with trace_malloc.TraceMalloc(key_type) as tm:
        test_over_512(list_of_strings)


def example_timeit_well_over_512():
    list_of_strings = []
    test_well_over_512(list_of_strings)


def example_timeit_well_over_512_with_trace_malloc(key_type):
    list_of_strings = []
    with trace_malloc.TraceMalloc(key_type) as tm:
        test_well_over_512(list_of_strings)


def run_timeit():
    NUMBER = 10_000
    REPEAT = 5
    CONVERT = 1_000_000
    print(f'number={NUMBER:,d} repeat={REPEAT:,d} convert={CONVERT:,d}')
    for function in (
            'example_timeit_under_512',
            'example_timeit_over_512',
            'example_timeit_well_over_512',
    ):
        # t = timeit.timeit(f"{function}()", setup=f"from __main__ import {function}", number=NUMBER) / NUMBER
        # print(f'{function:60}: {t:9.9f}')
        times = timeit.repeat(f"{function}()", setup=f"from __main__ import {function}", number=NUMBER, repeat=REPEAT)
        times = [CONVERT * t / NUMBER for t in times]
        result = [f'{v:9.3f}' for v in times]
        times_mean = sum(times) / REPEAT
        print(
            f'{function:60}:'
            f' {", ".join(result)}'
            f' mean={times_mean:9.3f}'
            f' min={min(times):9.3f}'
            f' max={max(times):9.3f}'
            f' span={max(times) - min(times):9.3f}'
        )
        for key_type in ('filename', 'lineno', 'traceback'):
            # With _with_trace_malloc
            times_with_trace_malloc = timeit.repeat(f"{function}_with_trace_malloc('{key_type}')", setup=f"from __main__ import {function}_with_trace_malloc", number=NUMBER, repeat=REPEAT)
            times_with_trace_malloc = [CONVERT * t / NUMBER for t in times_with_trace_malloc]
            result = [f'{v:9.3f}' for v in times_with_trace_malloc]
            times_mean_with_trace_malloc = sum(times_with_trace_malloc) / REPEAT
            function_str = function + f"_with_trace_malloc('{key_type}')"
            print(
                f'{function_str:60}:'
                f' {", ".join(result)}'
                f' mean={times_mean_with_trace_malloc:9.3f}'
                f' min={min(times_with_trace_malloc):9.3f}'
                f' max={max(times_with_trace_malloc):9.3f}'
                f' span={max(times_with_trace_malloc) - min(times_with_trace_malloc):9.3f}'
                f' x{times_mean_with_trace_malloc / times_mean:>8.3f}'
            )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        # format='%(asctime)s - %(filename)24s#%(lineno)-4d - %(funcName)24s - %(process)5d - (%(threadName)-10s) - %(levelname)-8s - %(message)s',
        format='%(asctime)s - %(filename)24s#%(lineno)-4d - %(process)5d - (%(threadName)-10s) - %(levelname)-8s - %(message)s',
        stream=sys.stdout
    )
    print()
    example_decorator_for_documentation([])
    print()
    example_trace_malloc_for_documentation([])
    # print()
    # example()
    return 0


if __name__ == '__main__':
    sys.exit(main())

