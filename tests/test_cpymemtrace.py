"""
At the moment these produce a log file per test.
"""
import faulthandler
import gc
import os
import pprint
import random
import sys
import tempfile
import time
import typing

import pytest

from pymemtrace import cPyMemTrace
from pymemtrace import cMemLeak

faulthandler.enable()


@pytest.mark.skipif(not (sys.version_info.minor < 13), reason='Python < 3.13')
def test_module_dir_pre_313():
    pprint.pprint(dir(cPyMemTrace))
    assert dir(cPyMemTrace) == [
        'Profile',
        'Trace',
        '__doc__',
        '__file__',
        '__loader__',
        '__name__',
        '__package__',
        '__spec__',
        'profile_wrapper_depth',
        'rss',
        'rss_peak',
        'trace_wrapper_depth',
    ]


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_module_dir_post_313():
    pprint.pprint(dir(cPyMemTrace))
    assert dir(cPyMemTrace) == [
        'Profile',
        'ReferenceTracing',
        'ReferenceTracingSimple',
        'Trace',
        '__doc__',
        '__file__',
        '__loader__',
        '__name__',
        '__package__',
        '__spec__',
        'profile_wrapper_depth',
        'reference_tracing_simple_wrapper_depth',
        'reference_tracing_wrapper_depth',
        'rss',
        'rss_peak',
        'trace_wrapper_depth',
    ]


@pytest.mark.skipif(not (sys.version_info.minor <= 10), reason='Python <= 3.10')
def test_profile_basic_lt_310():
    with cPyMemTrace.Profile(0) as profiler:
        b' ' * (1024 ** 2)
        print()
        print('test_profile_basic():')
        print(profiler)
        print(dir(profiler))
        assert dir(profiler) == ['__class__', '__delattr__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__',
                                 '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__',
                                 '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__',
                                 '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
                                 '__subclasshook__',
                                 'log_file_path',
                                 'write_message_to_log',
                                 'write_to_log',
                                 ]
        assert os.path.isfile(profiler.log_file_path())


@pytest.mark.skipif(not (sys.version_info.minor > 10), reason='Python > 3.10')
def test_profile_basic_gt_310():
    print()
    print('test_profile_basic_gt_310():')
    with cPyMemTrace.Profile(0) as profiler:
        b' ' * (1024 ** 2)
        print(f'Profiler: {profiler}')
        print(f'sys.getrefcount(profiler): {sys.getrefcount(profiler)}')
        print(f'sys.getrefcount(profiler): {sys.getrefcount(profiler)}')
        print(dir(profiler))
        assert dir(profiler) == ['__class__', '__delattr__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__',
                                 '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__',
                                 '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__',
                                 '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
                                 '__subclasshook__',
                                 'log_file_path',
                                 'write_message_to_log',
                                 'write_to_log',
                                 ]
        assert os.path.isfile(profiler.log_file_path())
    print(f'Profiler: {profiler}')
    print(type(profiler))
    print(profiler)
    print(f'Profiler: {profiler}')
    print(f'sys.getrefcount(profiler): {sys.getrefcount(profiler)}')
    print(f'sys.getrefcount(profiler): {sys.getrefcount(profiler)}')


@pytest.mark.skipif(not (sys.version_info.minor <= 10), reason='Python <= 3.10')
def test_trace_basic_lt_310():
    with cPyMemTrace.Trace(0) as tracer:
        b' ' * (1024 ** 2)
        print()
        print('test_trace_basic():')
        print(tracer)
        print(dir(tracer))
        assert dir(tracer) == ['__class__', '__delattr__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__',
                               '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__',
                               '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__',
                               '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
                               '__subclasshook__',
                               'log_file_path',
                               'write_message_to_log',
                               'write_to_log',
                               ]
        assert os.path.isfile(tracer.log_file_path())


@pytest.mark.skipif(not (sys.version_info.minor > 10), reason='Python > 3.10')
def test_trace_basic_gt_310():
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cPyMemTrace.Trace(0) as tracer:
        b' ' * (1024 ** 2)
        print()
        print('test_trace_basic():')
        print(tracer)
        print(dir(tracer))
        assert dir(tracer) == ['__class__', '__delattr__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__',
                               '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__',
                               '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__',
                               '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
                               '__subclasshook__',
                               'log_file_path',
                               'write_message_to_log',
                               'write_to_log',
                               ]
        print(tracer)
        print(dir(tracer))
        assert dir(tracer) == ['__class__', '__delattr__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__',
                               '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__',
                               '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__',
                               '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__',
                               'log_file_path', 'write_message_to_log', 'write_to_log']
        assert os.path.isfile(tracer.log_file_path())


