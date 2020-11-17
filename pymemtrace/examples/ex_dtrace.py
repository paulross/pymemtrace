"""
Example code to exercise DTrace.
"""
import logging
import os
import pprint
import sys
import sysconfig
import time

from pymemtrace import cMemLeak

logger = logging.getLogger(__file__)


def create_c_buffer_and_del(size: int):
    input(f'Waiting to create buffer PID={os.getpid()}, size={size} <cr> to continue... ')
    b = cMemLeak.CMalloc(size)
    input(f'Waiting to del buffer PID={os.getpid()}, size={size} <cr> to continue... ')
    del b
    input(f'DONE del buffer PID={os.getpid()}, size={size} <cr> to continue... ')


def create_c_buffer(size: int):
    b = cMemLeak.CMalloc(size)
    # logger.info(f'create_c_buffer() {b.size} at 0x{b.buffer:x}')
    print(f'create_c_buffer() {b.size} at 0x{b.buffer:x}')
    return b


def exercise_c_memory():
    logger.info('exercise_c_memory()')
    str_list = []
    for i in range(8):
        str_list.append(create_c_buffer(1652))
        # time.sleep(0.5)
        input(f'Waiting to pop PID={os.getpid()}, <cr> to continue... ')
        str_list.pop()
        input(f'Pop\'d PID={os.getpid()}, <cr> to continue... ')
    while len(str_list):
        str_list.pop()
    logger.info('DONE: exercise_c_ memory()')


def create_cmalloc_list():
    l = []
    for i in range(4):
        block = cMemLeak.CMalloc(1477)
        print(f'Created CMalloc size={block.size:d} buffer=0x{block.buffer:x}')
        l.append(block)
    while len(l):
        # Remove in reverse order
        block = l.pop(0)
        print(f'Pop\'d CMalloc size={block.size:d} buffer=0x{block.buffer:x}')
    l.clear()


def create_pyrawmalloc_list():
    l = []
    for i in range(4):
        block = cMemLeak.PyRawMalloc(128)
        print(f'Created PyRawMalloc size={block.size:d} buffer=0x{block.buffer:x}')
        l.append(block)
    while len(l):
        # Remove in reverse order
        block = l.pop(0)
        print(f'Pop\'d PyRawMalloc size={block.size:d} buffer=0x{block.buffer:x}')
    l.clear()


def create_pymalloc_list():
    print(f'Python at {sys.executable} is configured with CONFIG_ARGS: {sysconfig.get_config_var("CONFIG_ARGS")}')
    l = []
    for i in range(4):
        block = cMemLeak.PyMalloc(371)
        print(f'Created PyMalloc size={block.size:d} buffer=0x{block.buffer:x}')
        l.append(block)
    while len(l):
        # Remove in reverse order
        block = l.pop(0)
        print(f'Pop\'d PyMalloc size={block.size:d} buffer=0x{block.buffer:x}')
    l.clear()


def create_py_array_list(size: int):
    l = []
    for i in range(4):
        block = b' ' * size
        print(f'Created {type(block)} size={len(block):d} buffer=0x{id(block):x}')
        l.append(block)
    while len(l):
        # Remove in reverse order
        block = l.pop(0)
        print(f'Pop\'d {type(block)} size={len(block):d} buffer=0x{id(block):x}')
    l.clear()


def main():
    with_dtrace = sysconfig.get_config_var('WITH_DTRACE')
    if with_dtrace is None or with_dtrace != 1:
        raise RuntimeError(f'Python at {sys.executable} must be build with DTrace support.')
    logging.basicConfig(
        level=20,
        format='%(asctime)s - %(filename)-16s - %(lineno)4d - %(process)5d - (%(threadName)-10s) - %(levelname)-8s - %(message)s',
        stream=sys.stdout,
    )
    logger.info('Python at %s is configured with CONFIG_ARGS: %s', sys.executable, sysconfig.get_config_var('CONFIG_ARGS'))
    # Wait after logging initialised
    input(f'Waiting to start tracing PID: {os.getpid()} (<cr> to continue):')
    # exercise_c_memory()

    # create_cmalloc_list()
    # create_pyrawmalloc_list()
    # create_pymalloc_list()
    create_py_array_list(27)
    return 0


if __name__ == '__main__':
    sys.exit(main())


