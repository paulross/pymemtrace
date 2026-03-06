"""
This monitors a process **and** all its child processes.
"""
import argparse
import dataclasses
import json
import logging
import os
import sys
import time
import typing

import colorama
import psutil

logger = logging.getLogger(__file__)

colorama.init(autoreset=True)


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

    def name_and_units(self) -> str:
        if self.units:
            return f'{self.name}({self.units})'
        return self.name


@dataclasses.dataclass
class WriteSummaryConfig:
    """What to write out in the summary."""
    columns: typing.List[WriteSummaryColumn]
    json_file_path: str


class ProcessTree:
    """Creates a tree of psutil.Process objects"""
    DEPTH_INDENT_PREFIX = '  '

    def __init__(self, proc: typing.Union[int, psutil.Process]):
        """Takes a PID and creates the tree of all child processes."""
        if isinstance(proc, int):
            self.proc = psutil.Process(proc)
        else:
            self.proc = proc
        self.children: typing.List[ProcessTree] = []
        # So that value differences can be computes between write_summary calls.
        self.previous_values = {}

    def update_children(self) -> None:
        """Update the children process list.
        This preserves existing processes based on their ppid being the same as self.
        It adds new ones and discards old ones."""
        # self.clear_children()
        # Remove orphans.
        children = []
        for c in self.children:
            try:
                if c.proc.ppid() == self.proc.pid:
                    children.append(c)
            except psutil.NoSuchProcess:
                pass
        self.children = children
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

    @staticmethod
    def write_header(
            write_summary_config: WriteSummaryConfig,
            sep: str,
            ostream: typing.TextIO = sys.stdout,
    ) -> None:
        """Write the column header."""
        if sep:
            ostream.write(f'{"Time(s)":s}')
            ostream.write(f'{sep}{"PID":s}')
            ostream.write(f'{sep}{"Name":s}')
        else:
            ostream.write(f'{"Time(s)":8s}')
            ostream.write(f' ')
            ostream.write(f' {"PID":>5s}')
            ostream.write(f' {"Name":24s}')
        for col_spec in write_summary_config.columns:
            if sep:
                if col_spec.units:
                    name_and_units = f'{col_spec.name}({col_spec.units})'.strip()
                else:
                    name_and_units = f'{col_spec.name}'.strip()
            else:
                if col_spec.units:
                    name_and_units = f'{col_spec.name}({col_spec.units})'
                else:
                    name_and_units = f'{col_spec.name}'
            if sep:
                ostream.write(f'{sep}{name_and_units:s}')
            else:
                ostream.write(f' {name_and_units:>{col_spec.width_and_format.width}s}')
            if col_spec.width_and_format_diff is not None:
                if sep:
                    if col_spec.units:
                        name_and_units = f'd{col_spec.name}({col_spec.units})'.strip()
                    else:
                        name_and_units = f'd{col_spec.name}'.strip()
                else:
                    if col_spec.units:
                        name_and_units = f'd{col_spec.name}({col_spec.units})'
                    else:
                        name_and_units = f'd{col_spec.name}'
                if sep:
                    ostream.write(f'{sep}{name_and_units:s}')
                else:
                    ostream.write(f' {name_and_units:>{col_spec.width_and_format_diff.width}s}')
        ostream.write('\n')

    def load_previous(self, write_summary_config: WriteSummaryConfig) -> None:
        """This loads the "previous" cache values with the current values."""
        try:
            with self.proc.oneshot():
                for col_spec in write_summary_config.columns:
                    value = col_spec.getter(self.proc)
                    if col_spec.width_and_format_diff is not None:
                        self.previous_values[col_spec.name] = value
        except psutil.AccessDenied:
            pass
        for child in self.children:
            child.load_previous(write_summary_config)

    def _write_summary_time_pid_name(
            self,
            depth: int,
            sep: str,
            ostream: typing.TextIO = sys.stdout,
    ) -> int:
        """Write the prefix for this moment in time.
        Returns zero on success, non-zero on failure."""
        try:
            # Optional time and mandatory PID and name.
            if depth == 0:
                exec_time = self.get_exec_time(self.proc)
                if sep:
                    ostream.write(f'{exec_time:.1f}')
                else:
                    ostream.write(f'{exec_time:8.1f}')
            else:
                if not sep:
                    ostream.write(f'{"":8s}')
            if sep:
                ostream.write(f'{sep}{self.proc.pid:d}')
            else:
                ostream.write(f' {self.DEPTH_INDENT_PREFIX * depth:s} {self.proc.pid:5d}')
            proc_name = '"' + self.proc.name() + '"'
            if sep:
                ostream.write(f'{sep}{proc_name:s}')
            else:
                ostream.write(f' {proc_name:24}')
        except psutil.NoSuchProcess:
            return 1
        return 0

    def _write_diff(
            self,
            value: typing.Any,
            col_spec: WriteSummaryColumn,
            sep: str,
            ostream: typing.TextIO = sys.stdout,
    ) -> None:
        """Writes the difference between two values colourising it as appropriate."""
        assert col_spec.width_and_format_diff is not None
        if type(value) == str:
            if value != self.previous_values.get(col_spec.name, ''):
                delta = value
            else:
                delta = ''
        else:
            delta = value - self.previous_values.get(col_spec.name, 0)
        if sep:
            ostream.write(sep)
            delta_str = format(
                delta * col_spec.mult_factor,
                col_spec.width_and_format_diff.format
            ).strip()
        else:
            ostream.write(' ')
            delta_str = format(
                delta * col_spec.mult_factor,
                col_spec.width_and_format_diff.format
            )
        if type(value) == str:
            if delta:
                ostream.write(colorama.Fore.RED + delta_str)
            else:
                ostream.write(colorama.Fore.GREEN + delta_str)
        else:
            if delta > 0:
                ostream.write(colorama.Fore.RED + delta_str)
            elif delta < 0:
                ostream.write(colorama.Fore.GREEN + delta_str)
            else:
                ostream.write(delta_str)
        # ostream.write(f' ({col_spec.units})')
        self.previous_values[col_spec.name] = value

    def write_summary(
            self,
            depth: int,
            record_number: int,
            write_summary_config: WriteSummaryConfig,
            sep: str,
            ostream: typing.TextIO = sys.stdout,
    ) -> None:
        """Write the summary lines for this moment in time."""
        if self._write_summary_time_pid_name(depth, sep, ostream):
            return
        # Iterate through the required columns.
        try:
            with self.proc.oneshot():
                for col_spec in write_summary_config.columns:
                    value = col_spec.getter(self.proc)
                    if sep:
                        ostream.write(sep)
                        ostream.write(
                            format(value * col_spec.mult_factor, col_spec.width_and_format.format).strip(),
                        )
                    else:
                        ostream.write(' ')
                        ostream.write(
                            format(value * col_spec.mult_factor, col_spec.width_and_format.format),
                        )
                    if col_spec.width_and_format_diff is not None:
                        self._write_diff(value, col_spec, sep, ostream)
        except psutil.AccessDenied:
            ostream.write(colorama.Back.YELLOW + colorama.Fore.BLACK + 'ACCESS DENIED')
        except psutil.NoSuchProcess:
            return
        # Done with self.
        ostream.write('\n')
        if write_summary_config.json_file_path and depth == 0:
            self._write_summary_json(record_number, write_summary_config)
        # Recurse through the children.
        for child in self.children:
            child.write_summary(depth + 1, record_number, write_summary_config, sep, ostream)

    def _write_summary_json(self, record_number: int, write_summary_config: WriteSummaryConfig):
        """Writes the summary as a JSON file controlled by write_summary_config."""
        assert write_summary_config.json_file_path
        json_output = self._get_data_as_dict_for_json(write_summary_config)
        with open(write_summary_config.json_file_path, 'a') as file:
            # JSON does not like trailing commas so we write the comma lazily.
            if record_number:
                file.write(',\n')
            file.write(json.dumps(json_output, indent=2))
            # file.write(',\n')

    def _get_data_as_dict_for_json(self, write_summary_config: WriteSummaryConfig) -> typing.Dict[str, typing.Any]:
        """Recursive call to get all the tree as a dict suitable for writing to JSON."""
        json_output = {
            'process_time': self.get_exec_time(self.proc),
            'pid': self.proc.pid,
            'name': self.proc.name(),
        }
        for col_spec in write_summary_config.columns:
            value = col_spec.getter(self.proc)
            # json_output[col_spec.name_and_units()] = value
            json_output[col_spec.name] = value
        child_json = []
        for child in self.children:
            try:
                child_json.append(child._get_data_as_dict_for_json(write_summary_config))
            except psutil.AccessDenied:
                pass
            except psutil.NoSuchProcess:
                pass
        json_output['children'] = child_json
        return json_output

    # Static functions that return data from a process.
    # See: https://psutil.readthedocs.io/en/latest/#processes for the available data
    @staticmethod
    def get_exec_time(proc: psutil.Process) -> float:
        """Return the process time since start of process."""
        exec_time = time.time() - proc.create_time()
        return exec_time

    @staticmethod
    def get_cpu_percent(proc: psutil.Process) -> float:
        """Returns the reported CPU percent usage for this process only."""
        return proc.cpu_percent()

    @staticmethod
    def get_cpu_time_user(proc: psutil.Process) -> float:
        """Returns the reported CPU user time for this process only."""
        return proc.cpu_times().user

    @staticmethod
    def get_cpu_time_system(proc: psutil.Process) -> float:
        """Returns the reported CPU system time for this process only."""
        return proc.cpu_times().system

    @staticmethod
    def get_memory_rss(proc: psutil.Process) -> int:
        """Returns the reported Resident Set Size (RSS) for this process only."""
        return proc.memory_info().rss

    @staticmethod
    def get_memory_uss(proc: psutil.Process) -> int:
        """Returns the reported USS for this process only."""
        try:
            mem_info = proc.memory_full_info()
            return mem_info.uss
        except psutil.AccessDenied:
            # TODO: Why does this happen? Even with sudo.
            return -1  # * 1024**2

    @staticmethod
    def get_memory_page_faults(proc: psutil.Process) -> int:
        """Returns the reported number of page faults for this process only."""
        mem_info = proc.memory_info()
        if hasattr(mem_info, 'pfaults'):
            return mem_info.pfaults
        return 0

    @staticmethod
    def get_num_context_switches(proc: psutil.Process) -> int:
        """Returns the reported number of context switches for this process only."""
        # NOTE: This seems to be the total number of all processes???
        # Also the numbers look very dodgy.
        ctx = proc.num_ctx_switches()
        return ctx.involuntary + ctx.voluntary

    @staticmethod
    def get_num_threads(proc: psutil.Process) -> int:
        """Returns the reported number of threads for this process only."""
        return proc.num_threads()

    @staticmethod
    def get_status(proc: psutil.Process) -> str:
        """Returns the reported process status as a string. For example 'running'."""
        return proc.status()

    @staticmethod
    def get_num_open_files(proc: psutil.Process) -> int:
        """Returns the reported number of open files for this process only."""
        return len(proc.open_files())

    @staticmethod
    def get_num_net_connections(proc: psutil.Process) -> int:
        """Returns the reported number of network connections for this process only."""
        return len(proc.net_connections())

    @staticmethod
    def get_cmdline(proc: psutil.Process) -> str:
        """Returns the command line for this process."""
        return ' '.join(proc.cmdline())


