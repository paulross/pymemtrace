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
import logging
# import math
# import pprint

from pymemtrace import data
try:
    from pymemtrace.plot import Coord
    from pymemtrace.plot import SVGWriter
    from pymemtrace.plot import XmlWrite
except ImportError:
    from . import Coord, SVGWriter, XmlWrite

def compute_offsets_scales(viewport, margins, data_min, data_max):
    """
    Returns a dict of Coord.OffsetScale for keys 'time' and 'memory' from the
    data in the MemTrace object. ``margins`` is a dict of margins:
    ``{position : Coord.Dim(), ...}`` where ``position`` is 'top', 'bottom',
    'left', 'right'.
    """
    time_max = data_max.time
    if data_min.time == data_max.time:
        time_max = data_min.time + 1.0
    memory_max = data_max.memory
    if data_min.memory == data_max.memory:
        memory_max = data_min.memory + 1024
    result = {
        # coord_min, coord_max, value_min, value_max
        'time' : Coord.offset_scale(
            margins['top'],
            viewport.depth - margins['bottom'],
            data_min.time,
            time_max,
        ),
        'memory' : Coord.offset_scale(
            margins['left'],
            viewport.width - margins['right'],
            data_min.memory,
            memory_max,
        ),
    }
    logging.info('compute_offsets_scales():')
    logging.info('Time: {:3f} to {:3f} Diff: {:3f}'.format(
        data_min.time, time_max, time_max - data_min.time
    ))
    logging.info(' Mem: {:,d} to {:,d} Diff: {:,d}'.format(
        data_min.memory, memory_max, memory_max - data_min.memory
    ))
    return result

class PlotMemTrace:
    """
    This handles the plotting of a pymemtrace.MemTrace object.
    """
    #: Default SVG plot units
    DEFAULT_PLOT_UNITS = 'in'
    #: Number of pixels per standard plot unit.
    #: We have to plot polyline in this view box units rather than actual
    #: absolute values.
    VIEW_BOX_UNITS_PER_PLOT_UNITS = 96.0
    MARGINS_ABS = {
        'top'       : Coord.Dim(0.3, DEFAULT_PLOT_UNITS),
        'bottom'    : Coord.Dim(0.3, DEFAULT_PLOT_UNITS),
        'left'      : Coord.Dim(0.3, DEFAULT_PLOT_UNITS),
        'right'     : Coord.Dim(1.3, DEFAULT_PLOT_UNITS),
    }
    MARGIN_KEYS = tuple(MARGINS_ABS.keys())
    # MARGIN_AXIS = Coord.Dim(8, 'mm').convert(None) # Allow for axis text as well
    # MARGIN_FROM_AXIS = Coord.Dim(4, 'mm').convert(None)
    MARGIN_AXIS = Coord.Dim(0.3, DEFAULT_PLOT_UNITS) # Allow for axis text as well
    MARGIN_FROM_AXIS = Coord.Dim(0.3, DEFAULT_PLOT_UNITS)
    SVG_CANVAS = Coord.Box(
        Coord.Dim(12, DEFAULT_PLOT_UNITS), # .width, x, to right
        Coord.Dim(24, DEFAULT_PLOT_UNITS), # .depth, y, down.
    )
    def __init__(self,
                 function_encoder,
                 function_tree_seq,
                 data_min,
                 data_max,
                 fobj,
                 canvas=None):
        """
        Plots data in SVG to the file like object ``fobj``.
        """
        PlotMemTrace.PLOT_MARGINS = {
            k : (PlotMemTrace.MARGINS_ABS[k] + PlotMemTrace.MARGIN_AXIS + PlotMemTrace.MARGIN_FROM_AXIS)
                for k in PlotMemTrace.MARGINS_ABS
        }
        self.function_encoder = function_encoder
        self.function_tree_seq = function_tree_seq
        self.fobj = fobj
        canvas = canvas or self.SVG_CANVAS
        self.plot_offsets_scales = compute_offsets_scales(
            canvas, self.PLOT_MARGINS, data_min, data_max
        )
        # This offset is used when presenting data in pop-ups
        # Time is shown from trace start, memory is shown as is.
        self.data_text_offset = data.CallReturnData(data_min.time, 0)
        # Auto increment for the id="..." for the function data.
        # See _write_data_hover_points_SVG()
        self.data_function_id = 0
        # Auto increment for the id="..." for the time/memory onhover data points.
        # See _write_data_hover_points_SVG()
        self.data_hover_id = 0
        # Statistics on functions written
        self.function_counter = collections.Counter()
        # Write SVG
        root_attrs = {
            'viewBox' : "0 0 {:f} {:f}".format(canvas.width.value * PlotMemTrace.VIEW_BOX_UNITS_PER_PLOT_UNITS,
                                               canvas.depth.value * PlotMemTrace.VIEW_BOX_UNITS_PER_PLOT_UNITS)
        }
        with SVGWriter.SVGWriter(fobj, canvas, root_attrs) as svgS:
