"""

Example:

dtrace:::BEGIN
 77633  cmn_cmd_opts.py:141  -> set_log_level malloc(560) pntr 0x7fca83ef4240
 77633      __init__.py:422  -> validate malloc(1114) pntr 0x7fca858e4200
 77633      __init__.py:422  -> validate free(0x7fca858e4200)
 77633     threading.py:817  -> __init__ malloc(576) pntr 0x7fca83ef4470
 77633      __init__.py:471  -> _init malloc(576) pntr 0x7fca83ef46b0
 77633     threading.py:870  -> start malloc(264) pntr 0x7fca83ef21e0
 77633     threading.py:870  -> start malloc(16) pntr 0x7fca83d48a30
 77633     threading.py:574  -> wait malloc(536) pntr 0x7fca83d54be0
 77633     threading.py:364  -> notify malloc(528) pntr 0x7fca83c47e80
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data malloc(4096) pntr 0x7fca8408d200
 77633       process.py:268  -> _get_process_data malloc(25) pntr 0x7fca83c00620
 77633       process.py:268  -> _get_process_data malloc(4096) pntr 0x7fca8408e200
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x0)
 77633       process.py:268  -> _get_process_data free(0x7fca83c00620)
 77633       process.py:268  -> _get_process_data free(0x7fca8408e200)
 77633       process.py:268  -> _get_process_data free(0x7fca8408d200)
dtrace::END


2025-08-26 13:35:50,956 - dtrace_log_analyse.py#201 - INFO     - Ending DTrace block at line 16261386
DTraceMallocs:
malloc count outstanding:      926,784
 Total bytes outstanding:  122,456,515
   Max bytes outstanding:  220,487,009
    Total bytes malloc'd:  837,846,488
      Total bytes free'd:  715,389,973
          Maximum malloc:      589,880
         Max allocations:    2,314,384
           Count mallocs:    7,197,954
    Count frees non-null:    6,271,170
        Count frees null:       39,119
Total lines: 16,261,304 Failed parse lines: 36,526 Failed malloc: 931,407 Failed free: 1,785,128
Process time: 602.995 (s)
(pymemtrace_3.12_A)
engun@Pauls-MBP-2  ~/Documents/workspace/pymemtrace (develop)

"""
import argparse
import dataclasses
import io
import logging
import re
import sys
import time
import typing

logger = logging.getLogger(__file__)

# Matches ' 77633  cmn_cmd_opts.py:141  -> set_log_level malloc(560) pntr 0x7fca83ef4240'
# To: ('77633', 'cmn_cmd_opts.py', '141', 'set_log_level', '560', '0x7fca83ef4240')
RE_MALLOC = re.compile(r'^\s+(\d+)\s+([^:]+):(\d+)\s+->\s+(\S.*\S)?\s+malloc\((\d+)\)\s+pntr\s+(0x[0-9a-f]+)$')

# Given a line:
# " 77633 rs/paulross/PycharmProjects/TotalDepth/src/TotalDepth/common/np_summary.py:100  -> y malloc(15424) pntr 0x7fca8410fe00\n"
# split('->')
# Then apply RE_MALLOC_LEFT and RE_MALLOC_RIGHT
RE_MALLOC_LEFT = re.compile(r'^\s+(\d+)\s+([^:]+):(\d+)\s+$')
RE_MALLOC_RIGHT = re.compile(r'^\s+(\S+)?\s+malloc\((\d+)\)\s+pntr\s+(0x[0-9a-f]+)$')

# Matches '... malloc(560) pntr 0x7fca83ef4240'
# To: ('... ', '560', '0x7fca83ef4240')
RE_MALLOC_LAST_RESORT = re.compile(r'^(.+)malloc\((\d+)\)\s+pntr\s+(0x[0-9a-f]+)$')
# Matches ' 77633       process.py:268  -> _get_process_data free(0x7fca83c00620)'
# To: ('77633', 'process.py', '268', '_get_process_data', '0x7fca83c00620')
RE_FREE = re.compile(r'^\s+(\d+)\s+([^:]+)?:(\d+)\s+->\s+(\S.*\S)?\s+free\((0x[0-9a-f]+)\)$')
# Matches ' 77633  anything... free(0x7fca83c00620)'
# To: ('77633', 'anything... ', '0x7fca83c00620')
RE_FREE_FALLBACK_A = re.compile(r'^\s+(\d+)(.+)free\((0x[0-9a-f]+)\)$')
# Matches '... free(0x7fca83c00620)'
# To: ('... ', '0x7fca83c00620')
RE_FREE_LAST_RESORT = re.compile(r'^(.+)free\((0x[0-9a-f]+)\)$')


