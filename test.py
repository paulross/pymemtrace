import sys

import psutil

import custom
import cPyMemTrace


def create_string(l: int) -> str:
    return ' ' * l


COUNT = 16


def test_under_512():
    print(f'test_under_512 {COUNT}')
    l = []
    for i in range(COUNT):
        l.append(create_string(256))
    while len(l):
        l.pop()


def test_over_512():
    print(f'test_over_512 {COUNT}')
    l = []
    for i in range(COUNT):
        l.append(create_string(1024))
    while len(l):
        l.pop()


def test_well_over_512():
    print(f'test_well_over_512 {COUNT}')
    l = []
    for i in range(COUNT):
        l.append(create_string(1024**2))
    while len(l):
        l.pop()


def f(l):
    print('Hi')
    s = ' ' * l
    print('Bye')


def g():
    print(f'Creating Custom.')
    # pid = psutil.Process()
    # print(f'Creating Custom: {pid.memory_info()}')
    obj = custom.Custom('First', 'Last')
    print(obj.name())
    # print(f'Done: {pid.memory_info()}')
    print(f'Done.')


def main():
    # cPyMemTrace._attach_profile()
    # f(1024**2)
    # # f(1024**2)
    # g()
    # cPyMemTrace._detach_profile()

    with cPyMemTrace.Profile():
        # f(1024**2)
        # f(1024**2)
        # g()
        test_under_512()
        test_over_512()
        test_well_over_512()

    return 0


if __name__ == '__main__':
    sys.exit(main())