@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace,
    )
)
def test_profile_start_message_to_log_file(cls):
    message = 'test_profile_start_message_to_log_file():'
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cls(message=message) as profiler:
        log_path = profiler.log_file_path()
        print(f'Log file Profile: {log_path}')
        b' ' * (1024 ** 2)
        # print(dir(profiler))
        # with open(log_path) as file:
        time.sleep(2.0)
    with open(log_path) as file:
        file_data = file.read()
        print()
        print(f'File data [{len(file_data)}]:\n{file_data}')
        assert file_data.startswith(message)
    # Clean up on exit removes log file path
    assert profiler.log_file_path() is None


@pytest.mark.skipif(not (sys.version_info.minor < 13), reason='Python < 3.13')
@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace,
    )
)
def test_profile_inline_message_to_log_file_pre_313(cls):
    message = 'test_profile_inline_message_to_log_file():'
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cls() as profiler:
        b' ' * (1024 ** 2)
        profiler.write_message_to_log(message)
        log_file_path = profiler.log_file_path()
    with open(log_file_path) as file:
        file_data = file.read()
        print()
        print(f'File data [{len(file_data)}]:\n{file_data}')
        assert message in file_data


@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace,
    )
)
def test_profile_inline_message_to_log_file_post_313(cls):
    message = 'test_profile_inline_message_to_log_file():'
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cls() as profiler:
        b' ' * (1024 ** 2)
        profiler.write_message_to_log(message)
        log_file_path = profiler.log_file_path()
    with open(log_file_path) as file:
        file_data = file.read()
        print()
        print(f'File data [{len(file_data)}]:\n{file_data}')
        assert message in file_data


def create_bytes(length: int) -> bytes:
    return b' ' * length


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reference_trace_basic_post_313():
    message = 'test_profile_inline_message_to_log_file():'
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cPyMemTrace.ReferenceTracing() as profiler:
        l = []
        for i in range(4):
            b = create_bytes(random.randint(512, 1024) + 1024 ** 2)
            # print(f'TRACE test_reference_trace_basic_post_313(): 0x{id(b):x}')
            l.append(b)
            time.sleep(0.25)
        while len(l):
            l.pop()
        log_file_path = profiler.log_file_path()
    with open(log_file_path) as file:
        file_data = file.read()
        print()
        print(f'File data [{len(file_data)}]:\n{file_data}')
        # assert message in file_data


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_trace_basic_dir_gt_313():
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cPyMemTrace.ReferenceTracing() as profiler:
        b' ' * (1024 ** 2)
        print()
        print('test_trace_basic_dir_gt_313():')
        print(profiler)
        # assert repr(profiler) == 'cPyMemTrace.ReferenceTracing'
        dir_profiler = dir(profiler)
        print(dir_profiler)
        assert dir_profiler == ['__class__', '__delattr__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__',
                                '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__',
                                '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__',
                                '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
                                '__subclasshook__',
                                'count_del',
                                'count_new',
                                'log_file_path',
                                'resume',
                                'suspend',
                                'write_message_to_log',
                                # TODO: Why does un-commenting this cause an abort with debug Python?
                                # The abort is in Python/frame.c#48 assert(frame->frame_obj == NULL);
                                # 'not_present_at_all',
                                ]
        assert os.path.isfile(profiler.log_file_path())
    assert dir_profiler == ['__class__', '__delattr__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__',
                            '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__',
                            '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__',
                            '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
                            '__subclasshook__',
                            'count_del',
                            'count_new',
                            'log_file_path',
                            'resume',
                            'suspend',
                            'write_message_to_log',
                            # TODO: Why does un-commenting this **not** cause an abort with debug Python?
                            # The abort is in Python/frame.c#48 assert(frame->frame_obj == NULL);
                            # 'not_present_at_all',
                            ]


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_trace_basic_dir_suspend_resume_gt_313():
    time.sleep(1.1)  # Make sure that we increment the log file name by one second.
    with cPyMemTrace.ReferenceTracing() as profiler:
        b' ' * (1024 ** 2)
        print()
        print('test_trace_basic_dir_gt_313():')
        print(profiler)
        # assert repr(profiler) == 'cPyMemTrace.ReferenceTracing'
        dir_profiler = dir(profiler)
        print(dir_profiler)
        profiler.suspend()
        # TODO: Fix this.
        # with pytest.raises(ValueError) as err:
        #     assert dir_profiler == ['__class__', '__delattr__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__',
        #                             '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__',
        #                             '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__',
        #                             '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
        #                             '__subclasshook__',
        #                             'log_file_path',
        #                             'resume',
        #                             'suspend',
        #                             'write_message_to_log',
        #                             # TODO: Why does un-commenting this cause an abort with debug Python?
        #                             # The abort is in Python/frame.c#48 assert(frame->frame_obj == NULL);
        #                             'not_present_at_all',
        #                             ]
        # assert err.value.args[0] == "Right contains one more item: 'not_present_at_all'"
        profiler.resume()
        assert os.path.isfile(profiler.log_file_path())
    assert dir_profiler == ['__class__', '__delattr__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__',
                            '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__',
                            '__init__', '__init_subclass__', '__le__', '__lt__', '__ne__', '__new__', '__reduce__',
                            '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
                            '__subclasshook__',
                            'count_del',
                            'count_new',
                            'log_file_path',
                            'resume',
                            'suspend',
                            'write_message_to_log',
                            # TODO: Why does un-commenting this **not** cause an abort with debug Python?
                            # The abort is in Python/frame.c#48 assert(frame->frame_obj == NULL);
                            # 'not_present_at_all',
                            ]


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_trace_basic_list_cmp_suspend_resume_gt_313():
    with cPyMemTrace.ReferenceTracing(
            message='test_trace_basic_list_cmp_suspend_resume_gt_313() with result') as profiler:
        b' ' * (1024 ** 2)
        print()
        print('test_trace_basic_list_cmp_suspend_resume_gt_313():')
        print(profiler)
        # profiler.suspend()
        # assert ['a', 'b', 'c', ] == ['a', 'b', 'c', 'd', ]
        # profiler.resume()
        result = ['a', 'b', 'c', ] == ['a', 'b', 'c', 'd', ]
        print(f'Result: {result}')
        # assert result
        print(f'NEW: {profiler.count_new()}')
        print(f'DEL: {profiler.count_del()}')
        assert os.path.isfile(profiler.log_file_path())


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_trace_basic_list_cmp_ref_trace_simple_suspend_resume_gt_313():
    with cPyMemTrace.ReferenceTracingSimple() as profiler:
        print()
        print('test_trace_basic_list_cmp_suspend_resume_gt_313():')
        print(profiler)
        # profiler.suspend()
        # result = ['a', 'b', 'c', ] == ['a', 'b', 'c', ]  # 'd', ]
        with pytest.raises(AssertionError) as err:
            assert ['a', 'b', 'c', ] == ['a', 'b', 'c', 'd', ]
        # print(f'TRACE: {err.value.args[0]}')
        assert err.value.args[0].startswith("assert ['a', 'b', 'c'] == ['a', 'b', 'c', 'd']\n")
        # profiler.resume()
        # print(f'Result: {result}')
        print(f'NEW: {profiler.count_new()}')
        print(f'DEL: {profiler.count_del()}')


