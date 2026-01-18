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
class ColumnWidthFormat:
    """Specifies the column width and format string when writing out the summary."""
    # Find a way of combining this with the format?
    width: int
    format: str


@dataclasses.dataclass
class WriteSummaryColumn:
    """Specifies the column to write out in the summary."""
    name: str
    # A function that takes a psutil.Process and returns a value
    getter: typing.Callable
    mult_factor: float
    units: str
    width_and_format: ColumnWidthFormat
    width_and_format_diff: typing.Optional[ColumnWidthFormat]


@dataclasses.dataclass
class WriteSummaryConfig:
    """What to write out in the summary."""
    columns: typing.Tuple[WriteSummaryColumn, ...]


class ProcessTree:
    """Creates a tree of psutil.Process objects"""

    def __init__(self, proc: typing.Union[int, psutil.Process]):
        """Takes a PID and creates the tree of all child processes."""
        if isinstance(proc, int):
            self.proc = psutil.Process(proc)
        else:
            self.proc = proc
        self.children: typing.List[ProcessTree] = []
        # So that value differences can be computes between write_summary calls.
        # TODO: There is a flaw here as update_children deletes all the previous child data.
        self.previous_values = {}

    def clear_children(self) -> None:
        for child in self.children:
            child.clear_children()
        self.children = []

    def update_children(self) -> None:
        """Update the children process list.
        This preserves existing processes based on their ppid being the same as self.
        It adds new ones and discards old ones."""
        # self.clear_children()
        # Remove orphans. TODO: Does this actually do anything?
        self.children = [c for c in self.children if c.proc.ppid() == self.proc.pid]
        child_pids = set([c.proc.pid for c in self.children])
        # print(f'TRACE: {child_pids}')
        # Add any new processes.
        for child_process in self.proc.children(recursive=False):
            # child_process is a psutil.Process
            if child_process.pid not in child_pids:
                self.children.append(ProcessTree(child_process))
        # Sort the children by PID.
        self.children.sort(key=lambda process_tree: process_tree.proc.pid)
        for child in self.children:
            child.update_children()

    def write_summary(self, depth: int, write_summary_config: WriteSummaryConfig, ostream=sys.stdout) -> None:
        if depth == 0:
            exec_time = time.time() - self.proc.create_time()
            ostream.write(f'{exec_time:8.1f}')
        else:
            ostream.write(f'{"":8s}')
        ostream.write(f' {" " * depth:s} {self.proc.pid:5d}')
        # See: https://psutil.readthedocs.io/en/latest/#processes for the available data
        ostream.write(f' {self.proc.name():24}')

        try:
            for col_spec in write_summary_config.columns:
                value = col_spec.getter(self.proc)
                ostream.write(' ')
                ostream.write(format(value * col_spec.mult_factor, col_spec.width_and_format.format))
                ostream.write(f' ({col_spec.units})')
                if col_spec.width_and_format_diff is not None:
                    delta = value - self.previous_values.get(col_spec.name, 0)
                    ostream.write(' ')
                    ostream.write(format(delta * col_spec.mult_factor, col_spec.width_and_format_diff.format))
                    ostream.write(f' ({col_spec.units})')
                    self.previous_values[col_spec.name] = value
        except psutil.AccessDenied:
            pass
        # ostream.write(' '.join(self.proc.cmdline()))
        ostream.write('\n')
        # print(f'TRACE: {self.children}')
        for child in self.children:
            child.write_summary(depth + 1, write_summary_config, ostream)

    @staticmethod
    def get_memory_rss(proc: psutil.Process) -> int:
        return proc.memory_info().rss


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
    write_summary_config = WriteSummaryConfig(
        (
            WriteSummaryColumn(
                'RSS', ProcessTree.get_memory_rss, 1 / 1024**2, 'MB',
                ColumnWidthFormat(8, '8.1f'), ColumnWidthFormat(4, '+8.1f'),
            ),
        )
    )
    log_process(pid, args.interval, write_summary_config)
    print('Bye, bye!')
    return 0


if __name__ == '__main__':
    exit(main())
