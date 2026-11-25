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


def reference_tracing_thread_worker(thread_name, count, min_size, max_size, result_dict:dict):
    """Tests Reference Tracing with the include_builtins switch."""
    result_dict['thread_name'] = thread_name
    message = f'reference_tracing_thread_worker({thread_name}):'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.ReferenceTracing(
                message=message, filepath=file.name,
                include_tp_names=['StringAndTime', 'datetime.datetime',]
        ) as profiler:
            assert profiler.log_file_path() == file.name
            l = []
            for i in range(count):
                value = StringAndTime(random.randint(min_size, max_size))
                profiler.write_message_to_log(f'added item {i} at 0x{id(value):x} from thread {thread_name}')
                l.append(value)
                time.sleep(0.25)
            idx = len(l) - 1
            while (l):
                value = l.pop()
                profiler.write_message_to_log(f'removed item {idx} at 0x{id(value):x} from thread {thread_name}')
                idx -= 1
                time.sleep(0.25)
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


if __name__ == '__main__':
    test_basic_threading()
