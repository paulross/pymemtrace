import pytest

from pymemtrace import debug_malloc_stats


def test_get_debugmallocstats():
    result = debug_malloc_stats.get_debugmallocstats()
    assert isinstance(result, bytes)

@pytest.mark.parametrize(
    'line, expected',
    (
        (
            b'    0     16           2             294           212',
            (b'0', b'16', b'2', b'294', b'212'  ),
        ),
    ),
)
def test_re_debug_malloc_stats_line(line, expected):
    m = debug_malloc_stats.RE_DEBUG_MALLOC_STATS_LINE.match(line)
    assert m is not None
    assert m.groups() == expected


@pytest.mark.parametrize(
    'line, expected',
    (
        (b'# arenas allocated total           =                2,033', 2033),
    ),
)
def test_last_value_as_int(line, expected):
    result = debug_malloc_stats.last_value_as_int(line)
    assert result == expected


@pytest.mark.parametrize(
    'line, expected',
    (
        (
                b'18 arenas * 262144 bytes/arena     =            4,718,592',
            (b'18', b'262144', b'4,718,592'),
        ),
    ),
)
def test_re_debug_malloc_arenas_summary_line(line, expected):
    m = debug_malloc_stats.RE_DEBUG_MALLOC_ARENAS_SUMMARY_LINE.match(line)
    assert m is not None
    assert m.groups() == expected


@pytest.mark.parametrize(
    'line, expected',
    (
        (
            b'63 unused pools * 4096 bytes       =              258,048',
            (b'63', b'4096', b'258,048'),
        ),
    ),
)
def test_re_debug_malloc_pools_summary_line(line, expected):
    m = debug_malloc_stats.RE_DEBUG_MALLOC_POOLS_SUMMARY_LINE.match(line)
    assert m is not None
    assert m.groups() == expected


@pytest.mark.parametrize(
    'line, expected',
    (
        (
            b'   34 free 2-sized PyTupleObjects * 40 bytes each =                1,360',
            (b'34', b'2-sized PyTupleObjects', b'40', b'1,360'),
        ),
    ),
)
def test_re_debug_malloc_type_line(line, expected):
    m = debug_malloc_stats.RE_DEBUG_MALLOC_TYPE_LINE.match(line)
    assert m is not None
    assert m.groups() == expected


@pytest.mark.parametrize(
    'line, expected',
    (
        (
            b'Small block threshold = 512, in 32 size classes.',
            (b'512', b'32',),
        ),
    ),
)
def test_re_debug_malloc_header_line(line, expected):
    m = debug_malloc_stats.RE_DEBUG_MALLOC_HEADER_LINE.match(line)
    assert m is not None
    assert m.groups() == expected


@pytest.mark.parametrize(
    'args, expected',
    (
        ((0, 16, 4, 777, 235), 777 * 16),
    ),
)
def test_class_debugmallocstats_allocated_bytes(args, expected):
    dms = debug_malloc_stats.DebugMallocStat(*args)
    assert dms.allocated_bytes == expected


@pytest.mark.parametrize(
    'args, expected',
    (
        ((0, 16, 4, 777, 235), 235 * 16),
    ),
)
def test_class_debugmallocstats_available_bytes(args, expected):
    dms = debug_malloc_stats.DebugMallocStat(*args)
    assert dms.available_bytes == expected


@pytest.mark.parametrize(
    'args, expected',
    (
        ((0, 16, 4, 777, 235), 4 * debug_malloc_stats.POOL_OVERHEAD),
    ),
)
def test_class_debugmallocstats_pool_header_bytes(args, expected):
    dms = debug_malloc_stats.DebugMallocStat(*args)
    assert dms.pool_header_bytes == expected


@pytest.mark.parametrize(
    'args, expected',
    (
        ((0, 16, 4, 777, 235), 0),
    ),
)
def test_class_debugmallocstats_quantization(args, expected):
    dms = debug_malloc_stats.DebugMallocStat(*args)
    assert dms.quantization == expected


@pytest.mark.parametrize(
    'args, expected',
    (
        ((0, 16, 2, 297, 209), '    0     16           2             297           209'),
    ),
)
def test_class_debugmallocstats_repr(args, expected):
    dms = debug_malloc_stats.DebugMallocStat(*args)
    assert repr(dms) == expected