#             self._writeECMAScript(svgS)
            self.plot_axes(data_min, data_max, svgS)
            self.plot_history(svgS)

    def plot_axes(self, data_min, data_max, svgS):
        """Plots both memory and time axes."""
        xy_min = self.pt_from_cr_data(data_min, is_abs_units=True)
        xy_max = self.pt_from_cr_data(data_max, is_abs_units=True)
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


    def _plot_depth_generator(self, gen, wdefd, svgS, data_hover_ptS):
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
        wdefd_call = wdefd
        assert wdefd.event == 'call'
        function_id = wdefd.function_id
        # A list of CallReturnData()
        function_wdefS = [wdefd.data]
        data_hover_ptS.append(wdefd.data)
        # TODO: Asserts about depth of event, function_id and so on.
        try:
            while True:
                wdefd = next(gen)
                # print('TRACE: _plot_depth_generator(): wdefd', wdefd)
                assert wdefd.event in ('call', 'return')
                if wdefd.event == 'call':
                    function_wdefS.append(wdefd.data)
                    wdefd = self._plot_depth_generator(gen, wdefd, svgS, data_hover_ptS)
                    if wdefd.data.memory > function_wdefS[-1].memory:
                        # Add synthetic point
                        synth_point = data.CallReturnData(wdefd.data.time, function_wdefS[-1].memory)
                        function_wdefS.append(synth_point)
                    function_wdefS.append(wdefd.data)
                else:
                    function_wdefS.append(wdefd.data)
                    data_hover_ptS.append(wdefd.data)
                    break
        finally:
            # Make a synthetic point with return time and call memory
            synth_point = data.CallReturnData(wdefd.data.time, wdefd_call.data.memory)
            function_wdefS.append(synth_point)
            data_hover_ptS.append(synth_point)
            self._write_function_SVG(wdefd_call, function_id, function_wdefS, svgS)
        return wdefd

    def plot_history(self, svgS):
        """Plots all the history gathered by MemTrace."""
        # The data points that are used to provide time/memory pop-up information.
        # There should be no duplicates with child functions.
        # A list of CallReturnData()
        data_hover_ptS = []
        try:
            gen = self.function_tree_seq.gen_depth_first()
            while True:
                self._plot_depth_generator(gen, next(gen), svgS, data_hover_ptS)
        except StopIteration:
            pass
        self._write_data_hover_points_SVG(data_hover_ptS, svgS)

    def pt_from_cr_data(self, call_return_data, is_abs_units):
        """
        Returns a ``Coord.Pt()`` from a ``CallReturnData`` object.

        :param call_return_data: CallReturnData named tuple.
        :type call_return_data: ``pymemtrace.CallReturnData``

        :param offsets_scales: Offset and scale for the two axis.
            ``offsets_scales`` comes from ``compute_offsets_scales()``.
        :type offsets_scales: ``{field : Coord.OffsetScale`` with keys ``'time'`` and ``'memory'``.

        :return: ``Coord.Pt()``
        """
        x = Coord.dim_from_offset_scale(call_return_data.memory,
                                        self.plot_offsets_scales['memory'])
        y = Coord.dim_from_offset_scale(call_return_data.time,
                                        self.plot_offsets_scales['time'])
        if not is_abs_units:
            x = x._replace(units=None)
            x *= PlotMemTrace.VIEW_BOX_UNITS_PER_PLOT_UNITS
            y = y._replace(units=None)
            y *= PlotMemTrace.VIEW_BOX_UNITS_PER_PLOT_UNITS
        return Coord.Pt(x, y)

    def _data_hover_new_id(self):
        result = 'data_pt_{:d}'.format(self.data_hover_id)
        self.data_hover_id += 1
        return result

    def _function_id_attr(self, function_id):
        result = 'fn_{:d}'.format(self.data_function_id)
        self.data_function_id += 1
        return result
