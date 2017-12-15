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

def _viewport():
    view_port = Coord.Box(
        Coord.Dim(200, 'mm'), # .width, x, to right
        Coord.Dim(400, 'mm'), # .depth, y, down.
    )
    return view_port

def _plot_margins():
    """
    Returns a dict of margins for the main plot area.
    """
    return {k : (MARGINS_ABS[k] + MARGIN_AXIS + MARGIN_FROM_AXIS) for k in MARGIN_KEYS}

def _compute_offsets_scales(memtrace, viewport, margins):
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
            memtrace.date_min.time,
            memtrace.date_max.time,
        ),
        'memory' : Coord.offset_scale(
            margins['left'],
            viewport.width - margins['right'],
            memtrace.date_min.memory,
            memtrace.date_max.memory,
        ),
    }
    return result

def _pt_from_time_and_memory(offsets_scales, tim, mem):
    """
    Returns a Cooord.Pt() from time ``tim`` and memory ``mem`` using a dict of
    Coord.OffsetScale objects for each axis.
    
    ``offsets_scales`` comes from ``_compute_offsets_scales()``.
    """
    pt = Coord.Pt(
        Coord.dim_from_offset_scale(mem, offsets_scales['memory']),
        Coord.dim_from_offset_scale(tim, offsets_scales['time']),
    )
    return pt

def _plot_axes(memtrace, svgS, offsets_scales):
    """Plots both memory and time axes."""
    xy_min = _pt_from_time_and_memory(
        offsets_scales,
        memtrace.date_min.time,
        memtrace.date_min.memory
    )
    xy_max = _pt_from_time_and_memory(
        offsets_scales,
        memtrace.date_max.time,
        memtrace.date_max.memory
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

def _plot_history(memtrace, svgS, offsets_scales):
    """Plots all the history gathered by MemTrace."""
    pt_prev = None
    event_prev = None
    for wdefd in memtrace.function_tree_seq.gen_width_first():
        # wdefd is a named tuple:
        # WidthDepthEventFunctionData(width, depth, event, function_id, data)
        #
        # function_id can be decoded with:
        # memtrace.decode_function_id(function_id) which returns a named tuple:
        # FunctionLocation(filename, function, lineno)
        #
        # data is a named tuple:
        # CallReturnData(time, memory)
        pt = _pt_from_time_and_memory(offsets_scales, wdefd.data.time, wdefd.data.memory)
        if wdefd.event == 'return':
            assert wdefd.event == 'call'
            box = Coord.Box(pt.x - pt_prev.x, pt.y - pt_prev.y)
            with SVGWriter.SVGRect(svgS, pt_prev, box):
                pass
        pt_prev = pt
        event_prev = wdefd.event

def plot_memtrace_to_path(memtrace, file_path):
    """Plots a pymemtrace.MemTrace object in SVG to the ``file_path``."""
    with open(file_path, 'w') as fobj:
        plot_memtrace_to_file(memtrace, fobj)
        
def plot_memtrace_to_file(memtrace, fobj):
    """Plots a pymemtrace.MemTrace object in SVG to the file like object ``fobj``."""
    viewport = _viewport()
    with SVGWriter.SVGWriter(fobj, viewport) as svgS:
        plot_offsets_scales = _compute_offsets_scales(memtrace, viewport, _plot_margins())
        # Plot axes
        _plot_axes(memtrace, svgS, plot_offsets_scales)
        # Plot functions
        _plot_history(memtrace, svgS, plot_offsets_scales)
