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
        kwargs = {
            'message': message,
            'filepath': file.name,
            'include_builtins': include_builtins,
            'gc_collect_on_exit':  gc_collect_on_exit,
        }
        if exclude_tp_names is not None:
            kwargs['exclude_tp_names'] = exclude_tp_names
        if include_tp_names is not None:
            kwargs['include_tp_names'] = include_tp_names
        with cPyMemTrace.ReferenceTracing(**kwargs) as profiler:
            time_start = time.perf_counter()
            assert profiler.log_file_path() == file.name
            reference_tracing_push_pop_to_list(profiler, 'Main Thread', count, min_size, max_size)
            time_exec = time.perf_counter() - time_start
        file.flush()
        file_data = file.read()
        file_lines = file_data.split(b"\n")
        print(
            f'include_builtins {include_builtins:d}'
            f' exclude_tp_names {exclude_tp_names}'
            f' include_tp_names {include_tp_names}'
            f' gc_collect_on_exit {gc_collect_on_exit}'
            f' count {count}'
            f' min_size {min_size}'
            f' max_size {max_size}'
            f' File size {len(file_data):,d}'
            f' lines {len(file_lines):,d}'
            f' Time: {time_exec:.6f} (s)'
        )
        # print()
        # print(' file_0_data '.center(75, '-'))
        # for line in file_data.split(b'\n'):
        #     print(line)
        # print(' file_0_data DONE '.center(75, '-'))


if __name__ == '__main__':
    print('START')
    for args in [
        (
                # Profiler parameters
                True, None, None, -1,
                # Test parameters
                10, 1 << 14, 1 << 14
        ),
        (
                # Profiler parameters
                False, None, None, -1,
                # Test parameters
                10, 1 << 14, 1 << 14
        ),
        (
                # Profiler parameters
                False, None, ['StringAndTime', 'datetime.datetime',], -1,
                # Test parameters
                10, 1 << 14, 1 << 14
        ),
    ]:
        test_reference_tracing_performance_single_threaded(*args)
    print('FINISH')
