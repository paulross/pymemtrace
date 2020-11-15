import sys
import timeit

import typing
from pymemtrace import debug_malloc_stats

def create_string(l: int) -> str:
    return ' ' * l


def test_under_512(count: int, list_of_strings: typing.List[str]):
    for i in range(count):
        list_of_strings.append(create_string(256))


def test_over_512(count: int, list_of_strings: typing.List[str]):
    for i in range(count):
        list_of_strings.append(create_string(1024))


def test_well_over_512(count: int, list_of_strings: typing.List[str]):
    for i in range(count):
        list_of_strings.append(create_string(1024**2))


def example_debug_malloc_stats_for_documentation(list_of_strings):
    """An example of using the trace_malloc.trace_malloc_report decorator for logging memory usage.
    Typical output:

    .. code-block:: text

        example_trace_malloc_for_documentation()
        DiffSysDebugMallocStats.diff():
        class   size   num pools   blocks in use  avail blocks
        -----   ----   ---------   -------------  ------------
            1     32          +1             +52           +74
            2     48          +0             +17           -17
            3     64          +0             +33           -33
            4     80          +1             +51            -1
            5     96          +2             +34           +50
            6    112          +0              +2            -2
            7    128          +0              +1            -1
           10    176          +0              +1            -1
           12    208          +0              +1            -1
           17    288          +0              +1            -1
           18    304          +0              +2            -2
           25    416          +0              +3            -3
           26    432          +0              +3            -3
           27    448          +0              +3            -3
           29    480          +0              +3            -3
           30    496          +0              +1            -1
           31    512          +0              +1            -1

        # bytes in allocated blocks        =              +19,904
        # bytes in available blocks        =               -3,808
        -4 unused pools * 4096 bytes       =              -16,384
        # bytes lost to pool headers       =                 +192
        # bytes lost to quantization       =                  +96

          -1 free 1-sized PyTupleObjects * 32 bytes each =                  -32
          +1 free 5-sized PyTupleObjects * 64 bytes each =                  +64
                   +2 free PyDictObjects * 48 bytes each =                  +96
                   -2 free PyListObjects * 40 bytes each =                  -80
                 +1 free PyMethodObjects * 48 bytes each =                  +48

    """
    print(f'example_trace_malloc_for_documentation()')
    with debug_malloc_stats.DiffSysDebugMallocStats() as malloc_diff:
        for i in range(1, 9):
            list_of_strings.append(' ' * (i * 8))
    print(f'DiffSysDebugMallocStats.diff():')
    print(f'{malloc_diff.diff()}')


COUNT = 8

def example():
    for function in (test_under_512, test_over_512, test_well_over_512):
        print(f'Function: {function}'.center(75, '='))
        list_of_strings = []
        with debug_malloc_stats.DiffSysDebugMallocStats() as malloc_diff:
            function(COUNT, list_of_strings)
        print(f'DiffSysDebugMallocStats.diff():')
        print(f'{malloc_diff.diff()}')
        print(f'DONE: Function: {function}'.center(75, '='))
        print()


def example_timeit():
    for function in (test_under_512, test_over_512, test_well_over_512):
        list_of_strings = []
        function(COUNT, list_of_strings)


def example_timeit_with_debug_malloc_stats():
    for function in (test_under_512, test_over_512, test_well_over_512):
        list_of_strings = []
        with debug_malloc_stats.DiffSysDebugMallocStats() as malloc_diff:
            function(COUNT, list_of_strings)


def example_timeit_under_512():
    list_of_strings = []
    test_under_512(COUNT, list_of_strings)


def example_timeit_under_512_with_debug_malloc_stats():
    list_of_strings = []
    with debug_malloc_stats.DiffSysDebugMallocStats() as malloc_diff:
        test_under_512(COUNT, list_of_strings)


def example_timeit_over_512():
    list_of_strings = []
    test_over_512(COUNT, list_of_strings)


def example_timeit_over_512_with_debug_malloc_stats():
    list_of_strings = []
    with debug_malloc_stats.DiffSysDebugMallocStats() as malloc_diff:
        test_over_512(COUNT, list_of_strings)


def example_timeit_well_over_512():
    list_of_strings = []
    test_well_over_512(COUNT, list_of_strings)


def example_timeit_well_over_512_with_debug_malloc_stats():
    list_of_strings = []
    with debug_malloc_stats.DiffSysDebugMallocStats() as malloc_diff:
        test_well_over_512(COUNT, list_of_strings)


def main():
    # example_debug_malloc_stats_for_documentation([])
    print()
    # example()
    # print(timeit.repeat('p.memory_info().rss', setup='import psutil; p = psutil.Process()', number=1_000_000, repeat=5))

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
        # With _with_debug_malloc_stats
        times_with_debug_malloc_stats = timeit.repeat(f"{function}_with_debug_malloc_stats()", setup=f"from __main__ import {function}_with_debug_malloc_stats", number=NUMBER, repeat=REPEAT)
        times_with_debug_malloc_stats = [CONVERT * t / NUMBER for t in times_with_debug_malloc_stats]
        result = [f'{v:9.3f}' for v in times_with_debug_malloc_stats]
        times_mean_with_debug_malloc_stats = sum(times_with_debug_malloc_stats) / REPEAT
        print(
            f'{function + "_with_debug_malloc_stats":60}:'
            f' {", ".join(result)}'
            f' mean={times_mean_with_debug_malloc_stats:9.3f}'
            f' min={min(times_with_debug_malloc_stats):9.3f}'
            f' max={max(times_with_debug_malloc_stats):9.3f}'
            f' span={max(times_with_debug_malloc_stats) - min(times_with_debug_malloc_stats):9.3f}'
            f' x{times_mean_with_debug_malloc_stats / times_mean:>8.3f}'
        )
    return 0


if __name__ == '__main__':
    sys.exit(main())

