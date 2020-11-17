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
import io
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


#: In ``Object/obmalloc.c``:
#:
#: .. code-block:: text
#:
#:      #define POOL_SIZE               SYSTEM_PAGE_SIZE        /* must be 2^N */
#:
POOL_SIZE = 4096

#: This value is initially approximate.
#: In ``Object/obmalloc.c``:
#:
#: .. code-block:: c
#:
#:      #define POOL_OVERHEAD   _Py_SIZE_ROUND_UP(sizeof(struct pool_header), ALIGNMENT)
#:
#: We can calculate this from the sum of num_pools divided into ``'# bytes lost to pool headers'``.
#: This is done whenever a :py:class:`SysDebugMallocStats` is created.
POOL_OVERHEAD = 48


class DebugMallocStat(typing.NamedTuple):
    """Represents a single line in the malloc stats section. For example:

    .. code-block:: text

        class   size   num pools   blocks in use  avail blocks
        -----   ----   ---------   -------------  ------------
            0     16           2             297           209

    Nomenclature is from ``_PyObject_DebugMallocStats(stderr))`` in ``Objects/obmalloc.c``.
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
    if a.block_class != b.block_class:
        raise ValueError(f'a.block_class != b.block_class: {a.block_class} != {b.block_class}')
    if a.size != b.size:
        raise ValueError(f'a.size != b.size: {a.size} != {b.size}')
    return (
        f'{a.block_class:5d}'
        f'  {a.size:5d}'
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

    From Object/obmalloc.c:

    .. code-block:: c

        (void)printone(out, "# arenas allocated total", ntimes_arena_allocated);
        (void)printone(out, "# arenas reclaimed", ntimes_arena_allocated - narenas);
        (void)printone(out, "# arenas highwater mark", narenas_highwater);
        (void)printone(out, "# arenas allocated current", narenas);

        /* Total number of times malloc() called to allocate an arena. */
        static size_t ntimes_arena_allocated = 0;
        // b'# arenas allocated total           =                2,033'

        /* High water mark (max value ever seen) for narenas_currently_allocated. */
        static size_t narenas_highwater = 0;
        // b'# arenas highwater mark            =                   18'

        /* # of arenas actually allocated. */
        size_t narenas = 0;
        // b'# arenas allocated current         =                   18'

        PyOS_snprintf(buf, sizeof(buf), "%" PY_FORMAT_SIZE_T "u arenas * %d bytes/arena", narenas, ARENA_SIZE);
        (void)printone(out, buf, narenas * ARENA_SIZE);
        // b'18 arenas * 262144 bytes/arena     =            4,718,592'
        // Simple calculation: 18 * 262144 = 4718592

    """
    def __init__(self, debug_malloc: bytes):
        """Constructor, decomposes this:

        .. code-block:: text

            # arenas allocated total        -> self.ntimes_arena_allocated
            # arenas reclaimed              -> self.arenas_reclaimed
            # arenas highwater mark         -> self.narenas_highwater
            # arenas allocated current      -> self.narenas
            18 arenas * 262144 bytes/arena  -> self.narenas * self.arena_size  = self.arenas_total

        """
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

    def pool_overhead(self, num_pools: int) -> int:
        """Returns the POOL_OVERHEAD as self.pool_header_bytes // the number of pools.

        self.pool_header_bytes comes from::

            # bytes lost to pool headers       =               51,264

        Number of pools comes from the sum of ``num pools`` from DebugMallocStat.num_pools
        """
        return self.pool_header_bytes // num_pools

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
        """Returns a string of the form of these lines:

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


def diff_debug_type_stat(a: DebugTypeStat, b: DebugTypeStat) -> str:
    """Takes two DebugMallocStat objects and returns a string with the difference.
    The string is of similar format to the input from ``sys._debugmallocstats``."""
    if a.object_type != b.object_type:
        raise ValueError(f'a.object_type != b.object_type: {a.object_type} != {b.object_type}')
    if a.bytes_each != b.bytes_each:
        raise ValueError(f'a.bytes_each != b.bytes_each: {a.bytes_each} != {b.bytes_each}')
    lhs = f'{b.free_count - a.free_count:+d} free {a.object_type} * {a.bytes_each} bytes each'
    return f'{lhs:>48s} = {b.bytes_total - a.bytes_total:>+20,d}'


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
        # Set the global POOL_OVERHEAD by combining malloc_stats and pools_blocks
        num_pools = sum(v.num_pools for v in self.malloc_stats)
        pool_overhead = self.pools_blocks.pool_overhead(num_pools)
        global POOL_OVERHEAD
        POOL_OVERHEAD = pool_overhead

    def object_types(self) -> typing.KeysView[bytes]:
        """Return all the known object types."""
        return self.type_map.keys()

    def has_object_type(self, object_type: bytes):
        """Return True if the object type is present."""
        return object_type in self.type_map

    def type_stat(self, object_type: bytes) -> DebugTypeStat:
        """Return the DebugTypeStat for the named object type.
        May raise an KeyError if the object_type doe not exist."""
        return self.type_stats[self.type_map[object_type]]

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
    The diff is a list of lines of identical form to :py:meth:`sys._debugmallocstats` with '+' or '-' where appropriate.
    Lines that are the same are omitted.
    """
    ret: typing.List[str] = []
    has_header = False

    # Firstly the DebugMallocStat list
    if len(a_stats.malloc_stats) != len(b_stats.malloc_stats):
        raise ValueError(
            f'Malloc stats length  mismatch {len(a_stats.malloc_stats)} != {len(b_stats.malloc_stats)}'
        )
    for a, b in zip(a_stats.malloc_stats, b_stats.malloc_stats):
        if a != b:
            if not has_header:
                ret.append('class   size   num pools   blocks in use  avail blocks')
                ret.append('-----   ----   ---------   -------------  ------------')
                has_header = True
            ret.append(diff_debug_malloc_stat(a, b))
    has_header = False
    # Central two blocks
    # Arenas
    block = []
    if b_stats.arenas.ntimes_arena_allocated != a_stats.arenas.ntimes_arena_allocated:
        block.append(
            f'# arenas allocated total           ='
            f' {b_stats.arenas.ntimes_arena_allocated - a_stats.arenas.ntimes_arena_allocated:>+20,d}'
        )
    if b_stats.arenas.arenas_reclaimed != a_stats.arenas.arenas_reclaimed:
        block.append(
            f'# arenas reclaimed                 ='
            f' {b_stats.arenas.arenas_reclaimed - a_stats.arenas.arenas_reclaimed:>+20,d}'
        )
    if b_stats.arenas.narenas_highwater != a_stats.arenas.narenas_highwater:
        block.append(
            f'# arenas highwater mark            ='
            f' {b_stats.arenas.narenas_highwater - a_stats.arenas.narenas_highwater:>+20,d}'
        )
    assert a_stats.arenas.arena_size == b_stats.arenas.arena_size
    if b_stats.arenas.narenas != a_stats.arenas.narenas:
        block.append(
            f'# arenas allocated current         ='
            f' {b_stats.arenas.narenas - a_stats.arenas.narenas:>+20,d}'
        )
        lhs = f'{b_stats.arenas.narenas - a_stats.arenas.narenas:+d} arenas * {a_stats.arenas.arena_size} bytes/arena'
        block.append(f'{lhs:<34s} = {b_stats.arenas.arenas_total - a_stats.arenas.arenas_total:>+20,d}')
    if block:
        ret.append('')
        ret.extend(block)
    # Pools and blocks
    block = []
    assert a_stats.pools_blocks.pool_size == b_stats.pools_blocks.pool_size
    if b_stats.pools_blocks.allocated_bytes != a_stats.pools_blocks.allocated_bytes:
        block.append(
            f'# bytes in allocated blocks        ='
            f' {b_stats.pools_blocks.allocated_bytes - a_stats.pools_blocks.allocated_bytes:>+20,d}'
        )
    if b_stats.pools_blocks.available_bytes != a_stats.pools_blocks.available_bytes:
        block.append(
            f'# bytes in available blocks        ='
            f' {b_stats.pools_blocks.available_bytes - a_stats.pools_blocks.available_bytes:>+20,d}'
        )
    if b_stats.pools_blocks.numfreepools != a_stats.pools_blocks.numfreepools:
        lhs = (
            f'{b_stats.pools_blocks.numfreepools - a_stats.pools_blocks.numfreepools}'
            f' unused pools * {a_stats.pools_blocks.pool_size} bytes'
        )
        block.append(
            f'{lhs:<34s} = {b_stats.pools_blocks.unused_pool_total - a_stats.pools_blocks.unused_pool_total:>+20,d}'
        )
    if b_stats.pools_blocks.pool_header_bytes != a_stats.pools_blocks.pool_header_bytes:
        block.append(
            f'# bytes lost to pool headers       ='
            f' {b_stats.pools_blocks.pool_header_bytes - a_stats.pools_blocks.pool_header_bytes:>+20,d}'
        )
    if b_stats.pools_blocks.quantization != a_stats.pools_blocks.quantization:
        block.append(
            f'# bytes lost to quantization       ='
            f' {b_stats.pools_blocks.quantization - a_stats.pools_blocks.quantization:>+20,d}'
        )
    if b_stats.pools_blocks.arena_alignment != a_stats.pools_blocks.arena_alignment:
        block.append(
            f'# bytes lost to arena alignment    ='
            f' {b_stats.pools_blocks.arena_alignment - a_stats.pools_blocks.arena_alignment:>+20,d}'
        )
    if b_stats.pools_blocks.total != a_stats.pools_blocks.total:
        block.append(
            f'Total                              = {b_stats.pools_blocks.total - a_stats.pools_blocks.total:>+20,d}'
        )
    if block:
        ret.append('')
        ret.extend(block)
    has_header = False
    # The DebugTypeStat objects, the lists might not be the same.
    union_object_types = set(a_stats.object_types()) | set(b_stats.object_types())
    for object_type in sorted(union_object_types):
        diff_str = ''
        if a_stats.has_object_type(object_type):
            if b_stats.has_object_type(object_type):
                if a_stats.type_stat(object_type) != b_stats.type_stat(object_type):
                    diff_str = diff_debug_type_stat(a_stats.type_stat(object_type), b_stats.type_stat(object_type))
            else:
                # a only so dropped
                diff_str = f'-{a_stats.type_stat(object_type)!r}'
        else:
            # b only so added
            diff_str = f'+{a_stats.type_stat(object_type)!r}'
        if diff_str:
            if not has_header:
                ret.append('')
                has_header = True
            ret.append(diff_str)
    return ret


