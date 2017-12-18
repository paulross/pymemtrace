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
from pymemtrace.plot import Coord
from pymemtrace.plot import SVGWriter
from pymemtrace.plot import XmlWrite

MARGINS_ABS = {
    'top'       : Coord.Dim(8, 'mm'),
    'bottom'    : Coord.Dim(8, 'mm'),
    'left'      : Coord.Dim(8, 'mm'),
    'right'     : Coord.Dim(8, 'mm'),
}

MARGIN_KEYS = tuple(MARGINS_ABS.keys())
MARGIN_AXIS = Coord.Dim(8, 'mm') # Allow for axis text as well
MARGIN_FROM_AXIS = Coord.Dim(4, 'mm')

def get_viewport():
    view_port = Coord.Box(
        Coord.Dim(200, 'mm'), # .width, x, to right
        Coord.Dim(400, 'mm'), # .depth, y, down.
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


def pt_from_time_and_memory(offsets_scales, tim, mem):
    """
    Returns a Cooord.Pt() from time ``tim`` and memory ``mem`` using a dict of
    Coord.OffsetScale objects for each axis.

    ``offsets_scales`` comes from ``compute_offsets_scales()``.
    """
    pt = Coord.Pt(
        Coord.dim_from_offset_scale(mem, offsets_scales['memory']),
        Coord.dim_from_offset_scale(tim, offsets_scales['time']),
    )
    return pt

def plot_axes(memtrace, svgS, offsets_scales):
    """Plots both memory and time axes."""
    xy_min = pt_from_time_and_memory(
        offsets_scales,
        memtrace.data_min.time,
        memtrace.data_min.memory
    )
    xy_max = pt_from_time_and_memory(
        offsets_scales,
        memtrace.data_max.time,
        memtrace.data_max.memory
    )
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
    svgS.comment('_plot_depth_generator(): Entry {!r:s}'.format(wdefd), newLine=True)
    assert wdefd.event == 'call'
    ptS = []
    while True:
        pt_call = pt_from_time_and_memory(offsets_scales, wdefd.data.time, wdefd.data.memory)
        ptS.append(pt_call)
        wdefd = next(gen)
        if wdefd.event == 'call':
            wdefd = _plot_depth_generator(gen, wdefd, offsets_scales, svgS)
        elif wdefd.event == 'return':
            break
        else:
            assert 0

    with SVGWriter.SVGPolyline(svgS, ptS):
        pass
    svgS.comment('_plot_depth_generator():  Exit {!r:s}'.format(wdefd), newLine=True)
    return wdefd


def plot_history(memtrace, svgS, offsets_scales):
    """Plots all the history gathered by MemTrace."""
    try:
        gen = memtrace.function_tree_seq.gen_width_first()
        _plot_depth_generator(gen, next(gen), offsets_scales, svgS)
    except StopIteration:
        pass
    # for wdefd in memtrace.function_tree_seq.gen_width_first():
    #     # wdefd is a named tuple:
    #     # WidthDepthEventFunctionData(width, depth, event, function_id, data)
    #     #
    #     # function_id can be decoded with:
    #     # memtrace.decode_function_id(function_id) which returns a named tuple:
    #     # FunctionLocation(filename, function, lineno)
    #     #
    #     # data is a named tuple:
    #     # CallReturnData(time, memory)
    #     pt = pt_from_time_and_memory(offsets_scales, wdefd.data.time, wdefd.data.memory)
    #     if wdefd.event == 'return':
    #         assert event_prev == 'call'
    #         box = Coord.Box(pt.x - pt_prev.x, pt.y - pt_prev.y)
    #         with SVGWriter.SVGRect(svgS, pt_prev, box):
    #             pass
    #     pt_prev = pt
    #     event_prev = wdefd.event

def plot_memtrace_to_path(memtrace, file_path):
    """Plots a pymemtrace.MemTrace object in SVG to the ``file_path``."""
    with open(file_path, 'w') as fobj:
        plot_memtrace_to_file(memtrace, fobj)

def plot_memtrace_to_file(memtrace, fobj):
    """Plots a pymemtrace.MemTrace object in SVG to the file like object ``fobj``."""
    viewport = get_viewport()
    with SVGWriter.SVGWriter(fobj, viewport) as svgS:
        plot_offsets_scales = compute_offsets_scales(
            viewport, plot_margins(), memtrace.data_min, memtrace.data_max
        )
        # pprint.pprint(plot_offsets_scales)
        # Plot axes
        plot_axes(memtrace, svgS, plot_offsets_scales)
        # Plot functions
        plot_history(memtrace, svgS, plot_offsets_scales)