@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace,
    )
)
def test_profile_and_trace_bad_keywords(cls):
    with pytest.raises(TypeError) as err:
        with cls(foo=0):
            pass
    assert 'foo' in err.value.args[0]


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reference_trace_bad_keywords_post_313():
    with pytest.raises(TypeError) as err:
        with cPyMemTrace.ReferenceTracing(d_rss_trigger=0):
            pass
    assert err.value.args[0] == "this function got an unexpected keyword argument 'd_rss_trigger'"


@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace,
    )
)
def test_profile_and_trace_bad_arg_types(cls):
    with pytest.raises(TypeError) as err:
        with cls('foo'):
            pass
    assert 'str' in err.value.args[0]


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reference_trace_bad_arg_types_post_313():
    with pytest.raises(TypeError) as err:
        with cPyMemTrace.ReferenceTracing(21):
            pass
    assert err.value.args[0] == "argument 1 must be str, not int"


@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace,
    )
)
def test_profile_and_trace_too_many_args(cls):
    with pytest.raises(TypeError) as err:
        with cls('foo', 'bar', 'baz', 'stuff'):
            pass
    assert err.value.args[0] == "function takes at most 3 arguments (4 given)"


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reference_trace_too_many_args_post_313():
    with pytest.raises(TypeError) as err:
        with cPyMemTrace.ReferenceTracing(
                'message',
                'file_path',
                False, #'include_builtins',
                [], #'exclude_tp_names',
                [], #'include_tp_names',
                2, # 'gc_collect_on_exit'
                'and_one_more'
        ):
            pass
    assert err.value.args[0] == "function takes at most 6 arguments (7 given)"


class BytesWrapper:
    def __init__(self, length: int):
        self.bytes = b' ' * length


def exercise_bytes_wrapper():
    """Creates a bunch of BytesWrapper objects containing different lengths of bytes."""
    l = []
    for i in range(4):
        length = random.randint(512, 1024) + 1024 ** 2
        l.append(BytesWrapper(length))
        time.sleep(0.25)
    while len(l):
        p = l.pop()
        del p
        time.sleep(0.25)


