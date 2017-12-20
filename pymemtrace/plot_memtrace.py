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
    'right'     : Coord.Dim(0.3, DEFAULT_PLOT_UNITS),
}

MARGIN_KEYS = tuple(MARGINS_ABS.keys())
# MARGIN_AXIS = Coord.Dim(8, 'mm').convert(None) # Allow for axis text as well
# MARGIN_FROM_AXIS = Coord.Dim(4, 'mm').convert(None)
MARGIN_AXIS = Coord.Dim(0.3, DEFAULT_PLOT_UNITS) # Allow for axis text as well
MARGIN_FROM_AXIS = Coord.Dim(0.3, DEFAULT_PLOT_UNITS)

SVG_CANVAS = Coord.Box(
    Coord.Dim(8, DEFAULT_PLOT_UNITS), # .width, x, to right
    Coord.Dim(12, DEFAULT_PLOT_UNITS), # .depth, y, down.
)

# def get_viewport():
# #     view_port = Coord.Box(
# #         Coord.Dim(200, 'mm').convert(None), # .width, x, to right
# #         Coord.Dim(400, 'mm').convert(None), # .depth, y, down.
# #     )
#     view_port = Coord.Box(
#         Coord.Dim(8, DEFAULT_PLOT_UNITS), # .width, x, to right
#         Coord.Dim(12, DEFAULT_PLOT_UNITS), # .depth, y, down.
#     )
#     return view_port

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


def pt_from_cr_data(call_return_data, offsets_scales, is_abs_units):
    """
    Returns a ``Coord.Pt()`` from a ``CallReturnData`` object.

    :param call_return_data: CallReturnData naed tuple.
    :type call_return_data: ``pymemtrace.CallReturnData``

    :param offsets_scales: Offset and scale for the two axis.
        ``offsets_scales`` comes from ``compute_offsets_scales()``.
    :type offsets_scales: ``{field : Coord.OffsetScale`` with keys ``'time'`` and ``'memory'``.

    :return: ``Coord.Pt()``
    """
#     if is_abs_units:
#         pt = Coord.Pt(
#             Coord.dim_from_offset_scale(call_return_data.memory, offsets_scales['memory']),
#             Coord.dim_from_offset_scale(call_return_data.time, offsets_scales['time']),
#         )
#     else:
#         pt = Coord.Pt(
#             Coord.dim_from_offset_scale(call_return_data.memory, offsets_scales['memory']) * VIEW_BOX_UNITS_PER_PLOT_UNITS,
#             Coord.dim_from_offset_scale(call_return_data.time, offsets_scales['time']) * VIEW_BOX_UNITS_PER_PLOT_UNITS,
#         )
#     return pt
    x = Coord.dim_from_offset_scale(call_return_data.memory, offsets_scales['memory'])
    y = Coord.dim_from_offset_scale(call_return_data.time, offsets_scales['time'])
    if not is_abs_units:
        x._replace(units=None)
        x *= VIEW_BOX_UNITS_PER_PLOT_UNITS
        y._replace(units=None)
        y *= VIEW_BOX_UNITS_PER_PLOT_UNITS
    return Coord.Pt(x, y)

def plot_axes(memtrace, svgS, offsets_scales):
    """Plots both memory and time axes."""
    xy_min = pt_from_cr_data(memtrace.data_min, offsets_scales, is_abs_units=True)
    xy_max = pt_from_cr_data(memtrace.data_max, offsets_scales, is_abs_units=True)
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

def _write_popup_text(theSvg, thePointX, theList):
    # Write a grouping element and give it the alternate ID
    with SVGWriter.SVGGroup(theSvg, {'id' : 't%s%s' % (theId, self.ALT_ID_SUFFIX), 'opacity' : '0.0'}):
        altFontSize = self.ALT_FONT_PROPERTIES[self.ALT_FONT_FAMILY]['size']
        altFontLenFactor = self.ALT_FONT_PROPERTIES[self.ALT_FONT_FAMILY]['lenFactor']
        altFontHeightFactor = self.ALT_FONT_PROPERTIES[self.ALT_FONT_FAMILY]['heightFactor']
        # Compute masking box for alternate
        maxChars = max([len(s) for s in theAltS])
        # Take around 80% of character length
        boxWidth = Coord.Dim(altFontSize * maxChars * altFontLenFactor, 'pt')
        if len(theAltS) < 2:
            boxHeight = Coord.Dim(altFontSize * 2, 'pt')
        else:
            boxHeight = Coord.Dim(altFontSize * len(theAltS) * altFontHeightFactor, 'pt')
            
        boxAttrs = { 'fill' : self.ALT_RECT_FILL }
        with SVGWriter.SVGRect(
                theSvg,
                theAltPt,
                Coord.Box(boxWidth, boxHeight),
                boxAttrs,
            ):
            pass
        # As the main text is centered and the alt text is left
        # justified we need to move the text plot point left by a bit.
        myAltTextPt = Coord.newPt(
            theAltPt,
            incX=Coord.Dim(1 * altFontSize * 3 * altFontLenFactor / 2.0, 'pt'),
            incY=Coord.Dim(12, 'pt'),
        )
        with SVGWriter.SVGText(theSvg, myAltTextPt, 'Courier', altFontSize,
                    {
                        'font-weight'       : "normal",
                    }
                ):
            for i, aLine in enumerate(theList):
                elemAttrs = {}#'xml:space' : "preserve"}
                if i > 0:
                    elemAttrs['x'] = SVGWriter.dimToTxt(thePointX.x) 
                    elemAttrs['dy'] = "1.5em"
                with XmlWrite.Element(theSvg, 'tspan', elemAttrs):
                    theSvg.characters(aLine)
                    theSvg.characters(' ')
    # Add the trigger rectangle for writing on finalise
    boxAttrs = {
        'class' : self.CLASS_RECT_INVIS,
        'id'                : 't%s' % theId,
        'onmouseover'       : "swapOpacity('t%s', 't%s')" \
                    % (theId, theId+self.ALT_ID_SUFFIX),
        'onmouseout'        : "swapOpacity('t%s', 't%s')" \
                    % (theId, theId+self.ALT_ID_SUFFIX),
    }
    self._triggerS.append((theTrigPt, theTrigRect, boxAttrs))

