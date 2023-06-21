import pytest

from pymemtrace import trace_malloc


def test_trace_malloc_simple():
    list_of_strings = []
    # with trace_malloc.TraceMalloc('filename') as tm:
    with trace_malloc.TraceMalloc('lineno') as tm:
        list_of_strings.append(' ' * 1024)
    # print()
    # print(f'tm.memory_start={tm.memory_start}')
    # print(f'tm.memory_finish={tm.memory_finish}')
    # print(f'tm.net_statistics(): {tm.net_statistics()}')
    # for stat in tm.net_statistics():
    #     print(stat)
    # assert tm.diff == 0, f'tm.diff={tm.diff}'
    # Different versions of Python will have a different number of entries.
    assert len(tm.net_statistics()) in (3, 4, 5, 6,)
    assert len(tm.statistics) > 3


if __name__ == '__main__':
    test_trace_malloc_simple()
