"""
This is a wrapper around sys._debugmallocstats which writes to C stderr.
We capture this and can diff two calls to sys._debugmallocatats.

sys._debugmallocatats Implementation (Python 3.9)
=================================================

``sys__debugmallocstats_impl(PyObject *module)``

Calls:

``_PyObject_DebugMallocStats(stderr))``

Then:

``_PyObject_DebugTypeStats(stderr);``

Memory Usage by the Python Object Allocator
---------------------------------------------

``_PyObject_DebugMallocStats is defined in Objects/obmalloc.c:``

Which dumps out the arenas/pools/blocks.

Memory Usage by Type
------------------------------

``_PyObject_DebugTypeStats`` is defined in ``Objects/object.c``

This calls::

    _PyDict_DebugMallocStats(out); // in Objects/dictobject.c, just calls _PyDebugAllocatorStats in Objects/obmalloc.c
    _PyFloat_DebugMallocStats(out); // in Objects/dictobject.c, just calls _PyDebugAllocatorStats in Objects/obmalloc.c
    _PyFrame_DebugMallocStats(out); // etc.
    _PyList_DebugMallocStats(out);
    _PyTuple_DebugMallocStats(out); // in Objects/tupleobject.c, calls _PyDebugAllocatorStats in Objects/obmalloc.c for (i = 1; i < PyTuple_MAXSAVESIZE; i++)

Note that only dict, float, frame, list, tuple are reported.
"""
import contextlib
import difflib
import enum
import io
import pprint
import re
import sys
import typing

from pymemtrace import redirect_stdout


def get_debugmallocstats() -> bytes:
    """Invokes sys._debugmallocstats and captures the output as bytes."""
    stream = io.BytesIO()
    with redirect_stdout.stderr_redirector(stream):
        sys._debugmallocstats()
    return stream.getvalue()
    # return stream.getvalue().decode('ascii', 'replace')


# class DiffType(enum.Enum):
#     NDIFF = 1
#     CONTEXT = 2
#     UNIFIED = 3
#
#
# class DebugMallocStatsDiff:
#     """Class that acts as a context manager and takes a before and after snaphot of sys._debugmallocstats and
#     provides a simple textural diff."""
#     def __init__(self, diff_type: DiffType = DiffType.UNIFIED):
#         self.diff_type = diff_type
#         self.before: typing.Optional[bytes] = None
#         self.after: typing.Optional[bytes] = None
#         self.diff: typing.Optional[bytes] = None
#
#     def __enter__(self):
#         self.before = get_debugmallocstats()
#         return self
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.after = get_debugmallocstats()
#         if self.diff_type == DiffType.NDIFF:
#             self.diff = list(
#                 difflib.ndiff(
#                     self.before.decode('ascii').splitlines(keepends=False),
#                     self.after.decode('ascii').splitlines(keepends=False),
#                 )
#             )
#         elif self.diff_type == DiffType.CONTEXT:
#             self.diff = list(difflib.diff_bytes(difflib.context_diff, self.before.split(b'\n'), self.after.split(b'\n')))
#         elif self.diff_type == DiffType.UNIFIED:
#             self.diff = list(difflib.diff_bytes(difflib.unified_diff, self.before.split(b'\n'), self.after.split(b'\n')))
#         return False


#: In ``Object/obmalloc.c``:
#:
#: .. code-block:: text
#:
#:      #define POOL_SIZE               SYSTEM_PAGE_SIZE        /* must be 2^N */
#:
POOL_SIZE = 4096

#: In ``Object/obmalloc.c``:
#:
#: .. code-block:: text
#:
#:      #define POOL_OVERHEAD   _Py_SIZE_ROUND_UP(sizeof(struct pool_header), ALIGNMENT)
#:
#: TODO: We can calculate this from the sum of num_pools divided into '# bytes lost to pool headers'.
POOL_OVERHEAD = 48


