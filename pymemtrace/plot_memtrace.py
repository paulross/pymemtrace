#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# MIT License
#
# Copyright (c) 2017 paulross
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Paul Ross: apaulross@gmail.com

'''
This plots the results of a pymemtrace.MemTrace object in SVG
'''
import collections
import math
import pprint

# from pymemtrace import MemTrace
from pymemtrace import pymemtrace
from pymemtrace.plot import Coord
from pymemtrace.plot import SVGWriter
from pymemtrace.plot import XmlWrite

MARGINS_ABS = {
    'top'       : Coord.Dim(8, 'mm').convert(None),
    'bottom'    : Coord.Dim(8, 'mm').convert(None),
    'left'      : Coord.Dim(8, 'mm').convert(None),
    'right'     : Coord.Dim(8, 'mm').convert(None),
}

MARGIN_KEYS = tuple(MARGINS_ABS.keys())
MARGIN_AXIS = Coord.Dim(8, 'mm').convert(None) # Allow for axis text as well
MARGIN_FROM_AXIS = Coord.Dim(4, 'mm').convert(None)

def get_viewport():
    view_port = Coord.Box(
        Coord.Dim(200, 'mm').convert(None), # .width, x, to right
        Coord.Dim(400, 'mm').convert(None), # .depth, y, down.
    )
    return view_port

def plot_margins():
    """
    Returns a dict of margins for the main plot area.
    """
    return {k : (MARGINS_ABS[k] + MARGIN_AXIS + MARGIN_FROM_AXIS) for k in MARGIN_KEYS}

def compute_offsets_scales(viewport, margins, data_min, data_max):
    """
    Returns a dict of Coord.OffsetScale for keys 'time' and 'memory' from the
    data in the MemTrace object. ``margins`` is a dict of margins:
    ``{position : Coord.Dim(), ...}`` where ``position`` is 'top', 'bottom',
    'left', 'right'.
    """
    result = {
        # coord_min, coord_max, value_min, value_max
        'time' : Coord.offset_scale(
            margins['top'],
            viewport.depth - margins['bottom'],
            data_min.time,
            data_max.time,
        ),
        'memory' : Coord.offset_scale(
            margins['left'],
            viewport.width - margins['right'],
            data_min.memory,
            data_max.memory,
        ),
    }
    return result

def best_tick(largest, most_ticks):
    """
    Compute a pretty tick value. Adapted from:
    https://stackoverflow.com/questions/361681/algorithm-for-nice-grid-line-intervals-on-a-graph

    """
    minimum = largest / most_ticks
    magnitude = 10 ** math.floor(math.log(minimum, 10))
    residual = minimum / magnitude
    if residual > 5:
        tick = 10 * magnitude
    elif residual > 2:
        tick = 5 * magnitude
    elif residual > 1:
        tick = 2 * magnitude
    else:
        tick = magnitude
    return tick

def axis_bound(value):
    pass


def pt_from_cr_data(call_return_data, offsets_scales):
    """
    Returns a ``Coord.Pt()`` from a ``CallReturnData`` object.

    :param call_return_data: CallReturnData naed tuple.
    :type call_return_data: ``pymemtrace.CallReturnData``

    :param offsets_scales: Offset and scale for the two axis.
        ``offsets_scales`` comes from ``compute_offsets_scales()``.
    :type offsets_scales: ``{field : Coord.OffsetScale`` with keys ``'time'`` and ``'memory'``.

    :return: ``Coord.Pt()``
    """
    pt = Coord.Pt(
        Coord.dim_from_offset_scale(call_return_data.memory, offsets_scales['memory']),
        Coord.dim_from_offset_scale(call_return_data.time, offsets_scales['time']),
    )
    return pt

