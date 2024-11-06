"""
At the moment these produce a log file per test.
TODO: Would be handy if we could specify a temporary file or file path, inspect it and clean up.
"""
import os
import time

import pytest

from pymemtrace import cPyMemTrace


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
        print(tracer.trace_file_wrapper)
        print(dir(tracer.trace_file_wrapper))
        assert os.path.isfile(tracer.trace_file_wrapper.log_file_path)


def test_start_message_to_log_file():
    message = 'START MESSAGE TO LOG FILE'
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cPyMemTrace.Profile(message=message) as profiler:
        b' ' * (1024 ** 2)
    with open(profiler.trace_file_wrapper.log_file_path) as file:
        file_data = file.read()
        assert file_data.startswith(message)


def test_inline_message_to_log_file():
    message = 'INLINE MESSAGE TO LOG'
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cPyMemTrace.Profile() as profiler:
        b' ' * (1024 ** 2)
        profiler.trace_file_wrapper.write_to_log(message)
    with open(profiler.trace_file_wrapper.log_file_path) as file:
        file_data = file.read()
        assert message in file_data