def make_bytes_wrappers_with_reference_tracing() -> str:
    with cPyMemTrace.ReferenceTracing() as profiler:
        exercise_bytes_wrapper()
        return profiler.log_file_path()


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reference_trace_special_class_post_313():
    for i in range(1):
        log_file_path = make_bytes_wrappers_with_reference_tracing()
    with open(log_file_path) as file:
        file_data = file.read()
        print()
        print(f'File data [{len(file_data)}]:\n{file_data}')
        # assert 'message foo' in file_data


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reference_trace_depth():
    """Test stacking ReferenceTracing objects."""
    assert cPyMemTrace.profile_wrapper_depth() == 0
    assert cPyMemTrace.trace_wrapper_depth() == 0
    assert cPyMemTrace.reference_tracing_wrapper_depth() == 0

    with cPyMemTrace.ReferenceTracing('test_reference_trace_depth(): ref_trace_0') as ref_trace_0:
        assert cPyMemTrace.profile_wrapper_depth() == 0
        assert cPyMemTrace.trace_wrapper_depth() == 0
        assert cPyMemTrace.reference_tracing_wrapper_depth() == 1

        time.sleep(0.5)

        with cPyMemTrace.ReferenceTracing('test_reference_trace_depth(): ref_trace_1') as ref_trace_1:
            assert cPyMemTrace.profile_wrapper_depth() == 0
            assert cPyMemTrace.trace_wrapper_depth() == 0
            assert cPyMemTrace.reference_tracing_wrapper_depth() == 2

            time.sleep(0.5)

            with cPyMemTrace.ReferenceTracing('test_reference_trace_depth(): ref_trace_2') as ref_trace_2:
                assert cPyMemTrace.profile_wrapper_depth() == 0
                assert cPyMemTrace.trace_wrapper_depth() == 0
                assert cPyMemTrace.reference_tracing_wrapper_depth() == 3

                time.sleep(0.5)

            assert cPyMemTrace.profile_wrapper_depth() == 0
            assert cPyMemTrace.trace_wrapper_depth() == 0
            assert cPyMemTrace.reference_tracing_wrapper_depth() == 2

        assert cPyMemTrace.profile_wrapper_depth() == 0
        assert cPyMemTrace.trace_wrapper_depth() == 0
        assert cPyMemTrace.reference_tracing_wrapper_depth() == 1

    assert cPyMemTrace.profile_wrapper_depth() == 0
    assert cPyMemTrace.trace_wrapper_depth() == 0
    assert cPyMemTrace.reference_tracing_wrapper_depth() == 0


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reference_trace_and_profile_depth():
    assert cPyMemTrace.reference_tracing_wrapper_depth() == 0
    assert cPyMemTrace.profile_wrapper_depth() == 0
    with cPyMemTrace.ReferenceTracing() as ref_trace_0:
        assert cPyMemTrace.reference_tracing_wrapper_depth() == 1
        assert cPyMemTrace.profile_wrapper_depth() == 0
        with cPyMemTrace.Profile() as ref_trace_1:
            assert cPyMemTrace.reference_tracing_wrapper_depth() == 1
            assert cPyMemTrace.profile_wrapper_depth() == 1
        assert cPyMemTrace.reference_tracing_wrapper_depth() == 1
        assert cPyMemTrace.profile_wrapper_depth() == 0
    assert cPyMemTrace.reference_tracing_wrapper_depth() == 0
    assert cPyMemTrace.profile_wrapper_depth() == 0


@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace,
    )
)
def test_messaging_for_documentation(cls):
    with cls(d_rss_trigger=-1, message="Start message") as profiler:
        for i in range(8):
            str_len = random.randint(100 * 1024 ** 2, 500 * 1024 ** 2)
            profiler.write_message_to_log(f'Before allocation of {str_len} bytes.')
            s = ' ' * str_len
            time.sleep(0.5)
            del s
            profiler.write_message_to_log(f'After de-allocation of {str_len} bytes.')
            time.sleep(0.5)
        time.sleep(0.5)
        with open(profiler.log_file_path()) as file:
            file_data = file.read()
            print()
            print(f'File data [{len(file_data)}]:\n{file_data}')
            # assert 0


@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace
    )
)
def test_profile_inline_message_to_log_file_after_exit(cls):
    message = 'test_profile_inline_message_to_log_file():'
    with cls() as profiler:
        b' ' * (1024 ** 2)
        profiler.write_message_to_log(message)
    with pytest.raises(IOError) as err:
        profiler.write_message_to_log(message)
    assert err.value.args[0] == 'Log file is closed.'


def populate_list():
    temp_list = []
    for i in range(4):
        temp_list.append(b' ' * (1024 ** 2))
    while len(temp_list):
        temp_list.pop()


