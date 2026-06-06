"""
Analyses log files produced by cPyMemTrace.ReferenceTrace()

For example, given a log file such as:

.. code-block:: text

    SOF
    HDR:        Clock          Address LiveCnt Type                             File                                            Line Function                                              RSS             dRSS
    DEL:     0.816121   0x60000670f980      0 builtin_function_or_method       pymemtrace/tests/test_cpymemtrace.py             292 make_bytes_wrappers                              38207488         38207488
    NEW:     0.816183   0x6000025fde70      1 list                             pymemtrace/tests/test_cpymemtrace.py             293 make_bytes_wrappers                              38207488                0
    NEW:     0.816203   0x6000025ec6a0      1 range                            pymemtrace/tests/test_cpymemtrace.py             294 make_bytes_wrappers                              38207488                0
    NEW:     0.816218   0x60000169c210      1 range_iterator                   pymemtrace/tests/test_cpymemtrace.py             294 make_bytes_wrappers                              38207488                0
    DEL:     0.816229   0x6000025ec6a0      0 range                            pymemtrace/tests/test_cpymemtrace.py             294 make_bytes_wrappers                              38207488                0
    8<---- Snip ---->8
    NEW:     0.816531   0x7fa81fbf2a00      1 BytesWrapper                     pymemtrace/tests/test_cpymemtrace.py             296 make_bytes_wrappers                              38207488                0
    NEW:     0.816590   0x7fa823903010      1 bytes                            pymemtrace/tests/test_cpymemtrace.py             288 __init__                                         38207488                0
    DEL:     0.816634   0x60000385cf90      0 frame                            pymemtrace/tests/test_cpymemtrace.py             296 make_bytes_wrappers                              38207488                0
    DEL:     0.816645   0x6000025e34a0      0 tuple                            pymemtrace/tests/test_cpymemtrace.py             296 make_bytes_wrappers                              38207488                0
    8<---- Snip ---->8
    NEW:     0.817109   0x7fa81e7aa280      1 BytesWrapper                     pymemtrace/tests/test_cpymemtrace.py             296 make_bytes_wrappers                              38207488                0
    NEW:     0.817162   0x7fa823600010      1 bytes                            pymemtrace/tests/test_cpymemtrace.py             288 __init__                                         38207488                0
    DEL:     0.817203   0x6000038593a0      0 frame                            pymemtrace/tests/test_cpymemtrace.py             296 make_bytes_wrappers                              38207488                0
    NEW:     0.817250   0x60000169c110      1 int                              Python-3.13.2/Lib/random.py                      340 randint                                          38207488                0
    8<---- Snip ---->8
    DEL:     0.817495   0x60000168b350      0 int                              pymemtrace/tests/test_cpymemtrace.py             295 make_bytes_wrappers                              38207488                0
    NEW:     0.817513   0x7fa82347c940      1 BytesWrapper                     pymemtrace/tests/test_cpymemtrace.py             296 make_bytes_wrappers                              38207488                0
    NEW:     0.817602   0x7fa823701010      1 bytes                            pymemtrace/tests/test_cpymemtrace.py             288 __init__                                         38207488                0
    DEL:     0.817675   0x600003849540      0 frame                            pymemtrace/tests/test_cpymemtrace.py             296 make_bytes_wrappers                              38207488                0
    NEW:     0.817762   0x600001694d90      1 int                              Python-3.13.2/Lib/random.py                      340 randint                                          38207488                0
    NEW:     0.817885   0x600001694c90      1 int                              Python-3.13.2/Lib/random.py                      317 randrange                                        38207488                0
    8<---- Snip ---->8
    DEL:     0.818299   0x60000169c510      0 int                              pymemtrace/tests/test_cpymemtrace.py             295 make_bytes_wrappers                              38207488                0
    NEW:     0.818333   0x7fa81fafbe60      1 BytesWrapper                     pymemtrace/tests/test_cpymemtrace.py             296 make_bytes_wrappers                              38207488                0
    NEW:     0.818525   0x7fa823802010      1 bytes                            pymemtrace/tests/test_cpymemtrace.py             288 __init__                                         38207488                0
    DEL:     0.818701   0x6000038409e0      0 frame                            pymemtrace/tests/test_cpymemtrace.py             296 make_bytes_wrappers                              38207488                0
    DEL:     0.818776   0x60000169c210      0 range_iterator                   pymemtrace/tests/test_cpymemtrace.py             294 make_bytes_wrappers                              38207488                0
    DEL:     0.818860   0x7fa81fafbe60      0 BytesWrapper                     pymemtrace/tests/test_cpymemtrace.py             300 make_bytes_wrappers                              38207488                0
    DEL:     0.818875   0x7fa823802010      0 bytes                            pymemtrace/tests/test_cpymemtrace.py             300 make_bytes_wrappers                              38207488                0
    DEL:     0.819012   0x7fa82347c940      0 BytesWrapper                     pymemtrace/tests/test_cpymemtrace.py             300 make_bytes_wrappers                              38207488                0
    DEL:     0.819128   0x7fa823701010      0 bytes                            pymemtrace/tests/test_cpymemtrace.py             300 make_bytes_wrappers                              38207488                0
    DEL:     0.819370   0x7fa81e7aa280      0 BytesWrapper                     pymemtrace/tests/test_cpymemtrace.py             300 make_bytes_wrappers                              38207488                0
    DEL:     0.819447   0x7fa823600010      0 bytes                            pymemtrace/tests/test_cpymemtrace.py             300 make_bytes_wrappers                              38207488                0
    DEL:     0.819582   0x7fa81fbf2a00      0 BytesWrapper                     pymemtrace/tests/test_cpymemtrace.py             300 make_bytes_wrappers                              38207488                0
    DEL:     0.819648   0x7fa823903010      0 bytes                            pymemtrace/tests/test_cpymemtrace.py             300 make_bytes_wrappers                              38207488                0
    NEW:     0.820073   0x600003236b30      1 str                              pymemtrace/tests/test_cpymemtrace.py             304 make_bytes_wrappers                              38211584             4096
    NEW:     0.820357   0x6000067033e0      1 tuple                            pymemtrace/tests/test_cpymemtrace.py             292 make_bytes_wrappers                              38211584                0
    EOF

Then the output will be something like:

.. code-block:: text

    2026-03-18 11:51:12,278 - ref_trace_analyse.py#107 - WARNING  - DEL: on untracked object of type "builtin_function_or_method" at 0x60000670f980 on line 3
    2026-03-18 11:51:12,278 - ref_trace_analyse.py#107 - WARNING  - DEL: on untracked object of type "frame" at 0x600007cc44d0 on line 13
    2026-03-18 11:51:12,278 - ref_trace_analyse.py#107 - WARNING  - DEL: on untracked object of type "frame" at 0x7fa82347c930 on line 16
    8<---- Snip ---->8
    2026-03-18 11:51:12,280 - ref_trace_analyse.py#107 - WARNING  - DEL: on untracked object of type "frame" at 0x6000038409e0 on line 78
    Live Objects [4]:
        0x600001694c90    1 int                                      make_bytes_wrappers              test_cpymemtrace.py#295
        0x6000025fde70    1 list                                     make_bytes_wrappers              test_cpymemtrace.py#293
        0x600003236b30    1 str                                      make_bytes_wrappers              test_cpymemtrace.py#304
        0x6000067033e0    1 tuple                                    make_bytes_wrappers              test_cpymemtrace.py#292
    Previous Objects [26]:
        0x60000168b0d0 int                                      NEW: random.py#340 DEL: random.py#340
        0x60000168b190 int                                      NEW: random.py#322 DEL: test_cpymemtrace.py#295
        0x60000168b2d0 int                                      NEW: random.py#250 DEL: random.py#322
    8<---- Snip ---->8
        0x6000025e34a0 tuple                                    NEW: test_cpymemtrace.py#296 DEL: test_cpymemtrace.py#296
        0x6000025ec6a0 range                                    NEW: test_cpymemtrace.py#294 DEL: test_cpymemtrace.py#294
        0x6000067035c0 builtin_function_or_method               NEW: random.py#248 DEL: random.py#322
        0x600006709760 builtin_function_or_method               NEW: random.py#248 DEL: random.py#322
        0x60000670f980 builtin_function_or_method               NEW: random.py#248 DEL: random.py#322
        0x60000670f980 builtin_function_or_method               NEW: random.py#248 DEL: random.py#322
        0x7fa81e7aa280 BytesWrapper                             NEW: test_cpymemtrace.py#296 DEL: test_cpymemtrace.py#300
        0x7fa81fafbe60 BytesWrapper                             NEW: test_cpymemtrace.py#296 DEL: test_cpymemtrace.py#300
        0x7fa81fbf2a00 BytesWrapper                             NEW: test_cpymemtrace.py#296 DEL: test_cpymemtrace.py#300
        0x7fa82347c940 BytesWrapper                             NEW: test_cpymemtrace.py#296 DEL: test_cpymemtrace.py#300
        0x7fa823600010 bytes                                    NEW: test_cpymemtrace.py#288 DEL: test_cpymemtrace.py#300
        0x7fa823701010 bytes                                    NEW: test_cpymemtrace.py#288 DEL: test_cpymemtrace.py#300
        0x7fa823802010 bytes                                    NEW: test_cpymemtrace.py#288 DEL: test_cpymemtrace.py#300
        0x7fa823903010 bytes                                    NEW: test_cpymemtrace.py#288 DEL: test_cpymemtrace.py#300
    Type count [10]:
    Type                                          New      Del  New - Del
    BytesWrapper                                    4        4          0
    builtin_function_or_method                      4        5         -1
    bytes                                           4        4          0
    frame                                           0       16        -16
    int                                            19       18          1
    list                                            1        0          1
    range                                           1        1          0
    range_iterator                                  1        1          0
    str                                             1        0          1
    tuple                                           2        1          1
    Process time: 0.004 (s)

"""
import argparse
import collections
import dataclasses
import logging
import os
import re
import sys
import time
import typing

