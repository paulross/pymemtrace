import datetime
import pprint
import random
import string
import tempfile
import threading
import time

from pymemtrace import cPyMemTrace

class StringAndTime:
    """Just a recognisable class wit a datetime and a random string."""
    def __init__(self, size: int):
        self.now = datetime.datetime.now()
        self.str = ''.join(random.choices(string.printable, k=size))

def reference_tracing_simple_thread_worker(thread_name, siz, sleep_before, sleep_mid, sleep_after):
    """Tests Reference Tracing with the include_builtins switch."""
    message = f'reference_tracing_thread_worker({thread_name}):'
    time.sleep(sleep_before)
    with cPyMemTrace.ReferenceTracing(
            message=message,
            include_tp_names=['StringAndTime', 'datetime.datetime',]
    ) as profiler:
        value = StringAndTime(siz)
        value_id = id(value)
        profiler.write_message_to_log(f'# Created item at 0x{value_id} from thread {thread_name}')
        time.sleep(sleep_mid)
        del value
        profiler.write_message_to_log(f'# Deleted item 0x{id(value_id)} from thread {thread_name}')
        time.sleep(sleep_after)


def test_simple_threading():
    threads = [
        threading.Thread(
            target=reference_tracing_simple_thread_worker,
            args=('Thread-A', 1024**2, 0.0, 0.25, 0.0,),
        ),
        threading.Thread(
            target=reference_tracing_simple_thread_worker,
            # args=('Thread-B', 1024**2, 0.125, 0.25, 0.25,),
            args=('Thread-B', 1024**2, 1.125, 0.25, 0.25,),
        ),
    ]
    # Start each thread
    for t in threads:
        t.start()
    # Wait for all threads to finish
    for t in threads:
        t.join()


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
                profiler.write_message_to_log(f'# adding item {i} at 0x{id(value)} from thread {thread_name}')
                l.append(value)
                time.sleep(0.25)
            while (l):
                value = l.pop()
                profiler.write_message_to_log(f'# removed item {len(l) - 1} at 0x{id(value)} from thread {thread_name}')
                time.sleep(0.25)
        file.flush()
        result_dict['file_data'] = file.read()

def _test_basic_threading():
    result_dict_a = {}
    result_dict_b = {}
    threads = [
        threading.Thread(target=reference_tracing_thread_worker, args=('Thread-A', 4, 1 << 10, 1 <<14, result_dict_a,)),
        threading.Thread(target=reference_tracing_thread_worker, args=('Thread-B', 4, 1 << 10, 1 <<14, result_dict_b,)),
    ]
    # Start each thread
    for t in threads:
        t.start()
    # Wait for all threads to finish
    for t in threads:
        t.join()
    print()
    file_data_a = result_dict_a['file_data'].decode('ascii')
    for line in file_data_a.split('\n'):
        print(line)
    file_data_b = result_dict_b['file_data'].decode('ascii')
    for line in file_data_b.split('\n'):
        print(line)