@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace,
    )
)
def test_profile_trace_0_populate_list(cls):
    message = 'test_profile_0_populate_list()'
    with cls(0, message=message):
        for i in range(4):
            populate_list()
        time.sleep(1.0)


@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace,
    )
)
def test_profile_trace_populate_list(cls):
    message = 'test_profile_trace_populate_list()'
    with cls(message=message):
        for i in range(4):
            populate_list()
        time.sleep(1.0)


@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace,
    )
)
def test_profile_trace_to_specific_log_file(cls):
    message = 'test_profile_trace_to_specific_log_file():'
    with tempfile.NamedTemporaryFile() as file:
        with cls(0, message=message, filepath=file.name) as profiler:
            assert profiler.log_file_path() == file.name
            for i in range(4):
                populate_list()
        time.sleep(1.0)
        file.flush()
        file_data = file.read()
        # print()
        # print('file_data:')
        # for line in file_data.split(b'\n'):
        #     print(line)
        assert file_data.startswith(bytes(message, 'ascii'))


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reference_tracing_to_specific_log_file():
    message = 'test_reference_tracing_to_specific_log_file():'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.ReferenceTracing(message=message, filepath=file.name) as profiler:
            assert profiler.log_file_path() == file.name
            for i in range(4):
                populate_list()
        time.sleep(1.0)
        file.flush()
        file_data = file.read()
        print()
        print(' file_0_data '.center(75, '-'))
        for line in file_data.split(b'\n'):
            print(line)
        print(' file_0_data DONE '.center(75, '-'))
        assert file_data.startswith(bytes(message, 'ascii'))


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
@pytest.mark.parametrize(
    'include_builtins',
    (
            True,
            False,
    )
)
def test_reference_tracing_include_builtins_choice(include_builtins):
    """Tests Reference Tracing with the include_builtins switch."""
    message = f'test_reference_tracing_include_builtins_choice({include_builtins}):'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.ReferenceTracing(
                message=message, filepath=file.name, include_builtins=include_builtins
        ) as profiler:
            assert profiler.log_file_path() == file.name
            exercise_bytes_wrapper()
        time.sleep(1.0)
        file.flush()
        file_data = file.read()
        print()
        print(' file_0_data '.center(75, '-'))
        for line in file_data.split(b'\n'):
            print(line)
        print(' file_0_data DONE '.center(75, '-'))
        assert file_data.startswith(bytes(message, 'ascii'))
        # Some tests on the output, weather it has builtin types
        # Note the spaces around the type name, so we don't pick up spurious data.
        # Note b' range_iterator ' is not detected as a builtin as it does not have
        # a Py*_Check() C API so include_builtins=False will not eliminate it.
        assert b'BytesWrapper' in file_data
        for type_name in (
                b' int ', b' str ', b' bytes ', b' list ', b' tuple ',
                b' builtin_function_or_method ', b' range ',):
            if include_builtins:
                assert type_name in file_data
            else:
                assert type_name not in file_data


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
@pytest.mark.parametrize(
    'exclude_tp_names',
    (
            ['range_iterator',],
    )
)
def test_reference_tracing_exclude_tp_names(exclude_tp_names):
    """Tests Reference Tracing with the include_builtins switch."""
    message = f'test_reference_tracing_exclude_tp_names():'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.ReferenceTracing(
                message=message, filepath=file.name,
                include_builtins=False, exclude_tp_names=exclude_tp_names,
        ) as profiler:
            assert profiler.log_file_path() == file.name
            exercise_bytes_wrapper()
        time.sleep(1.0)
        file.flush()
        file_data = file.read()
        print()
        print(' file_0_data '.center(75, '-'))
        for line in file_data.split(b'\n'):
            print(line)
        print(' file_0_data DONE '.center(75, '-'))
        assert file_data.startswith(bytes(message, 'ascii'))
        # Some tests on the output, weather it has builtin types
        # Note the spaces around the type name, so we don't pick up spurious data.
        # Note b' range_iterator ' is not detected as a builtin as it does not have
        # a Py*_Check() C API so include_builtins=False will not eliminate it.
        assert b'BytesWrapper' in file_data
        for type_name in exclude_tp_names:
            assert type_name.encode('ascii') not in file_data


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
@pytest.mark.parametrize(
    'include_tp_names',
    (
            ['BytesWrapper',],
    )
)
def test_reference_tracing_include_tp_names(include_tp_names):
    """Tests Reference Tracing with the include_builtins switch."""
    message = f'test_reference_tracing_exclude_tp_names():'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.ReferenceTracing(
                message=message, filepath=file.name,
                include_builtins=False, include_tp_names=include_tp_names,
        ) as profiler:
            assert profiler.log_file_path() == file.name
            exercise_bytes_wrapper()
        time.sleep(1.0)
        file.flush()
        file_data = file.read()
        print()
        print(' file_0_data '.center(75, '-'))
        for line in file_data.split(b'\n'):
            print(line)
        print(' file_0_data DONE '.center(75, '-'))
        assert file_data.startswith(bytes(message, 'ascii'))
        # Some tests on the output, weather it has builtin types
        # Note the spaces around the type name, so we don't pick up spurious data.
        # Note b' range_iterator ' is not detected as a builtin as it does not have
        # a Py*_Check() C API so include_builtins=False will not eliminate it.
        assert b'BytesWrapper' in file_data
        assert b'range_iterator' not in file_data


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
@pytest.mark.parametrize(
    'include_tp_names',
    (
            ['BytesWrapper',],
    )
)
def test_reference_tracing_include_tp_names_with_gc_collect(include_tp_names):
    """Tests Reference Tracing with the include_builtins switch."""
    message = f'test_reference_tracing_exclude_tp_names():'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.ReferenceTracing(
                message=message, filepath=file.name,
                include_builtins=False, include_tp_names=include_tp_names,
                gc_collect_on_exit=2,
        ) as profiler:
            assert profiler.log_file_path() == file.name
            exercise_bytes_wrapper()
        time.sleep(1.0)
        file.flush()
        file_data = file.read()
        print()
        print(' file_0_data '.center(75, '-'))
        for line in file_data.split(b'\n'):
            print(line)
        print(' file_0_data DONE '.center(75, '-'))
        assert file_data.startswith(bytes(message, 'ascii'))
        # Some tests on the output, weather it has builtin types
        # Note the spaces around the type name, so we don't pick up spurious data.
        # Note b' range_iterator ' is not detected as a builtin as it does not have
        # a Py*_Check() C API so include_builtins=False will not eliminate it.
        assert b'BytesWrapper' in file_data
        assert b'range_iterator' not in file_data