def _write_data_hover_points(data_hover_ptS, offsets_scales):
    """Write some invisible circles at the list of CallReturnData points with
    a hover pop-up giving the time and memory. There are three components,
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
                <tspan>
                    1.234 (s) 598.454 (kb) 
                </tspan>
            </text>
            <set attributeName="opacity" from="0.0" to="1.0"
                begin="data_pt_0.mouseover" end="data_pt_0.mouseout" /> 
        </g>
    """
    circle_attrs = {
    }
    for data_point in data_hover_ptS:
        pass


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
    wdefd_call = wdefd
    assert wdefd.event == 'call'
    # The points that make up the polygon of this function.
    # There will be duplicates with child functions at the boundaries.
    # A list of Coord.Pt()
    polygon_ptS = [pt_from_cr_data(wdefd.data, offsets_scales, is_abs_units=False),]
    # The data points that are used to provide time/memory pop-up information.
    # There should be no duplicates with child functions.
    # A list of CallReturnData()
    data_hover_ptS = [wdefd.data] 
    while True:
        wdefd = next(gen)
        assert wdefd.event in ('call', 'return')
        if wdefd.event == 'call':
            polygon_ptS.append(pt_from_cr_data(wdefd.data, offsets_scales, is_abs_units=False))
            wdefd = _plot_depth_generator(gen, wdefd, offsets_scales, svgS)
            polygon_ptS.append(pt_from_cr_data(wdefd.data, offsets_scales, is_abs_units=False))
        else:
            polygon_ptS.append(pt_from_cr_data(wdefd.data, offsets_scales, is_abs_units=False))
            date_hover_ptS.append(wdefd.data)
            break
    # Make a synthetic point with return time and call memory
    synth_point = pymemtrace.CallReturnData(wdefd.data.time, wdefd_call.data.memory)
    polygon_ptS.append(pt_from_cr_data(synth_point, offsets_scales, is_abs_units=False))
    date_hover_ptS.append(synth_point)
    svgS.comment('_plot_depth_generator(): {!r:s}'.format(wdefd_call), newLine=False)
    polyline_attrs = {
        'fill' : "none",
        'stroke' : "black",
        'stroke-width' : "1",
        'id' : 'fn_{:d}'.format(wdefd_call.function_id)
    }
    with SVGWriter.SVGPolygon(svgS, polygon_ptS, polyline_attrs):
        pass
    _write_data_hover_points(data_hover_ptS, offsets_scales)
    return wdefd

def plot_history(memtrace, svgS, offsets_scales):
    """Plots all the history gathered by MemTrace."""
    try:
        gen = memtrace.function_tree_seq.gen_depth_first()
        _plot_depth_generator(gen, next(gen), offsets_scales, svgS)
    except StopIteration:
        pass

def _writeECMAScript(svgS):
    myScripts = """
function swapOpacity(idFrom, idTo) {
    var svgFrom = document.getElementById(idFrom);
    var svgTo = document.getElementById(idTo);
    var attrFrom = svgFrom.getAttribute("opacity");
    var attrTo = svgTo.getAttribute("opacity");
    svgTo.setAttributeNS(null, "opacity", attrFrom);
    svgFrom.setAttributeNS(null, "opacity", attrTo);
}
function setOpacity(id, value) {
    var svgElem = document.getElementById(id);
    svgElem.setAttributeNS(null, "opacity", value);
}
"""
    svgS.writeECMAScript(myScripts)

def plot_memtrace_to_file(memtrace, fobj):
    """Plots a pymemtrace.MemTrace object in SVG to the file like object ``fobj``."""
    root_attrs = {
        'viewBox' : "0 0 {:f} {:f}".format(SVG_CANVAS.width.value * VIEW_BOX_UNITS_PER_PLOT_UNITS,
                                           SVG_CANVAS.depth.value * VIEW_BOX_UNITS_PER_PLOT_UNITS)
    }
    with SVGWriter.SVGWriter(fobj, SVG_CANVAS, root_attrs) as svgS:
        plot_offsets_scales = compute_offsets_scales(
            SVG_CANVAS, plot_margins(), memtrace.data_min, memtrace.data_max
        )
        # pprint.pprint(plot_offsets_scales)
        _writeECMAScript(svgS)
        # Plot axes
        plot_axes(memtrace, svgS, plot_offsets_scales)
        # Plot functions
        plot_history(memtrace, svgS, plot_offsets_scales)

def plot_memtrace_to_path(memtrace, file_path):
    """Plots a pymemtrace.MemTrace object in SVG to the ``file_path``."""
    with open(file_path, 'w') as fobj:
        plot_memtrace_to_file(memtrace, fobj)