SYS_DEBUGMALLOCSTATS_EXAMPLE = b"""Small block threshold = 512, in 32 size classes.

class   size   num pools   blocks in use  avail blocks
-----   ----   ---------   -------------  ------------
    0     16           2             297           209
    1     32           9            1131             3
    2     48          58            4788            84
    3     64         303           19065            24
    4     80         214           10672            28
    5     96          36            1507             5
    6    112          19             659            25
    7    128          16             478            18
    8    144          70            1944            16
    9    160          12             292             8
   10    176         116            2665             3
   11    192           6             123             3
   12    208          30             555            15
   13    224          55             982             8
   14    240          10             149            11
   15    256           8             116             4
   16    272           4              45            11
   17    288           4              49             7
   18    304          25             321             4
   19    320           3              29             7
   20    336           3              26            10
   21    352           2              21             1
   22    368           3              30             3
   23    384           3              24             6
   24    400           4              35             5
   25    416           9              67            14
   26    432          10              78            12
   27    448           8              69             3
   28    464           8              57             7
   29    480           6              43             5
   30    496           7              53             3
   31    512          33             228             3

# arenas allocated total           =                2,034
# arenas reclaimed                 =                2,016
# arenas highwater mark            =                   18
# arenas allocated current         =                   18
18 arenas * 262144 bytes/arena     =            4,718,592

# bytes in allocated blocks        =            4,310,720
# bytes in available blocks        =               68,704
56 unused pools * 4096 bytes       =              229,376
# bytes lost to pool headers       =               52,608
# bytes lost to quantization       =               57,184
# bytes lost to arena alignment    =                    0
Total                              =            4,718,592

       4 free PyCFunctionObjects * 56 bytes each =                  224
            3 free PyDictObjects * 48 bytes each =                  144
           5 free PyFloatObjects * 24 bytes each =                  120
          0 free PyFrameObjects * 368 bytes each =                    0
           23 free PyListObjects * 40 bytes each =                  920
          7 free PyMethodObjects * 48 bytes each =                  336
   3 free 1-sized PyTupleObjects * 32 bytes each =                   96
  54 free 2-sized PyTupleObjects * 40 bytes each =                2,160
   5 free 3-sized PyTupleObjects * 48 bytes each =                  240
   5 free 4-sized PyTupleObjects * 56 bytes each =                  280
   3 free 5-sized PyTupleObjects * 64 bytes each =                  192
   4 free 6-sized PyTupleObjects * 72 bytes each =                  288
  11 free 7-sized PyTupleObjects * 80 bytes each =                  880
  10 free 8-sized PyTupleObjects * 88 bytes each =                  880
   4 free 9-sized PyTupleObjects * 96 bytes each =                  384
 0 free 10-sized PyTupleObjects * 104 bytes each =                    0
 1 free 11-sized PyTupleObjects * 112 bytes each =                  112
 2 free 12-sized PyTupleObjects * 120 bytes each =                  240
 0 free 13-sized PyTupleObjects * 128 bytes each =                    0
 1 free 14-sized PyTupleObjects * 136 bytes each =                  136
 0 free 15-sized PyTupleObjects * 144 bytes each =                    0
 1 free 16-sized PyTupleObjects * 152 bytes each =                  152
 2 free 17-sized PyTupleObjects * 160 bytes each =                  320
 1 free 18-sized PyTupleObjects * 168 bytes each =                  168
 2 free 19-sized PyTupleObjects * 176 bytes each =                  352
"""

def test_class_sysdebugmallocstats_sys_debugmallocstats_example():
    sdms = debug_malloc_stats.SysDebugMallocStats(SYS_DEBUGMALLOCSTATS_EXAMPLE)
    assert sdms is not None


def test_class_sysdebugmallocstats_sys_debugmallocstats_example_repr():
    sdms = debug_malloc_stats.SysDebugMallocStats(SYS_DEBUGMALLOCSTATS_EXAMPLE)
    # print()
    # print(SYS_DEBUGMALLOCSTATS_EXAMPLE)
    # print(repr(sdms).encode('ascii'))
    assert bytes(repr(sdms).encode('ascii')) == SYS_DEBUGMALLOCSTATS_EXAMPLE