def create_tmp_list_of_memory_objects(cls: typing.Type, siz: int, count: int, cause_leak: bool):
    l = []
    for i in range(count):
        obj = cls(siz)
        if cause_leak:
            obj.inc_refcnt(1)
        l.append(obj)
    while len(l):
        l.pop()


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
@pytest.mark.parametrize(
    'cls, cause_leak',
    (
            (cMemLeak.CMalloc, False),
            (cMemLeak.CMalloc, True),
            (cMemLeak.PyRawMalloc, False),
            (cMemLeak.PyRawMalloc, True),
            (cMemLeak.PyMalloc, False),
            (cMemLeak.PyMalloc, True),
    )
)
def test_reference_tracing_deliberate_leak_to_temp_file(cls, cause_leak):
    """Tests Reference Tracing by causing a deliberate memory leak to a temporary file."""
    message = f'test_reference_tracing_deliberate_leak_to_temp_file():' \
              f' Class: {cls.__name__} Leak: {cause_leak}'
    with tempfile.NamedTemporaryFile() as file:
        with cPyMemTrace.ReferenceTracing(
                message=message, filepath=file.name,
                include_builtins=False,
                include_tp_names=[f'cMemLeak.{cls.__name__}',],
                gc_collect_on_exit=2,
        ) as profiler:
            assert profiler.log_file_path() == file.name
            create_tmp_list_of_memory_objects(cls, 128, 4, cause_leak)
        time.sleep(1.0)
        file.flush()
        file_data = file.read()
        print()
        print(' file_0_data '.center(75, '-'))
        for line in file_data.split(b'\n'):
            print(line)
        print(' file_0_data DONE '.center(75, '-'))
        assert file_data.startswith(bytes(message, 'ascii'))
        assert bytes(cls.__name__, encoding='ascii') in file_data


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
@pytest.mark.parametrize(
    'cls, cause_leak',
    (
            (cMemLeak.CMalloc, False),
            (cMemLeak.CMalloc, True),
            (cMemLeak.PyRawMalloc, False),
            (cMemLeak.PyRawMalloc, True),
            (cMemLeak.PyMalloc, False),
            (cMemLeak.PyMalloc, True),
    )
)
def test_reference_tracing_deliberate_leak_to_cwd(cls, cause_leak):
    """Tests Reference Tracing by causing a deliberate memory leak to a log file."""
    message = f'test_reference_tracing_deliberate_leak_to_cwd():' \
              f' Class: {cls.__name__} Leak: {cause_leak}'
    with cPyMemTrace.ReferenceTracing(
            message=message,
            include_builtins=False,
            include_tp_names=[f'cMemLeak.{cls.__name__}',],
            gc_collect_on_exit=2,
    ) as profiler:
        create_tmp_list_of_memory_objects(cls, 128, 4, cause_leak)