from pymemtrace.util import gnuplot

logger = logging.getLogger(__file__)


@dataclasses.dataclass
class ObjectData:
    """Contents of a single line of the log file with the columns in their appropriate types."""
    line_num: int
    clock: float
    address: int
    live_cnt: int
    type: str
    file: str
    line: int
    function: str
    rss: int
    drss: int


class LogFileResult:
    """Class that can read the log file into an internal representation."""

    def __init__(self, log_file_id: str, include_untracked: bool):
        """If include_untracked is True then de-allocations without the respective allocation are ignored."""
        self.log_file_id = log_file_id
        self.include_untracked = include_untracked
        self.intro_message_lines = []
        self.header_columns = []
        # All lines converted to ObjectData objects.
        self.objects: typing.List[ObjectData] = []
        # The key is the address.
        self.live_objects: typing.Dict[int, ObjectData] = {}
        # Pairs of (NEW, DEL)
        # The key is the address.
        self.prev_objects: typing.Dict[int, typing.List[typing.Tuple[ObjectData, ObjectData]]] = {}
        # Count of type allocation and de-allocation.
        self.type_count_new: typing.Dict[str, int] = collections.defaultdict(int)
        self.type_count_del: typing.Dict[str, int] = collections.defaultdict(int)
        self.type_count_untracked: typing.Dict[str, int] = collections.defaultdict(int)
        self.count_new = self.count_del = self.count_msg = 0
        # The earliest clock value of the process.
        self.clock_first = None
        self.clock_message_dict = {}
        self.rss_min = 0
        self.rss_max = 0

    def _parse_line(self, line_num: int, line: str) -> typing.Dict[str, typing.Any]:
        """Parse a line of the log file into a dict of the columns of the form: {header: value}."""
        columns = line.strip().split()
        if len(columns) != len(self.header_columns):
            raise ValueError(
                f'Line: {line_num}: len columns {len(columns)}'
                f' != header columns {len(self.header_columns)}'
            )
        ret = {}
        for hdr, col in zip(self.header_columns, columns):
            if hdr == 'Clock':
                val = float(col)
            elif hdr == 'Address':
                val = int(col, 16)
            elif hdr in ('LiveCnt', 'Line', 'RSS', 'dRSS'):
                val = int(col)
            else:
                val = col
            ret[hdr] = val
        return ret

    def _create_object(self, line_num: int, line_dict: typing.Dict[str, typing.Any]) -> ObjectData:
        """Create an ObjectData from the dict of {header: value}."""
        if self.clock_first is None:
            self.clock_first = line_dict['Clock']
        if self.rss_min == 0 or self.rss_min > line_dict['RSS']:
            self.rss_min = line_dict['RSS']
        if self.rss_max == 0 or self.rss_max < line_dict['RSS']:
            self.rss_max = line_dict['RSS']
        ret = ObjectData(
            line_num,
            line_dict['Clock'],
            line_dict['Address'],
            line_dict['LiveCnt'],
            line_dict['Type'],
            line_dict['File'],
            line_dict['Line'],
            line_dict['Function'],
            line_dict['RSS'],
            line_dict['dRSS'],
        )
        self.objects.append(ret)
        return ret

    def add_new(self, line_num: int, line: str) -> None:
        """Add a line starting "NEW:"."""
        line_dict = self._parse_line(line_num, line)
        assert line_dict['HDR:'] == 'NEW:'
        obj_repr = self._create_object(line_num, line_dict)
        if obj_repr.live_cnt != 1:
            logger.debug(
                f'NEW: object type "{obj_repr.type}"'
                f' has Reference count of {obj_repr.live_cnt} instead of unity.'
                f' Line: {line_num}'
            )
        if obj_repr.address in self.live_objects:
            logger.error(
                f'NEW address 0x{obj_repr.address:012x}'
                f' type: "{obj_repr.type}"'
                f' from line {line_num}'
                f' already exists from line {self.live_objects[obj_repr.address].line_num}.'
                f' type: "{self.live_objects[obj_repr.address].type}".'
            )
        self.live_objects[obj_repr.address] = obj_repr
        self.type_count_new[obj_repr.type] += 1
        self.count_new += 1

    def add_del(self, line_num: int, line: str) -> None:
        """Add a line starting "DEL:"."""
        line_dict = self._parse_line(line_num, line)
        assert line_dict['HDR:'] == 'DEL:'
        obj_repr = self._create_object(line_num, line_dict)
        if obj_repr.live_cnt != 0:
            logger.debug(
                f'DEL: object type "{obj_repr.type}"'
                f' has Reference count of {obj_repr.live_cnt} instead of zero.'
                f' Line: {line_num}'
            )
        if obj_repr.address in self.live_objects:
            if obj_repr.address not in self.prev_objects:
                self.prev_objects[obj_repr.address] = []
            self.prev_objects[obj_repr.address].append((self.live_objects[obj_repr.address], obj_repr))
            del self.live_objects[obj_repr.address]
        else:
            self.type_count_untracked[obj_repr.type] += 1
            if self.include_untracked:
                logger.warning(
                    f'DEL: on untracked object'
                    f' of type "{obj_repr.type}"'
                    f' at 0x{obj_repr.address:012x}'
                    f' LiveCnt: {obj_repr.live_cnt}'
                    f' on line {line_num}'
                )
        self.type_count_del[obj_repr.type] += 1
        self.count_del += 1

    def add_msg(self, line_num: int, line: str) -> None:
        """Add a line starting "MSG:".
        Example:

            MSG:    16.723673 # list_of_str_and_time.pop() Length 2869519
        """
        m = RE_COMPILE_LOG_FILE_MSG.match(line)
        if m is None:
            raise ValueError(f'Line {line_num} "{line}" does not match MSG format')
        clock_time = float(m.group(1))
        if clock_time not in self.clock_message_dict:
            self.clock_message_dict[clock_time] = []
        self.clock_message_dict[clock_time].append(m.group(2))
        self.count_msg += 1

    def add_err(self, line_num: int, line: str) -> None:
        """Add a line starting "ERR:"."""
        logger.error(f'Line {line_num} {line}')

    def long_str_list(self, show_full_path: bool, include_historical: bool) -> typing.List[str]:
        """Return the analysis as a list of strings suitable for printing."""

        def _str_from_object_file(obj: ObjectData, show_full_path: bool) -> str:
            if show_full_path:
                return f'{obj.file}'
            return f'{os.path.basename(obj.file)}'

        def _str_from_object(obj: ObjectData, show_full_path: bool) -> str:
            # Address is typically 0x7fd1f8028000
            return (
                f'0x{obj.address:012x}'
                f' {obj.clock:.6f}'
                f' {obj.live_cnt:4d}'
                f' {obj.type:40}'
                f' {obj.function:32}'
                f' {_str_from_object_file(obj, show_full_path)}#{obj.line}'
            )

        def _str_from_object_pair(obj_pair: typing.Tuple[ObjectData, ObjectData], show_full_path: bool) -> str:
            assert obj_pair[0].address == obj_pair[1].address
            assert obj_pair[0].type == obj_pair[1].type
            return (
                f'0x{obj_pair[0].address:012x} {obj_pair[0].type:40}'
                f' NEW:'
                f' t: {obj_pair[0].clock:.6f}'
                f' {_str_from_object_file(obj_pair[0], show_full_path)}#{obj_pair[0].line}'
                f' DEL:'
                f' dt: {obj_pair[1].clock - obj_pair[0].clock:.6f}'
                f' {_str_from_object_file(obj_pair[1], show_full_path)}#{obj_pair[1].line}'
            )

        ret = []
        if self.intro_message_lines:
            ret.append('Initial Message:')
            ret.extend(self.intro_message_lines)

        if self.include_untracked:
            ret.append(f'Untracked Objects [{len(self.type_count_untracked)}]:')
            ret.append(f'{"Type":40} {"Count":>8}')
            for type_name in sorted(self.type_count_untracked.keys()):
                ret.append(
                    f'{type_name:40}'
                    f' {self.type_count_untracked[type_name]:>8}'
                )

        ret.append(f'Live Objects [{len(self.live_objects)}]:')
        for address in sorted(self.live_objects.keys()):
            obj = self.live_objects[address]
            ret.append(f'    {_str_from_object(obj, show_full_path)}')

        ret.append(f'Previous Objects, sorted by clock [{len(self.prev_objects)}]:')
        if include_historical:
            # for address in sorted(self.prev_objects.keys()):
            #     for obj_pair in self.prev_objects[address]:
            #         ret.append(f'    {_str_from_object_pair(obj_pair, show_full_path)}')
            all_values = []
            for k in self.prev_objects.keys():
                all_values.extend(self.prev_objects[k])
            all_values.sort(key=lambda v: v[0].clock)
            for obj_pair in all_values:
                ret.append(f'    {_str_from_object_pair(obj_pair, show_full_path)}')

        all_types = sorted(set(self.type_count_new.keys()) | set(self.type_count_del.keys()))
        ret.append(f'Type count [{len(all_types)}]:')
        ret.append(f'{"Type":40} {"New":>8} {"Del":>8} {"New - Del":>10}')
        for type_name in all_types:
            ret.append(
                f'{type_name:40}'
                f' {self.type_count_new[type_name]:>8}'
                f' {self.type_count_del[type_name]:>8}'
                f' {self.type_count_new[type_name] - self.type_count_del[type_name]:10}'
            )
        return ret


