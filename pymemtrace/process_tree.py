"""
This monitors a process **and** all its child processes.
"""
import argparse
import dataclasses
import logging
import os
import sys
import time
import typing

import psutil

logger = logging.getLogger(__file__)


@dataclasses.dataclass
class WriteSummaryConfig:
    """What to write out in the summary.
    TODO: """
    pass


class ProcessTree:
    """Creates a tree of psutil.Process objects"""

    def __init__(self, proc: typing.Union[int, psutil.Process]):
        """Takes a PID and creates the tree of all child processes."""
        if isinstance(proc, int):
            self.proc = psutil.Process(proc)
        else:
            self.proc = proc
        self.children: typing.List[ProcessTree] = []

    def clear_children(self) -> None:
        for child in self.children:
            child.clear_children()
        self.children = []

    def update_children(self) -> None:
        self.clear_children()
        for child_process in self.proc.children(recursive=False):
            # child_process is a psutil.Process
            self.children.append(ProcessTree(child_process))

    def write_summary(self, depth: int, write_summary_config: WriteSummaryConfig, ostream=sys.stdout) -> None:
        if depth == 0:
            exec_time = time.time() - self.proc.create_time()
            ostream.write(f'{exec_time:6.1f} ')
        else:
            ostream.write(f'{"":6s} ')
        ostream.write(f'{" " * depth:s} {self.proc.pid:5d} ')
        # See: https://psutil.readthedocs.io/en/latest/#processes for the available data
        ostream.write('\n')
        for child in self.children:
            child.write_summary(depth + 1, write_summary_config, ostream)


def log_process(pid: int, interval: float, write_summary_config: WriteSummaryConfig):
    proc_tree = ProcessTree(pid)
    try:
        while True:
            proc_tree.update_children()
            proc_tree.write_summary(0, write_summary_config, sys.stdout)
            time.sleep(interval)
    except KeyboardInterrupt:
        print('KeyboardInterrupt!')


def main() -> int:
    """Main CLI entry point. For testing."""
    parser = argparse.ArgumentParser(
        prog='process.py',
        description="""Reads an annotated log of a process and writes a Gnuplot graph.""",
    )
    parser.add_argument('-i', '--interval', type=float, help='Logging interval in seconds [default: %(default)s]',
                        default=1.0)
    parser.add_argument('-p', '--pid', type=int, help='PID to monitor, -1 it this [default: %(default)s]',
                        default=-1)
    parser.add_argument("-l", "--log_level", type=int, dest="log_level", default=20,
                        help="Log Level (debug=10, info=20, warning=30, error=40, critical=50)"
                             " [default: %(default)s]"
                        )
    # parser.add_argument('path_in', type=str, help='Input path.', nargs='?')
    # parser.add_argument('path_out', type=str, help='Output path.', nargs='?')
    args = parser.parse_args()
    logging.basicConfig(
        level=args.log_level,
        format='%(asctime)s - %(filename)s#%(lineno)d - %(process)5d - (%(threadName)-10s) - %(levelname)-8s - %(message)s',
    )
    if args.pid < 1:
        pid = os.getpid()
    else:
        pid = args.pid
    logger.info(f'Processing PID {pid}')
    write_summary_config = WriteSummaryConfig()
    log_process(pid, args.interval, write_summary_config)
    print('Bye, bye!')
    return 0


if __name__ == '__main__':
    exit(main())
