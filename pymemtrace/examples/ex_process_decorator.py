"""
Example of using process as a decorator that logs process data to the current log.
"""
import logging
import random
import sys
import time

from pymemtrace import process

logger = logging.getLogger(__file__)


# Log process data to the log file every 0.5 seconds.
@process.log_process_dec(interval=0.5, log_level=logger.getEffectiveLevel())
def example_process_decorator_basic():
    # create_list_of_strings...
    l = []
    for i in range(4):
        l.append(' ' * random.randint(20 * 1024 ** 2, 50 * 1024 ** 2))
        time.sleep(0.5)
    while len(l):
        l.pop()
        time.sleep(0.5)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(filename)s#%(lineno)d - %(process)5d - (%(threadName)-10s) - %(levelname)-8s - %(message)s',
        stream=sys.stdout,
    )
    logger.info('Demonstration of logging a process')
    example_process_decorator_basic()
    return 0


if __name__ == '__main__':
    sys.exit(main())