@pytest.mark.parametrize(
    'cls',
    (
            cPyMemTrace.Profile,
            cPyMemTrace.Trace,
    )
)
def test_profile_trace_to_specific_log_file_nested(cls):
    """This tests that the nested context managers work properly.
    In particular, when the inner one exists the outer one takes over."""
    SLEEP = 1.0
    d_rss_trigger = 0
    message = 'test_profile_trace_to_specific_log_file_nested():'
    with tempfile.NamedTemporaryFile() as file_0:
        # Create the outer context manager.
        with cls(d_rss_trigger, message=message + '#level0', filepath=file_0.name) as trace_0:
            trace_0.write_message_to_log('# Level 0 __enter__')
            # Exercise the outer context manager *before* the inner context manager.
            assert trace_0.log_file_path() == file_0.name
            for i in range(4):
                populate_list()
            trace_0.write_message_to_log('# Level 0 after populate_list()')

            # Now the inner.
            with tempfile.NamedTemporaryFile() as file_1:
                trace_0.write_message_to_log('# Level 0 just prior to level 1 __enter__')

                # Create the inner context manager.
                with cls(d_rss_trigger, message=message + '#level1', filepath=file_1.name) as trace_1:

                    trace_0.write_message_to_log('# Level 0 events should be suspended')

                    trace_1.write_message_to_log('# Level 1 __enter__')
                    # Exercise the inner context manager.
                    assert trace_1.log_file_path() == file_1.name
                    for i in range(4):
                        trace_0.write_message_to_log('# Level 0 events should be suspended')
                        populate_list()

                    trace_0.write_message_to_log('# Level 0 events should be suspended')

                    trace_1.write_message_to_log('# Level 1 after populate_list()')

                # Check the inner output
                time.sleep(SLEEP)
                file_1.flush()
                file_1_data = file_1.read()
                print()
                print(' file_1_data '.center(75, '-'))
                for line in file_1_data.split(b'\n'):
                    print(line.decode('ascii'))
                print(' file_1_data DONE '.center(75, '-'))
                assert file_1_data.startswith(bytes(message + '#level1', 'ascii'))

            trace_0.write_message_to_log('# Level 0 after level 1 exit')
            # Exercise the outer context manager *before* the inner context manager.
            assert trace_0.log_file_path() == file_0.name
            for i in range(4):
                populate_list()
            trace_0.write_message_to_log('# Level 0 after level 1 exit and populate_list()')

        time.sleep(SLEEP)
        file_0.flush()
        file_0_data = file_0.read()
        print()
        print(' file_0_data '.center(75, '-'))
        for line in file_0_data.split(b'\n'):
            print(line.decode('ascii'))
        print(' file_0_data DONE '.center(75, '-'))
        assert file_0_data.startswith(bytes(message + '#level0', 'ascii'))


@pytest.mark.skipif(not (sys.version_info.minor >= 13), reason='Python >= 3.13')
def test_reference_tracing_to_specific_log_file_nested():
    """This tests that the nested context managers work properly.
    In particular, when the inner one exists the outer one takes over."""
    SLEEP = 1.0
    message = 'test_reference_tracing_to_specific_log_file_nested():'
    with tempfile.NamedTemporaryFile() as file_0:
        # Create the outer context manager.
        with cPyMemTrace.ReferenceTracing(message=message + '#level0', filepath=file_0.name) as trace_0:
            trace_0.write_message_to_log('# Level 0 __enter__')
            # Exercise the outer context manager *before* the inner context manager.
            assert trace_0.log_file_path() == file_0.name
            for i in range(4):
                populate_list()
            trace_0.write_message_to_log('# Level 0 after populate_list()')

            # # Now the inner.
            # with tempfile.NamedTemporaryFile() as file_1:
            #     trace_0.write_message_to_log('# Level 0 just prior to level 1 __enter__')
            #
            #     # Create the inner context manager.
            #     with cls(message=message + '#level1', filepath=file_1.name) as trace_1:
            #
            #         trace_0.write_message_to_log('# Level 0 events should be suspended')
            #
            #         trace_1.write_message_to_log('# Level 1 __enter__')
            #         # Exercise the inner context manager.
            #         assert trace_1.log_file_path() == file_1.name
            #         for i in range(4):
            #             trace_0.write_message_to_log('# Level 0 events should be suspended')
            #             populate_list()
            #
            #         trace_0.write_message_to_log('# Level 0 events should be suspended')
            #
            #         trace_1.write_message_to_log('# Level 1 after populate_list()')
            #
            #     # Check the inner output
            #     time.sleep(SLEEP)
            #     file_1.flush()
            #     file_1_data = file_1.read()
            #     print()
            #     print(' file_1_data '.center(75, '-'))
            #     for line in file_1_data.split(b'\n'):
            #         print(line.decode('ascii'))
            #     print(' file_1_data DONE '.center(75, '-'))
            #     assert file_1_data.startswith(bytes(message + '#level1', 'ascii'))

            trace_0.write_message_to_log('# Level 0 after level 1 exit')
            # Exercise the outer context manager *before* the inner context manager.
            assert trace_0.log_file_path() == file_0.name
            for i in range(4):
                populate_list()
            trace_0.write_message_to_log('# Level 0 after level 1 exit and populate_list()')

        time.sleep(SLEEP)
        file_0.flush()
        file_0_data = file_0.read()
        print()
        print(' file_0_data '.center(75, '-'))
        for line in file_0_data.split(b'\n'):
            print(line.decode('ascii'))
        print(' file_0_data DONE '.center(75, '-'))
        assert file_0_data.startswith(bytes(message + '#level0', 'ascii'))


