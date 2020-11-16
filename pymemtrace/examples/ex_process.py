"""
Example of using process that logs process data to the current log.
"""
import logging
import random
import sys
import time

from pymemtrace import process

logger = logging.getLogger(__file__)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(filename)s#%(lineno)d - %(process)5d - (%(threadName)-10s) - %(levelname)-8s - %(message)s',
    )
    logger.info('Demonstration of logging a process')
    # Log process data to the log file every 0.5 seconds.
    with process.log_process(interval=0.5, log_level=logger.getEffectiveLevel()):
        for i in range(8):
            size = random.randint(128, 128 + 256) * 1024 ** 2
            # Add a message to report in the next process write.
            process.add_message_to_queue(f'String of {size:,d} bytes')
            s = ' ' * size
            time.sleep(0.75 + random.random())
            del s
            time.sleep(0.25 + random.random() / 2)
    return 0


if __name__ == '__main__':
    sys.exit(main())
