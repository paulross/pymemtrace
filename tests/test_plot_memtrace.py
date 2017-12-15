
import io 

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
        Coord.Dim(256 + 16, 'mm'), # .width, x, to right
        Coord.Dim(512 + 16, 'mm'), # .depth, y, down.
    )
    data_min = pymemtrace.CallReturnData(8.0, 512.0)
    data_max = pymemtrace.CallReturnData(16.0, 1024.0)
    result = plot_memtrace.compute_offsets_scales(viewport, margins, data_min, data_max)
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
    assert Coord.dim_from_offset_scale(16, result['time']) == Coord.Dim(256+16, 'mm')
    assert Coord.dim_from_offset_scale(512.0, result['memory']) == Coord.Dim(8, 'mm')
    assert Coord.dim_from_offset_scale(1024.0, result['memory']) == Coord.Dim(512+16, 'mm')

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