def log_process(
        pid: int,
        interval: float,
        omit_first: bool,
        write_summary_config: WriteSummaryConfig,
        sep: str,
        ostream: typing.TextIO = sys.stdout,
) -> int:
    """Log the process and all its child processes to the output stream."""
    try:
        proc_tree = ProcessTree(pid)
    except psutil.NoSuchProcess as err:
        logger.error(err)
        return -1
    cmd_args = []
    for cmd_arg in proc_tree.proc.cmdline():
        if ' ' in cmd_arg:
            cmd_args.append(f'"{cmd_arg}"')
        else:
            cmd_args.append(cmd_arg)
    print(f'CMD: {" ".join(cmd_args)}')
    proc_tree.write_header(write_summary_config, sep, ostream)
    record_number = 0
    if write_summary_config.json_file_path:
        with open(write_summary_config.json_file_path, 'w') as json_file:
            json_file.write('[\n')
    try:
        while True:
            if not proc_tree.proc.is_running():
                print(f'Parent process {proc_tree.proc.pid} is not running.')
                break
            t_start = time.time()
            proc_tree.update_children()
            if omit_first and record_number == 0:
                proc_tree.load_previous(write_summary_config)
            else:
                proc_tree.write_summary(0, record_number, write_summary_config, sep, ostream)
            record_number += 1
            t_exec = time.time() - t_start
            if interval > t_exec:
                time.sleep(interval - t_exec)
        # if write_summary_config.json_file_path:
        #     with open(write_summary_config.json_file_path, 'a') as json_file:
        #         json_file.write('\n]\n')
    except KeyboardInterrupt:
        print('KeyboardInterrupt!')
    if write_summary_config.json_file_path and record_number > 0:
        with open(write_summary_config.json_file_path, 'a') as json_file:
            json_file.write('\n]\n')
    return 0