#         return 'fn_{:d}'.format(function_id)

    def _write_function_SVG(self, wdefd_call, function_id, function_cr_data, svgS):
        """
        Writes the function as a polygon and its pop-up data.
        """
        assert len(function_cr_data) > 1
        # The points that make up the polygon of this function.
        # There will be duplicates with child functions at the boundaries.
        # A list of Coord.Pt()
        polygon_ptS = [self.pt_from_cr_data(cr_data, is_abs_units=False) for cr_data in function_cr_data]
        # Reduce the polygons points to eliminate points that are the same x/y
        distinct_polygon_ptS = polygon_ptS[:1]
        for point in polygon_ptS[1:]:
            if abs(point.x.value - distinct_polygon_ptS[-1].x.value) > 1 or abs(point.y.value - distinct_polygon_ptS[-1].y.value) > 1:
                distinct_polygon_ptS.append(point)
        # Ignore sub one pixel elements
        diff_x = max([p.x.value for p in distinct_polygon_ptS]) - min([p.x.value for p in distinct_polygon_ptS])
        diff_y = max([p.y.value for p in distinct_polygon_ptS]) - min([p.y.value for p in distinct_polygon_ptS])
        diff_min = 2
        if diff_x > diff_min and diff_y > diff_min:
            logging.info(
                '_write_function_SVG() dx={:6.1f} dy={:6.1f}  writing: {!s:s} {!s:s}'.format(
                    diff_x, diff_y, self.function_encoder.decode(function_id), function_cr_data[-1] - function_cr_data[0]
                )
            )
            # print('TRACE: function_cr_data: {!s:s}'.format(function_cr_data[-1] - function_cr_data[0]))
            # pprint.pprint(function_cr_data)
            svgS.comment(
                ' _write_function_SVG(): {!r:s} {!r:s} '.format(
                    wdefd_call,
                    self.function_encoder.decode(function_id),
                ),
                newLine=True
            )
            func_id_attr = self._function_id_attr(function_id)
            polygon_attrs = {
                'fill' : "white", # Need a fill for the mouseover to work
                'stroke' : "black",
                'stroke-width' : "1",
                'id' : func_id_attr
            }
            with SVGWriter.SVGPolygon(svgS, distinct_polygon_ptS, polygon_attrs):
                pass
            self._write_function_popup_SVG(function_id, func_id_attr, function_cr_data, svgS)
            self.function_counter.update(Written=1)
        else:
            logging.info(
                '_write_function_SVG() dx={:6.1f} dy={:6.1f} ignoring: {!s:s}'.format(
                    diff_x, diff_y, self.function_encoder.decode(function_id)
                )
            )
            self.function_counter.update(Ignored=1)
            # pprint.pprint(function_cr_data)

    def _write_function_popup_SVG(self, function_id, func_id_attr, function_cr_data, svgS):
        """
        Writes the pop-up box thus:

        .. code-block:: xml

            <g id="fn_0.alt" opacity="0.0">
                <rect fill="khaki" height="48pt" width="250" x="215" y="300" />
                <text font-family="Courier" font-size="10" font-weight="normal" x="220" y="310">
                    <tspan>File: ../../demo/src/main.cpp#421 </tspan>
                    <tspan dy="1.5em" x="220">Function: get_something</tspan>
                    <tspan dy="1.5em" x="220">Time: 1.23456 to 1.56780 (s)</tspan>
                    <tspan dy="1.5em" x="220">Memory: min 234.123, max 598.454 (kb) </tspan>
                </text>
                <set attributeName="opacity" from="0.0" to="1.0"
                    begin="fn_0.mouseover" end="fn_0.mouseout" />
            </g>
        """
        assert len(function_cr_data) > 2
        svgS.comment(' _write_function_popup_SVG(): {:d} '.format(function_id), newLine=True)
        # Where to pop-up
        memory_min = min([d.memory for d in function_cr_data])
        memory_max = max([d.memory for d in function_cr_data])
        time_min = min([d.time for d in function_cr_data])
        time_max = max([d.time for d in function_cr_data])
        data_min = data.CallReturnData(time=time_min, memory=memory_min)
        data_max = data.CallReturnData(time=time_max, memory=memory_max)
        mid_data = data.CallReturnData(
            time=time_min + (time_max - time_min) / 2.0,
            memory=memory_min + (memory_max - memory_min) / 2.0,
        )
        mid_pt = self.pt_from_cr_data(mid_data, is_abs_units=False)
        # named tuple: FunctionLocation(filename, function, lineno)
        fn_location = self.function_encoder.decode(function_id)
        # Text strings
        textS = [
            'File: {:s}#{:d}'.format(fn_location.filename, fn_location.lineno),
            'Function: {:s}()'.format(fn_location.function),
            '    Call: {!s:s}'.format(function_cr_data[0] - self.data_text_offset),
            '  Return: {!s:s}'.format(function_cr_data[-2] - self.data_text_offset), # [-1] is synthetic
            '    Diff: {!s:s}'.format(function_cr_data[-2] - function_cr_data[0]),
#             'Time range: {:s} to {:s}'.format(data_min.str_pair()[0], data_max.str_pair()[0]),
#             'Memory range: {:s} to {:s}'.format(data_min.str_pair()[1], data_max.str_pair()[1]),
        ]
        len_max = max([len(t) for t in textS])
        with SVGWriter.SVGGroup(svgS, {'opacity' : '0.0'}):
            # <rect fill="khaki" height="48pt" width="250" x="215" y="300" />
            # rect
            box = Coord.Box(
                Coord.Dim(12 * len_max / 2, 'pt'),
                Coord.Dim(12 * len(textS), 'pt')
            )
            with SVGWriter.SVGRect(svgS, mid_pt, box, {'fill' : 'khaki'}):
                pass
            # text
            text_pt = Coord.newPt(mid_pt, incX=Coord.Dim(10, None), incY=Coord.Dim(10, None))
            with SVGWriter.SVGText(svgS, text_pt,
                                   'Courier', 10,
                                   {'font-weight' : 'normal'}):
                # tspan
                tspan_attrs = {}
                for text in textS:
                    with XmlWrite.Element(svgS, 'tspan', tspan_attrs):
                        svgS.characters(text)
                    tspan_attrs = {
                        'dy' : "1.5em",
                        'x' : SVGWriter.dimToTxt(text_pt.x),
                    }
            # set