class DebugMallocStat(typing.NamedTuple):
    """Represents a single line in the malloc stats section. For example:

    .. code-block:: text

        class   size   num pools   blocks in use  avail blocks
        -----   ----   ---------   -------------  ------------
            0     16           2             297           209

    Nomenclature is from ``_PyObject_DebugMallocStats(stderr))`` in ``Objects/obmalloc.c``

    Typical implementation:

    .. code-block:: c

        for (i = 0; i < numclasses; ++i) {
            size_t p = numpools[i];
            size_t b = numblocks[i];
            size_t f = numfreeblocks[i];
            uint size = INDEX2SIZE(i);
            if (p == 0) {
                assert(b == 0 && f == 0);
                continue;
            }
            fprintf(out, "%5u %6u "
                            "%11" PY_FORMAT_SIZE_T "u "
                            "%15" PY_FORMAT_SIZE_T "u "
                            "%13" PY_FORMAT_SIZE_T "u\\n",
                    i, size, p, b, f);
            allocated_bytes += b * size;
            available_bytes += f * size;
            pool_header_bytes += p * POOL_OVERHEAD;
            quantization += p * ((POOL_SIZE - POOL_OVERHEAD) % size);
        }
        fputc('\\n', out);

    """
    block_class: int
    size: int
    num_pools: int
    blocks_in_use: int
    avail_blocks: int

    # @property
    # def bytes_in_use(self)-> int:
    #     return self.size * self.num_pools * self.blocks_in_use

    @property
    def allocated_bytes(self) -> int:
        return self.blocks_in_use * self.size

    @property
    def available_bytes(self) -> int:
        return self.avail_blocks * self.size

    @property
    def pool_header_bytes(self) -> int:
        return self.num_pools * POOL_OVERHEAD

    @property
    def quantization(self) -> int:
        return self.num_pools * ((POOL_SIZE - POOL_OVERHEAD) % self.size)

    def __repr__(self):
        """Representation of self of the form:

        .. code-block:: text

                0     16           4             777           235

        """
        return f'{self.block_class:5d}  {self.size:5d}  {self.num_pools:10d}  {self.blocks_in_use:14d}  {self.avail_blocks:12d}'


def diff_debug_malloc_stat(a: DebugMallocStat, b: DebugMallocStat) -> str:
    """Takes two DebugMallocStat objects and returns a string with the difference.
    The string is of similar format to the input from ``sys._debugmallocstats``."""
    return (
        f'{b.block_class - a.block_class:+5d}'
        f'  {b.size - a.size:+5d}'
        f'  {b.num_pools - a.num_pools:+10d}'
        f'  {b.blocks_in_use - a.blocks_in_use:+14d}'
        f'  {b.avail_blocks - a.avail_blocks:+12d}')


#: Matches::
#:
#:      b'    0     16           2             294           212'
#:
#: Decomposed to extract the five integers.
RE_DEBUG_MALLOC_STATS_LINE = re.compile(rb'^\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$')


def last_value_as_int(line: bytes) -> int:
    """Returns that last value of the line such as:

    .. code-block:: text

        b'# arenas allocated total           =                2,033'

    """
    return int(line.split(b'=')[1].replace(b',', b''))


# Understanding the middle section.
# First arenas:
#
# From Object/obmalloc.c
# (void)printone(out, "# arenas allocated total", ntimes_arena_allocated);
# (void)printone(out, "# arenas reclaimed", ntimes_arena_allocated - narenas);
# (void)printone(out, "# arenas highwater mark", narenas_highwater);
# (void)printone(out, "# arenas allocated current", narenas);
#
# /* Total number of times malloc() called to allocate an arena. */
# static size_t ntimes_arena_allocated = 0;
# b'# arenas allocated total           =                2,033'
#
# /* High water mark (max value ever seen) for narenas_currently_allocated. */
# static size_t narenas_highwater = 0;
# b'# arenas highwater mark            =                   18'
#
# /* # of arenas actually allocated. */
# size_t narenas = 0;
# b'# arenas allocated current         =                   18'
#
# PyOS_snprintf(buf, sizeof(buf), "%" PY_FORMAT_SIZE_T "u arenas * %d bytes/arena", narenas, ARENA_SIZE);
# (void)printone(out, buf, narenas * ARENA_SIZE);
#
# b'18 arenas * 262144 bytes/arena     =            4,718,592'
# Simple calculation: 18 * 262144 = 4718592

#: Matches::
#:
#:      b'18 arenas * 262144 bytes/arena     =            4,718,592'
#:
#: Decomposed to extract the two integers, the total is computed.
RE_DEBUG_MALLOC_ARENAS_SUMMARY_LINE = re.compile(rb'^(\d+) arenas \* (\d+) bytes/arena\s+=\s+(.+)$')


