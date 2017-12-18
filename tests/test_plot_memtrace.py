
import io
import pprint

from pymemtrace import pymemtrace
from pymemtrace import plot_memtrace
from pymemtrace.plot import Coord

def test_compute_offsets_scales():
    margins = {
        'top'       : Coord.Dim(8, 'mm'),
        'bottom'    : Coord.Dim(8, 'mm'),
        'left'      : Coord.Dim(8, 'mm'),
        'right'     : Coord.Dim(8, 'mm'),
    }
    viewport = Coord.Box(
        Coord.Dim(256 + 16, 'mm'), # Memory: .width, x, to right
        Coord.Dim(512 + 16, 'mm'), # Time: .depth, y, down.
    )
    data_min = pymemtrace.CallReturnData(8.0, 512.0)
    data_max = pymemtrace.CallReturnData(16.0, 1024.0)
    result = plot_memtrace.compute_offsets_scales(viewport, margins, data_min, data_max)
    # Expected:
    # Memory:
    #    scale is (272mm - 8mm - 8mm) / (1024 - 512) == 256mm / 512 == 0.5mm/byte
    #    offset is 8mm - 512 * 0.5mm/byte == 8mm - 256mm == 248mm
    # Time:
    #    scale is (272mm - 8mm - 8mm) / (16 - 8) == 256mm / 8 == 64mm/second
    #    offset is 8mm - 8 * 64mm/second == 8mm - 512mm == -504mm
    assert result == {
        'memory': Coord.OffsetScale(
            offset=Coord.Dim(value=-248.0, units='mm'),
            scale=Coord.Dim(value=0.5, units='mm')
        ),
        'time': Coord.OffsetScale(
            offset=Coord.Dim(value=-504.0, units='mm'),
            scale=Coord.Dim(value=64.0, units='mm')
        ),
    }
    assert Coord.dim_from_offset_scale(8, result['time']) == Coord.Dim(8, 'mm')
    assert Coord.dim_from_offset_scale(16, result['time']) == Coord.Dim(512+8, 'mm')
    assert Coord.dim_from_offset_scale(512.0, result['memory']) == Coord.Dim(8, 'mm')
    assert Coord.dim_from_offset_scale(1024.0, result['memory']) == Coord.Dim(256+8, 'mm')

def test_best_tick():
    # best_tick(largest, most_ticks)
    assert plot_memtrace.best_tick(10.0, 10) == 1
    assert plot_memtrace.best_tick(10.0, 5) == 2
    assert plot_memtrace.best_tick(200.0, 5) == 50


def test_plot_memtrace_MemTrace_simple():
    mt = pymemtrace.MemTrace()
    # Add a couple of sequential functions
    mt.add_data_point('filename', 'parent', 12, 'call', pymemtrace.CallReturnData(0.1, 1000))
    mt.add_data_point('filename', 'parent', 12, 'return', pymemtrace.CallReturnData(0.2, 1000))
    mt.add_data_point('filename', 'child', 15, 'call', pymemtrace.CallReturnData(0.2, 1000))
    mt.add_data_point('filename', 'child', 15, 'return', pymemtrace.CallReturnData(0.6, 4000))
    mt.finalise()
    print()
    print('mt.data_initial:', mt.data_initial)
    print('    mt.data_min:', mt.data_min)
    print('    mt.data_max:', mt.data_max)
    print('  mt.data_final:', mt.data_final)
    fobj = io.StringIO()
    plot_memtrace.plot_memtrace_to_file(mt, fobj)
    print()
    print(fobj.getvalue())

def test_plot_memtrace_MemTrace_depth_two():
    mt = pymemtrace.MemTrace()
    # Add a couple of sequential functions
    # See notebook for 2017-12-17 +2
    mt.add_data_point('filename', 'f0', 12, 'call',     pymemtrace.CallReturnData(0.0, 1000))
    mt.add_data_point('filename', 'f00', 15, 'call',    pymemtrace.CallReturnData(1.0, 6000))
    mt.add_data_point('filename', 'f00', 15, 'return',  pymemtrace.CallReturnData(3.0, 9000))
    mt.add_data_point('filename', 'f01', 20, 'call',    pymemtrace.CallReturnData(5.0, 9000))
    mt.add_data_point('filename', 'f01', 20, 'return',  pymemtrace.CallReturnData(6.0, 5000))
    mt.add_data_point('filename', 'f0', 12, 'return',   pymemtrace.CallReturnData(7.0, 4000))
    mt.finalise()
    expected_depth = [
        pymemtrace.WidthDepthEventFunctionData(width=0, depth=0, event='call', function_id=0, data=pymemtrace.CallReturnData(time=0.0, memory=1000)),
        pymemtrace.WidthDepthEventFunctionData(width=0, depth=1, event='call', function_id=1, data=pymemtrace.CallReturnData(time=1.0, memory=6000)),
        pymemtrace.WidthDepthEventFunctionData(width=0, depth=1, event='return', function_id=1, data=pymemtrace.CallReturnData(time=3.0, memory=9000)),
        pymemtrace.WidthDepthEventFunctionData(width=0, depth=1, event='call', function_id=2, data=pymemtrace.CallReturnData(time=5.0, memory=9000)),
        pymemtrace.WidthDepthEventFunctionData(width=0, depth=1, event='return', function_id=2, data=pymemtrace.CallReturnData(time=6.0, memory=5000)),
        pymemtrace.WidthDepthEventFunctionData(width=0, depth=0, event='return', function_id=0, data=pymemtrace.CallReturnData(time=7.0, memory=4000)),
    ]
    print()
    print('mt.data_initial:', mt.data_initial)
    print('    mt.data_min:', mt.data_min)
    print('    mt.data_max:', mt.data_max)
    print('  mt.data_final:', mt.data_final)
    pprint.pprint(list(mt.function_tree_seq.gen_depth_first()))
    fobj = io.StringIO()
    plot_memtrace.plot_memtrace_to_file(mt, fobj)
    print()
    print(fobj.getvalue())