#             fn_id = self._function_id_attr(function_id)
            set_attrs = {
                'attributeName' : 'opacity',
                'from' : '0.0',
                'to' : '1.0',
                'begin' : '{:s}.mouseover'.format(func_id_attr),
                'end' : '{:s}.mouseout'.format(func_id_attr),
            }
            with XmlWrite.Element(svgS, 'set', set_attrs):
                pass

    def _write_data_hover_points_SVG(self, data_hover_ptS, svgS):
        """Write some invisible circles at the list of CallReturnData points with
        a hover pop-up giving the time and memory. There are three components:
        and invisible circle that captures the mouseover/mouse out events, a small
        visible circle that hints that data is here and lastly a rect/text with the
        pop-up data in a group.

        .. code-block:: xml

            <circle id="data_pt_0" cx="600" cy="500" r="10" opacity="0.0" />
            <circle cx="600" cy="500" r="4" fill="red" />
            <g opacity="0.0">
                <rect fill="aliceblue" height="12pt" width="250" x="600" y="500" />
                <text font-family="Courier" font-size="10" font-weight="normal"
                    x="610" y="510">
                    <tspan>1.234 (s) 598.454 (kb)</tspan>
                </text>
                <set attributeName="opacity" from="0.0" to="1.0"
                    begin="data_pt_0.mouseover" end="data_pt_0.mouseout" />
            </g>
        """
        svgS.comment(' _write_data_hover_points_SVG(): ', newLine=True)
        old_pt = None
        for data_point in data_hover_ptS:
            pt_id = self._data_hover_new_id()