# Matches:
# MSG:     3.289042 # Detaching this Reference Tracing file wrapper. New file: 20260420_091558_50_53552_O_1_PY3.13.0.log
RE_COMPILE_LOG_FILE_PUSH = re.compile(r'MSG: .+ # Detaching this Reference Tracing file wrapper. New file: (.+)')
# Matches:
# MSG:     3.298763 # Re-attaching this Reference Tracing file wrapper.
RE_COMPILE_LOG_FILE_POP = re.compile(r'MSG: .+ Re-attaching this Reference Tracing file wrapper.')
# Matches 'MSG:    16.723673 # list_of_str_and_time.pop() Length 2869519'
# Two groups: clock and message text.
RE_COMPILE_LOG_FILE_MSG = re.compile(r'MSG:\s+([0-9.]+) # (.+)')


def process_file_to_log_result(file: typing.TextIO, file_size: int, recurse_log_files: bool, result: LogFileResult):
    has_sof = False
    line_num = 0
    bytes_read = 0
    for l, line in enumerate(file):
        line_num = l + 1
        bytes_read += len(line)
        # Hack for '<frozen importlib.' etc. column breaks
        line = line.replace('<frozen ', '<frozen_')
        if line_num % 10000 == 0:
            if file_size:
                fraction_read = bytes_read / file_size
                logger.info(f'Reading line {line_num:16,d} [{fraction_read:6.2%}]')
            else:
                logger.info(f'Reading line {line_num:16,d}')
        assert line.endswith('\n')
        if line == 'SOF\n':
            has_sof = True
        elif line == 'EOF\n':
            break
        else:
            # Decide on what the line is
            if not has_sof:
                # Remove '\n' from the end.
                result.intro_message_lines.append(line[:-1])
            else:
                if line.startswith('HDR:'):
                    if len(result.header_columns) == 0:
                        assert len(result.header_columns) == 0
                        result.header_columns = line.strip().split()
                    else:
                        assert result.header_columns == line.strip().split()
                elif line.startswith('NEW:'):
                    result.add_new(line_num, line)
                elif line.startswith('DEL:'):
                    result.add_del(line_num, line)
                elif line.startswith('MSG:'):
                    result.add_msg(line_num, line)
                    # Handle this and include sub-file if requested.
                    if recurse_log_files:
                        # MSG:     3.289042 # Detaching this Reference Tracing file wrapper. New file: /Users/paulross/Documents/workspace/pymemtrace/20260420_091558_50_53552_O_1_PY3.13.0.log
                        m = RE_COMPILE_LOG_FILE_PUSH.match(line)
                        if m is not None:
                            # recurse
                            logger.info(f'Recusing into log file: {m.group(1)}')
                            with open(m.group(1)) as sub_file:
                                process_file_to_log_result(
                                    sub_file, os.path.getsize(m.group(1)), recurse_log_files, result
                                )
                            logger.info(f'Finished log file: {m.group(1)}')
                    # MSG:     3.298763 # Re-attaching this Reference Tracing file wrapper.
                    # m = RE_COMPILE_LOG_FILE_POP.match(line)
                    # if m is not None:
                    #     # Ignore.
                    #     pass
                elif line.startswith('ERR:'):
                    result.add_err(line_num, line)
                else:
                    logger.error(f'Line {line_num}: Can not process line "{line}"')
    logger.info(
        f'Lines: {line_num:,d}'
        f' NEW: {result.count_new:,d}'
        f' DEL: {result.count_del:,d}'
        f' NEW - DEL: {result.count_new - result.count_del:,d}'
        f' MSG: {result.count_msg:,d}'
    )


