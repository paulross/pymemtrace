import datetime
import random
import string

from pymemtrace import cpymemtrace_decs
from pymemtrace import cPyMemTrace


class StringAndTime:
    def __init__(self, size: int):
        self.now = datetime.datetime.now()
        self.str = ''.join(random.choices(string.printable, k=size))


@cpymemtrace_decs.reference_tracing(
    message='With include_builtins=True',
    include_builtins=True,
)
def example_reference_tracing():
    print(f'example_reference_tracing()')
    print(f'Logging to {cPyMemTrace.reference_tracing_log_path()}')
    list_of_str_and_time = []
    for i in range(4):
        str_len = random.randint(1024, 2048)
        v = StringAndTime(str_len)
        list_of_str_and_time.append(v)


def main():
    example_reference_tracing()
    return 0


if __name__ == '__main__':
    exit(main())