def plot_axes(memtrace, svgS, offsets_scales):
    """Plots both memory and time axes."""
    xy_min = pt_from_cr_data(memtrace.data_min, offsets_scales)
    xy_max = pt_from_cr_data(memtrace.data_max, offsets_scales)
    # Memory axis
    with SVGWriter.SVGLine(
            svgS,
            Coord.Pt(xy_min.x, xy_min.y),
            Coord.Pt(xy_max.x, xy_min.y),
            {'stroke-width' : "5", 'stroke' : 'red'}
        ):
        pass
    # Memory axis
    with SVGWriter.SVGLine(
            svgS,
            Coord.Pt(xy_min.x, xy_min.y),
            Coord.Pt(xy_min.x, xy_max.y),
            {'stroke-width' : "5", 'stroke' : 'green'}
        ):
        pass
    # TODO: Axis text, axis tick marks, gridlines.

def _plot_depth_generator(gen, wdefd, offsets_scales, svgS):
    """
    :param gen: A generator of WidthDepthEventFunctionData events.

    :param wdefd: The current WidthDepthEventFunctionData event.
    :type wdefd: A ``WidthDepthEventFunctionData(width, depth, event, function_id, data)`` object.

    :param offsets_scales: Offset and scale for the two axis.
    :type offsets_scales: ``{field : Coord.OffsetScale`` with keys ``'time'`` and ``'memory'``.

    :param svgS: The SVG stream.
    :type svgS: ``SVGWriter.SVGWriter``

    :return: The outstanding ``WidthDepthEventFunctionData(width, depth, event, function_id, data)`` event.
    """
#     print('TRACE: 0', wdefd)
    wdefd_call = wdefd
    assert wdefd.event == 'call'
    ptS = [pt_from_cr_data(wdefd.data, offsets_scales),]
    while True:
        wdefd = next(gen)
#         print('TRACE: 1', wdefd)
        if wdefd.event == 'call':
            ptS.append(pt_from_cr_data(wdefd.data, offsets_scales))
            wdefd = _plot_depth_generator(gen, wdefd, offsets_scales, svgS)
            ptS.append(pt_from_cr_data(wdefd.data, offsets_scales))
        elif wdefd.event == 'return':
            ptS.append(pt_from_cr_data(wdefd.data, offsets_scales))
            break
        else:
            assert 0
    # Make a synthetic point with return time and call memory
    synth_point = pymemtrace.CallReturnData(wdefd.data.time, wdefd_call.data.memory)
    ptS.append(pt_from_cr_data(synth_point, offsets_scales))
    svgS.comment('_plot_depth_generator(): {!r:s}'.format(wdefd_call), newLine=True)
    polyline_attrs = {
        'fill' : "none",
        'stroke' : "black",
        'stroke-width' : "1",
    }
    # Close the polygon
    ptS.append(ptS[0])
    with SVGWriter.SVGPolyline(svgS, ptS, polyline_attrs):
        pass
    return wdefd

def plot_history(memtrace, svgS, offsets_scales):
    """Plots all the history gathered by MemTrace."""
    try:
        gen = memtrace.function_tree_seq.gen_depth_first()
        _plot_depth_generator(gen, next(gen), offsets_scales, svgS)
    except StopIteration:
        pass

def plot_memtrace_to_path(memtrace, file_path):
    """Plots a pymemtrace.MemTrace object in SVG to the ``file_path``."""
    with open(file_path, 'w') as fobj:
        plot_memtrace_to_file(memtrace, fobj)

def plot_memtrace_to_file(memtrace, fobj):
    """Plots a pymemtrace.MemTrace object in SVG to the file like object ``fobj``."""
    viewport = get_viewport()
    root_attrs = {
        'viewBox' : "0 0 {!s:s} {!s:s}".format(viewport.width.value, viewport.depth.value)
    }
    with SVGWriter.SVGWriter(fobj, viewport, root_attrs) as svgS:
        plot_offsets_scales = compute_offsets_scales(
            viewport, plot_margins(), memtrace.data_min, memtrace.data_max
        )
        # pprint.pprint(plot_offsets_scales)
        # Plot axes
        plot_axes(memtrace, svgS, plot_offsets_scales)
        # Plot functions
        plot_history(memtrace, svgS, plot_offsets_scales)
