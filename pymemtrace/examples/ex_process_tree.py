"""
Example of using multiprocessing to claim and reclaim memory that can be monitored by process_tree.py.
"""
import logging
import multiprocessing
import os
import random
import sys
import time

logger = logging.getLogger(__file__)

ROUNDS_LOWER_BOUND = 4
ROUNDS_UPPER_BOUND = 5
ALLOC_REPEAT = 1
ALLOC_LOWER_BOUND = 128 * 1024 ** 2
ALLOC_UPPER_BOUND = 1024 ** 3
# Note: random.random() is added to these sleeps.
SLEEP_HOLD = 0.75
SLEEP_PAUSE = 0.25
NUM_TASKS = 8
NUM_PROCESSES = 8

LOG_FORMAT_WITH_THREADS = (
    '%(asctime)s - %(filename)s#%(lineno)d - %(process)5d - (%(threadName)-10s) - %(levelname)-8s - %(message)s'
)
LOG_FORMAT_NO_THREADS = (
    '%(asctime)s - %(filename)s#%(lineno)d - %(process)5d - %(levelname)-8s - %(message)s'
)


def sub_process(task_id: int) -> int:
    """Randomly allocates memory for a random number of rounds."""
    ret = 0
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT_NO_THREADS,
        stream=sys.stdout,
    )
    # logger.fatal('oops')
    logger.info(f'Task {task_id} START')
    for round_index in range(random.randint(ROUNDS_LOWER_BOUND, ROUNDS_UPPER_BOUND)):
        logger.info(f'Task {task_id} round {round_index}')
        for alloc in range(ALLOC_REPEAT):
            str_len = random.randint(ALLOC_LOWER_BOUND, ALLOC_UPPER_BOUND, )
            logger.info(f'Task {task_id} round {round_index} allocating {str_len:,d}')
            string = ' ' * str_len
            ret += len(string)
            time.sleep(SLEEP_HOLD + random.random())
            del string
            time.sleep(SLEEP_PAUSE + random.random())
    logger.info(f'Task {task_id} DONE returning {ret:,d}')
    return ret


def run_processes():
    tasks = range(NUM_TASKS)
    with multiprocessing.Pool(processes=NUM_PROCESSES) as pool:
        result = [
            r.get()[0] for r in [
                pool.map_async(sub_process, [t, ]) for t in tasks
            ]
        ]
        logger.info(f'Result: {result}')


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT_NO_THREADS,
        stream=sys.stdout,
    )
    logger.info('Demonstration of multiprocessing')
    input(f'PID is {os.getpid()} ready? ')
    logger.info('Starting...')
    run_processes()
    logger.info('Bye, bye!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