def process_file(
        file: typing.TextIO,
        log_file_id: str,
        file_size: int,
        include_untracked: bool,
        recurse_log_files: bool) -> LogFileResult:
    """Process the file into a LogFileResult and return that.
    If include_untracked is True then de-allocations without the respective allocation are ignored."""
    result = LogFileResult(log_file_id=log_file_id, include_untracked=include_untracked)
    process_file_to_log_result(file, file_size, recurse_log_files, result)
    return result


def process_file_path(file_path: str, include_untracked: bool, recurse_files: bool) -> LogFileResult:
    """Process the file path into a LogFileResult and return that."""
    with open(file_path) as file:
        logger.info(f'Starting log file: {file_path}')
        result = process_file(
            file, file_path, os.path.getsize(file_path), include_untracked, recurse_files
        )
        logger.info(f'Finished log file: {file_path}')
        return result


#: Usage: GNUPLOT_PLT.format(name=dat_file_name, extension='png', labels=[])
GNUPLOT_PLT = """
set grid
set title "Memory and Live Object Count." font ",14"
set xlabel "Elapsed Time (s)"
# set mxtics 5
# set xrange [0:3000]
set xrange [0:]
# set xtics
# set format x ""

#set logscale y
set ylabel "Memory Usage (Mb)"
set yrange [0:]
# set ytics 20
# set mytics 2
# set ytics 8,35,3

#set logscale y2
set y2label "Live Object Count"
# set y2range [0:200]
set y2range [0:]
set y2tics

set pointsize 1
set datafile separator whitespace#"	"
set datafile missing "NaN"

set terminal {extension} size 1200,800 # choose the file format
set output "{name}.{extension}" # choose the output device

# set key off

{labels}

#set key title "Window Length"
#  lw 2 pointsize 2

plot {plot}

reset
"""


