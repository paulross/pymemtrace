# import sys
import dataclasses
import datetime
import gc
import random
import string
import time

# import psutil

from pymemtrace import cpymemtrace_decs
from pymemtrace import cPyMemTrace


class StringAndTime:
    def __init__(self, size: int):
        self.now = datetime.datetime.now()
        self.str = ''.join(random.choices(string.printable, k=size))


# @dataclasses.dataclass
# class StringAndTime:
#     m_now: datetime.datetime
#     m_str: str


def create_string_and_time_list():
    list_of_str_and_time = []
    for i in range(8):
        str_len = random.randint(1024, 2048)
        v = StringAndTime(datetime.datetime.now(), str_len)
        # print(v)
        list_of_str_and_time.append(v)
        # v = StringAndTime(str_len)
        # del v
    # while len(l):
    #     l.pop()
    # gc.collect(2)
    # del l
    # time.sleep(1.0)


@cpymemtrace_decs.reference_tracing()
def example_reference_tracing():
    print(f'example_reference_tracing()')
    print(f'Logging to {cPyMemTrace.reference_tracing_log_path()}')
    # create_string_and_time_list()
    l = []
    for i in range(4):
        str_len = random.randint(1024, 2048)
        v = StringAndTime(str_len)
        l.append(v)
        # v = StringAndTime(str_len)
        # del v
    # del l
    # while len(l):
    #     l.pop()
    # gc.collect(2)


def main():
    example_reference_tracing()
    return 0


if __name__ == '__main__':
    exit(main())
