"""
Analyses log files produced by cPyMemTrace.ReferenceTrace()

"""
import argparse
import dataclasses
import logging
import os
import sys
import time
import typing

logger = logging.getLogger(__file__)


@dataclasses.dataclass
class ObjectData:
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

    def __init__(self):
        self.intro_message_lines = []
        self.header_columns = []
        # The key is the address.
        self.live_objects: typing.Dict[int, ObjectData] = {}
        # Pairs of (NEW, DEL)
        self.prev_objects: typing.Dict[int, typing.List[typing.Tuple[ObjectData, ObjectData]]] = {}

    def _parse_line(self, line_num: int, line: str) -> typing.Dict[str, typing.Any]:
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
        # print(f'TRACE: {line}')
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

    def add_del(self, line_num: int, line: str) -> None:
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
                f' at 0x{obj_repr.address:08x} on line {line_num}'
            )

    def add_msg(self, line_num: int, line: str) -> None:
        pass

    def long_str_list(self) -> typing.List[str]:

        def _str_from_object_file(obj: ObjectData) -> str:
            return f'{os.path.basename(obj.file)}'
            # return f'{obj.file}'

        def _str_from_object(obj: ObjectData) -> str:
            return (
                f'0x{obj.address:08x}'
                f' {obj.ref_cnt:4d}'
                f' {obj.type:40}'
                f' {_str_from_object_file(obj)}#{obj.line}'
            )

        def _str_from_object_pair(obj_pair: typing.Tuple[ObjectData, ObjectData]) -> str:
            assert obj_pair[0].address == obj_pair[1].address
            assert obj_pair[0].type == obj_pair[1].type
            return (
                f'0x{obj_pair[0].address:08x} {obj_pair[0].type:40}'
                f' NEW: {_str_from_object_file(obj_pair[0])}#{obj_pair[0].line}'
                f' DEL: {_str_from_object_file(obj_pair[1])}#{obj_pair[1].line}'
            )

        ret = []
        if self.intro_message_lines:
            ret.append('Initial Message:')
            ret.extend(self.intro_message_lines)
        ret.append(f'Live Objects [{len(self.live_objects)}]:')
        for address in sorted(self.live_objects.keys()):
            obj = self.live_objects[address]
            ret.append(f'    {_str_from_object(obj)}')
        ret.append(f'Previous Objects [{len(self.prev_objects)}]:')
        for address in sorted(self.prev_objects.keys()):
            for obj_pair in self.prev_objects[address]:
                ret.append(f'    {_str_from_object_pair(obj_pair)}')
        return ret


def process_file(file: typing.TextIO) -> LogFileResult:
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
                    # print(f'TRACE: {line}')
                    result.add_new(line_num, line)
                elif line.startswith('DEL:'):
                    result.add_del(line_num, line)
                elif line.startswith('MSG:'):
                    result.add_msg(line_num, line)
                else:
                    logger.error(f'Line {line_num}: Can not process line "{line}"')
    # print(result)
    return result


def process_file_path(file_path: str):
    with open(file_path) as file:
        return process_file(file)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog=__file__,
        description="""Reads an Reference Tracing log of a process and analyses it.""",
    )
    parser.add_argument("-l", "--log_level", type=int, dest="log_level", default=20,
                        help="Log Level (debug=10, info=20, warning=30, error=40, critical=50)"
                             " [default: %(default)s]"
                        )
    parser.add_argument('log_path', type=str, help='Input path to the log.')
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
    print('\n'.join(result.long_str_list()))
    print()
    print(f'Process time: {time.perf_counter() - time_start:.3f} (s)')
    return 0


if __name__ == '__main__':
    exit(main())