def invoke_gnuplot(
        log_result: LogFileResult,
        tp_names: typing.List[str],
        gnuplot_dir: str) -> int:
    """Reads a log file, extracts the data, writes it out to gnuplot_dir and invokes gnuplot on it."""
    os.makedirs(gnuplot_dir, exist_ok=True)
    # ret = gnuplot.write_test_file(gnuplot_dir, 'png')
    # if ret:
    #     logger.error(f'Can not write gnuplot test file with error code {ret}')
    #     return ret
    if len(tp_names) == 0:
        logger.error(f'Need a list of tp_names for gnuplot')
        return -1
    running_live_counts = {k: 0 for k in tp_names}
    table = []
    for entry in log_result.objects:
        if entry.type in running_live_counts:
            running_live_counts[entry.type] = entry.live_cnt
            row = [entry.clock, ]
            row.extend([running_live_counts[k] for k in sorted(running_live_counts.keys())])
            row.append(entry.rss)
            row.append(entry.drss)
            table.append(row)

    # Make the list of labels from the MSG: lines.
    label_lines = []
    # y_value = (0.5 * (log_result.rss_max - log_result.rss_min)) / 1024 ** 2
    y_value = 5.0
    for clock_t in sorted(log_result.clock_message_dict.keys()):
        for msg in log_result.clock_message_dict[clock_t]:
            msg = msg.replace('"', '')
            # if len(msg) > 40:
            #     msg = msg[:40] + '...'
            label_lines.append(f'set arrow from {clock_t},{y_value} to {clock_t},0 lt -1 lw 1')
            # label_lines.append(
            #     f'set label "{msg}" at {clock_t},{y_value * 1.025}'
            #     f' left font ",9" rotate by 90 noenhanced front'
            # )
            label_lines.append(
                f'set label "{msg}" at {clock_t},{y_value + 1}'
                f' left font ",6" rotate by 90 noenhanced front'
            )
    file_name = os.path.basename(log_result.log_file_id)
    prefix_lines = [
        f'# File ID {log_result.log_file_id}',
        ' '.join(['# Clock', ] + tp_names + ['RSS', 'dRSS']),
    ]
    plot_lines = [
        f'"{file_name}.dat" using 1:(${2 + len(tp_names)} / 1024**2) axes x1y1 title "RSS (Mb), left axis" with lines lt 1 lw 2',
        # f'"{file_name}.dat" using 1:5 axes x1y2 title "Mean CPU (%), right axis" with lines lt 2 lw 1',
        # f'"{file_name}.dat" using 1:$3 / 10000) axes x1y2 title "Page Faults (10,000/s), right axis" with lines lt 3 lw 1',
        # f'"{file_name}.dat" using 1:6 axes x1y2 title "Instantaneous CPU (%), right axis" with lines lt 7 lw 1',
    ]
    for i, tp_name in enumerate(tp_names):
        plot_lines.append(
            f'"{file_name}.dat" using 1:{2 + i} axes x1y2 title "{tp_name}, right axis" with lines lt {2 + i} lw 2',
        )

    ret = gnuplot.invoke_gnuplot(
        gnuplot_dir, file_name, prefix_lines, table,
        GNUPLOT_PLT.format(
            name=file_name, extension='png', labels='\n'.join(label_lines),
            plot=', \\\n'.join(plot_lines)
        )
    )
    return ret

    # table, _t_min, _t_max, rss_min, rss_max = extract_json_as_table(json_data)
    # for pid in table:
    #     log_name = f'{os.path.basename(log_path)}_{pid}'
    #     labels = extract_labels_from_json(json_data)
    #     label_lines = []
    #     y_value = (0.5 * (rss_max[pid] - rss_min[pid])) / 1024 ** 2
    #     for label_dict in labels:
    #         t_value = label_dict[KEY_ELAPSED_TIME]
    #         label_lines.append(f'set arrow from {t_value},{y_value} to {t_value},0 lt -1 lw 1')
    #         label_lines.append(
    #             f'set label "{label_dict[KEY_LABEL]}" at {t_value},{y_value * 1.025}'
    #             f' left font ",10" rotate by 90 noenhanced front'
    #         )
    #     ret = gnuplot.invoke_gnuplot(
    #         gnuplot_dir, log_name, table[pid],
    #         GNUPLOT_PLT.format(name=log_name, extension='png', labels='\n'.join(label_lines))
    #     )
    #     if ret:
    #         break