class DebugMallocArenas:
    """Decomposes this::

        # arenas allocated total           =                2,033
        # arenas reclaimed                 =                2,015
        # arenas highwater mark            =                   18
        # arenas allocated current         =                   18
        18 arenas * 262144 bytes/arena     =            4,718,592

    Into values for: ntimes_arena_allocated, narenas, narenas_highwater, ARENA_SIZE.

    Infers: arenas_reclaimed, arenas_total.
    """
    def __init__(self, debug_malloc: bytes):
        for line in debug_malloc.splitlines(keepends=False):
            if line.startswith(b'# arenas allocated total'):
                # (void)printone(out, "# arenas allocated total", ntimes_arena_allocated);
                self.ntimes_arena_allocated = last_value_as_int(line)
            elif line.startswith(b'# arenas reclaimed'):
                # (void)printone(out, "# arenas reclaimed", ntimes_arena_allocated - narenas);
                pass
            elif line.startswith(b'# arenas highwater mark'):
                # (void)printone(out, "# arenas highwater mark", narenas_highwater);
                self.narenas_highwater = last_value_as_int(line)
            elif line.startswith(b'# arenas allocated current'):
                # (void)printone(out, "# arenas allocated current", narenas);
                self.narenas = last_value_as_int(line)
            else:
                m = RE_DEBUG_MALLOC_ARENAS_SUMMARY_LINE.match(line)
                if m:
                    # PyOS_snprintf(buf, sizeof(buf), "%" PY_FORMAT_SIZE_T "u arenas * %d bytes/arena", narenas, ARENA_SIZE);
                    # (void)printone(out, buf, narenas * ARENA_SIZE);
                    #
                    # b'18 arenas * 262144 bytes/arena     =            4,718,592'
                    # Simple calculation: 18 * 262144 = 4718592
                    self.arena_size = int(m.group(2))
        expected_attrs = ('ntimes_arena_allocated', 'narenas_highwater', 'narenas', 'arena_size')
        if not all(hasattr(self, name) for name in expected_attrs):
            raise ValueError(f'Can not find required attributes {expected_attrs}')

    @property
    def arenas_reclaimed(self) -> int:
        return self.ntimes_arena_allocated - self.narenas

    @property
    def arenas_total(self) -> int:
        return self.narenas * self.arena_size

    def __repr__(self):
        """Returns a string similar to sys._debugmallocstats."""
        ret= [
                f'# arenas allocated total           = {self.ntimes_arena_allocated:>20,d}',
                f'# arenas reclaimed                 = {self.arenas_reclaimed:>20,d}',
                f'# arenas highwater mark            = {self.narenas_highwater:>20,d}',
                f'# arenas allocated current         = {self.narenas:>20,d}',
            ]
        lhs = f'{self.narenas} arenas * {self.arena_size} bytes/arena'
        ret.append(f'{lhs:<34s} = {self.arenas_total:>20,d}')
        return '\n'.join(ret)


#: Matches::
#:
#:      b'63 unused pools * 4096 bytes       =              258,048'
#:
#: Decomposed to extract the two integers, the total is computed.
RE_DEBUG_MALLOC_POOLS_SUMMARY_LINE = re.compile(rb'^(\d+) unused pools \* (\d+) bytes\s+=\s+(.+)$')