def test_profile_depth():
    assert cPyMemTrace.profile_wrapper_depth() == 0
    with cPyMemTrace.Profile(0, message='test_profile_depth()') as profiler_0:
        assert cPyMemTrace.profile_wrapper_depth() == 1
        with cPyMemTrace.Profile(0, message='test_profile_depth()') as profiler_1:
            assert cPyMemTrace.profile_wrapper_depth() == 2
            with cPyMemTrace.Profile(message='test_profile_depth()') as profiler_2:
                assert cPyMemTrace.profile_wrapper_depth() == 3
            assert cPyMemTrace.profile_wrapper_depth() == 2
        assert cPyMemTrace.profile_wrapper_depth() == 1
    assert cPyMemTrace.profile_wrapper_depth() == 0


def test_trace_depth():
    assert cPyMemTrace.trace_wrapper_depth() == 0
    with cPyMemTrace.Trace(0, message='test_trace_depth()') as tracer_0:
        assert cPyMemTrace.trace_wrapper_depth() == 1
        with cPyMemTrace.Trace(0, message='test_trace_depth()') as tracer_1:
            assert cPyMemTrace.trace_wrapper_depth() == 2
            with cPyMemTrace.Trace(0, message='test_trace_depth()') as tracer_2:
                assert cPyMemTrace.trace_wrapper_depth() == 3
            assert cPyMemTrace.trace_wrapper_depth() == 2
        assert cPyMemTrace.trace_wrapper_depth() == 1
    assert cPyMemTrace.trace_wrapper_depth() == 0


def test_mixed_profile_trace_depth():
    assert cPyMemTrace.profile_wrapper_depth() == 0
    assert cPyMemTrace.trace_wrapper_depth() == 0
    with cPyMemTrace.Profile(0, message='test_mixed_profile_trace_depth()') as profiler_0:
        assert cPyMemTrace.profile_wrapper_depth() == 1
        assert cPyMemTrace.trace_wrapper_depth() == 0
        with cPyMemTrace.Trace(0, message='test_mixed_profile_trace_depth()') as tracer_0:
            assert cPyMemTrace.profile_wrapper_depth() == 1
            assert cPyMemTrace.trace_wrapper_depth() == 1
            with cPyMemTrace.Trace(message='test_mixed_profile_trace_depth()') as tracer_1:
                assert cPyMemTrace.profile_wrapper_depth() == 1
                assert cPyMemTrace.trace_wrapper_depth() == 2
            assert cPyMemTrace.profile_wrapper_depth() == 1
            assert cPyMemTrace.trace_wrapper_depth() == 1
        assert cPyMemTrace.profile_wrapper_depth() == 1
        assert cPyMemTrace.trace_wrapper_depth() == 0
    assert cPyMemTrace.profile_wrapper_depth() == 0
    assert cPyMemTrace.trace_wrapper_depth() == 0


@pytest.mark.skipif(not (sys.version_info.minor < 14), reason='Python < 3.14')
def test_context_manager_refcounts_pre_314():
    with open(__file__) as f:
        print(f'Refcount: {sys.getrefcount(f)}')
        assert sys.getrefcount(f) == 3
    print(f'Refcount: {sys.getrefcount(f)}')
    assert sys.getrefcount(f) == 2


@pytest.mark.skipif(not (sys.version_info.minor >= 14), reason='Python >= 3.14')
def test_context_manager_refcounts_post_314():
    with open(__file__) as f:
        print(f'Refcount: {sys.getrefcount(f)}')
        assert sys.getrefcount(f) == 2
    print(f'Refcount: {sys.getrefcount(f)}')
    assert sys.getrefcount(f) == 1


if __name__ == '__main__':
    print('START')
    test_profile_basic_gt_310()
    print('FINISH')