@dataclasses.dataclass
class DTraceMallocCall:
    log_line: int
    process: int
    file: str
    line: int
    function: typing.Optional[str]
    size: int
    pointer: int


@dataclasses.dataclass
class DTraceFreeCall:
    log_line_num: int
    process: int
    file: str
    line: int
    function: str
    pointer: int


class DTraceMallocs:
    def __init__(self):
        self.malloc_dict: typing.Dict[int, DTraceMallocCall] = {}
        self.count_mallocs = 0
        self.count_frees_non_null = 0
        self.count_frees_null = 0
        self.count_lines = 0
        self.total_bytes_malloced = 0
        self.total_bytes_freed = 0
        self.total_bytes_outstanding = 0
        self.max_malloc = 0
        self.max_allocations = 0
        self.max_bytes_outstanding = 0
        self.failed_to_add_malloc = 0
        self.failed_to_add_free = 0
        self.failed_to_parse_line = 0

    def __len__(self) -> int:
        return len(self.malloc_dict)

    def add_malloc(self, malloc_call: DTraceMallocCall):
        if malloc_call.pointer in self.malloc_dict:
            was = self.malloc_dict[malloc_call.pointer]
            # raise ValueError(
            #     f'Malloc call at 0x{malloc_call.pointer:012x} already in dict'
            #     f' Was log line: {was.log_line} now {malloc_call.log_line}'
            # )
            logger.error(
                f'Malloc call at 0x{malloc_call.pointer:012x} already in dict'
                f' Was log line: {was.log_line} now {malloc_call.log_line}'
            )
            self.failed_to_add_malloc += 1
        else:
            self.malloc_dict[malloc_call.pointer] = malloc_call
            self.count_mallocs += 1
            self.total_bytes_malloced += malloc_call.size
            self.total_bytes_outstanding += malloc_call.size
            self.max_allocations = max(self.max_allocations, len(self))
            self.max_bytes_outstanding = max(self.max_bytes_outstanding, self.total_bytes_outstanding)
            self.max_malloc = max(self.max_malloc, malloc_call.size)
        self.count_lines += 1

    def add_free(self, free_call: DTraceFreeCall):
        if free_call.pointer != 0:
            if free_call.pointer not in self.malloc_dict:
                # raise ValueError(f'Free call at 0x{free_call.pointer:012x} not in dict')
                logger.error(
                    f'Free call at 0x{free_call.pointer:012x} line {free_call.log_line_num} not in dict'
                )
                self.failed_to_add_free += 1
            else:
                size_free = self.malloc_dict[free_call.pointer].size
                self.total_bytes_freed += size_free
                self.total_bytes_outstanding -= size_free
                del self.malloc_dict[free_call.pointer]
                self.count_frees_non_null += 1
        else:
            self.count_frees_null += 1
        self.count_lines += 1

    def str_failures(self) -> str:
        return (
            f'Total lines: {(self.count_lines + self.failed_to_parse_line):,d}'
            f' Failed parse lines: {self.failed_to_parse_line:,d}'
            f' Failed malloc: {self.failed_to_add_malloc:,d}'
            f' Failed free: {self.failed_to_add_free:,d}'
        )


def match_malloc_line(line: str, log_line: int) -> typing.Optional[DTraceMallocCall]:
    m = RE_MALLOC.match(line)
    if m is not None:
        malloc_call = DTraceMallocCall(
            log_line, int(m.group(1)), m.group(2), int(m.group(3)),
            m.group(4), int(m.group(5)), int(m.group(6), base=16)
        )
        return malloc_call
    else:
        # Fall back on a split technique that matches:
        # " 77633 rs/paulross/PycharmProjects/TotalDepth/src/TotalDepth/common/np_summary.py:100  -> y malloc(15424) pntr 0x7fca8410fe00\n"
        split = line.split('->')
        if len(split) == 2:
            m_left = RE_MALLOC_LEFT.match(split[0])
            m_right = RE_MALLOC_RIGHT.match(split[1])
            if m_left and m_right:
                malloc_call = DTraceMallocCall(
                    log_line, int(m_left.group(1)), m_left.group(2), int(m_left.group(3)),
                    m_right.group(1), int(m_right.group(2)), int(m_right.group(3), base=16)
                )
                return malloc_call
            else:
                m = RE_MALLOC_LAST_RESORT.match(line)
                if m is not None:
                    malloc_call = DTraceMallocCall(
                        log_line, -1, m.group(1), -1,
                        '', int(m.group(2)), int(m.group(3), base=16)
                    )
                    return malloc_call


