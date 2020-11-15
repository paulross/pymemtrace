"""
Parses DTrace output.

Example from toolkit/py_flow_malloc_free.d:
dtrace:::BEGIN
 77633  cmn_cmd_opts.py:141  -> set_log_level malloc(560) pntr 0x7fca83ef4240
 77633      __init__.py:422  -> validate malloc(1114) pntr 0x7fca858e4200
 77633      __init__.py:422  -> validate free(0x7fca858e4200)
 77633     threading.py:817  -> __init__ malloc(576) pntr 0x7fca83ef4470

"""
import logging
import pprint
import re
import sys
import typing


logger = logging.getLogger(__file__)


#: Matches " 77633  cmn_cmd_opts.py:141  -> set_log_level malloc(560) pntr 0x7fca83ef4240"
#: Six groups:
#: To ('77633', 'cmn_cmd_opts.py', '141', 'set_log_level', '560', '0x7fca83ef4240')
RE_PY_FLOW_MALLOC_FREE_MALLOC = re.compile(r'^\s+(\d+)\s+(.+?):(\d+)\s+-> (\S+) malloc\((\d+)\) pntr (.+)$')


class Malloc(typing.NamedTuple):
    log_line: int
    pid: int
    file: str
    line: int
    function: str
    size: int
    address: int

    def __str__(self):
        return f'Malloc: {self.log_line} {self.file}:{self.line} {self.function} {self.size} 0x{self.address:x}'

def match_to_malloc(line: int, m: re.match) -> Malloc:
    """Given a match that has groups: ('77633', 'cmn_cmd_opts.py', '141', 'set_log_level', '560', '0x7fca83ef4240')
    this returns a Malloc() object."""
    return Malloc(
        line,
        int(m.group(1)),
        m.group(2),
        int(m.group(3)),
        m.group(4),
        int(m.group(5)),
        int(m.group(6), 16),
    )


#: Matches " 77633      __init__.py:422  -> validate free(0x7fca858e4200)"
#: Five groups:
#: To ('77633', '__init__.py', '422', 'validate', '0x7fca858e4200')
RE_PY_FLOW_MALLOC_FREE_FREE = re.compile(r'^\s+(\d+)\s+(.+?):(\d+)\s+-> (\S+) free\((\S+)\)$')


class Free(typing.NamedTuple):
    log_line: int
    pid: int
    file: str
    line: int
    function: str
    address: int

    def __str__(self):
        return f'Free: {self.log_line} {self.file}:{self.line} {self.function}'# 0x{self.address:x}'


def match_to_free(line: int, m: re.match) -> Free:
    """Given a match that has groups: ('77633', '__init__.py', '422', 'validate', '0x7fca858e4200')
    this returns a Malloc() object."""
    return Free(
        line,
        int(m.group(1)),
        m.group(2),
        int(m.group(3)),
        m.group(4),
        int(m.group(5), 16),
    )


def parse_py_flow_malloc_free(file: typing.BinaryIO) -> typing.Dict[int, Malloc]:
    file.seek(0)
    malloc_dict: typing.Dict[int, Malloc] = {}
    for l, bin_line in enumerate(file):
        line = bin_line.decode('ascii', 'ignore')
        # print(f'TRACE: {line!r}')
        m = RE_PY_FLOW_MALLOC_FREE_MALLOC.match(line)
        if m is not None:
            malloc = match_to_malloc(l, m)
            if malloc.address in malloc_dict:
                logger.error('Line %d malloc address 0x%x already in malloc dict', l, malloc.address)
            else:
                malloc_dict[malloc.address] = malloc
        else:
            m = RE_PY_FLOW_MALLOC_FREE_FREE.match(line)
            if m is not None:
                free = match_to_free(l, m)
                if free.address == 0:
                    logger.error('Ignoring 0x0 %s', free)
                else:
                    if free.address not in malloc_dict:
                        logger.error('Line %d free address 0x%x not in malloc dict', l, free.address)
                    else:
                        logger.info('%s free\'d %s', malloc_dict[free.address], free)
                        del malloc_dict[free.address]
    return malloc_dict



def main():
    logging.basicConfig(
        level=20,
        format='%(asctime)s - %(filename)-16s - %(lineno)4d - %(process)5d - (%(threadName)-10s) - %(levelname)-8s - %(message)s',
        stream=sys.stdout,
    )
    with open(sys.argv[1], 'rb') as file:
        malloc_dict = parse_py_flow_malloc_free(file)
        pprint.pprint(malloc_dict)
    return 0


if __name__ == '__main__':
    sys.exit(main())