def main() -> int:
    """Main entry point. Options:

    usage: ref_trace_analyse.py
           [-h] [--full-path] [--include-untracked] [--include-historical]
           [--recurse-files] [-l LOG_LEVEL]
           log_path

    Reads an Reference Tracing log of a process and analyses it.

    positional arguments:
      log_path              Input path to the log.

    options:
      -h, --help            show this help message and exit
      --full-path           Show the full Python file path. [default: False]
      --include-untracked   Include untracked objects. These are objects that are
                            de-allocated with no corresponding allocation.
                            [default: False]
      --include-historical  Ignore objects that were allocated and de-allocated
                            correctly. [default: False]
      --recurse-files       If True then recurse into child log files. [default:
                            False]
      -l, --log_level LOG_LEVEL
                            Log Level (debug=10, info=20, warning=30, error=40,
                            critical=50) [default: 20]
    """
    parser = argparse.ArgumentParser(
        prog=__file__,
        description="""Reads an Reference Tracing log of a process and analyses it.""",
    )
    parser.add_argument('log_path', type=str, help='Input path to the log.')
    parser.add_argument(
        "--full-path",
        action="store_true",
        help="Show the full Python file path."
             " [default: %(default)s]",
    )
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Include untracked objects."
             " These are objects that are de-allocated with no corresponding allocation."
             " [default: %(default)s]",
    )
    parser.add_argument(
        "--include-historical",
        action="store_true",
        help="Ignore objects that were allocated and de-allocated correctly."
             " [default: %(default)s]",
    )
    parser.add_argument(
        "--recurse-files",
        action="store_true",
        help="If True then recurse into child log files."
             " [default: %(default)s]",
    )
    parser.add_argument('--gnuplot-path', type=str, help='Output path for the gnuplot results.')
    parser.add_argument(
        '--gnuplot-types',
        default='',
        help="Comma seperated list of types to monitor for the gnuplot results."
             " [default: %(default)s]",
    )
    parser.add_argument("-l", "--log_level", type=int, dest="log_level", default=20,
                        help="Log Level (debug=10, info=20, warning=30, error=40, critical=50)"
                             " [default: %(default)s]"
                        )
    args = parser.parse_args()
    logging.basicConfig(
        level=args.log_level,
        # format='%(asctime)s - %(filename)s#%(lineno)d - %(process)5d - (%(threadName)-10s) - %(levelname)-8s - %(message)s',
        format='%(asctime)s - %(filename)s#%(lineno)d - %(levelname)-8s - %(message)s',
        stream=sys.stdout,
    )
    # print(args)
    # return 0
    time_start = time.perf_counter()
    print(f'File path: {args.log_path}')
    result = process_file_path(args.log_path, args.include_untracked, args.recurse_files)
    print('\n'.join(result.long_str_list(args.full_path, args.include_historical)))
    if args.gnuplot_path:
        invoke_gnuplot(
            result,
            [v.strip() for v in args.gnuplot_types.split(',')],
            args.gnuplot_path,
        )
    print(f'Process time: {time.perf_counter() - time_start:.3f} (s)')
    return 0


if __name__ == '__main__':
    exit(main())
