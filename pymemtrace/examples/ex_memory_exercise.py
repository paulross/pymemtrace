import argparse
import logging
import os
import sys
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


def create_string(size: int) -> str:
    return ' ' * size


def exercise_memory():
    logger.info('exercise_memory()')
    str_list = []
    for i in range(8):
        str_list.append(create_string(1024**2))
        time.sleep(0.5)
    while len(str_list):
        str_list.pop()
    logger.info('DONE: exercise_memory()')


def main():
    parser = argparse.ArgumentParser(
        description='Excercise Python and C memory',
        # formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # parser.add_argument("-s", "--subdir", type=str, dest="subdir",
    #                     default=SUB_DIR_FOR_COMMON_FILES,
    #                     help="Sub-directory for writing the common files. [default: %(default)s]")
    parser.add_argument("-p", "--pause", action="store_true", dest="pause",
                        default=False,
                        help="Pause before starting. [default: %(default)s]")
    # parser.add_argument("-v", "--verbose", action="store_true", dest="verbose",
    #                     default=False,
    #                     help="Verbose, lists duplicate files and sizes. [default: %(default)s]")
    parser.add_argument(
        "-l", "--log_level",
        type=int,
        dest="log_level",
        default=20,
        help="Log Level (debug=10, info=20, warning=30, error=40, critical=50)"
             " [default: %(default)s]"
    )
    # parser.add_argument(
    #     dest="path",
    #     nargs=1,
    #     help="Path to source directory. WARNING: This will be rewritten in-place."
    # )
    args = parser.parse_args()
    if args.pause:
        input(f'Waiting to continue PID={os.getpid()}, <cr> to continue... ')

    clock_start = time.perf_counter()
    # Initialise logging etc.
    logging.basicConfig(level=args.log_level,
                        format='%(asctime)s - %(filename)-16s - %(lineno)4d - %(process)5d - (%(threadName)-10s) - %(levelname)-8s - %(message)s',
                        # datefmt='%y-%m-%d % %H:%M:%S',
                        stream=sys.stdout)
    try:
        while True:
            # exercise_memory()
            exercise_c_memory()
            # create_c_buffer_and_del(1653)
    except KeyboardInterrupt:
        print('Interrupted!')
    print(f'Runtime: {time.perf_counter() - clock_start:.3f} (s)')
    print('Bye, bye!')
    return 0


if __name__ == '__main__':
    sys.exit(main())