class DiffSysDebugMallocStats:
    """Context manager that compares two snapshots of ``sys._getdebugmallocstats()`` and can provide a diff between
    them."""
    def __init__(self):
        self.before: typing.Optional[SysDebugMallocStats] = None
        self.after: typing.Optional[SysDebugMallocStats] = None
        self._diff: typing.Optional[str] = None

    def __enter__(self):
        """Enters the context manager taking a snapshot of ``sys._getdebugmallocstats()``."""
        self.before = SysDebugMallocStats()
        self.after = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exits the context manager taking a snapshot of ``sys._getdebugmallocstats()``."""
        self.after = SysDebugMallocStats()
        return False

    def diff(self) -> str:
        """Returns the difference between two snapshots."""
        if self.before is None:
            raise RuntimeError('Context manager not entered.')
        if self.after is None:
            raise RuntimeError('Context manager not exited.')
        return '\n'.join(diff_debugmallocstats(self.before, self.after))


def main():
    print('sys._debugmallocstats()')
    print(get_debugmallocstats().decode('ascii'))

    print()
    # dms_a = SysDebugMallocStats()
    # # print(repr(dms_a))
    # l = []
    # l.append({})
    # l.append(set())
    # l.append((1, 2, 3))
    # for i in range(80):
    #     l.append(tuple(list(range(4))))
    # dms_b = SysDebugMallocStats()
    #
    # # pprint.pprint(diff_debugmallocstats(dms_a, dms_b))
    # print('\n'.join(diff_debugmallocstats(dms_a, dms_b)))

    print(f'POOL_OVERHEAD {POOL_OVERHEAD}')

    with DiffSysDebugMallocStats() as diff_dms:
        l = []
        l.append({})
        l.append(set())
        l.append((1, 2, 3))
        for i in range(80):
            l.append(tuple(list(range(4))))
    print(f'POOL_OVERHEAD {POOL_OVERHEAD}')
    print(diff_dms.diff())

    return 0


if __name__ == '__main__':
    sys.exit(main())
