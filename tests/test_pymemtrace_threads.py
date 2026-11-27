import datetime
import pprint
import random
import string
import tempfile
import threading
import time

import pytest

from pymemtrace import cPyMemTrace


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
        time.sleep(0.25)
    idx = len(object_list) - 1
    print(f' reference_tracing_live_object_counts({thread_name}) '.center(75, '-'))
    pprint.pprint(cPyMemTrace.reference_tracing_live_object_counts())
    print(f' reference_tracing_live_object_counts({thread_name}) DONE '.center(75, '-'))

    while object_list:
        value = object_list.pop()
        profiler.write_message_to_log(f'removed item {idx} at 0x{id(value):x} from thread {thread_name}')
        idx -= 1
        time.sleep(0.25)


def reference_tracing_thread_worker(
        thread_name: str,
        count: int,
        min_size: int, max_size:int, result_dict: dict
) -> None:
    """Tests Reference Tracing with the include_builtins switch."""
    result_dict['thread_name'] = thread_name
    message = f'reference_tracing_thread_worker({thread_name}):'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.ReferenceTracing(
                message=message, filepath=file.name,
                include_tp_names=['StringAndTime', 'datetime.datetime',]
        ) as profiler:
            assert profiler.log_file_path() == file.name
            reference_tracing_push_pop_to_list(profiler, thread_name, count, min_size, max_size)
        file.flush()
        result_dict['file_data'] = file.read()


def test_basic_threading():
    result_dict_a = {}
    result_dict_b = {}
    count = 2
    size_min = 1 << 10
    size_max = 1 << 14
    threads = [
        threading.Thread(
            target=reference_tracing_thread_worker,
            args=('Thread-A', count, size_min, size_max, result_dict_a,),
        ),
        threading.Thread(
            target=reference_tracing_thread_worker,
            args=('Thread-B', count, size_min, size_max, result_dict_b,),
        ),
    ]
    # Start each thread
    for t in threads:
        t.start()
        print(f'Started thread ident={t.ident}')
    # Wait for all threads to finish
    for t in threads:
        print(f'Joining thread ident={t.ident}')
        t.join()
    print()
    file_data_a = result_dict_a['file_data'].decode('ascii')
    for line in file_data_a.split('\n'):
        print(line)
    file_data_b = result_dict_b['file_data'].decode('ascii')
    for line in file_data_b.split('\n'):
        print(line)


def reference_tracing_thread_worker_in_depth(
        thread_name: str,
        depth: int,
        count: int,
        min_size: int, max_size:int, result_dict: dict
) -> None:
    """"""
    full_thread_name = f'{thread_name}.{depth}'
    # result_dict['thread_name'] = full_thread_name
    message = f'reference_tracing_thread_worker_in_depth({full_thread_name}):'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.ReferenceTracing(
                message=message, filepath=file.name,
                include_tp_names=['StringAndTime', 'datetime.datetime',]
        ) as profiler:
            assert profiler.log_file_path() == file.name
            reference_tracing_push_pop_to_list(profiler, thread_name, count // 2, min_size, max_size)
            if depth > 0:
                # Recurse...
                reference_tracing_thread_worker_in_depth(
                    thread_name, depth - 1, count, min_size, max_size, result_dict
                )
            else:
                print(' cPyMemTrace.reference_tracing_ll_dump_to_stdout() '.center(75, '-'))
                cPyMemTrace.reference_tracing_ll_dump_to_stdout(f'{full_thread_name}')
                print(' cPyMemTrace.reference_tracing_ll_dump_to_stdout() DONE '.center(75, '-'))
            reference_tracing_push_pop_to_list(profiler, thread_name, count // 2, min_size, max_size)
        file.flush()
        assert f'{full_thread_name}.file_data' not in result_dict
        result_dict[f'{full_thread_name}.file_data'] = file.read()


def test_threading_in_depth():
    num_threads = 4
    depth = 4
    count = 4
    size_min = 1 << 10
    size_max = 1 << 14
    # results = [dict() for _i in range(num_threads)]
    results = {}
    threads = [
        threading.Thread(
            target=reference_tracing_thread_worker_in_depth,
            args=(f'Thread-{chr(i + 65)}', depth, count, size_min, size_max, results,),
        ) for i in range(num_threads)
    ]
    # Start each thread
    for t in threads:
        t.start()
        print(f'Started thread ident={t.ident}')
    # Wait for all threads to finish
    for t in threads:
        print(f'Joining thread ident={t.ident}')
        t.join()
    print()
    # print(sorted(results.keys()))
    # print(results)
    for key in sorted(results.keys()):
        print(key)
        file_data = results[key].decode('ascii')
        for line in file_data.split('\n'):
            print(line)


if __name__ == '__main__':
    # test_basic_threading()
    test_threading_in_depth()