#             print('TRACE:', data_point)
            pt = self.pt_from_cr_data(data_point, is_abs_units=False)
            if old_pt is not None and abs(pt.x.value - old_pt.x.value) < 4 and abs(pt.y.value - old_pt.y.value) < 4:
                continue
            old_pt = pt
#             print('TRACE:', pt)
            # Larger, invisible, onhover circle:
            # <circle id="data_pt_0" cx="600" cy="500" r="10" opacity="0.0" />
            rad = Coord.Dim(20, None)
            with SVGWriter.SVGCircle(svgS, pt, rad,
                                     {'id' : pt_id, 'opacity' : '0.0'}):
                pass
#             # Small, visible circle: <circle cx="600" cy="500" r="4" fill="red" />
#             rad = Coord.Dim(4, None)
#             with SVGWriter.SVGCircle(svgS, pt, rad, {'fill' : 'red'}):
#                 pass
            text = str(data_point - self.data_text_offset)
            with SVGWriter.SVGGroup(svgS, {'opacity' : '0.0'}):
                # rect
                box = Coord.Box(
                    Coord.Dim(12 * len(text) / 2, 'pt'),
                    Coord.Dim(12, 'pt')
                )
                with SVGWriter.SVGRect(svgS, pt, box, {'fill' : 'aliceblue'}):
                    pass
                # text
                text_pt = Coord.newPt(pt, incX=Coord.Dim(10, None), incY=Coord.Dim(10, None))
                with SVGWriter.SVGText(svgS, text_pt,
                                       'Courier', 10,
                                       {'font-weight' : 'normal'}):
                    # tspan
                    with XmlWrite.Element(svgS, 'tspan', {}):
                        svgS.characters(text)
                # set
                set_attrs = {
                    'attributeName' : 'opacity',
                    'from' : '0.0',
                    'to' : '1.0',
                    'begin' : '{:s}.mouseover'.format(pt_id),
                    'end' : '{:s}.mouseout'.format(pt_id),
                }
                with XmlWrite.Element(svgS, 'set', set_attrs):
                    pass
            # End group: </g>

# def best_tick(largest, most_ticks):
#     """
#     Compute a pretty tick value. Adapted from:
#     https://stackoverflow.com/questions/361681/algorithm-for-nice-grid-line-intervals-on-a-graph
#
#     """
#     minimum = largest / most_ticks
#     magnitude = 10 ** math.floor(math.log(minimum, 10))
#     residual = minimum / magnitude
#     if residual > 5:
#         tick = 10 * magnitude
#     elif residual > 2:
#         tick = 5 * magnitude
#     elif residual > 1:
#         tick = 2 * magnitude
#     else:
#         tick = magnitude
#     return tick

def plot_memtrace_to_file(memtrace, fobj):
    """Plots a pymemtrace.MemTrace object in SVG to the file like object ``fobj``."""
    pmt = PlotMemTrace(
        memtrace.function_encoder,
        memtrace.function_tree_seq,
        memtrace.data_min,
        memtrace.data_max,
        fobj,
        canvas=None,
    )
    return pmt

def plot_memtrace_to_path(memtrace, file_path):
    """Plots a pymemtrace.MemTrace object in SVG to the ``file_path``."""
    with open(file_path, 'w') as fobj:
        return plot_memtrace_to_file(memtrace, fobj)
