"""
Tests the cost of cPyMemTrace.
"""
import datetime
import faulthandler
import pprint
import random
import string
import sys
import tempfile
import time

import pytest

from pymemtrace import cPyMemTrace

faulthandler.enable()


class StringAndTime:
    """Just a recognisable class wit a datetime and a random string."""
    def __init__(self, size: int):
        self.now = datetime.datetime.now()
        self.str = ''.join(random.choices(string.printable, k=size))


def reference_tracing_push_pop_to_list(
        profiler: cPyMemTrace.ReferenceTracing,
        thread_name: str, count: int, min_size: int, max_size:int
) -> None:
    object_list = []
    for i in range(count):
        value = StringAndTime(random.randint(min_size, max_size))
        profiler.write_message_to_log(f'added item {i} at 0x{id(value):x} from thread {thread_name}')
        object_list.append(value)
    idx = len(object_list) - 1
    # print(f' reference_tracing_live_object_counts({thread_name}) '.center(75, '-'))
    # pprint.pprint(cPyMemTrace.reference_tracing_live_object_counts())
    # print(f' reference_tracing_live_object_counts({thread_name}) DONE '.center(75, '-'))

    while object_list:
        value = object_list.pop()
        profiler.write_message_to_log(f'removed item {idx} at 0x{id(value):x} from thread {thread_name}')
        idx -= 1


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
@pytest.mark.parametrize(
    # Profiler parameters
    'include_builtins, exclude_tp_names, include_tp_names, gc_collect_on_exit'
    # Test parameters
    ', count, min_size, max_size',
    (
            (
                # Profiler parameters
                True, [], [], -1,
                # Test parameters
                1, 1 << 10, 1 << 10
            ),
    )
)
def test_reference_tracing_performance_single_threaded(
        include_builtins, exclude_tp_names, include_tp_names, gc_collect_on_exit,
        count, min_size, max_size
):
    """Tests Reference Tracing writing to a temporary file."""
    message = f'test_reference_tracing_performance():'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.ReferenceTracing(
                message=message, filepath=file.name,
                include_builtins=include_builtins,
                exclude_tp_names=exclude_tp_names,
                include_tp_names=include_tp_names,
                gc_collect_on_exit=gc_collect_on_exit,
        ) as profiler:
            time_start = time.perf_counter()
            assert profiler.log_file_path() == file.name
            reference_tracing_push_pop_to_list(profiler, 'Main Thread', count, min_size, max_size)
            print(f'Time: {time.perf_counter() - time_start:.6f} (s)')


if __name__ == '__main__':
    print('START')
    args = (
        # Profiler parameters
        True, [], [], -1,
        # Test parameters
        1, 1 << 10, 1 << 10
    )
    test_reference_tracing_performance_single_threaded(*args)
    print('FINISH')