def main() -> int:
    """Main CLI entry point.

    .. code-block:: text

        usage: process_tree.py [-h] [-i INTERVAL] [-p PID] [-l LOG_LEVEL] [--sep SEP] [-1] [-u] [-g] [-c] [-x] [-t] [-s] [-f] [-n] [--cmdline] [-a] [--json JSON]

        Tracks the resource usage of a process and all of it's child processes.

        options:
          -h, --help            show this help message and exit
          -i INTERVAL, --interval INTERVAL
                                Logging interval in seconds [default: 1.0]
          -p PID, --pid PID     PID to monitor, -1 it is this process [default: -1]
          -l LOG_LEVEL, --log_level LOG_LEVEL
                                Log Level (debug=10, info=20, warning=30, error=40, critical=50) [default: 20]
          --sep SEP             String to use as seperator such as "|". Default is to format as a table [default: ""]
          -1, --omit-first      Omit the first sample. This makes the diffs a bit cleaner. [default: False]
          -u, --uss             The USS, this is the amount of memory that would be freed if the process was terminated right now. [default: False]
          -g, --page-faults     Number of page faults. [default: False]
          -c, --cpu-times       user and system time. [default: False]
          -x, --context-switches
                                Show number of contest switches. [default: False]
          -t, --threads         Show number of threads. [default: False]
          -s, --status          Show the status. [default: False]
          -f, --open-files      Show the number of open files. [default: False]
          -n, --net-connections
                                Show the number of network connections. [default: False]
          --cmdline             Show the command line for each process (verbose). [default: False]
          -a, --all             Show typical data, equivalent to -cfgstn. [default: False]
          --json JSON           Path to a JSON file to also write the data to. [default: "]"]
    """
    parser = argparse.ArgumentParser(
        prog='process_tree.py',
        description="""Tracks the resource usage of a process and all of it's child processes.""",
    )
    parser.add_argument('-i', '--interval', type=float, help='Logging interval in seconds [default: %(default)s]',
                        default=1.0)
    parser.add_argument('-p', '--pid', type=int, help='PID to monitor, -1 it is this process [default: %(default)s]',
                        default=-1)
    parser.add_argument("-l", "--log_level", type=int, dest="log_level", default=20,
                        help="Log Level (debug=10, info=20, warning=30, error=40, critical=50)"
                             " [default: %(default)s]"
                        )

    parser.add_argument('--sep', type=str,
                        help=(
                            'String to use as seperator such as "|".'
                            ' Default is to format as a table [default: "%(default)s"]'
                        ),
                        default='')
    parser.add_argument("-1", "--omit-first", action="store_true",
                        help="Omit the first sample. This makes the diffs a bit cleaner. [default: %(default)s]")

    parser.add_argument("-u", "--uss", action="store_true",
                        help=(
                            "The USS, this is the amount of memory that would be"
                            " freed if the process was terminated right now."
                            " [default: %(default)s]"
                        )
                        )
    parser.add_argument("-g", "--page-faults", action="store_true",
                        help="Number of page faults. [default: %(default)s]")
    parser.add_argument("-c", "--cpu-times", action="store_true",
                        help="user and system time. [default: %(default)s]")
    parser.add_argument("-x", "--context-switches", action="store_true",
                        help="Show number of contest switches. [default: %(default)s]")
    parser.add_argument("-t", "--threads", action="store_true",
                        help="Show number of threads. [default: %(default)s]")
    parser.add_argument("-s", "--status", action="store_true",
                        help="Show the status. [default: %(default)s]")
    parser.add_argument("-f", "--open-files", action="store_true",
                        help="Show the number of open files. [default: %(default)s]")
    parser.add_argument("-n", "--net-connections", action="store_true",
                        help="Show the number of network connections. [default: %(default)s]")
    parser.add_argument("--cmdline", action="store_true",
                        help="Show the command line for each process (verbose). [default: %(default)s]")

    parser.add_argument("-a", "--all", action="store_true",
                        help="Show typical data, equivalent to -cfgstn. [default: %(default)s]")

    parser.add_argument('--json', type=str,
                        help=(
                            'Path to a JSON file to also write the data to.'
                            ' [default: "%(default)s]"]'
                        ),
                        default='')

    # parser.add_argument('path_in', type=str, help='Input path.', nargs='?')
    # parser.add_argument('path_out', type=str, help='Output path.', nargs='?')
    args = parser.parse_args()
    # print(args)
    # return 0
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
        [
            WriteSummaryColumn(
                'RSS', ProcessTree.get_memory_rss, 1 / 1024 ** 2, 'MB',
                ColumnWidthFormat(8, '8,.1f'), ColumnWidthFormat(8, '+8,.1f'),
            ),
        ],
        args.json,
    )
    if args.uss:  # or args.all:
        write_summary_config.columns.append(
            WriteSummaryColumn(
                'USS', ProcessTree.get_memory_uss, 1 / 1024 ** 2, 'MB',
                ColumnWidthFormat(8, '8,.1f'), ColumnWidthFormat(8, '+8,.1f'),
            ),
        )
    if args.page_faults or args.all:
        write_summary_config.columns.append(
            WriteSummaryColumn(
                'PFaults', ProcessTree.get_memory_page_faults, 1, '',
                ColumnWidthFormat(12, '12,d'), ColumnWidthFormat(12, '+12,d'),
            ),
        )
    write_summary_config.columns.append(
        WriteSummaryColumn(
            'CPU', ProcessTree.get_cpu_percent, 1, '%',
            ColumnWidthFormat(8, '8.1f'), ColumnWidthFormat(8, '+8.1f'),
        ),
    )
    if args.cpu_times or args.all:
        write_summary_config.columns.append(
            WriteSummaryColumn(
                'User', ProcessTree.get_cpu_time_user, 1, 's',
                ColumnWidthFormat(8, '8,.3f'), None,  # ColumnWidthFormat(8, '+8,.1f'),
            )
        )
        write_summary_config.columns.append(
            WriteSummaryColumn(
                'Sys', ProcessTree.get_cpu_time_system, 1, 's',
                ColumnWidthFormat(8, '8,.3f'), None,  # ColumnWidthFormat(8, '+8,.1f'),
            ),
        )
    if args.context_switches:
        write_summary_config.columns.append(
            WriteSummaryColumn(
                'Ctx', ProcessTree.get_num_context_switches, 1e-6, 'm',
                ColumnWidthFormat(8, '8,.1f'), ColumnWidthFormat(8, '8,.1f'),
            ),
        )
    if args.threads or args.all:
        write_summary_config.columns.append(
            WriteSummaryColumn(
                'Thrds', ProcessTree.get_num_threads, 1, '',
                ColumnWidthFormat(6, '6,d'), ColumnWidthFormat(6, '+6,d'),
            ),
        )
    if args.status or args.all:
        write_summary_config.columns.append(
            WriteSummaryColumn(
                'Status', ProcessTree.get_status, 1, '',
                ColumnWidthFormat(10, '>10s'), ColumnWidthFormat(10, '>10s'),
            ),
        )
    if args.open_files or args.all:
        write_summary_config.columns.append(
            WriteSummaryColumn(
                'Files', ProcessTree.get_num_open_files, 1, '',
                ColumnWidthFormat(6, '>6d'), ColumnWidthFormat(6, '>6d'),
            ),
        )
    if args.net_connections or args.all:
        write_summary_config.columns.append(
            WriteSummaryColumn(
                'Net', ProcessTree.get_num_net_connections, 1, '',
                ColumnWidthFormat(6, '>6d'), ColumnWidthFormat(6, '>6d'),
            ),
        )
    # Not or args.all
    if args.cmdline:
        write_summary_config.columns.append(
            WriteSummaryColumn(
                'CmdLine', ProcessTree.get_cmdline, 1, '',
                ColumnWidthFormat(0, 's'), None,
            ),
        )
    result_code = log_process(pid, args.interval, args.omit_first, write_summary_config, args.sep)
    if result_code:
        print(f'Logging failed with results code {result_code}')
    print('Bye, bye!')
    return 0


if __name__ == '__main__':
    exit(main())
