"""
Analyses log files produced by cPyMemTrace.ReferenceTrace()

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
    def __init__(self):
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
            raise ValueError(
                f'NEW address {obj_repr.address}'
                f' from line {line_num}'
                f' already exists from line {self.live_objects[obj_repr.address].line_num}.'
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
        else:
            logger.warning(
                f'DEL: on untracked object'
                f' of type "{obj_repr.type}"'
                f' at 0x{obj_repr.address:012x} on line {line_num}'
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


def process_file(file: typing.TextIO) -> LogFileResult:
    """Process the file into a LogFileResult and return that."""
    result = LogFileResult()
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
                result.intro_message_lines.append(line)
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


def process_file_path(file_path: str) -> LogFileResult:
    """Process the file path into a LogFileResult and return that."""
    with open(file_path) as file:
        return process_file(file)


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
    result = process_file_path(args.log_path)
    print('\n'.join(result.long_str_list(args.full_path)))
    print(f'Process time: {time.perf_counter() - time_start:.3f} (s)')
    return 0


if __name__ == '__main__':
    exit(main())