class DebugMallocPoolsBlocks:
    """Decomposes this::

        # bytes in allocated blocks        =            4,280,848
        # bytes in available blocks        =               70,368
        63 unused pools * 4096 bytes       =              258,048
        # bytes lost to pool headers       =               52,272
        # bytes lost to quantization       =               57,056
        # bytes lost to arena alignment    =                    0
        Total                              =            4,718,592

    From Object/obmalloc.c::

        total = printone(out, "# bytes in allocated blocks", allocated_bytes);
        total += printone(out, "# bytes in available blocks", available_bytes);

        PyOS_snprintf(buf, sizeof(buf), "%u unused pools * %d bytes", numfreepools, POOL_SIZE);
        total += printone(out, buf, (size_t)numfreepools * POOL_SIZE);

        total += printone(out, "# bytes lost to pool headers", pool_header_bytes);
        total += printone(out, "# bytes lost to quantization", quantization);
        total += printone(out, "# bytes lost to arena alignment", arena_alignment);
        (void)printone(out, "Total", total);

    Extracts: allocated_bytes, available_bytes, numfreepools, POOL_SIZE, pool_header_bytes, quantization, arena_alignment.

    Infers: unused_pool_total, TOTAL.
    """
    def __init__(self, debug_malloc: bytes):
        for line in debug_malloc.splitlines(keepends=False):
            if line.startswith(b'# bytes in allocated blocks'):
                # total = printone(out, "# bytes in allocated blocks", allocated_bytes);
                self.allocated_bytes = last_value_as_int(line)
            elif line.startswith(b'# bytes in available blocks'):
                # total += printone(out, "# bytes in available blocks", available_bytes);
                self.available_bytes = last_value_as_int(line)
            elif line.startswith(b'# bytes lost to pool headers'):
                # total += printone(out, "# bytes lost to pool headers", pool_header_bytes);
                self.pool_header_bytes = last_value_as_int(line)
            elif line.startswith(b'# bytes lost to quantization'):
                # total += printone(out, "# bytes lost to quantization", quantization);
                self.quantization = last_value_as_int(line)
            elif line.startswith(b'# bytes lost to arena alignment'):
                # total += printone(out, "# bytes lost to arena alignment", arena_alignment);
                self.arena_alignment = last_value_as_int(line)
            else:
                m = RE_DEBUG_MALLOC_POOLS_SUMMARY_LINE.match(line)
                if m:
                    # PyOS_snprintf(buf, sizeof(buf), "%u unused pools * %d bytes", numfreepools, POOL_SIZE);
                    # total += printone(out, buf, (size_t)numfreepools * POOL_SIZE);
                    #
                    # 63 unused pools * 4096 bytes       =              258,048
                    # Simple calculation: 63 * 4096 = 258048
                    self.numfreepools = int(m.group(1))
                    self.pool_size = int(m.group(2))
        expected_attrs = (
        'allocated_bytes', 'available_bytes', 'pool_header_bytes', 'quantization', 'arena_alignment', 'numfreepools',
        'pool_size'
        )
        if not all(hasattr(self, name) for name in expected_attrs):
            raise ValueError(f'Can not find required attributes {expected_attrs}')

    @property
    def unused_pool_total(self) -> int:
        return self.numfreepools * self.pool_size

    @property
    def total(self) -> int:
        return self.allocated_bytes + self.available_bytes + self.unused_pool_total + self.pool_header_bytes \
               + self.quantization + self.arena_alignment

    def __repr__(self):
        """Returns a string similar to sys._debugmallocstats."""
        ret = [
            f'# bytes in allocated blocks        = {self.allocated_bytes:>20,d}',
            f'# bytes in available blocks        = {self.available_bytes:>20,d}',
        ]
        lhs = f'{self.numfreepools} unused pools * {self.pool_size} bytes'
        ret.append(f'{lhs:<34s} = {self.unused_pool_total:>20,d}')
        ret.extend([
            f'# bytes lost to pool headers       = {self.pool_header_bytes:>20,d}',
            f'# bytes lost to quantization       = {self.quantization:>20,d}',
            f'# bytes lost to arena alignment    = {self.arena_alignment:>20,d}',
            f'Total                              = {self.total:>20,d}',
        ])
        return '\n'.join(ret)


class DebugTypeStat(typing.NamedTuple):
    """Represents a single line from ``sys._debugmallocstats``.

    Decomposed from a line such as:

    .. code-block:: text

        4 free PyCFunctionObjects * 56 bytes each =                  224

    See ``_PyObject_DebugTypeStats(stderr);`` in ``Objects/obmalloc.c``
    """
    free_count: int
    object_type: str
    bytes_each: int
    bytes_total: int

    def __repr__(self):
        """Returns a string of the form:

        .. code-block:: text

                   4 free PyCFunctionObjects * 56 bytes each =                  224
                        9 free PyDictObjects * 48 bytes each =                  432
                       5 free PyFloatObjects * 24 bytes each =                  120
                      0 free PyFrameObjects * 368 bytes each =                    0
                       80 free PyListObjects * 40 bytes each =                3,200
                      8 free PyMethodObjects * 48 bytes each =                  384
               7 free 1-sized PyTupleObjects * 32 bytes each =                  224
              52 free 2-sized PyTupleObjects * 40 bytes each =                2,080
               1 free 3-sized PyTupleObjects * 48 bytes each =                   48
             0 free 10-sized PyTupleObjects * 104 bytes each =                    0

        """
        lhs = f'{self.free_count} free {self.object_type} * {self.bytes_each} bytes each'
        return f'{lhs:>48s} = {self.bytes_total:>20,d}'


#: Matches::
#:
#:      b'   34 free 2-sized PyTupleObjects * 40 bytes each =                1,360'
#:
#: NOTE: commas in last value caused by printone() in Object/obmalloc.c
#: printone is used in many places where there is message = value such as memory pool totals and type memory information.
RE_DEBUG_MALLOC_TYPE_LINE = re.compile(rb'^\s*(\d+) free (.+?) \* (\d+) bytes each =\s+(.+)$')


