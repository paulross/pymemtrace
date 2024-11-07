"""
At the moment these produce a log file per test.
TODO: Would be handy if we could specify a temporary file or file path, inspect it and clean up.
"""
import gc
import os
import tempfile
import time

import pytest

from pymemtrace import cPyMemTrace


def test_module_dir():
    assert dir(cPyMemTrace) == [
        'Profile',
        'Trace',
        '__doc__',
        '__file__',
        '__loader__',
        '__name__',
        '__package__',
        '__spec__',
        'get_log_file_path_profile',
        'get_log_file_path_trace',
        'profile_wrapper_depth',
        'rss',
        'rss_peak',
        'trace_wrapper_depth'
    ]


def test_profile_basic():
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cPyMemTrace.Profile(0) as profiler:
        b' ' * (1024 ** 2)
        print(profiler)
        print(dir(profiler))
        assert dir(profiler) == ['__class__', '__delattr__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__',
                                 '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__',
                                 '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__',
                                 '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
                                 '__subclasshook__', 'trace_file_wrapper']
        print(profiler.trace_file_wrapper)
        print(dir(profiler.trace_file_wrapper))
        assert dir(profiler.trace_file_wrapper) == ['__class__', '__delattr__', '__dir__', '__doc__', '__eq__',
                                                    '__format__', '__ge__', '__getattribute__', '__getstate__',
                                                    '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__',
                                                    '__lt__', '__ne__', '__new__', '__reduce__', '__reduce_ex__',
                                                    '__repr__', '__setattr__', '__sizeof__', '__str__',
                                                    '__subclasshook__', 'd_rss_trigger', 'event_number', 'event_text',
                                                    'log_file_path', 'previous_event_number', 'rss', 'write_to_log']
        assert os.path.isfile(profiler.trace_file_wrapper.log_file_path)


def test_trace_basic():
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cPyMemTrace.Trace(0) as tracer:
        b' ' * (1024 ** 2)
        print(tracer)
        print(dir(tracer))
        assert dir(tracer) == ['__class__', '__delattr__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__',
                               '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__',
                               '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__',
                               '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
                               '__subclasshook__', 'trace_file_wrapper']
        print(tracer.trace_file_wrapper)
        print(dir(tracer.trace_file_wrapper))
        assert dir(tracer.trace_file_wrapper) == ['__class__', '__delattr__', '__dir__', '__doc__', '__eq__',
                                                  '__format__', '__ge__', '__getattribute__', '__getstate__',
                                                  '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__',
                                                  '__lt__', '__ne__', '__new__', '__reduce__', '__reduce_ex__',
                                                  '__repr__', '__setattr__', '__sizeof__', '__str__',
                                                  '__subclasshook__', 'd_rss_trigger', 'event_number', 'event_text',
                                                  'log_file_path', 'previous_event_number', 'rss', 'write_to_log']
        assert os.path.isfile(tracer.trace_file_wrapper.log_file_path)


def test_profile_start_message_to_log_file():
    message = 'START MESSAGE TO LOG FILE'
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cPyMemTrace.Profile(message=message) as profiler:
        b' ' * (1024 ** 2)
    with open(profiler.trace_file_wrapper.log_file_path) as file:
        file_data = file.read()
        assert file_data.startswith(message)


def test_profile_inline_message_to_log_file():
    message = 'INLINE MESSAGE TO LOG'
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cPyMemTrace.Profile() as profiler:
        b' ' * (1024 ** 2)
        profiler.trace_file_wrapper.write_to_log(message)
    with open(profiler.trace_file_wrapper.log_file_path) as file:
        file_data = file.read()
        assert message in file_data


def populate_list():
    temp_list = []
    for i in range(4):
        temp_list.append(b' ' * (1024 ** 2))
    while len(temp_list):
        temp_list.pop()


def test_profile_to_specific_log_file():
    message = 'START MESSAGE TO LOG FILE'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.Profile(0, message=message, filepath=file.name) as profiler:
            assert profiler.trace_file_wrapper.log_file_path == file.name
            for i in range(4):
                populate_list()
        time.sleep(1.0)
        file.flush()
        file_data = file.read()
        print()
        print('file_data:')
        for line in file_data.split(b'\n'):
            print(line)
        assert file_data.startswith(bytes(message, 'ascii'))


def test_trace_to_specific_log_file():
    message = 'START MESSAGE TO LOG FILE'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.Trace(0, message=message, filepath=file.name) as profiler:
            assert profiler.trace_file_wrapper.log_file_path == file.name
            for i in range(4):
                populate_list()
        time.sleep(1.0)
        file.flush()
        file_data = file.read()
        print()
        print('file_data:')
        for line in file_data.split(b'\n'):
            print(line)
        assert file_data.startswith(bytes(message, 'ascii'))


def test_profile_depth():
    assert cPyMemTrace.profile_wrapper_depth() == 0
    with cPyMemTrace.Profile(0) as profiler_0:
        assert cPyMemTrace.profile_wrapper_depth() == 1
        with cPyMemTrace.Profile(0) as profiler_1:
            assert cPyMemTrace.profile_wrapper_depth() == 2
            with cPyMemTrace.Profile(0) as profiler_2:
                assert cPyMemTrace.profile_wrapper_depth() == 3
            assert cPyMemTrace.profile_wrapper_depth() == 2
        assert cPyMemTrace.profile_wrapper_depth() == 1
    assert cPyMemTrace.profile_wrapper_depth() == 0


def test_trace_depth():
    assert cPyMemTrace.trace_wrapper_depth() == 0
    with cPyMemTrace.Trace(0) as tracer_0:
        assert cPyMemTrace.trace_wrapper_depth() == 1
        with cPyMemTrace.Trace(0) as tracer_1:
            assert cPyMemTrace.trace_wrapper_depth() == 2
            with cPyMemTrace.Trace(0) as tracer_2:
                assert cPyMemTrace.trace_wrapper_depth() == 3
            assert cPyMemTrace.trace_wrapper_depth() == 2
        assert cPyMemTrace.trace_wrapper_depth() == 1
    assert cPyMemTrace.trace_wrapper_depth() == 0