def match_free_line(line: str, log_line: int) -> typing.Optional[DTraceFreeCall]:
    m = RE_FREE.match(line)
    if m is not None:
        free_call = DTraceFreeCall(
            log_line, int(m.group(1)), m.group(2), int(m.group(3)),
            m.group(4), int(m.group(5), base=16)
        )
        return free_call
    else:
        m = RE_FREE_FALLBACK_A.match(line)
        if m is not None:
            free_call = DTraceFreeCall(
                log_line, int(m.group(1)), "", -1,
                m.group(2), int(m.group(3), base=16)
            )
            return free_call
        else:
            m = RE_FREE_LAST_RESORT.match(line)
            if m is not None:
                free_call = DTraceFreeCall(
                    log_line, -1, m.group(1), -1,
                    "", int(m.group(2), base=16)
                )
                return free_call



def read_dtrace_log_file(log_file: io.StringIO) -> DTraceMallocs:
    in_dtrace_block = False
    log_line_num = 1
    malloc_dict = DTraceMallocs()
    for line in log_file.readlines():
        if log_line_num % 1000 == 0:
            logger.info('Reading line %d', log_line_num)
        if line != '\n':
            if line == 'dtrace:::BEGIN\n':
                in_dtrace_block = True
                logger.info('Starting DTrace block at line %d', log_line_num)
            elif line == 'dtrace:::END\n':
                in_dtrace_block = False
                logger.info('Ending DTrace block at line %d', log_line_num)
                break
            elif in_dtrace_block:
                malloc_call = match_malloc_line(line, log_line_num)
                if malloc_call is not None:
                    malloc_dict.add_malloc(malloc_call)
                else:
                    free_call = match_free_line(line, log_line_num)
                    if free_call is not None:
                        malloc_dict.add_free(free_call)
                    else:
                        logger.error(f'Can not parse line [{log_line_num}]: "{line}"')
                        malloc_dict.failed_to_parse_line += 1
        log_line_num += 1
    return malloc_dict


def read_dtrace_log(log_path: str) -> DTraceMallocs:
    with open(log_path, encoding='latin-1') as log_file:
        return read_dtrace_log_file(log_file)


def pprint_mallocs(dtm: DTraceMallocs, st=sys.stdout) -> None:
    st.write('DTraceMallocs:\n')
    st.write(f'malloc count outstanding: {len(dtm):12,d}\n')
    st.write(f' Total bytes outstanding: {dtm.total_bytes_outstanding:12,d}\n')
    st.write(f'   Max bytes outstanding: {dtm.max_bytes_outstanding:12,d}\n')
    st.write(f"    Total bytes malloc'd: {dtm.total_bytes_malloced:12,d}\n")
    st.write(f"      Total bytes free'd: {dtm.total_bytes_freed:12,d}\n")
    st.write(f"          Maximum malloc: {dtm.max_malloc:12,d}\n")
    st.write(f'         Max allocations: {dtm.max_allocations:12,d}\n')
    st.write(f'           Count mallocs: {dtm.count_mallocs:12,d}\n')
    st.write(f'    Count frees non-null: {dtm.count_frees_non_null:12,d}\n')
    st.write(f'        Count frees null: {dtm.count_frees_null:12,d}\n')
    st.write(dtm.str_failures() + '\n')


def main():
    parser = argparse.ArgumentParser(
        prog='process.py',
        description="""Reads an DTrace log of a process and analyses it.""",
    )
    parser.add_argument("-l", "--log_level", type=int, dest="log_level", default=20,
                        help="Log Level (debug=10, info=20, warning=30, error=40, critical=50)"
                             " [default: %(default)s]"
                        )
    parser.add_argument('path_in', type=str, help='Input path to the DTrace log.', nargs='?')
    args = parser.parse_args()
    logging.basicConfig(
        level=args.log_level,
        # format='%(asctime)s - %(filename)s#%(lineno)d - %(process)5d - (%(threadName)-10s) - %(levelname)-8s - %(message)s',
        format='%(asctime)s - %(filename)s#%(lineno)d - %(levelname)-8s - %(message)s',
        stream=sys.stdout,
    )
    time_start = time.perf_counter()
    result = read_dtrace_log(args.path_in)
    pprint_mallocs(result)
    print(f'Process time: {time.perf_counter() - time_start:.3f} (s)')


if __name__ == '__main__':
    exit(main())
