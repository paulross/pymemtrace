# import sys
import datetime
import random
import string

# import psutil

from pymemtrace import cpymemtrace_decs
from pymemtrace import cPyMemTrace

class StringAndTime:
    def __init__(self, size: int):
        now = datetime.datetime.now()
        str = ''.join(random.choices(string.printable, k=size))


@cpymemtrace_decs.reference_tracing()
def example_reference_tracing():
    print(f'example_reference_tracing()')
    # print(f'Logging to {cPyMemTrace.get_log_file_path_reference_tracing()}')
    l = []
    for i in range(8):
        str_len = random.randint(1024, 2048)
        l.append(StringAndTime(str_len))
    while len(l):
        l.pop()


def main():
    example_reference_tracing()
    return 0


if __name__ == '__main__':
    exit(main())