#: Matches::
#:
#:      b'Small block threshold = 512, in 32 size classes.'
#:
#: Decomposed to extract the two integers.
RE_DEBUG_MALLOC_HEADER_LINE = re.compile(rb'^Small block threshold = (\d+), in (\d+) size classes\.$')


class SysDebugMallocStats:
    """This decomposes the output of ``sys._debugmallocstats`` into these areas:

    - A list of malloc stats showing the pools and blocks.
    - Descriptions of arenas.
    - Descriptions of pools and blocks.
    - A list of malloc usage by (some) types.

    This class takes a snapshot of the debug malloc stats from ``sys._debugmallocstats``.
    Importantly it can identify the difference between two snapshots.
    """
    def __init__(self, debug_malloc: bytes = b''):
        """Constructor, this optionally takes a bytes object for testing.
        If nothing supplied this gets the bytes object from sys._debugmallocstats.
        """
        self.malloc_stats: typing.List[DebugMallocStat] = []
        self.type_stats: typing.List[DebugTypeStat] = []
        # Used for lookup by type
        self.type_map: typing.Dict[bytes, int] = {}
        if not debug_malloc:
            debug_malloc: bytes = get_debugmallocstats()
        for line in debug_malloc.splitlines(keepends=False):
            m = RE_DEBUG_MALLOC_STATS_LINE.match(line)
            if m:
                self.malloc_stats.append(DebugMallocStat(*[int(v) for v in m.groups()]))
            else:
                m = RE_DEBUG_MALLOC_TYPE_LINE.match(line)
                if m:
                    self.type_map[m.group(2)] = len(self.type_stats)
                    self.type_stats.append(DebugTypeStat(
                            int(m.group(1)), m.group(2).decode('ascii'), int(m.group(3)),
                            int(m.group(4).replace(b',', b''))
                        ))
                else:
                    m = RE_DEBUG_MALLOC_HEADER_LINE.match(line)
                    if m:
                        self.small_block_threshold = int(m.group(1))
                        self.size_classes = int(m.group(2))
        self.arenas = DebugMallocArenas(debug_malloc)
        self.pools_blocks = DebugMallocPoolsBlocks(debug_malloc)
        expected_attrs = ('small_block_threshold', 'size_classes')
        if not all(hasattr(self, name) for name in expected_attrs):
            raise ValueError(f'Can not find required attributes {expected_attrs}')

    def __repr__(self):
        """Representation of self similar to the output of sys._debugmallocstats"""
        results = [
            f'Small block threshold = {self.small_block_threshold}, in {self.size_classes} size classes.',
            '',
            'class   size   num pools   blocks in use  avail blocks',
            '-----   ----   ---------   -------------  ------------',
        ]
        for stat in self.malloc_stats:
            results.append(repr(stat))
        results.append('')
        results.append(repr(self.arenas))
        results.append('')
        results.append(repr(self.pools_blocks))
        results.append('')
        for stat in self.type_stats:
            results.append(repr(stat))
        # Terminate with a '\n'
        results.append('')
        return '\n'.join(results)


# def debugmallocstats_to_malloc_blocks() -> typing.List[DebugMallocStats]:
#     debug_malloc: bytes = get_debugmallocstats()
#     ret = []
#     for line in debug_malloc.splitlines(keepends=False):
#         m = RE_DEBUG_MALLOC_STATS_LINE.match(line)
#         if m:
#             ret.append(DebugMallocStats(*[int(v) for v in m.groups()]))
#     return ret


def diff_debugmallocstats(a_stats: SysDebugMallocStats, b_stats: SysDebugMallocStats):
    """
    This takes two SysDebugMallocStats objects and identifies what is different between them.
    """
    ret: typing.List[str] = []
    # TODO: Header?

    # Firstly the DebugMallocStat list
    if len(a_stats.malloc_stats) != len(b_stats.malloc_stats):
        raise ValueError(
            f'Malloc stats length  mismatch {len(a_stats.malloc_stats)} != {len(b_stats.malloc_stats)}'
        )
    for a, b in zip(a_stats.malloc_stats, b_stats.malloc_stats):
        if a != b:
            ret.append(diff_debug_malloc_stat(a, b))
    # Firstly the DebugTypeStat objects, the lists might not be the same.


def main():
    print('sys._debugmallocstats()')
    print(get_debugmallocstats().decode('ascii'))

    print()
    dms = SysDebugMallocStats()
    print(repr(dms))
    return 0


if __name__ == '__main__':
    sys.exit(main())
