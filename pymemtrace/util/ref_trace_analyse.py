"""
Analyses log files produced by cPyMemTrace.ReferenceTrace()

For example, given a log file such as:

.. code-block:: text

    SOF
    HDR:        Clock          Address RefCnt Type                             File                                            Line Function                                              RSS             dRSS
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
import sys
import time
import typing

logger = logging.getLogger(__file__)


@dataclasses.dataclass
class ObjectData:
    """Contents of a single line of the log file with the columns in their appropriate types."""
    line_num: int
    clock: float
    address: int
    ref_cnt: int
    type: str
    file: str
    line: int
    function: str
    rss: int
    drss: int


class LogFileResult:
    """Class that can read the log file into an internal representation."""
    def __init__(self, ignore_untracked: bool):
        self.ignore_untracked = ignore_untracked
        self.intro_message_lines = []
        self.header_columns = []
        # The key is the address.
        self.live_objects: typing.Dict[int, ObjectData] = {}
        # Pairs of (NEW, DEL)
        # The key is the address.
        self.prev_objects: typing.Dict[int, typing.List[typing.Tuple[ObjectData, ObjectData]]] = {}
        # Count of type allocation and de-allocation.
        self.type_count_new: typing.Dict[str, int] = collections.defaultdict(int)
        self.type_count_del: typing.Dict[str, int] = collections.defaultdict(int)

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
            elif hdr in ('RefCnt', 'Line', 'RSS', 'dRSS'):
                val = int(col)
            else:
                val = col
            ret[hdr] = val
        return ret

    def _create_object(self, line_num: int, line_dict: typing.Dict[str, typing.Any]) -> ObjectData:
        """Create an ObjectData from the dict of {header: value}."""
        return ObjectData(
            line_num,
            line_dict['Clock'],
            line_dict['Address'],
            line_dict['RefCnt'],
            line_dict['Type'],
            line_dict['File'],
            line_dict['Line'],
            line_dict['Function'],
            line_dict['RSS'],
            line_dict['dRSS'],
        )

    def add_new(self, line_num: int, line: str) -> None:
        """Add a line starting "NEW:"."""
        line_dict = self._parse_line(line_num, line)
        assert line_dict['HDR:'] == 'NEW:'
        obj_repr = self._create_object(line_num, line_dict)
        if obj_repr.address in self.live_objects:
            # raise ValueError(
            logger.error(
                f'NEW address 0x{obj_repr.address:012x}'
                f' type: "{obj_repr.type}"'
                f' from line {line_num}'
                f' already exists from line {self.live_objects[obj_repr.address].line_num}.'
                f' type: "{self.live_objects[obj_repr.address].type}".'
            )
        self.live_objects[obj_repr.address] = obj_repr
        self.type_count_new[obj_repr.type] += 1

    def add_del(self, line_num: int, line: str) -> None:
        """Add a line starting "DEL:"."""
        line_dict = self._parse_line(line_num, line)
        assert line_dict['HDR:'] == 'DEL:'
        obj_repr = self._create_object(line_num, line_dict)
        if obj_repr.address in self.live_objects:
            if obj_repr.address not in self.prev_objects:
                self.prev_objects[obj_repr.address] = []
            self.prev_objects[obj_repr.address].append((self.live_objects[obj_repr.address], obj_repr))
            del self.live_objects[obj_repr.address]
        elif not self.ignore_untracked:
            logger.warning(
                f'DEL: on untracked object'
                f' of type "{obj_repr.type}"'
                f' at 0x{obj_repr.address:012x}'
                f' RefCnt: {obj_repr.ref_cnt}'
                f' on line {line_num}'
            )
        self.type_count_del[obj_repr.type] += 1

    def add_msg(self, line_num: int, line: str) -> None:
        """Add a line starting "MSG:"."""
        pass

    def long_str_list(self, show_full_path: bool) -> typing.List[str]:
        """Return the analysis as a list of strings suitable for printing."""
        def _str_from_object_file(obj: ObjectData, show_full_path: bool) -> str:
            if show_full_path:
                return f'{obj.file}'
            return f'{os.path.basename(obj.file)}'

        def _str_from_object(obj: ObjectData, show_full_path: bool) -> str:
            # Address is typically 0x7fd1f8028000
            return (
                f'0x{obj.address:012x}'
                f' {obj.ref_cnt:4d}'
                f' {obj.type:40}'
                f' {obj.function:32}'
                f' {_str_from_object_file(obj, show_full_path)}#{obj.line}'
            )

        def _str_from_object_pair(obj_pair: typing.Tuple[ObjectData, ObjectData], show_full_path: bool) -> str:
            assert obj_pair[0].address == obj_pair[1].address
            assert obj_pair[0].type == obj_pair[1].type
            return (
                f'0x{obj_pair[0].address:012x} {obj_pair[0].type:40}'
                f' NEW: {_str_from_object_file(obj_pair[0], show_full_path)}#{obj_pair[0].line}'
                f' DEL: {_str_from_object_file(obj_pair[1], show_full_path)}#{obj_pair[1].line}'
            )

        ret = []
        if self.intro_message_lines:
            ret.append('Initial Message:')
            ret.extend(self.intro_message_lines)
        # print(f'TRACE self.intro_message_lines {self.intro_message_lines}')

        ret.append(f'Live Objects [{len(self.live_objects)}]:')
        for address in sorted(self.live_objects.keys()):
            obj = self.live_objects[address]
            ret.append(f'    {_str_from_object(obj, show_full_path)}')

        ret.append(f'Previous Objects [{len(self.prev_objects)}]:')
        for address in sorted(self.prev_objects.keys()):
            for obj_pair in self.prev_objects[address]:
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


def process_file(file: typing.TextIO, ignore_untracked: bool) -> LogFileResult:
    """Process the file into a LogFileResult and return that."""
    result = LogFileResult(ignore_untracked=ignore_untracked)
    has_sof = False
    for l, line in enumerate(file):
        line_num = l + 1
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
                    assert len(result.header_columns) == 0
                    result.header_columns = line.strip().split()
                elif line.startswith('NEW:'):
                    result.add_new(line_num, line)
                elif line.startswith('DEL:'):
                    result.add_del(line_num, line)
                elif line.startswith('MSG:'):
                    result.add_msg(line_num, line)
                else:
                    logger.error(f'Line {line_num}: Can not process line "{line}"')
    return result


def process_file_path(file_path: str, ignore_untracked: bool) -> LogFileResult:
    """Process the file path into a LogFileResult and return that."""
    with open(file_path) as file:
        return process_file(file, ignore_untracked)


def main() -> int:
    """Main entry point."""
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
        '-i', "--ignore-untracked",
        action="store_true",
        help="Ignore untracked objects."
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
    time_start = time.perf_counter()
    print(f'File path: {args.log_path}')
    result = process_file_path(args.log_path, args.ignore_untracked)
    print('\n'.join(result.long_str_list(args.full_path)))
    print(f'Process time: {time.perf_counter() - time_start:.3f} (s)')
    return 0


if __name__ == '__main__':
    exit(main())
